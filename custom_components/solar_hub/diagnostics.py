"""Diagnostics for Solar Hub."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    """Return a redacted diagnostic snapshot."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = runtime.get("coordinator")
    data = dict(coordinator.data or {}) if coordinator else {}
    if isinstance(data.get("connection"), dict):
        data["connection"] = {**data["connection"], "host": "REDACTED"}
    return data
