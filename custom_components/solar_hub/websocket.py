"""WebSocket API for the Solar Hub panel."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN, WS_DEEP_SCAN, WS_OVERVIEW, WS_PREDBAT
from .predbat import snapshot_predbat


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register Solar Hub WebSocket commands once."""

    @websocket_api.websocket_command({vol.Required("type"): WS_OVERVIEW})
    @websocket_api.async_response
    async def overview(hass: HomeAssistant, connection, msg) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_result(msg["id"], {})
            return
        runtime = hass.data.get(DOMAIN, {}).get(entries[0].entry_id, {})
        coordinator = runtime.get("coordinator")
        connection.send_result(msg["id"], coordinator.data if coordinator else {})

    @websocket_api.websocket_command({vol.Required("type"): WS_PREDBAT})
    @websocket_api.async_response
    async def predbat(hass: HomeAssistant, connection, msg) -> None:
        connection.send_result(msg["id"], snapshot_predbat(hass))

    @websocket_api.websocket_command({vol.Required("type"): WS_DEEP_SCAN})
    @websocket_api.async_response
    async def deep_scan(hass: HomeAssistant, connection, msg) -> None:
        """Run the explicitly requested extended hardware scan."""
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            connection.send_error(msg["id"], "not_configured", "Solar Hub is not configured")
            return
        runtime = hass.data.get(DOMAIN, {}).get(entries[0].entry_id, {})
        coordinator = runtime.get("coordinator")
        if not coordinator:
            connection.send_error(msg["id"], "not_ready", "Solar Hub is not ready")
            return
        connection.send_result(msg["id"], await coordinator.async_deep_scan())

    websocket_api.async_register_command(hass, overview)
    websocket_api.async_register_command(hass, predbat)
    websocket_api.async_register_command(hass, deep_scan)
