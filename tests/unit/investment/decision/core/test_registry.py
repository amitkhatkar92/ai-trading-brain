"""tests/unit/investment/decision/core/test_registry.py
Tests for DecisionRegistry, DecisionFactory, DecisionLoader, DecisionCatalog.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.core.decision_catalog import CatalogEntry, DecisionCatalog
from iios.investment.decision.core.decision_configuration import DecisionConfiguration
from iios.investment.decision.core.decision_constants import (
    DecisionType,
    EnvironmentProfile,
)
from iios.investment.decision.core.decision_context import make_context
from iios.investment.decision.core.decision_events import EventDispatcher
from iios.investment.decision.core.decision_factory import DecisionFactory
from iios.investment.decision.core.decision_loader import DecisionLoader
from iios.investment.decision.core.decision_registry import (
    DecisionRegistry,
    DuplicateDecisionTypeError,
    UnknownDecisionTypeError,
)
from iios.investment.decision.core.decision_types import get_descriptor
from tests.unit.investment.decision.core.conftest import SimpleBuyDecision, RejectedDecision


# ===========================================================================
# DecisionRegistry
# ===========================================================================

class TestDecisionRegistry:
    def test_register_and_get(self):
        reg = DecisionRegistry()
        reg.register("simple_buy", SimpleBuyDecision)
        assert reg.get("simple_buy") is SimpleBuyDecision

    def test_get_unknown_raises(self):
        reg = DecisionRegistry()
        with pytest.raises(UnknownDecisionTypeError):
            reg.get("nonexistent")

    def test_get_optional_returns_none(self):
        reg = DecisionRegistry()
        assert reg.get_optional("missing") is None

    def test_duplicate_raises(self):
        reg = DecisionRegistry()
        reg.register("t1", SimpleBuyDecision)
        with pytest.raises(DuplicateDecisionTypeError):
            reg.register("t1", RejectedDecision)

    def test_duplicate_overwrite_allowed(self):
        reg = DecisionRegistry()
        reg.register("t1", SimpleBuyDecision)
        reg.register("t1", RejectedDecision, overwrite=True)
        assert reg.get("t1") is RejectedDecision

    def test_unregister(self):
        reg = DecisionRegistry()
        reg.register("t2", SimpleBuyDecision)
        reg.unregister("t2")
        assert not reg.has("t2")

    def test_unregister_missing_is_noop(self):
        reg = DecisionRegistry()
        reg.unregister("nonexistent")  # should not raise

    def test_has(self):
        reg = DecisionRegistry()
        reg.register("t3", SimpleBuyDecision)
        assert reg.has("t3")
        assert not reg.has("t99")

    def test_all_keys(self):
        reg = DecisionRegistry()
        reg.register("a", SimpleBuyDecision)
        reg.register("b", RejectedDecision)
        keys = reg.all_keys()
        assert "a" in keys
        assert "b" in keys

    def test_count(self):
        reg = DecisionRegistry()
        assert reg.count() == 0
        reg.register("c1", SimpleBuyDecision)
        assert reg.count() == 1

    def test_version_stored(self):
        reg = DecisionRegistry()
        reg.register("v1", SimpleBuyDecision, version="2.0.0")
        assert reg.version("v1") == "2.0.0"

    def test_capabilities_stored(self):
        reg = DecisionRegistry()
        reg.register("cap1", SimpleBuyDecision, capabilities=("scoring", "approval"))
        assert "scoring" in reg.capabilities("cap1")


# ===========================================================================
# DecisionFactory
# ===========================================================================

class TestDecisionFactory:
    def _make_factory(self) -> tuple:
        reg = DecisionRegistry()
        reg.register("simple_buy", SimpleBuyDecision)
        reg.register("rejected",   RejectedDecision)
        factory = DecisionFactory(reg)
        return factory, reg

    def test_create_known_type(self):
        factory, _ = self._make_factory()
        ctx = make_context(DecisionType.INVESTMENT, "INFY", "equity", "test")
        decision = factory.create("simple_buy", ctx)
        assert isinstance(decision, SimpleBuyDecision)

    def test_create_unknown_raises(self):
        factory, _ = self._make_factory()
        ctx = make_context(DecisionType.INVESTMENT, "INFY", "equity", "test")
        with pytest.raises(UnknownDecisionTypeError):
            factory.create("nonexistent", ctx)

    def test_can_create_true(self):
        factory, _ = self._make_factory()
        assert factory.can_create("simple_buy")

    def test_can_create_false(self):
        factory, _ = self._make_factory()
        assert not factory.can_create("missing")

    def test_supported_types(self):
        factory, _ = self._make_factory()
        types = factory.supported_types()
        assert "simple_buy" in types
        assert "rejected" in types

    def test_config_injected(self):
        factory, _ = self._make_factory()
        cfg = DecisionConfiguration(approval_threshold=90.0)
        ctx = make_context(DecisionType.INVESTMENT, "TCS", "equity", "test")
        decision = factory.create("simple_buy", ctx, config=cfg)
        assert decision.config.approval_threshold == 90.0

    def test_dispatcher_injected(self):
        dispatcher = EventDispatcher()
        reg = DecisionRegistry()
        reg.register("simple_buy", SimpleBuyDecision)
        factory  = DecisionFactory(reg, dispatcher=dispatcher)
        ctx      = make_context(DecisionType.INVESTMENT, "ONGC", "equity", "test")
        decision = factory.create("simple_buy", ctx)
        assert decision.dispatcher is dispatcher


# ===========================================================================
# DecisionLoader
# ===========================================================================

class TestDecisionLoader:
    def test_load_from_class_path(self):
        reg    = DecisionRegistry()
        loader = DecisionLoader(reg)
        ok = loader.load_from_class_path(
            "tests.unit.investment.decision.core.conftest.SimpleBuyDecision",
            key="simple_buy_loaded",
        )
        assert ok
        assert reg.has("simple_buy_loaded")

    def test_load_invalid_path_returns_false(self):
        reg    = DecisionRegistry()
        loader = DecisionLoader(reg)
        ok = loader.load_from_class_path("nonexistent.module.SomeClass", key="bad")
        assert not ok

    def test_load_from_module(self):
        reg    = DecisionRegistry()
        loader = DecisionLoader(reg)
        count  = loader.load_from_module(
            "tests.unit.investment.decision.core.conftest"
        )
        # Should find SimpleBuyDecision, RejectedDecision, FailingDecision
        assert count >= 3

    def test_loaded_list_populated(self):
        reg    = DecisionRegistry()
        loader = DecisionLoader(reg)
        loader.load_from_class_path(
            "tests.unit.investment.decision.core.conftest.SimpleBuyDecision",
            key="track_test",
        )
        assert len(loader.loaded) >= 1

    def test_load_nonexistent_module_returns_zero(self):
        reg    = DecisionRegistry()
        loader = DecisionLoader(reg)
        count  = loader.load_from_module("totally.fake.module.path")
        assert count == 0


# ===========================================================================
# DecisionCatalog
# ===========================================================================

class TestDecisionCatalog:
    def test_builtins_preloaded(self):
        catalog = DecisionCatalog()
        assert catalog.count() == len(list(DecisionType))

    def test_get_builtin(self):
        catalog = DecisionCatalog()
        entry   = catalog.get(DecisionType.INVESTMENT)
        assert entry is not None
        assert entry.is_builtin

    def test_register_custom(self):
        catalog  = DecisionCatalog()
        desc     = get_descriptor(DecisionType.INVESTMENT)
        catalog.register(desc, "my.module.MyDecision", tags=("custom",))
        entry = catalog.get(DecisionType.INVESTMENT)
        assert not entry.is_builtin
        assert "custom" in entry.tags

    def test_unregister(self):
        catalog = DecisionCatalog()
        n       = catalog.count()
        catalog.unregister(DecisionType.INVESTMENT.value)
        assert catalog.count() == n - 1

    def test_all_returns_list(self):
        catalog = DecisionCatalog()
        entries = catalog.all()
        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_supported_types(self):
        catalog = DecisionCatalog()
        types   = catalog.supported_types()
        assert DecisionType.INVESTMENT.value in types

    def test_to_dict(self):
        catalog = DecisionCatalog()
        entry   = catalog.get(DecisionType.INVESTMENT)
        d       = entry.to_dict()
        assert "decision_type" in d
        assert "is_builtin" in d
