"""Native Home Assistant sensors for Solar Hub."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarHubCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarHubSensorDescription:
    """Description of one Solar Hub sensor."""

    key: str
    name: str
    path: tuple[str, ...]
    native_unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = None


CORE_DESCRIPTIONS = (
    SolarHubSensorDescription(key="solar_power", name="Solar Power", path=("solar", "power"), native_unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="home_power", name="Home Power", path=("home", "power"), native_unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="grid_power", name="Grid Power", path=("grid", "power"), native_unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="battery_power", name="Battery Power", path=("battery_bank", "power"), native_unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="battery_soc", name="Battery State of Charge", path=("battery_bank", "soc"), native_unit=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="battery_voltage", name="Battery Voltage", path=("battery_bank", "voltage"), native_unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="battery_temperature", name="Battery Temperature", path=("battery_bank", "temperature"), native_unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="grid_voltage", name="Grid Voltage", path=("grid", "voltage"), native_unit=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT),
    SolarHubSensorDescription(key="grid_frequency", name="Grid Frequency", path=("grid", "frequency"), native_unit=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT),
)

ENERGY_DESCRIPTIONS = (
    ("solar_energy_today", "Solar Energy Today", ("energy_today", "solar_generation")),
    ("home_energy_today", "Home Energy Today", ("energy_today", "consumption")),
    ("grid_import_today", "Grid Import Today", ("energy_today", "grid_import")),
    ("grid_export_today", "Grid Export Today", ("energy_today", "grid_export")),
    ("battery_charge_today", "Battery Charge Today", ("energy_today", "battery_charge")),
    ("battery_discharge_today", "Battery Discharge Today", ("energy_today", "battery_discharge")),
    ("solar_energy_total", "Solar Energy Total", ("energy_total", "solar_generation")),
    ("home_energy_total", "Home Energy Total", ("energy_total", "consumption")),
    ("grid_import_total", "Grid Import Total", ("energy_total", "grid_import")),
    ("grid_export_total", "Grid Export Total", ("energy_total", "grid_export")),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create entities from the detected hardware profile."""
    coordinator: SolarHubCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    data = coordinator.data or {}

    descriptions = list(CORE_DESCRIPTIONS)
    descriptions.extend(
        SolarHubSensorDescription(
            key=key,
            name=name,
            path=path,
            native_unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
        )
        for key, name, path in ENERGY_DESCRIPTIONS
    )

    for position, string in enumerate(data.get("solar", {}).get("strings", [])):
        index = int(string.get("index", position + 1))
        descriptions.extend(
            (
                SolarHubSensorDescription(
                    key=f"pv_string_{index}_power",
                    name=f"PV String {index} Power",
                    path=("solar", "strings", str(position), "power"),
                    native_unit=UnitOfPower.WATT,
                    device_class=SensorDeviceClass.POWER,
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                SolarHubSensorDescription(
                    key=f"pv_string_{index}_voltage",
                    name=f"PV String {index} Voltage",
                    path=("solar", "strings", str(position), "voltage"),
                    native_unit=UnitOfElectricPotential.VOLT,
                    device_class=SensorDeviceClass.VOLTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                SolarHubSensorDescription(
                    key=f"pv_string_{index}_current",
                    name=f"PV String {index} Current",
                    path=("solar", "strings", str(position), "current"),
                    native_unit=UnitOfElectricCurrent.AMPERE,
                    device_class=SensorDeviceClass.CURRENT,
                    state_class=SensorStateClass.MEASUREMENT,
                ),
            )
        )

    async_add_entities(SolarHubSensor(coordinator, entry, description) for description in descriptions)


class SolarHubSensor(CoordinatorEntity[SolarHubCoordinator], SensorEntity):
    """A sensor backed by the Solar Hub coordinator snapshot."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarHubCoordinator,
        entry: ConfigEntry,
        description: SolarHubSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{description.key}"
        self._attr_native_unit_of_measurement = description.native_unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category

        profile = (coordinator.data or {}).get("system_profile", {})
        serial = str(profile.get("serial") or entry.unique_id or entry.entry_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name="Solar Hub Inverter",
            manufacturer=str(profile.get("manufacturer") or "Solar Hub"),
            model=str(profile.get("model") or "Detected inverter"),
            serial_number=serial,
            sw_version=str(profile.get("firmware")) if profile.get("firmware") else None,
        )

    @property
    def native_value(self) -> Any:
        value: Any = self.coordinator.data or {}
        for part in self.description.path:
            if isinstance(value, list):
                try:
                    value = value[int(part)]
                except (IndexError, TypeError, ValueError):
                    return None
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        if isinstance(value, dict) and "value" in value:
            return None if value.get("available") is False else value.get("value")
        return value
