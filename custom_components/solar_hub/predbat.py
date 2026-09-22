"""Optional PredBat discovery."""
from __future__ import annotations

from typing import Any
from homeassistant.core import HomeAssistant

KEYWORDS = (
    "predbat",
    "best_charge",
    "best_discharge",
    "best_export",
    "charge_limit",
    "plan_html",
    "metric",
)


def snapshot_predbat(hass: HomeAssistant) -> dict[str, Any]:
    """Return likely PredBat entities without making PredBat a dependency."""
    entities: list[dict[str, Any]] = []
    for state in hass.states.async_all():
        haystack = f"{state.entity_id} {state.name}".lower()
        if not any(keyword in haystack for keyword in KEYWORDS):
            continue
        entities.append(
            {
                "entity_id": state.entity_id,
                "name": state.name,
                "state": state.state,
                "unit": state.attributes.get("unit_of_measurement"),
            }
        )
    return {"available": bool(entities), "count": len(entities), "entities": entities}
