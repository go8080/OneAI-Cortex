"""Adapter registry — lookup adapters by framework name."""

from __future__ import annotations

from app.adapters.protocol import FrameworkAdapter
from app.core.exceptions import AdapterError

__all__ = ["AdapterRegistry"]


class AdapterRegistry:
    """Thread-safe registry of framework adapters, keyed by framework name."""

    def __init__(self) -> None:
        self._adapters: dict[str, FrameworkAdapter] = {}

    def register(self, adapter: FrameworkAdapter) -> None:
        """Register a framework adapter. Raises on duplicate."""
        name = adapter.framework_name
        if name in self._adapters:
            raise AdapterError(f"Adapter '{name}' already registered", adapter=name)
        self._adapters[name] = adapter

    def get(self, framework_name: str) -> FrameworkAdapter:
        """Get an adapter by framework name. Raises if not found."""
        adapter = self._adapters.get(framework_name)
        if adapter is None:
            available = ", ".join(sorted(self._adapters.keys())) or "none"
            raise AdapterError(
                f"No adapter registered for '{framework_name}'. Available: {available}",
                adapter=framework_name,
            )
        return adapter

    def list_adapters(self) -> list[str]:
        """List all registered adapter names."""
        return sorted(self._adapters.keys())
