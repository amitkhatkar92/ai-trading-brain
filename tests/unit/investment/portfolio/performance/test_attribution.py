"""Tests for performance attribution (BHB, sector, security, factor, strategy)."""
import pytest
from iios.investment.portfolio.performance.sector_attribution import (
    compute_sector_attribution,
)
from iios.investment.portfolio.performance.security_attribution import (
    compute_security_attribution,
)
from iios.investment.portfolio.performance.factor_attribution import (
    compute_factor_attribution, FACTOR_RETURNS,
)
from iios.investment.portfolio.performance.strategy_attribution import (
    compute_strategy_attribution,
)
from iios.investment.portfolio.performance.performance_attribution import (
    AttributionResult, PortfolioAttributionEngine,
)
from iios.investment.portfolio.performance.benchmark_engine import BenchmarkEngine


class TestSectorAttribution:
    def test_basic(self, positions_diverse):
        r = compute_sector_attribution(positions_diverse, benchmark_return=0.12)
        assert r.total_active is not None
        assert len(r.records) > 0

    def test_sectors_present(self, positions_diverse):
        r = compute_sector_attribution(positions_diverse, benchmark_return=0.12)
        sector_names = {rec.sector for rec in r.records}
        assert "Technology" in sector_names

    def test_bhb_components(self, positions_diverse):
        r = compute_sector_attribution(positions_diverse, benchmark_return=0.12)
        # Verify BHB identity: total = alloc + select + interaction
        expected = r.total_allocation + r.total_selection + r.total_interaction
        assert abs(r.total_active - expected) < 1e-9

    def test_empty(self):
        r = compute_sector_attribution([])
        assert r.total_active == 0.0
        assert len(r.records) == 0

    def test_to_dict(self, positions_diverse):
        r = compute_sector_attribution(positions_diverse, benchmark_return=0.12)
        d = r.to_dict()
        assert "total_allocation" in d
        assert "records" in d

    def test_top_sector_set(self, positions_diverse):
        r = compute_sector_attribution(positions_diverse, benchmark_return=0.12)
        assert r.top_sector != ""


class TestSecurityAttribution:
    def test_basic(self, positions_diverse):
        r = compute_security_attribution(positions_diverse)
        assert r.total_contribution != 0.0
        assert len(r.records) == 5

    def test_top_bottom_contributor(self, positions_diverse):
        r = compute_security_attribution(positions_diverse)
        assert r.top_contributor != ""
        assert r.bottom_contributor != ""
        assert r.top_contribution >= r.bottom_contribution

    def test_contribution_sum(self, positions_diverse):
        r = compute_security_attribution(positions_diverse)
        total = sum(rec.contribution for rec in r.records)
        assert abs(r.total_contribution - total) < 1e-9

    def test_outperformers_count(self, positions_diverse):
        r = compute_security_attribution(positions_diverse)
        assert r.n_outperformers + r.n_underperformers == len(positions_diverse)

    def test_empty(self):
        r = compute_security_attribution([])
        assert r.total_contribution == 0.0

    def test_to_dict(self, positions_diverse):
        r = compute_security_attribution(positions_diverse)
        d = r.to_dict()
        assert "top_contributor" in d


class TestFactorAttribution:
    def test_basic(self, positions_diverse):
        r = compute_factor_attribution(positions_diverse)
        assert len(r.records) == 6   # 6 factors

    def test_factor_names(self, positions_diverse):
        r = compute_factor_attribution(positions_diverse)
        names = {rec.factor_name for rec in r.records}
        assert names == {"quality", "momentum", "low_vol", "value", "growth", "size"}

    def test_exposure_range(self, positions_diverse):
        r = compute_factor_attribution(positions_diverse)
        for rec in r.records:
            assert -1.0 <= rec.exposure <= 1.0

    def test_dominant_factor(self, positions_diverse):
        r = compute_factor_attribution(positions_diverse)
        assert r.dominant_factor in FACTOR_RETURNS

    def test_total_contribution(self, positions_diverse):
        r = compute_factor_attribution(positions_diverse)
        total = sum(rec.contribution for rec in r.records)
        assert abs(r.total_contribution - total) < 1e-9

    def test_empty(self):
        r = compute_factor_attribution([])
        assert r.total_contribution == 0.0


class TestStrategyAttribution:
    def test_basic(self, positions_diverse):
        r = compute_strategy_attribution(positions_diverse)
        assert r.n_strategies > 0
        assert len(r.records) == r.n_strategies

    def test_strategy_buckets(self, positions_diverse):
        r = compute_strategy_attribution(positions_diverse)
        ids = {rec.strategy_id for rec in r.records}
        assert "momentum" in ids
        assert "value" in ids
        assert "quality" in ids

    def test_contribution_sum(self, positions_diverse):
        r = compute_strategy_attribution(positions_diverse)
        total = sum(rec.strategy_contribution for rec in r.records)
        assert abs(r.total_contribution - total) < 1e-9

    def test_best_strategy_set(self, positions_diverse):
        r = compute_strategy_attribution(positions_diverse)
        assert r.best_strategy != ""

    def test_concentrated(self, positions_concentrated):
        r = compute_strategy_attribution(positions_concentrated)
        assert r.n_strategies == 1

    def test_empty(self):
        r = compute_strategy_attribution([])
        assert r.n_strategies == 0


class TestPortfolioAttributionEngine:
    def test_full_attribution(self, positions_diverse):
        engine = BenchmarkEngine()
        comp = engine.run_primary(positions_diverse, 0.15, "p1")
        attr_engine = PortfolioAttributionEngine()
        result = attr_engine.analyze(positions_diverse, comp, "p1")
        assert isinstance(result, AttributionResult)
        assert result.sector_attribution is not None
        assert result.security_attribution is not None
        assert result.factor_attribution is not None
        assert result.strategy_attribution is not None

    def test_attribution_without_benchmark(self, positions_diverse):
        attr_engine = PortfolioAttributionEngine()
        result = attr_engine.analyze(positions_diverse)
        assert result.benchmark_return == 0.0

    def test_attribution_bhb_identity(self, positions_diverse):
        attr_engine = PortfolioAttributionEngine()
        result = attr_engine.analyze(positions_diverse)
        s = result.sector_attribution
        if s:
            expected = s.total_allocation + s.total_selection + s.total_interaction
            assert abs(s.total_active - expected) < 1e-9

    def test_to_dict(self, positions_diverse):
        attr_engine = PortfolioAttributionEngine()
        result = attr_engine.analyze(positions_diverse)
        d = result.to_dict()
        assert "allocation_effect" in d
        assert "selection_effect" in d
