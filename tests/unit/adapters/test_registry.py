"""Tests for app.adapters.registry — AdapterRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.adapters.registry import AdapterRegistry
from app.core.exceptions import AdapterError


@pytest.fixture
def registry() -> AdapterRegistry:
    return AdapterRegistry()


def _make_adapter(name: str = "deepagents") -> MagicMock:
    adapter = MagicMock()
    adapter.framework_name = name
    return adapter


class TestAdapterRegistry:
    def test_register_and_get(self, registry):
        adapter = _make_adapter("deepagents")
        registry.register(adapter)
        assert registry.get("deepagents") is adapter

    def test_get_unknown_raises(self, registry):
        with pytest.raises(AdapterError):
            registry.get("nonexistent")

    def test_list_adapters_empty(self, registry):
        assert registry.list_adapters() == []

    def test_list_adapters_returns_names(self, registry):
        registry.register(_make_adapter("deepagents"))
        registry.register(_make_adapter("crewai"))
        result = registry.list_adapters()
        assert sorted(result) == ["crewai", "deepagents"]

    def test_register_duplicate_raises(self, registry):
        adapter1 = _make_adapter("deepagents")
        adapter2 = _make_adapter("deepagents")
        registry.register(adapter1)
        with pytest.raises(AdapterError):
            registry.register(adapter2)
        # Original adapter still accessible
        assert registry.get("deepagents") is adapter1
