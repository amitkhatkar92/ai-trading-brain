"""test_concentration_analysis.py"""
import pytest

from iios.investment.portfolio.diversification.concentration_analysis import (
    analyze_exposure_concentration,
    analyze_position_concentration,
)
from iios.investment.portfolio.diversification.concentration_engine import ConcentrationEngine
from iios.investment.portfolio.diversification.sector_concentration import analyze_sector_concentration
from iios.investment.portfolio.diversification.factor_concentration import analyze_factor_concentration
from iios.investment.portfolio.diversification.diversification_types import (
    ConcentrationLevel, PositionData,
)


class TestPositionConcentration:
    def test_equal_weights_moderate(self, positions_5_diverse):
        # 5 × 0.20 → HHI = 0.20, which falls in the MODERATE band (0.18–0.25)
        r = analyze_position_concentration(positions_5_diverse)
        assert r.hhi == pytest.approx(0.20, abs=1e-4)
        assert r.effective_n == pytest.approx(5.0, abs=0.01)
        assert r.concentration_level == ConcentrationLevel.MODERATE

    def test_ten_equal_weights_low_or_minimal(self, positions_10_balanced):
        # 10 × 0.10 → HHI = 0.10; boundary is MINIMAL/LOW depending on operator (<=)
        r = analyze_position_concentration(positions_10_balanced)
        assert r.hhi == pytest.approx(0.10, abs=1e-4)
        assert r.concentration_level in (ConcentrationLevel.MINIMAL, ConcentrationLevel.LOW)

    def test_concentrated_top1(self, positions_3_concentrated):
        r = analyze_position_concentration(positions_3_concentrated)
        assert r.top1_weight == pytest.approx(0.60, abs=1e-4)
        assert r.top1_symbol == "TCS"

    def test_top5_capped_at_n(self, positions_3_concentrated):
        r = analyze_position_concentration(positions_3_concentrated)
        assert r.top5_weight == pytest.approx(1.0, abs=1e-4)  # only 3 positions

    def test_empty_positions(self):
        r = analyze_position_concentration([])
        assert r.n_positions == 0

    def test_n_positions_count(self, positions_10_balanced):
        r = analyze_position_concentration(positions_10_balanced)
        assert r.n_positions == 10

    def test_entropy_positive(self, positions_5_diverse):
        r = analyze_position_concentration(positions_5_diverse)
        assert r.entropy > 0


class TestExposureConcentration:
    def test_sector_exposure(self, positions_3_concentrated):
        r = analyze_exposure_concentration(positions_3_concentrated, "sector")
        # technology: TCS(0.60) + INFY(0.25) = 0.85
        assert r.bucket_weights.get("technology", 0) == pytest.approx(0.85, abs=1e-4)
        assert r.top1_bucket == "technology"

    def test_n_buckets_correct(self, positions_5_diverse):
        r = analyze_exposure_concentration(positions_5_diverse, "sector")
        assert r.n_buckets == 5  # 5 unique sectors

    def test_empty_returns_default(self):
        r = analyze_exposure_concentration([], "sector")
        assert r.n_buckets == 0


class TestSectorConcentration:
    def test_report_has_all_dimensions(self, positions_5_diverse):
        r = analyze_sector_concentration(positions_5_diverse)
        assert r.sector.n_buckets > 0
        assert r.industry.n_buckets > 0
        assert r.asset_class.n_buckets > 0

    def test_sector_count(self, positions_5_diverse):
        r = analyze_sector_concentration(positions_5_diverse)
        assert r.sector_count == 5


class TestFactorConcentration:
    def test_returns_factor_exposure(self, positions_5_diverse):
        f = analyze_factor_concentration(positions_5_diverse)
        assert 0.0 <= f.quality_tilt <= 1.0
        assert 0.0 <= f.volatility_tilt <= 1.0
        assert 0.0 <= f.momentum_tilt <= 1.0

    def test_high_conviction_raises_quality_tilt(self):
        high_conv = [PositionData("X", 0.5, "tech", "sw", "equity", conviction=0.90)]
        low_conv  = [PositionData("Y", 0.5, "tech", "sw", "equity", conviction=0.30)]
        assert analyze_factor_concentration(high_conv).quality_tilt > analyze_factor_concentration(low_conv).quality_tilt

    def test_empty_returns_default(self):
        f = analyze_factor_concentration([])
        assert f.quality_tilt == 0.5


class TestConcentrationEngine:
    def test_full_report(self, positions_5_diverse):
        e = ConcentrationEngine()
        r = e.evaluate(positions_5_diverse, "P1", "plan1")
        assert r.portfolio_id == "P1"
        assert r.plan_id      == "plan1"
        assert r.position.n_positions == 5

    def test_concentrated_flags(self, positions_3_concentrated):
        e = ConcentrationEngine()
        r = e.evaluate(positions_3_concentrated)
        assert r.has_position_concentration  # TCS is 60%
        assert r.has_sector_concentration

    def test_well_diversified_no_flags(self, positions_10_balanced):
        e = ConcentrationEngine()
        r = e.evaluate(positions_10_balanced)
        assert not r.has_position_concentration

    def test_warnings_generated(self, positions_3_concentrated):
        e = ConcentrationEngine()
        r = e.evaluate(positions_3_concentrated)
        assert len(r.warnings) > 0

    def test_empty_positions(self):
        e = ConcentrationEngine()
        r = e.evaluate([])
        assert r.position.n_positions == 0
