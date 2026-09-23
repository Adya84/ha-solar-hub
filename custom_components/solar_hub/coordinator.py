"""Update coordinator for Solar Hub."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .providers import GivEnergyProvider

_LOGGER = logging.getLogger(__name__)


class SolarHubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Own provider refreshes and preserve the last good snapshot."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{host}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.provider = GivEnergyProvider(host, port)
        self._last_good: dict[str, Any] | None = None
        self._deep_profile: dict[str, Any] = {}

    async def async_scan(self) -> dict[str, Any]:
        """Perform the initial capability scan."""
        data = await self.provider.async_scan()
        self._attach_deep_profile(data)
        self._last_good = data
        return data

    async def async_deep_scan(self) -> dict[str, Any]:
        """Run the user-requested extended hardware scan outside live polling."""
        current = deepcopy(self.data or self._last_good or {})
        profile = current.setdefault("system_profile", {})
        profile["deep_scan"] = {
            "state": "running",
            "progress": 0,
            "stage": "Preparing scan",
            "completed_at": None,
            "error": None,
        }
        self.async_set_updated_data(current)
        def report(progress: int, stage: str) -> None:
            profile["deep_scan"] = {
                "state": "running",
                "progress": progress,
                "stage": stage,
                "completed_at": None,
                "error": None,
            }
            self.async_set_updated_data(current)
        try:
            scanned = await asyncio.wait_for(self.provider.async_deep_scan(report), timeout=120)
        except Exception as err:
            profile["deep_scan"] = {
                "state": "failed",
                "progress": 0,
                "stage": "Failed",
                "completed_at": None,
                "error": err.__class__.__name__,
            }
            self.async_set_updated_data(current)
            return current
        self._deep_profile = deepcopy(scanned.get("system_profile", {}))
        self._last_good = scanned
        self.async_set_updated_data(scanned)
        return scanned

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.provider.async_refresh()
            self._attach_deep_profile(data)
            self._last_good = data
            return data
        except Exception as err:
            if self._last_good is None:
                raise UpdateFailed(str(err)) from err
            stale = deepcopy(self._last_good)
            stale["connection"] = {
                **stale.get("connection", {}),
                "state": "offline",
                "stale": True,
                "last_error": err.__class__.__name__,
            }
            return stale

    def _attach_deep_profile(self, data: dict[str, Any]) -> None:
        """Keep completed deep-scan fields through lightweight refreshes."""
        if not self._deep_profile:
            return
        profile = data.setdefault("system_profile", {})
        for key in ("deep_data", "deep_scan"):
            if key in self._deep_profile:
                profile[key] = deepcopy(self._deep_profile[key])

    async def async_close(self) -> None:
        """Close the provider."""
        await self.provider.async_close()
