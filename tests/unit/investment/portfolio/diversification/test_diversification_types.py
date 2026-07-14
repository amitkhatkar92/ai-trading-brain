"""test_diversification_types.py — enums, constants, PositionData, factories."""
import math
import pytest

from iios.investment.portfolio.diversification.diversification_types import (
    AlertSeverity, ConcentrationLevel, DiversificationGrade, DiversificationStatus,
    PositionData, TrendDirection,
    compute_entropy, compute_hhi, effective_n, hhi_to_concentration_level,
    positions_from_plan,
    HHI_MINIMAL_THRESHOLD, SECTOR_WARNING_THRESHOLD, TOP1_WARNING_THRESHOLD,
    CORR_SAME_INDUSTRY, CORR_SAME_SECTOR, CORR_SAME_SYMBOL,
)


class TestEnums:
    def test_all_str_enums(self):
        for e in [AlertSeverity, ConcentrationLevel, DiversificationGrade, DiversificationStatus, TrendDirection]:
            for v in e:
                assert isinstance(v.value, str)

    def test_diversification_grades(self):
        grades = {g.value for g in DiversificationGrade}
        for g in ("A","B","C","D","F"):
            assert g in grades

    def test_concentration_levels(self):
        levels = {c.value for c in ConcentrationLevel}
        for l in ("minimal","low","moderate","high","extreme"):
            assert l in levels


class TestHHI:
    def test_equal_weights_hhi(self):
        w = [0.20, 0.20, 0.20, 0.20, 0.20]
        assert abs(compute_hhi(w) - 0.20) < 1e-6

    def test_single_position_hhi_is_one(self):
        assert compute_hhi([1.0]) == 1.0

    def test_hhi_increases_with_concentration(self):
        equal = [0.25, 0.25, 0.25, 0.25]
        conc  = [0.70, 0.10, 0.10, 0.10]
        assert compute_hhi(conc) > compute_hhi(equal)

    def test_hhi_to_level_minimal(self):
        assert hhi_to_concentration_level(0.05) == ConcentrationLevel.MINIMAL

    def test_hhi_to_level_extreme(self):
        assert hhi_to_concentration_level(0.80) == ConcentrationLevel.EXTREME


class TestEntropy:
    def test_max_entropy_equal_weights(self):
        n = 5
        w = [1/n] * n
        entropy = compute_entropy(w)
        expected = math.log(n)
        assert abs(entropy - expected) < 1e-6

    def test_zero_entropy_single_position(self):
        assert abs(compute_entropy([1.0])) < 1e-6

    def test_entropy_increases_with_diversification(self):
        conc  = [0.90, 0.05, 0.05]
        equal = [1/3, 1/3, 1/3]
        assert compute_entropy(equal) > compute_entropy(conc)


class TestEffectiveN:
    def test_equal_weights_effective_n(self):
        w = [0.25, 0.25, 0.25, 0.25]
        assert abs(effective_n(w) - 4.0) < 0.01

    def test_concentrated_lower_effective_n(self):
        equal = [0.2]*5
        conc  = [0.8, 0.05, 0.05, 0.05, 0.05]
        assert effective_n(conc) < effective_n(equal)


class TestPositionData:
    def test_default_weight(self):
        p = PositionData("X", 0.25, "tech", "software", "equity")
        assert p.weight == 0.25
        assert p.sector == "tech"

    def test_to_dict(self):
        p = PositionData("X", 0.25, "tech", "software", "equity")
        d = p.to_dict()
        assert d["symbol"] == "X"
        assert d["sector"] == "tech"


class TestPositionsFromPlan:
    def test_extracts_from_optimization_plan(self, plan_5_diverse):
        positions = positions_from_plan(plan_5_diverse)
        assert len(positions) == 5
        assert all(isinstance(p, PositionData) for p in positions)

    def test_weights_normalised(self, plan_5_diverse):
        positions = positions_from_plan(plan_5_diverse)
        total = sum(p.weight for p in positions)
        assert abs(total - 1.0) < 1e-4

    def test_empty_plan(self):
        class _Empty:
            positions = []
        assert positions_from_plan(_Empty()) == []

    def test_symbol_extracted(self, plan_5_diverse):
        positions = positions_from_plan(plan_5_diverse)
        symbols = {p.symbol for p in positions}
        assert "RELIANCE" in symbols


class TestConstants:
    def test_thresholds_in_range(self):
        assert 0 < TOP1_WARNING_THRESHOLD < 1
        assert 0 < SECTOR_WARNING_THRESHOLD < 1
        assert 0 < HHI_MINIMAL_THRESHOLD < 1

    def test_correlation_ordering(self):
        assert CORR_SAME_SYMBOL > CORR_SAME_INDUSTRY > CORR_SAME_SECTOR
