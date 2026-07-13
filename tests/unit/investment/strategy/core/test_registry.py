"""tests/unit/investment/strategy/core/test_registry.py
Tests for InstitutionalStrategyRegistry, Factory, Loader, and Catalog.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.core import (
    AssetSupport, InstitutionalStrategyCatalog, InstitutionalStrategyFactory,
    InstitutionalStrategyRegistry, LoaderError, RegistrationError,
    StrategyCapability, StrategyDescriptor, StrategyVersion,
    SupportedAssetClass, TradingStyle,
)
from iios.investment.strategy.core.strategy_loader import StrategyLoader
from .conftest import (
    ConcreteStrategy, make_descriptor, make_config,
)


# ── InstitutionalStrategyRegistry ─────────────────────────────────────────────

class TestInstitutionalStrategyRegistry:
    def test_register_and_lookup(self):
        reg = InstitutionalStrategyRegistry()
        desc = make_descriptor()
        reg.register(ConcreteStrategy, desc)
        assert reg.is_registered("test_strategy")
        assert reg.get_class("test_strategy") is ConcreteStrategy

    def test_duplicate_raises(self):
        reg = InstitutionalStrategyRegistry()
        desc = make_descriptor()
        reg.register(ConcreteStrategy, desc)
        with pytest.raises(RegistrationError):
            reg.register(ConcreteStrategy, desc)

    def test_replace_allowed(self):
        reg = InstitutionalStrategyRegistry()
        desc = make_descriptor()
        reg.register(ConcreteStrategy, desc)
        reg.register(ConcreteStrategy, desc, replace=True)

    def test_missing_dependency_raises(self):
        reg = InstitutionalStrategyRegistry()
        desc = make_descriptor(
            strategy_id="child",
            dependencies=("missing_parent",),
        )
        with pytest.raises(RegistrationError):
            reg.register(ConcreteStrategy, desc)

    def test_dependency_satisfied(self):
        reg = InstitutionalStrategyRegistry()
        parent_desc = make_descriptor(strategy_id="parent")
        child_desc = make_descriptor(
            strategy_id="child", dependencies=("parent",)
        )
        reg.register(ConcreteStrategy, parent_desc)
        reg.register(ConcreteStrategy, child_desc)
        assert reg.is_registered("child")

    def test_unregister(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor())
        reg.unregister("test_strategy")
        assert not reg.is_registered("test_strategy")

    def test_enable_disable(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor())
        reg.disable("test_strategy")
        assert not reg.is_enabled("test_strategy")
        reg.enable("test_strategy")
        assert reg.is_enabled("test_strategy")

    def test_enable_unregistered_raises(self):
        reg = InstitutionalStrategyRegistry()
        with pytest.raises(RegistrationError):
            reg.enable("unknown")

    def test_all_ids(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor("a"))
        reg.register(ConcreteStrategy, make_descriptor("b"))
        assert set(reg.all_ids()) == {"a", "b"}

    def test_enabled_ids_excludes_disabled(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor("a"))
        reg.register(ConcreteStrategy, make_descriptor("b"))
        reg.disable("b")
        assert "a" in reg.enabled_ids()
        assert "b" not in reg.enabled_ids()

    def test_deprecated_disabled_by_default(self):
        reg = InstitutionalStrategyRegistry()
        desc = make_descriptor(is_deprecated=True)
        reg.register(ConcreteStrategy, desc)
        assert not reg.is_enabled("test_strategy")

    def test_count(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor("x"))
        assert reg.count() == 1

    def test_to_dict(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor())
        d = reg.to_dict()
        assert "test_strategy" in d
        assert "enabled" in d["test_strategy"]


# ── InstitutionalStrategyFactory ──────────────────────────────────────────────

class TestInstitutionalStrategyFactory:
    @pytest.fixture
    def factory(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor())
        return InstitutionalStrategyFactory(reg)

    def test_create_returns_instance(self, factory):
        inst = factory.create("test_strategy")
        assert isinstance(inst, ConcreteStrategy)

    def test_create_with_config_loads(self, factory):
        config = make_config()
        inst = factory.create("test_strategy", config=config)
        from iios.investment.strategy.core import StrategyState
        assert inst.state == StrategyState.LOADED

    def test_create_unknown_raises(self, factory):
        from iios.investment.strategy.core import FactoryError
        with pytest.raises(FactoryError):
            factory.create("unknown")

    def test_create_disabled_raises(self, factory):
        from iios.investment.strategy.core import FactoryError
        factory._registry.disable("test_strategy")
        with pytest.raises(FactoryError):
            factory.create("test_strategy")

    def test_build_default_config(self, factory):
        config = factory.build_default_config("test_strategy")
        assert config.strategy_id == "test_strategy"
        assert config.environment == "paper"

    def test_build_default_config_unknown_raises(self, factory):
        from iios.investment.strategy.core import FactoryError
        with pytest.raises(FactoryError):
            factory.build_default_config("nonexistent")


# ── StrategyLoader ────────────────────────────────────────────────────────────

class TestStrategyLoader:
    def test_load_direct(self):
        reg = InstitutionalStrategyRegistry()
        loader = StrategyLoader(reg)
        desc = make_descriptor("direct_load")
        sid = loader.load_direct(ConcreteStrategy, desc)
        assert sid == "direct_load"
        assert reg.is_registered("direct_load")

    def test_load_direct_duplicate_raises(self):
        reg = InstitutionalStrategyRegistry()
        loader = StrategyLoader(reg)
        desc = make_descriptor("x")
        loader.load_direct(ConcreteStrategy, desc)
        with pytest.raises(LoaderError):
            loader.load_direct(ConcreteStrategy, desc)

    def test_load_direct_replace(self):
        reg = InstitutionalStrategyRegistry()
        loader = StrategyLoader(reg)
        desc = make_descriptor("x")
        loader.load_direct(ConcreteStrategy, desc)
        loader.load_direct(ConcreteStrategy, desc, replace=True)

    def test_load_from_nonexistent_module_raises(self):
        reg = InstitutionalStrategyRegistry()
        loader = StrategyLoader(reg)
        with pytest.raises(LoaderError):
            loader.load_from_module("iios.nonexistent_strategy_module_xyz")

    def test_load_from_nonexistent_file_raises(self, tmp_path):
        reg = InstitutionalStrategyRegistry()
        loader = StrategyLoader(reg)
        with pytest.raises(LoaderError):
            loader.load_from_file(str(tmp_path / "missing.py"))

    def test_load_directory_with_valid_module(self, tmp_path):
        """Write a valid plugin file and load it from directory."""
        plugin = tmp_path / "my_plugin.py"
        plugin.write_text(
            "from iios.investment.strategy.core.institutional_base_strategy import "
            "InstitutionalBaseStrategy, ExecutionPlan, Signal\n"
            "from iios.investment.strategy.core.strategy_configuration import "
            "StrategyConfiguration\n"
            "from iios.investment.strategy.core.strategy_context import StrategyContext\n"
            "from iios.investment.strategy.core.strategy_descriptor import "
            "StrategyDescriptor, StrategyVersion\n"
            "from iios.investment.strategy.core.asset_support import AssetSupport\n"
            "from iios.investment.strategy.core.market_support import MarketSupport\n"
            "from iios.investment.strategy.core.timeframe_support import TimeframeSupport\n\n"
            "class PluginStrategy(InstitutionalBaseStrategy):\n"
            "    def initialize(self): pass\n"
            "    def load_configuration(self, c): pass\n"
            "    def validate_inputs(self, ctx): return True\n"
            "    def prepare(self, ctx): pass\n"
            "    def analyze_market(self, ctx): return {}\n"
            "    def generate_candidates(self, ctx, a): return []\n"
            "    def evaluate_candidates(self, cs, ctx, a): return cs\n"
            "    def generate_signals(self, cs, ctx, a): return []\n"
            "    def validate_signals(self, sigs, ctx): return sigs\n"
            "    def position_sizing(self, sigs, ctx): return {}\n"
            "    def risk_validation(self, sigs, sz, ctx): return sigs\n"
            "    def execution_plan(self, sigs, sz, ctx):\n"
            "        return ExecutionPlan(self.strategy_id, sigs)\n"
            "    def post_execution(self, plan, ctx): pass\n"
            "    def shutdown(self): pass\n\n"
            "STRATEGY_CLASS = PluginStrategy\n"
            "STRATEGY_DESCRIPTOR = StrategyDescriptor(\n"
            "    strategy_id='plugin_strategy',\n"
            "    name='Plugin',\n"
            "    asset_support=AssetSupport.equity_only(),\n"
            "    market_support=MarketSupport.indian_equity(),\n"
            "    timeframe_support=TimeframeSupport.intraday(),\n"
            ")\n"
        )

        reg = InstitutionalStrategyRegistry()
        loader = StrategyLoader(reg)
        loaded = loader.load_directory(str(tmp_path))
        assert "plugin_strategy" in loaded
        assert reg.is_registered("plugin_strategy")


# ── InstitutionalStrategyCatalog ──────────────────────────────────────────────

class TestInstitutionalStrategyCatalog:
    @pytest.fixture
    def catalog(self):
        reg = InstitutionalStrategyRegistry()
        reg.register(ConcreteStrategy, make_descriptor("equity_swing", tags=("swing", "equity")))
        reg.register(
            ConcreteStrategy,
            make_descriptor(
                "equity_intraday",
                tags=("intraday",),
                capabilities=frozenset({StrategyCapability.REAL_TIME}),
                timeframe_support=__import__(
                    "iios.investment.strategy.core", fromlist=["TimeframeSupport"]
                ).TimeframeSupport.intraday(),
            ),
        )
        reg.register(
            ConcreteStrategy,
            make_descriptor("deprecated_strat", is_deprecated=True),
        )
        return InstitutionalStrategyCatalog(reg)

    def test_count(self, catalog):
        assert catalog.count() == 2  # deprecated excluded

    def test_all_includes_deprecated(self, catalog):
        assert len(catalog.all(include_deprecated=True)) == 3

    def test_get(self, catalog):
        desc = catalog.get("equity_swing")
        assert desc is not None
        assert desc.strategy_id == "equity_swing"

    def test_get_unknown_returns_none(self, catalog):
        assert catalog.get("unknown") is None

    def test_by_tag(self, catalog):
        results = catalog.by_tag("swing")
        assert len(results) == 1
        assert results[0].strategy_id == "equity_swing"

    def test_by_capability(self, catalog):
        results = catalog.by_capability(StrategyCapability.REAL_TIME)
        assert any(r.strategy_id == "equity_intraday" for r in results)

    def test_by_style_swing(self, catalog):
        results = catalog.by_style(TradingStyle.SWING)
        sids = [r.strategy_id for r in results]
        assert "equity_swing" in sids

    def test_strategy_ids(self, catalog):
        ids = catalog.strategy_ids()
        assert "equity_swing" in ids
        assert "deprecated_strat" not in ids
