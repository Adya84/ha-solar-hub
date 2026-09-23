"""Direct local GivEnergy Modbus provider."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from givenergy_modbus.client.client import Client

from ..models import HardwareProfile
from .base import SolarProvider


def _read(obj: Any, *names: str, default: Any = None) -> Any:
    if obj is None:
        return default
    for name in names:
        try:
            value = getattr(obj, name)
        except (AttributeError, TypeError, ValueError):
            continue
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if value is not None:
            return value
    return default


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.name
    name = getattr(value, "name", None)
    return str(name if name is not None else value)


def _metric(value: Any, unit: str | None = None) -> dict[str, Any]:
    return {"value": _plain(value), "unit": unit, "available": value is not None}


class GivEnergyProvider(SolarProvider):
    """Read a supported GivEnergy system directly from the LAN."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._client = Client(host=host, port=port)
        self._detected = False

    async def _ensure_ready(self) -> None:
        if not self._client.connected:
            await self._client.connect()
            self._detected = False
        if not self._detected:
            await self._client.detect()
            self._detected = True

    async def _refresh_plant(self) -> Any:
        await self._ensure_ready()
        return await self._client.refresh()

    async def async_scan(self) -> dict[str, Any]:
        return self._normalise(await self._refresh_plant())

    async def async_refresh(self) -> dict[str, Any]:
        return self._normalise(await self._refresh_plant())

    async def async_deep_scan(self, progress: Callable[[int, str], None] | None = None) -> dict[str, Any]:
        """Perform a deliberate, complete BMS pass outside the live refresh loop.

        The ordinary poll is intentionally lightweight.  This pass first fetches the
        inverter configuration blocks and then reads every detected battery's input
        register bank in sequence.  The battery bank contains the individual cell
        voltages and BMS health fields, so it may take a little while on a busy bus.
        """
        self._report_progress(progress, 5, "Connecting to inverter")
        await self._ensure_ready()
        self._report_progress(progress, 20, "Reading inverter configuration")
        # The inverter serialises Modbus traffic and GivTCP/PredBat may be polling
        # at the same time.  A patient timeout and short retry delay make this an
        # actual complete BMS pass without affecting normal live updates.
        warnings: list[str] = []
        try:
            await self._client.load_config(timeout=5.0, retries=1, retry_delay=0.75)
        except Exception as err:
            if getattr(err, "plant", None) is None:
                raise
            warnings.append("Some inverter configuration registers did not respond")
        self._report_progress(progress, 45, "Reading battery BMS registers")
        try:
            plant = await self._client.refresh(timeout=5.0, retries=1, retry_delay=0.75)
        except Exception as err:
            plant = getattr(err, "plant", None)
            if plant is None:
                raise
            warnings.append("Some BMS registers did not respond")
        self._report_progress(progress, 85, "Decoding cell voltages and battery health")
        snapshot = self._normalise(plant)
        batteries = list(_read(plant, "batteries", default=[]) or [])
        if not batteries:
            batteries = list(_read(plant, "aio_battery_modules", default=[]) or [])
        batteries = self._deep_battery_data(batteries)
        if not batteries or not any(item.get("cells") for item in batteries):
            raise RuntimeError("No battery cell readings were returned by the BMS")
        snapshot["system_profile"]["deep_data"] = {"batteries": batteries}
        snapshot["system_profile"]["deep_scan"] = {
            "state": "completed_with_warnings" if warnings else "completed",
            "progress": 100,
            "stage": "Complete with warnings" if warnings else "Complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": "; ".join(warnings) if warnings else None,
        }
        self._report_progress(progress, 100, "Complete")
        return snapshot

    async def async_set_control(self, key: str, value: Any) -> None:
        """Reject writes until a verified register mapping is available."""
        raise ValueError(f"Solar Hub cannot safely write '{key}' on this inverter yet")

    async def async_close(self) -> None:
        await self._client.close()
        self._detected = False

    @staticmethod
    def _deep_battery_data(batteries: list[Any]) -> list[dict[str, Any]]:
        """Return only battery fields genuinely provided by the BMS object."""
        details: list[dict[str, Any]] = []
        for index, battery in enumerate(batteries, start=1):
            detail: dict[str, Any] = {
                "index": index,
                "serial": _plain(_read(battery, "serial_number", "serial")),
            }
            for key, names in {
                "cycles": ("num_cycles",),
                "capacity_ah": ("cap_design", "cap_design2"),
                "capacity_remaining_ah": ("cap_remaining",),
                "temperature_min": ("t_min",),
                "temperature_max": ("t_max",),
                "bms_temperature": ("t_bms_mosfet",),
                "bms_firmware": ("bms_firmware_version",),
                "lifetime_charge_kwh": ("e_battery_charge_total",),
                "lifetime_discharge_kwh": ("e_battery_discharge_total",),
            }.items():
                value = _read(battery, *names)
                if value is not None:
                    detail[key] = _plain(value)
            cells = []
            cell_count = _read(battery, "num_cells") or 24
            for cell in range(1, int(cell_count) + 1):
                voltage = _read(battery, f"v_cell_{cell:02d}", f"v_cell_{cell}", f"cell_{cell}_voltage")
                if voltage is not None:
                    cells.append(
                        {
                            "index": cell,
                            "voltage": _plain(voltage),
                            "status": GivEnergyProvider._cell_voltage_status(voltage),
                        }
                    )
            if cells:
                detail["cells"] = cells
            details.append(detail)
        return details

    @staticmethod
    def _cell_voltage_status(voltage: Any) -> str:
        """Classify a LiFePO4 cell reading for the tablet dashboard.

        These are display-only alert bands, not a battery-management decision. The
        BMS remains the authority for protection and balancing.
        """
        try:
            value = float(voltage)
        except (TypeError, ValueError):
            return "unknown"
        if 3.10 <= value <= 3.50:
            return "good"
        if 3.00 <= value <= 3.60:
            return "warning"
        return "critical"

    @staticmethod
    def _report_progress(progress: Callable[[int, str], None] | None, percent: int, stage: str) -> None:
        if progress is not None:
            progress(percent, stage)

    def _normalise(self, plant: Any) -> dict[str, Any]:
        inverter = _read(plant, "gateway") or _read(plant, "inverter")
        batteries = list(_read(plant, "batteries", default=[]) or [])
        if not batteries:
            batteries = list(_read(plant, "aio_battery_modules", default=[]) or [])

        strings: list[dict[str, Any]] = []
        for index in range(1, 9):
            power = _read(inverter, f"p_pv{index}")
            voltage = _read(inverter, f"v_pv{index}")
            current = _read(inverter, f"i_pv{index}")
            if any(value is not None for value in (power, voltage, current)):
                strings.append(
                    {
                        "index": index,
                        "power": _metric(power, "W"),
                        "voltage": _metric(voltage, "V"),
                        "current": _metric(current, "A"),
                    }
                )

        solar_power = _read(inverter, "p_pv")
        if solar_power is None:
            watts = [
                item["power"]["value"]
                for item in strings
                if isinstance(item["power"]["value"], (int, float))
            ]
            solar_power = sum(watts) if watts else None

        battery_profiles: list[dict[str, Any]] = []
        battery_snapshots: list[dict[str, Any]] = []
        for index, battery in enumerate(batteries, start=1):
            serial = _plain(_read(battery, "serial_number", "serial"))
            battery_profiles.append(
                {
                    "index": index,
                    "serial": serial,
                    "cell_count": _plain(_read(battery, "num_cells")),
                    "design_capacity_ah": _plain(_read(battery, "cap_design", "cap_design2")),
                    "bms_firmware": _plain(_read(battery, "bms_firmware_version")),
                }
            )
            battery_snapshots.append(
                {
                    "index": index,
                    "serial": serial,
                    "soc": _metric(_read(battery, "soc"), "%"),
                    "voltage": _metric(_read(battery, "v_out", "v_battery"), "V"),
                    "current": _metric(_read(battery, "i_out", "i_battery"), "A"),
                    "temperature_min": _metric(_read(battery, "t_min"), "°C"),
                    "temperature_max": _metric(_read(battery, "t_max"), "°C"),
                    "cycles": _metric(_read(battery, "num_cycles")),
                }
            )

        profile = HardwareProfile(
            provider="givenergy_modbus",
            manufacturer="GivEnergy",
            model=_plain(_read(inverter, "model")),
            serial=_plain(_read(plant, "inverter_serial_number", "serial_number")),
            firmware=_plain(_read(inverter, "firmware_version")),
            phases=_plain(_read(inverter, "num_phases")),
            mppt_count=_plain(_read(inverter, "num_mppt")),
            pv_string_count=len(strings),
            battery_count=len(batteries),
            batteries=battery_profiles,
            controls={
                "charge_enable": _read(inverter, "enable_charge") is not None,
                "discharge_enable": _read(inverter, "enable_discharge") is not None,
                "charge_target_soc": _read(inverter, "charge_target_soc") is not None,
                "reserve_soc": _read(inverter, "battery_soc_reserve") is not None,
                "charge_limit": _read(inverter, "battery_charge_limit") is not None,
                "discharge_limit": _read(inverter, "battery_discharge_limit") is not None,
            },
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "connection": {
                "state": "online",
                "host": self.host,
                "port": self.port,
                "stale": False,
            },
            "system_profile": profile.as_dict(),
            "solar": {"power": _metric(solar_power, "W"), "strings": strings},
            "home": {
                "power": _metric(_read(inverter, "p_load_demand", "p_load", "load_power"), "W")
            },
            "grid": {
                "power": _metric(_read(inverter, "grid_power", "p_grid_out", "p_grid"), "W"),
                "voltage": _metric(_read(inverter, "v_ac1", "v_grid"), "V"),
                "frequency": _metric(_read(inverter, "f_ac1", "f_grid"), "Hz"),
            },
            "battery_bank": {
                "power": _metric(_read(inverter, "p_battery", "battery_power"), "W"),
                "soc": _metric(_read(inverter, "battery_soc", "soc"), "%"),
                "voltage": _metric(_read(inverter, "v_battery"), "V"),
                "temperature": _metric(_read(inverter, "t_battery"), "°C"),
                "count": len(batteries),
            },
            "batteries": battery_snapshots,
            "energy_today": {
                "solar_generation": _metric(_read(inverter, "e_pv_generation_today", "e_pv_day"), "kWh"),
                "consumption": _metric(_read(inverter, "e_consumption_today", "e_load_today"), "kWh"),
                "grid_import": _metric(_read(inverter, "e_grid_in_day"), "kWh"),
                "grid_export": _metric(_read(inverter, "e_grid_out_day"), "kWh"),
                "battery_charge": _metric(_read(inverter, "e_battery_charge_today"), "kWh"),
                "battery_discharge": _metric(_read(inverter, "e_battery_discharge_today"), "kWh"),
            },
            "energy_total": {
                "solar_generation": _metric(_read(inverter, "e_pv_generation_total", "e_pv_total"), "kWh"),
                "consumption": _metric(_read(inverter, "e_consumption_total", "e_load_total"), "kWh"),
                "grid_import": _metric(_read(inverter, "e_grid_in_total"), "kWh"),
                "grid_export": _metric(_read(inverter, "e_grid_out_total"), "kWh"),
            },
        }
