"""Tests for adapters: LegacyStrategyAdapter, AdapterFactory, AdapterRegistry."""
import pytest

from iios.investment.strategy.migration.adapter_factory import AdapterFactory
from iios.investment.strategy.migration.adapter_registry import AdapterRegistry
from iios.investment.strategy.migration.strategy_adapter import (
    AdaptationMode,
    LegacyStrategyAdapter,
)
from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyType


class TestLegacyStrategyAdapter:
    def test_create_adapter(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        assert adapter is not None

    def test_adapter_name_matches_metadata(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        assert adapter.name == basic_metadata.strategy_name

    def test_adapter_id_matches_metadata(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        assert adapter.strategy_id == basic_metadata.strategy_id

    def test_get_definition_returns_definition(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        defn = adapter.get_definition()
        assert defn is not None
        assert defn.name == basic_metadata.strategy_name

    def test_get_risk_params_preserves_min_rr(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        rp = adapter.get_risk_params()
        assert abs(rp["min_rr"] - basic_metadata.min_rr) < 1e-9

    def test_get_risk_params_preserves_max_loss(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        rp = adapter.get_risk_params()
        assert abs(rp["max_loss_pct"] - basic_metadata.max_loss_pct) < 1e-9

    def test_evaluate_entry_no_conditions(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        result = adapter.evaluate_entry({"rsi": 30})
        # code-based strategy with no conditions → None
        assert result is None or isinstance(result, bool)

    def test_evaluate_entry_with_conditions(self, json_metadata):
        adapter = LegacyStrategyAdapter(metadata=json_metadata)
        result = adapter.evaluate_entry({"rsi": 25.0, "volume_ratio": 2.0})
        assert result is True

    def test_evaluate_entry_conditions_false(self, json_metadata):
        adapter = LegacyStrategyAdapter(metadata=json_metadata)
        result = adapter.evaluate_entry({"rsi": 60.0, "volume_ratio": 0.5})
        assert result is False

    def test_get_performance_snapshot(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        snap = adapter.get_performance_snapshot()
        assert "precision" in snap or "win_rate" in snap or isinstance(snap, dict)

    def test_summary_is_dict(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        s = adapter.summary()
        assert isinstance(s, dict)

    def test_default_adaptation_mode(self, basic_metadata):
        adapter = LegacyStrategyAdapter(metadata=basic_metadata)
        assert isinstance(adapter.adaptation_mode, AdaptationMode)

    def test_custom_mode(self, basic_metadata):
        adapter = LegacyStrategyAdapter(
            metadata=basic_metadata,
            adaptation_mode=AdaptationMode.PARAMETER_BRIDGE,
        )
        assert adapter.adaptation_mode == AdaptationMode.PARAMETER_BRIDGE


class TestAdapterFactory:
    def setup_method(self):
        self.factory = AdapterFactory()

    def test_create_code_based(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        assert isinstance(adapter, LegacyStrategyAdapter)
        assert adapter.adaptation_mode == AdaptationMode.PARAMETER_BRIDGE

    def test_create_json_based(self, json_metadata):
        adapter = self.factory.create(json_metadata)
        assert adapter.adaptation_mode == AdaptationMode.BEHAVIOR_DELEGATE

    def test_create_all(self, basic_metadata, json_metadata):
        adapters = self.factory.create_batch([basic_metadata, json_metadata])
        assert len(adapters) == 2

    def test_create_preserves_metadata(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        assert adapter.metadata.strategy_name == basic_metadata.strategy_name

    def test_create_with_override_mode(self, basic_metadata):
        adapter = self.factory.create(basic_metadata, mode=AdaptationMode.FULL_WRAP)
        assert adapter.adaptation_mode == AdaptationMode.FULL_WRAP

    def test_describe_adaptation(self, basic_metadata):
        desc = self.factory.describe_adaptation(basic_metadata)
        assert "chosen_mode" in desc
        assert "gap_count" in desc
        assert desc["can_adapt"] is True

    def test_fill_gaps_stop_loss(self, basic_metadata):
        from dataclasses import replace
        no_stop = replace(basic_metadata, stop_loss_pct=0.0)
        adapter = self.factory.create(no_stop)
        assert adapter.metadata.stop_loss_pct == no_stop.max_loss_pct


class TestAdapterRegistry:
    def setup_method(self):
        self.registry = AdapterRegistry()
        self.factory  = AdapterFactory()

    def _make_adapter(self, metadata):
        return self.factory.create(metadata)

    def test_register_and_get_by_name(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        found = self.registry.get_by_name(basic_metadata.strategy_name)
        assert found is adapter

    def test_get_by_id(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        found = self.registry.get(basic_metadata.strategy_id)
        assert found is adapter

    def test_count(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        assert self.registry.count() == 1

    def test_all(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        all_adapters = self.registry.all()
        assert adapter in all_adapters

    def test_names(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        assert basic_metadata.strategy_name in self.registry.names()

    def test_contains(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        assert self.registry.contains(basic_metadata.strategy_id)

    def test_remove(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        removed = self.registry.remove(basic_metadata.strategy_id)
        assert removed is True
        assert self.registry.get_by_name(basic_metadata.strategy_name) is None

    def test_remove_nonexistent_returns_false(self):
        assert self.registry.remove("does-not-exist") is False

    def test_by_source(self, basic_metadata):
        adapter = self._make_adapter(basic_metadata)
        self.registry.register(adapter)
        found = self.registry.by_source(basic_metadata.source)
        assert len(found) >= 1
