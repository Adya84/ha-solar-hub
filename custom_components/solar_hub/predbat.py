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

PLAN_KINDS = ("charge", "discharge", "export", "import", "solar")


def _plan_kind(value: Any) -> str:
    """Map arbitrary PredBat wording to the panel's fixed colour vocabulary."""
    text = str(value or "").lower()
    for kind in PLAN_KINDS:
        if kind in text:
            return kind
    return "unknown"


def _plan_segments(attributes: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract only serialisable, safely displayable plan rows from attributes."""
    raw = attributes.get("plan") or attributes.get("plan_segments") or []
    if not isinstance(raw, list):
        return []
    segments: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("action") or item.get("type") or "Planned")
        segments.append(
            {
                "kind": _plan_kind(item.get("kind") or item.get("action") or item.get("type")),
                "label": label,
                "start": item.get("start") or item.get("start_time"),
                "end": item.get("end") or item.get("end_time"),
                "rate": item.get("rate"),
                "target_soc": item.get("target_soc"),
            }
        )
    return segments


def snapshot_predbat(hass: HomeAssistant) -> dict[str, Any]:
    """Return likely PredBat entities without making PredBat a dependency."""
    entities: list[dict[str, Any]] = []
    plan_segments: list[dict[str, Any]] = []
    current_action: str | None = None
    override: str | None = None
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
        if not plan_segments:
            plan_segments = _plan_segments(dict(state.attributes))
        if current_action is None and any(word in haystack for word in ("status", "action", "mode")):
            current_action = str(state.state)
        if override is None and "override" in haystack:
            override = str(state.state)
    return {
        "available": bool(entities),
        "count": len(entities),
        "entities": entities,
        "current_action": current_action,
        "override": override,
        "plan_segments": plan_segments,
    }
