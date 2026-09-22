"""Solar Hub integration."""
from __future__ import annotations

import logging

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    FRONTEND_PATH,
    PANEL_ELEMENT,
    PANEL_URL,
    STATIC_URL,
    VERSION,
)
from .coordinator import SolarHubCoordinator
from .websocket import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up shared Solar Hub resources."""
    hass.data.setdefault(DOMAIN, {})
    if not hass.data[DOMAIN].get("shared_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_PATH), False)]
        )
        async_register_websocket_api(hass)
        hass.data[DOMAIN]["shared_registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one Solar Hub config entry."""
    host = str(entry.data[CONF_HOST]).strip()
    port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))

    coordinator = SolarHubCoordinator(hass, host, port)
    first = await coordinator.async_scan()
    coordinator.async_set_updated_data(first)

    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    frontend.async_remove_panel(hass, PANEL_URL)
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_ELEMENT,
        frontend_url_path=PANEL_URL,
        module_url=f"{STATIC_URL}/solar-hub-panel.js?v={VERSION}",
        sidebar_title="Solar Hub",
        sidebar_icon="mdi:solar-power-variant",
        require_admin=False,
        config={"entry_id": entry.entry_id, "version": VERSION},
    )

    _LOGGER.info("Solar Hub %s loaded", VERSION)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Solar Hub config entry."""
    frontend.async_remove_panel(hass, PANEL_URL)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runtime = hass.data[DOMAIN].pop(entry.entry_id, {})
    coordinator = runtime.get("coordinator")
    if coordinator:
        await coordinator.async_close()
    return unloaded
