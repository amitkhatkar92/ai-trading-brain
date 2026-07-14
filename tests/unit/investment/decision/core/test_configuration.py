"""tests/unit/investment/decision/core/test_configuration.py
Tests for ParameterValidator, ParameterRegistry, ConfigurationVersion,
ConfigurationEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.core.configuration_engine import ConfigurationEngine
from iios.investment.decision.core.configuration_version import ConfigurationVersion
from iios.investment.decision.core.decision_configuration import (
    DEVELOPMENT_CONFIG,
    LIVE_CONFIG,
    PAPER_CONFIG,
    BACKTEST_CONFIG,
    DecisionConfiguration,
)
from iios.investment.decision.core.decision_constants import (
    DEFAULT_APPROVAL_THRESHOLD,
    EnvironmentProfile,
)
from iios.investment.decision.core.parameter_registry import (
    ParameterDescriptor,
    ParameterRegistry,
)
from iios.investment.decision.core.parameter_validation import (
    ParameterRule,
    ParameterValidator,
)


# ===========================================================================
# ParameterValidator
# ===========================================================================

class TestParameterValidator:
    def test_range_passes(self):
        v = ParameterValidator()
        v.add_range("score", 0.0, 100.0)
        results = v.validate("score", 75.0)
        assert all(r.passed for r in results)

    def test_range_fails(self):
        v = ParameterValidator()
        v.add_range("score", 0.0, 100.0)
        results = v.validate("score", 150.0)
        assert any(not r.passed for r in results)

    def test_positive_passes(self):
        v = ParameterValidator()
        v.add_positive("timeout")
        results = v.validate("timeout", 60.0)
        assert all(r.passed for r in results)

    def test_positive_fails_on_zero(self):
        v = ParameterValidator()
        v.add_positive("timeout")
        results = v.validate("timeout", 0.0)
        assert any(not r.passed for r in results)

    def test_type_check_passes(self):
        v = ParameterValidator()
        v.add_type("flag", bool)
        results = v.validate("flag", True)
        assert all(r.passed for r in results)

    def test_type_check_fails(self):
        v = ParameterValidator()
        v.add_type("flag", bool)
        results = v.validate("flag", "yes")
        assert any(not r.passed for r in results)

    def test_is_valid_all_pass(self):
        v = ParameterValidator()
        v.add_range("approval_threshold", 0.0, 100.0)
        ok, errors = v.is_valid({"approval_threshold": 65.0})
        assert ok
        assert errors == []

    def test_is_valid_failure_message(self):
        v = ParameterValidator()
        v.add_range("approval_threshold", 0.0, 100.0)
        ok, errors = v.is_valid({"approval_threshold": 150.0})
        assert not ok
        assert len(errors) > 0

    def test_validate_all(self):
        v = ParameterValidator()
        v.add_range("a", 0.0, 10.0)
        v.add_range("b", 0.0, 10.0)
        results = v.validate_all({"a": 5.0, "b": 15.0})
        assert all(r.passed for r in results["a"])
        assert any(not r.passed for r in results["b"])

    def test_no_rules_always_valid(self):
        v = ParameterValidator()
        ok, errors = v.is_valid({"x": 999})
        assert ok

    def test_to_dict(self):
        v = ParameterValidator()
        v.add_range("score", 0.0, 100.0)
        results = v.validate("score", 50.0)
        d = results[0].to_dict()
        assert "key" in d
        assert "passed" in d

    def test_custom_rule(self):
        rule = ParameterRule(
            rule_id="custom",
            rule_name="must_be_even",
            predicate=lambda v: int(v) % 2 == 0,
            message="Must be even.",
        )
        v = ParameterValidator()
        v.add_rule("n", rule)
        assert v.validate("n", 4)[0].passed
        assert not v.validate("n", 3)[0].passed


# ===========================================================================
# ParameterRegistry
# ===========================================================================

class TestParameterRegistry:
    def test_defaults_loaded(self):
        reg = ParameterRegistry()
        assert len(reg.keys()) >= 6

    def test_get_existing(self):
        reg  = ParameterRegistry()
        desc = reg.get("approval_threshold")
        assert desc is not None
        assert desc.param_type == float

    def test_get_missing_returns_none(self):
        reg = ParameterRegistry()
        assert reg.get("nonexistent") is None

    def test_register_custom(self):
        reg  = ParameterRegistry()
        desc = ParameterDescriptor(
            key="custom_param", display_name="Custom", description="",
            param_type=int, default_value=5, min_value=1, max_value=100,
            is_required=False, unit="",
        )
        reg.register(desc)
        assert reg.get("custom_param") is desc

    def test_no_duplicate_by_default(self):
        reg  = ParameterRegistry()
        desc = ParameterDescriptor(
            key="approval_threshold", display_name="Override", description="",
            param_type=float, default_value=80.0, min_value=None, max_value=None,
            is_required=True, unit="%",
        )
        reg.register(desc)
        # Should NOT overwrite by default
        assert reg.get("approval_threshold").default_value == DEFAULT_APPROVAL_THRESHOLD

    def test_overwrite_allowed(self):
        reg  = ParameterRegistry()
        desc = ParameterDescriptor(
            key="approval_threshold", display_name="Override", description="",
            param_type=float, default_value=80.0, min_value=None, max_value=None,
            is_required=True, unit="%",
        )
        reg.register(desc, overwrite=True)
        assert reg.get("approval_threshold").default_value == 80.0

    def test_defaults_dict(self):
        reg = ParameterRegistry()
        d   = reg.defaults()
        assert "approval_threshold" in d

    def test_to_dict(self):
        reg  = ParameterRegistry()
        desc = reg.get("approval_threshold")
        d    = desc.to_dict()
        assert "key" in d
        assert "param_type" in d


# ===========================================================================
# ConfigurationVersion
# ===========================================================================

class TestConfigurationVersion:
    def test_initial_version_is_1(self):
        cv = ConfigurationVersion({"a": 1})
        assert cv.version == 1

    def test_commit_increments_version(self):
        cv = ConfigurationVersion({"a": 1})
        cv.commit({"a": 2}, note="update")
        assert cv.version == 2

    def test_current_reflects_latest(self):
        cv = ConfigurationVersion({"x": 10})
        cv.commit({"x": 20})
        assert cv.current.config_data["x"] == 20

    def test_get_version_by_number(self):
        cv = ConfigurationVersion({"v": 1})
        cv.commit({"v": 2})
        snap = cv.get_version(1)
        assert snap is not None
        assert snap.config_data["v"] == 1

    def test_get_version_missing_returns_none(self):
        cv = ConfigurationVersion({"v": 1})
        assert cv.get_version(99) is None

    def test_rollback(self):
        cv = ConfigurationVersion({"x": 1})
        cv.commit({"x": 2})
        cv.commit({"x": 3})
        rolled = cv.rollback(1)
        assert rolled is not None
        assert rolled.config_data["x"] == 1

    def test_history_grows(self):
        cv = ConfigurationVersion({"h": 0})
        cv.commit({"h": 1})
        cv.commit({"h": 2})
        assert len(cv.history()) == 3

    def test_to_dict(self):
        cv   = ConfigurationVersion({"k": "v"})
        snap = cv.current
        d    = snap.to_dict()
        assert "snapshot_id" in d
        assert "version" in d


# ===========================================================================
# ConfigurationEngine
# ===========================================================================

class TestConfigurationEngine:
    def test_get_default_development(self):
        engine = ConfigurationEngine()
        cfg    = engine.get_default(EnvironmentProfile.DEVELOPMENT)
        assert cfg.environment == EnvironmentProfile.DEVELOPMENT
        assert cfg.auto_approve is True

    def test_get_default_live(self):
        engine = ConfigurationEngine()
        cfg    = engine.get_default(EnvironmentProfile.LIVE)
        assert cfg.environment == EnvironmentProfile.LIVE
        assert cfg.auto_approve is False

    def test_register_and_get(self):
        engine = ConfigurationEngine()
        cfg    = DecisionConfiguration(approval_threshold=90.0)
        engine.register("momentum", cfg)
        retrieved = engine.get("momentum")
        assert retrieved is not None
        assert retrieved.approval_threshold == 90.0

    def test_get_missing_returns_none(self):
        engine = ConfigurationEngine()
        assert engine.get("nonexistent") is None

    def test_get_or_default(self):
        engine = ConfigurationEngine()
        cfg    = engine.get_or_default("missing", EnvironmentProfile.PAPER)
        assert cfg.environment == EnvironmentProfile.PAPER

    def test_all_names(self):
        engine = ConfigurationEngine()
        engine.register("type_a", DecisionConfiguration())
        engine.register("type_b", DecisionConfiguration())
        names = engine.all_names()
        assert "type_a" in names
        assert "type_b" in names

    def test_validate_valid_config(self):
        engine = ConfigurationEngine()
        cfg    = DEVELOPMENT_CONFIG
        ok, errors = engine.validate(cfg)
        assert ok, errors

    def test_validate_invalid_config(self):
        engine = ConfigurationEngine()
        # approval_threshold out of range
        cfg    = DecisionConfiguration(approval_threshold=200.0)
        ok, errors = engine.validate(cfg)
        assert not ok

    def test_version_history_after_register(self):
        engine = ConfigurationEngine()
        engine.register("type_c", DecisionConfiguration())
        history = engine.version_history("type_c")
        assert len(history) == 1

    def test_rollback(self):
        engine = ConfigurationEngine()
        cfg1   = DecisionConfiguration(approval_threshold=60.0)
        cfg2   = DecisionConfiguration(approval_threshold=90.0)
        engine.register("type_d", cfg1)
        engine.register("type_d", cfg2, note="update")
        rolled = engine.rollback("type_d", version=1)
        assert rolled is not None
        assert rolled.approval_threshold == 60.0

    def test_rollback_missing_name_returns_none(self):
        engine = ConfigurationEngine()
        assert engine.rollback("ghost", 1) is None
