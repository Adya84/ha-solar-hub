"""Normalised Solar Hub data models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class HardwareProfile:
    """Hardware detected during the initial provider scan."""

    provider: str
    manufacturer: str
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    phases: int | None = None
    mppt_count: int | None = None
    pv_string_count: int = 0
    battery_count: int = 0
    batteries: list[dict[str, Any]] = field(default_factory=list)
    controls: dict[str, bool] = field(default_factory=dict)
    deep_data: dict[str, Any] = field(default_factory=dict)
    deep_scan: dict[str, Any] = field(
        default_factory=lambda: {
            "state": "not_run",
            "completed_at": None,
            "error": None,
        }
    )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""
        return asdict(self)
