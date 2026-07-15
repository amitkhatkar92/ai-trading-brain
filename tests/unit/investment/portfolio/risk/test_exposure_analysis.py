"""tests/unit/investment/portfolio/risk/test_exposure_analysis.py"""
import pytest
from iios.investment.portfolio.risk.asset_exposure import analyze_asset_exposure
from iios.investment.portfolio.risk.factor_exposure import analyze_factor_exposure
from iios.investment.portfolio.risk.style_exposure import analyze_style_exposure
from iios.investment.portfolio.risk.exposure_statistics import compute_exposure_statistics
from iios.investment.portfolio.risk.portfolio_exposure import (
    PortfolioExposureAnalyzer, PortfolioExposureReport,
)


# ── Asset exposure ──────────────────────────────────────────────────────────

def test_asset_exposure_empty():
    r = analyze_asset_exposure([])
    assert r.n_asset_classes == 0


def test_asset_exposure_hhi_range(positions_5_diverse):
    r = analyze_asset_exposure(positions_5_diverse)
    assert 0.0 <= r.asset_class_hhi <= 1.0


def test_asset_exposure_dominant_set(positions_5_diverse):
    r = analyze_asset_exposure(positions_5_diverse)
    assert r.dominant_class != ""


def test_asset_exposure_n_classes(positions_5_diverse):
    r = analyze_asset_exposure(positions_5_diverse)
    assert r.n_asset_classes >= 1


def test_asset_exposure_to_dict(positions_5_diverse):
    d = analyze_asset_exposure(positions_5_diverse).to_dict()
    assert "asset_class_weights" in d


# ── Factor exposure ──────────────────────────────────────────────────────────

def test_factor_exposure_empty():
    r = analyze_factor_exposure([])
    assert r.dominant_factor == "none"


def test_factor_exposure_returns(positions_5_diverse):
    r = analyze_factor_exposure(positions_5_diverse)
    assert r.dominant_factor in ("quality", "value", "growth", "momentum", "low_vol")


def test_factor_exposure_tilts_in_range(positions_5_diverse):
    r = analyze_factor_exposure(positions_5_diverse)
    for tilt in (r.quality_tilt, r.value_tilt, r.growth_tilt, r.momentum_tilt):
        assert 0.0 <= tilt <= 1.0


def test_factor_exposure_to_dict(positions_5_diverse):
    d = analyze_factor_exposure(positions_5_diverse).to_dict()
    assert "quality_tilt" in d


# ── Style exposure ───────────────────────────────────────────────────────────

def test_style_exposure_empty():
    r = analyze_style_exposure([])
    assert r.dominant_style == "unknown"


def test_style_exposure_returns(positions_5_diverse):
    r = analyze_style_exposure(positions_5_diverse)
    assert r.dominant_style in ("growth", "value", "quality", "defensive", "cyclical")


def test_style_tilts_have_signs(positions_5_diverse):
    r = analyze_style_exposure(positions_5_diverse)
    # just ensure they are float
    assert isinstance(r.growth_vs_value, float)
    assert isinstance(r.defensive_vs_cyclical, float)


def test_style_to_dict(positions_5_diverse):
    d = analyze_style_exposure(positions_5_diverse).to_dict()
    assert "dominant_style" in d


# ── Exposure statistics ──────────────────────────────────────────────────────

def test_exposure_stats_empty():
    r = compute_exposure_statistics([])
    assert r.sector_hhi == 0.0


def test_exposure_stats_counts(positions_5_diverse):
    r = compute_exposure_statistics(positions_5_diverse)
    assert r.n_sectors >= 1
    assert r.n_asset_classes >= 1


def test_exposure_stats_overall_concentration(positions_5_diverse):
    r = compute_exposure_statistics(positions_5_diverse)
    assert 0.0 <= r.overall_concentration <= 1.0


def test_exposure_stats_concentrated(positions_3_concentrated):
    r = compute_exposure_statistics(positions_3_concentrated)
    assert r.top_sector_weight > 0.5


# ── Portfolio exposure report ────────────────────────────────────────────────

def test_portfolio_exposure_empty():
    analyzer = PortfolioExposureAnalyzer()
    r = analyzer.analyze([], "p1")
    assert r.n_positions == 0


def test_portfolio_exposure_returns_report(positions_5_diverse):
    analyzer = PortfolioExposureAnalyzer()
    r = analyzer.analyze(positions_5_diverse, "p1", "plan1")
    assert isinstance(r, PortfolioExposureReport)
    assert r.portfolio_id == "p1"
    assert r.plan_id == "plan1"
    assert r.n_positions == 5


def test_portfolio_exposure_has_subresults(positions_5_diverse):
    analyzer = PortfolioExposureAnalyzer()
    r = analyzer.analyze(positions_5_diverse)
    assert r.asset is not None
    assert r.factor is not None
    assert r.style is not None
    assert r.statistics is not None


def test_portfolio_exposure_sector_weights(positions_5_diverse):
    analyzer = PortfolioExposureAnalyzer()
    r = analyzer.analyze(positions_5_diverse)
    assert len(r.sector_weights) >= 1


def test_portfolio_exposure_to_dict(positions_5_diverse):
    analyzer = PortfolioExposureAnalyzer()
    d = analyzer.analyze(positions_5_diverse).to_dict()
    assert "sector_weights" in d
    assert "n_positions" in d
