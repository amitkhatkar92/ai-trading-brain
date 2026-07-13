"""tests/unit/investment/strategy/core/test_configuration.py
Tests for strategy configuration, parameter specs, registry, validation,
versioning, and configuration engine.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.core import (
    ConfigurationError, ConfigurationEngine, ConfigVersion,
    ConfigurationVersionStore, ParameterRegistry, ParameterSpec,
    ParameterValidator, StrategyConfiguration, ValidationResult,
)


# ── ParameterSpec ─────────────────────────────────────────────────────────────

class TestParameterSpec:
    def test_validate_required_missing_raises(self):
        spec = ParameterSpec(name="x", type=int, required=True)
        with pytest.raises(ConfigurationError, match="required"):
            spec.validate(None)

    def test_validate_coerces_type(self):
        spec = ParameterSpec(name="n", type=int)
        assert spec.validate("42") == 42

    def test_validate_min_value(self):
        spec = ParameterSpec(name="n", type=float, min_value=0.0)
        with pytest.raises(ConfigurationError, match="below minimum"):
            spec.validate(-1.0)

    def test_validate_max_value(self):
        spec = ParameterSpec(name="n", type=float, max_value=100.0)
        with pytest.raises(ConfigurationError, match="exceeds maximum"):
            spec.validate(101.0)

    def test_validate_choices(self):
        spec = ParameterSpec(name="mode", type=str, choices=["a", "b"])
        with pytest.raises(ConfigurationError, match="choices"):
            spec.validate("c")

    def test_validate_returns_default_when_none_and_not_required(self):
        spec = ParameterSpec(name="n", type=int, default=10)
        assert spec.validate(None) == 10

    def test_validate_valid_value_passes(self):
        spec = ParameterSpec(name="n", type=float, min_value=0.0, max_value=1.0)
        assert spec.validate(0.5) == pytest.approx(0.5)


# ── StrategyConfiguration ─────────────────────────────────────────────────────

class TestStrategyConfiguration:
    def test_get_returns_param(self):
        c = StrategyConfiguration(strategy_id="x", parameters={"alpha": 5})
        assert c.get("alpha") == 5

    def test_get_returns_default(self):
        c = StrategyConfiguration(strategy_id="x")
        assert c.get("missing", 99) == 99

    def test_override_takes_precedence(self):
        c = StrategyConfiguration(strategy_id="x", parameters={"a": 1})
        c.override("a", 99)
        assert c.get("a") == 99

    def test_clear_override_restores_base(self):
        c = StrategyConfiguration(strategy_id="x", parameters={"a": 1})
        c.override("a", 99)
        c.clear_override("a")
        assert c.get("a") == 1

    def test_all_parameters_merges(self):
        c = StrategyConfiguration(strategy_id="x", parameters={"a": 1, "b": 2})
        c.override("b", 20)
        merged = c.all_parameters()
        assert merged["a"] == 1 and merged["b"] == 20

    def test_set_updates_param(self):
        c = StrategyConfiguration(strategy_id="x")
        c.set("new_key", 42)
        assert c.get("new_key") == 42

    def test_to_dict(self):
        c = StrategyConfiguration(strategy_id="x", parameters={"k": 7})
        d = c.to_dict()
        assert d["strategy_id"] == "x"
        assert d["parameters"]["k"] == 7

    def test_copy_with(self):
        c = StrategyConfiguration(strategy_id="x", environment="paper")
        c2 = c.copy_with(environment="live")
        assert c2.environment == "live"
        assert c.environment == "paper"

    def test_clear_all_overrides(self):
        c = StrategyConfiguration(strategy_id="x", parameters={"a": 1})
        c.override("a", 99)
        c.override("b", 0)
        c.clear_all_overrides()
        assert c.get("a") == 1
        assert c.get("b") is None


# ── ParameterRegistry ─────────────────────────────────────────────────────────

class TestParameterRegistry:
    def test_register_and_get(self):
        reg = ParameterRegistry()
        spec = ParameterSpec(name="alpha", type=float, default=0.5)
        reg.register("strat1", spec)
        assert reg.get("strat1", "alpha") is spec

    def test_register_all(self):
        reg = ParameterRegistry()
        specs = [
            ParameterSpec(name="a", type=int),
            ParameterSpec(name="b", type=float),
        ]
        reg.register_all("s", specs)
        assert reg.parameter_count("s") == 2

    def test_required_parameters(self):
        reg = ParameterRegistry()
        reg.register("s", ParameterSpec(name="req", type=int, required=True))
        reg.register("s", ParameterSpec(name="opt", type=int, required=False))
        assert len(reg.required_parameters("s")) == 1
        assert len(reg.optional_parameters("s")) == 1

    def test_unknown_strategy_returns_empty(self):
        reg = ParameterRegistry()
        assert reg.specs_for("unknown") == {}

    def test_all_strategy_ids(self):
        reg = ParameterRegistry()
        reg.register("a", ParameterSpec(name="x", type=int))
        reg.register("b", ParameterSpec(name="y", type=int))
        assert set(reg.all_strategy_ids()) == {"a", "b"}


# ── ParameterValidator ────────────────────────────────────────────────────────

class TestParameterValidator:
    def _setup(self):
        reg = ParameterRegistry()
        reg.register("s", ParameterSpec(name="n", type=int, required=True))
        reg.register("s", ParameterSpec(name="x", type=float, default=0.5))
        validator = ParameterValidator(reg)
        return validator

    def test_validation_passes(self):
        v = self._setup()
        config = StrategyConfiguration(strategy_id="s", parameters={"n": 5})
        result = v.validate(config)
        assert result.passed

    def test_validation_fails_missing_required(self):
        v = self._setup()
        config = StrategyConfiguration(strategy_id="s", parameters={})
        result = v.validate(config)
        assert not result.passed
        assert len(result.errors) == 1

    def test_unknown_param_generates_warning(self):
        v = self._setup()
        config = StrategyConfiguration(
            strategy_id="s", parameters={"n": 1, "unknown_param": 99}
        )
        result = v.validate(config)
        assert len(result.warnings) >= 1

    def test_validate_and_apply_coerces(self):
        v = self._setup()
        config = StrategyConfiguration(
            strategy_id="s", parameters={"n": "10"}
        )
        result = v.validate_and_apply(config)
        assert result.passed
        assert config.get("n") == 10

    def test_validate_strict_raises_on_error(self):
        v = self._setup()
        config = StrategyConfiguration(strategy_id="s", parameters={})
        with pytest.raises(ConfigurationError):
            v.validate_strict(config)

    def test_validation_result_to_dict(self):
        result = ValidationResult(strategy_id="s")
        d = result.to_dict()
        assert "strategy_id" in d and "passed" in d


# ── ConfigurationVersionStore ─────────────────────────────────────────────────

class TestConfigurationVersionStore:
    def test_save_and_latest(self):
        store = ConfigurationVersionStore()
        config = StrategyConfiguration(strategy_id="s")
        cv = store.save(config, reason="init")
        assert store.latest("s") is cv

    def test_version_increments(self):
        store = ConfigurationVersionStore()
        config = StrategyConfiguration(strategy_id="s")
        store.save(config)
        store.save(config)
        assert store.current_version_number("s") == 2

    def test_at_version(self):
        store = ConfigurationVersionStore()
        config = StrategyConfiguration(strategy_id="s")
        cv1 = store.save(config)
        cv2 = store.save(config)
        assert store.at_version("s", cv1.version) is cv1
        assert store.at_version("s", cv2.version) is cv2

    def test_history_limited_by_n(self):
        store = ConfigurationVersionStore()
        config = StrategyConfiguration(strategy_id="s")
        for _ in range(5):
            store.save(config)
        assert len(store.history("s", n=3)) == 3

    def test_unknown_strategy_returns_none(self):
        store = ConfigurationVersionStore()
        assert store.latest("unknown") is None

    def test_config_version_to_dict(self):
        store = ConfigurationVersionStore()
        config = StrategyConfiguration(strategy_id="s")
        cv = store.save(config, reason="test")
        d = cv.to_dict()
        assert d["reason"] == "test"
        assert "config" in d

    def test_max_versions_ring_buffer(self):
        store = ConfigurationVersionStore(max_versions=3)
        config = StrategyConfiguration(strategy_id="s")
        for _ in range(6):
            store.save(config)
        assert len(store.history("s", n=10)) == 3


# ── ConfigurationEngine ───────────────────────────────────────────────────────

class TestConfigurationEngine:
    def test_build_applies_defaults(self):
        engine = ConfigurationEngine()
        engine.declare_parameter("s", ParameterSpec(name="n", type=int, default=42))
        config = engine.build("s")
        assert config.get("n") == 42

    def test_build_with_overrides(self):
        engine = ConfigurationEngine()
        engine.declare_parameter("s", ParameterSpec(name="n", type=int, default=42))
        config = engine.build("s", parameters={"n": 99})
        assert config.get("n") == 99

    def test_apply_persists_version(self):
        engine = ConfigurationEngine()
        config = StrategyConfiguration(strategy_id="s")
        engine.apply(config, reason="first", validate=False)
        assert engine.current_version("s") == 1

    def test_validate_returns_result(self):
        engine = ConfigurationEngine()
        config = StrategyConfiguration(strategy_id="s")
        result = engine.validate(config)
        assert isinstance(result, ValidationResult)

    def test_update_parameter(self):
        engine = ConfigurationEngine()
        config = StrategyConfiguration(strategy_id="s", parameters={"x": 1})
        engine.update_parameter(config, "x", 99, reason="update")
        assert config.get("x") == 99
        assert engine.current_version("s") == 1

    def test_latest_config_after_apply(self):
        engine = ConfigurationEngine()
        config = StrategyConfiguration(strategy_id="s")
        engine.apply(config, validate=False)
        assert engine.latest_config("s") is config

    def test_config_history(self):
        engine = ConfigurationEngine()
        config = StrategyConfiguration(strategy_id="s")
        engine.apply(config, validate=False)
        engine.apply(config, validate=False)
        assert len(engine.config_history("s")) == 2

    def test_parameter_registry_accessible(self):
        engine = ConfigurationEngine()
        assert engine.parameter_registry is not None
