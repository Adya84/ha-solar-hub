"""Provider contract used by Solar Hub."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SolarProvider(ABC):
    """Interface implemented by inverter/data providers."""

    @abstractmethod
    async def async_scan(self) -> dict[str, Any]:
        """Connect, identify hardware and return an initial snapshot."""

    @abstractmethod
    async def async_refresh(self) -> dict[str, Any]:
        """Return a fresh normalised snapshot."""

    @abstractmethod
    async def async_deep_scan(self) -> dict[str, Any]:
        """Read extended, on-demand hardware details."""

    @abstractmethod
    async def async_set_control(self, key: str, value: Any) -> None:
        """Write a known supported control."""

    @abstractmethod
    async def async_close(self) -> None:
        """Close provider resources."""
