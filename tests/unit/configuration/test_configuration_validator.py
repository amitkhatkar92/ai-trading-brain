"""
tests/unit/configuration/test_configuration_validator.py
=========================================================
Unit tests for ConfigurationValidator and schema validation.
"""

from __future__ import annotations

import pytest

from iios.configuration.configuration_exception import (
    ConfigurationValidationError,
    FieldValidationError,
)
from iios.configuration.configuration_schema import FieldSpec, SectionSchema, IIOS_SCHEMA
from iios.configuration.configuration_validator import (
    ConfigurationValidator,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# FieldSpec
# ---------------------------------------------------------------------------


class TestFieldSpec:
    def test_valid_string(self):
        spec = FieldSpec("env", str, allowed_values=["development", "production"])
        spec.validate("development", "system")  # no raise

    def test_invalid_allowed_value(self):
        spec = FieldSpec("env", str, allowed_values=["development", "production"])
        with pytest.raises(FieldValidationError):
            spec.validate("staging", "system")

    def test_range_min_violation(self):
        spec = FieldSpec("port", int, min_value=1024)
        with pytest.raises(FieldValidationError):
            spec.validate(80, "network")

    def test_range_max_violation(self):
        spec = FieldSpec("pct", float, min_value=0.0, max_value=1.0)
        with pytest.raises(FieldValidationError):
            spec.validate(1.5, "risk")

    def test_required_missing(self):
        spec = FieldSpec("token", str, required=True)
        with pytest.raises(FieldValidationError):
            spec.validate("", "notification")

    def test_none_not_required(self):
        spec = FieldSpec("optional", str, required=False)
        spec.validate(None, "test")  # no raise

    def test_valid_range(self):
        spec = FieldSpec("vix", float, min_value=5.0, max_value=200.0)
        spec.validate(45.0, "risk")  # no raise


# ---------------------------------------------------------------------------
# SectionSchema
# ---------------------------------------------------------------------------


class TestSectionSchema:
    def _make_schema(self) -> SectionSchema:
        s = SectionSchema("test_section")
        s.add_field(FieldSpec("level", str, allowed_values=["DEBUG", "INFO", "WARNING"]))
        s.add_field(FieldSpec("max_retries", int, min_value=0, max_value=10))
        return s

    def test_valid_data_no_errors(self):
        schema = self._make_schema()
        errors = schema.validate({"level": "INFO", "max_retries": 3})
        assert errors == []

    def test_invalid_data_returns_errors(self):
        schema = self._make_schema()
        errors = schema.validate({"level": "TRACE", "max_retries": 3})
        assert len(errors) == 1
        assert "level" in errors[0].field

    def test_out_of_range_int(self):
        schema = self._make_schema()
        errors = schema.validate({"level": "INFO", "max_retries": 99})
        assert len(errors) == 1
        assert "max_retries" in errors[0].field


# ---------------------------------------------------------------------------
# ConfigurationValidator
# ---------------------------------------------------------------------------


class TestConfigurationValidator:
    def _make_valid_data(self) -> dict:
        return {
            "risk": {
                "vix_threshold": 45.0,
                "daily_loss_pct": 0.02,
                "max_risk_per_trade_pct": 0.01,
                "kelly_fraction": 0.25,
                "atr_multiplier": 2.0,
                "max_portfolio_var_pct": 0.05,
                "max_portfolio_cvar_pct": 0.08,
                "max_drawdown_pct": 0.15,
                "max_correlation": 0.70,
            },
            "decision": {
                "decision_threshold": 6.5,
                "debate_agents": 5,
                "debate_timeout_seconds": 10.0,
                "cooldown_seconds": 60,
                "max_concurrent_decisions": 3,
            },
            "system": {
                "env": "development",
                "paper_trading": True,
                "layers": 17,
            },
        }

    def test_valid_config_passes(self):
        v = ConfigurationValidator()
        report = v.validate(self._make_valid_data())
        assert report.is_valid

    def test_invalid_env_value(self):
        v = ConfigurationValidator()
        data = self._make_valid_data()
        data["system"]["env"] = "staging"  # not in allowed_values
        report = v.validate(data)
        assert not report.is_valid
        error_fields = [e.field for e in report.errors]
        assert "env" in error_fields

    def test_vix_below_minimum(self):
        v = ConfigurationValidator()
        data = self._make_valid_data()
        data["risk"]["vix_threshold"] = 3.0  # below min_value=5.0
        report = v.validate(data)
        assert not report.is_valid

    def test_invariant_warning_on_threshold_change(self):
        v = ConfigurationValidator(enforce_invariants=True)
        data = self._make_valid_data()
        data["decision"]["decision_threshold"] = 7.0  # != 6.5
        report = v.validate(data)
        assert len(report.warnings) >= 1
        assert any("decision_threshold" in w.field for w in report.warnings)

    def test_invariant_warning_on_vix_change(self):
        v = ConfigurationValidator(enforce_invariants=True)
        data = self._make_valid_data()
        data["risk"]["vix_threshold"] = 50.0  # != 45.0
        report = v.validate(data)
        assert any("vix_threshold" in w.field for w in report.warnings)

    def test_no_invariant_warnings_with_correct_values(self):
        v = ConfigurationValidator(enforce_invariants=True)
        report = v.validate(self._make_valid_data())
        assert report.is_valid
        # No invariant warnings for certified values
        invariant_warns = [
            w for w in report.warnings
            if "threshold" in w.field or "vix" in w.field
        ]
        assert invariant_warns == []

    def test_raise_if_invalid(self):
        v = ConfigurationValidator()
        data = self._make_valid_data()
        data["system"]["env"] = "badenv"
        report = v.validate(data)
        with pytest.raises(ConfigurationValidationError):
            report.raise_if_invalid()

    def test_raise_if_valid_does_not_raise(self):
        v = ConfigurationValidator()
        report = v.validate(self._make_valid_data())
        report.raise_if_invalid()  # no raise

    def test_dotted_key_normalisation(self):
        """Flat dotted keys should be accepted alongside nested dicts."""
        v = ConfigurationValidator()
        data = {
            "system.env": "development",
            "system.paper_trading": True,
            "system.layers": 17,
        }
        report = v.validate(data)
        # Should not error on env being valid
        system_errors = [e for e in report.errors if e.section == "system"]
        assert not any(e.field == "env" for e in system_errors)

    def test_validate_single_value_valid(self):
        v = ConfigurationValidator()
        report = v.validate_value("logging", "level", "DEBUG")
        assert report.is_valid

    def test_validate_single_value_invalid(self):
        v = ConfigurationValidator()
        report = v.validate_value("logging", "level", "VERBOSE")
        assert not report.is_valid

    def test_validate_single_value_unknown_section(self):
        v = ConfigurationValidator()
        report = v.validate_value("unknown_section", "some_field", "value")
        # Should return warning, not error
        assert report.is_valid
        assert len(report.warnings) == 1


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


class TestValidationReport:
    def test_empty_report_is_valid(self):
        r = ValidationReport()
        assert r.is_valid
        assert r.errors == []
        assert r.warnings == []

    def test_add_error_marks_invalid(self):
        r = ValidationReport()
        r.add_error("risk", "vix_threshold", "bad value")
        assert not r.is_valid
        assert len(r.errors) == 1

    def test_add_warning_stays_valid(self):
        r = ValidationReport()
        r.add_warning("risk", "vix_threshold", "off certified")
        assert r.is_valid
        assert len(r.warnings) == 1

    def test_add_info(self):
        r = ValidationReport()
        r.add_info("system", "env", "using default")
        assert r.is_valid
