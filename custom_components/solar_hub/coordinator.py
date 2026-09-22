"""Update coordinator for Solar Hub."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
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

    async def async_scan(self) -> dict[str, Any]:
        """Perform the initial capability scan."""
        data = await self.provider.async_scan()
        self._last_good = data
        return data

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.provider.async_refresh()
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

    async def async_close(self) -> None:
        """Close the provider."""
        await self.provider.async_close()
