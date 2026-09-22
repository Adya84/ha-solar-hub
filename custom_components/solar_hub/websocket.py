"""WebSocket API for the Solar Hub panel."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN, WS_OVERVIEW, WS_PREDBAT
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

    websocket_api.async_register_command(hass, overview)
    websocket_api.async_register_command(hass, predbat)
