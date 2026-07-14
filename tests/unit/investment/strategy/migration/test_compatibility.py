"""Tests for compatibility layer and validators."""
import pytest

from iios.investment.strategy.migration.compatibility_layer import CompatibilityLayer
from iios.investment.strategy.migration.compatibility_validator import CompatibilityValidator
from iios.investment.strategy.migration.migration_validator import MigrationValidator
from iios.investment.strategy.migration.validation_report import (
    CheckSeverity,
    ValidationReport,
)
from iios.investment.strategy.migration.adapter_factory import AdapterFactory
from iios.investment.strategy.strategy_constants import (
    AssetClass,
    MarketRegime,
    StrategyCategory,
    StrategyTimeframe,
)


class TestCompatibilityLayer:
    def test_translate_params_min_rr(self):
        result = CompatibilityLayer.translate_params({"min_rr": 2.0})
        assert "minimum_risk_reward_ratio" in result
        assert result["minimum_risk_reward_ratio"] == 2.0

    def test_translate_params_preserves_unknown_keys(self):
        result = CompatibilityLayer.translate_params({"custom_key": 99})
        assert result["custom_key"] == 99

    def test_translate_params_non_destructive(self):
        original = {"min_rr": 1.5, "stop_loss_pct": 0.02}
        result = CompatibilityLayer.translate_params(original)
        assert "min_rr" not in result    # translated
        assert "stop_loss_pct" not in result    # translated

    def test_translate_regime_to_iios_bull(self):
        r = CompatibilityLayer.translate_regime_to_iios("bull_trend")
        assert r == MarketRegime.BULL

    def test_translate_regime_to_iios_unknown(self):
        r = CompatibilityLayer.translate_regime_to_iios("unknown_regime")
        assert r is None

    def test_translate_regime_to_legacy(self):
        legacy = CompatibilityLayer.translate_regime_to_legacy("bull")
        assert legacy is not None

    def test_translate_regimes_list(self):
        regimes = CompatibilityLayer.translate_regimes_to_iios(["bull_trend", "bear_market"])
        assert MarketRegime.BULL in regimes
        assert MarketRegime.BEAR in regimes

    def test_infer_asset_class_equity(self):
        ac = CompatibilityLayer.infer_asset_class("breakout", "Breakout_Volume")
        assert ac == AssetClass.EQUITY

    def test_infer_asset_class_options(self):
        ac = CompatibilityLayer.infer_asset_class("options", "Bull_Call_Spread")
        assert ac == AssetClass.OPTIONS

    def test_infer_timeframe_default(self):
        tf = CompatibilityLayer.infer_timeframe("Breakout_Volume")
        assert isinstance(tf, StrategyTimeframe)

    def test_infer_category_breakout(self):
        cat = CompatibilityLayer.infer_category("Breakout_Volume", "breakout")
        assert cat == StrategyCategory.BREAKOUT

    def test_infer_category_momentum(self):
        cat = CompatibilityLayer.infer_category("Momentum_Retest", "momentum")
        assert cat == StrategyCategory.MOMENTUM

    def test_check_interface_gaps_valid(self, basic_metadata):
        gaps = CompatibilityLayer.check_interface_gaps(basic_metadata)
        assert isinstance(gaps, list)

    def test_check_interface_gaps_invalid_min_rr(self, invalid_metadata):
        gaps = CompatibilityLayer.check_interface_gaps(invalid_metadata)
        assert any("min_rr" in g for g in gaps)

    def test_build_iios_params(self, basic_metadata):
        params = CompatibilityLayer.build_iios_params(basic_metadata)
        assert "minimum_risk_reward_ratio" in params
        assert "legacy_source" in params

    def test_translate_regimes_deduplicates(self):
        regimes = CompatibilityLayer.translate_regimes_to_iios(
            ["bull_trend", "bull"]
        )
        assert regimes.count(MarketRegime.BULL) == 1


class TestCompatibilityValidator:
    def setup_method(self):
        self.validator = CompatibilityValidator()

    def test_validate_valid_strategy(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        assert isinstance(report, ValidationReport)

    def test_validate_passes_for_clean_metadata(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        assert report.is_migration_approved

    def test_validate_fails_for_invalid_metadata(self, invalid_metadata):
        report = self.validator.validate(invalid_metadata)
        assert not report.is_migration_approved

    def test_report_has_checks(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        assert len(report.checks) > 0

    def test_report_has_strategy_name(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        assert report.strategy_name == basic_metadata.strategy_name

    def test_report_has_duration(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        assert report.duration_ms > 0

    def test_report_compatibility_level(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        assert report.compatibility_level in (
            "full", "partial", "requires_adapter", "incompatible"
        )

    def test_invalid_min_rr_causes_error(self, invalid_metadata):
        report = self.validator.validate(invalid_metadata)
        blocking = [
            c for c in report.checks
            if c.severity in (CheckSeverity.ERROR, CheckSeverity.FATAL)
        ]
        assert len(blocking) > 0

    def test_to_dict(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        d = report.to_dict()
        assert "strategy_id" in d
        assert "checks" in d

    def test_validation_check_to_dict(self, basic_metadata):
        report = self.validator.validate(basic_metadata)
        for c in report.checks:
            d = c.to_dict()
            assert "check_type" in d
            assert "name" in d
            assert "severity" in d


class TestMigrationValidator:
    def setup_method(self):
        self.validator = MigrationValidator()
        self.factory   = AdapterFactory()

    def test_validate_metadata(self, basic_metadata):
        report = self.validator.validate_metadata(basic_metadata)
        assert isinstance(report, ValidationReport)

    def test_validate_adapter_valid(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        result  = self.validator.validate_adapter(adapter)
        assert result.is_valid
        assert len(result.issues) == 0

    def test_validate_and_create_report(self, basic_metadata):
        adapter = self.factory.create(basic_metadata)
        report  = self.validator.validate_and_create_report(basic_metadata, adapter)
        assert isinstance(report, ValidationReport)

    def test_validate_and_create_report_no_adapter(self, basic_metadata):
        report = self.validator.validate_and_create_report(basic_metadata, None)
        assert isinstance(report, ValidationReport)
