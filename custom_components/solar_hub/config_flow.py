"""Config flow for Solar Hub."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, NAME
from .providers import GivEnergyProvider


class SolarHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Solar Hub using only the inverter IP."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            provider = GivEnergyProvider(host, DEFAULT_PORT)
            try:
                snapshot = await provider.async_scan()
                profile = snapshot.get("system_profile", {})
                serial = str(profile.get("serial") or host)
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                title = str(profile.get("model") or serial)
                return self.async_create_entry(
                    title=f"{NAME} · {title}",
                    data={CONF_HOST: host, CONF_PORT: DEFAULT_PORT},
                )
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                try:
                    await provider.async_close()
                except Exception:
                    pass

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )
