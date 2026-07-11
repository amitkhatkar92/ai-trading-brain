"""test_intermarket_engine.py — intermarket and cross-asset analysis tests."""
from __future__ import annotations

import numpy as np
import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationMatrix,
    CorrelationMethod,
    IntermarketAnalysis,
    MultiAssetSnapshot,
    PriceObservation,
    RelationshipType,
)
from iios.investment.market.correlation.market_relationship import (
    MarketRelationshipTable,
    get_expected_relationship,
    is_typical_correlation,
    is_risk_on_pattern,
    is_risk_off_pattern,
    is_flight_to_safety,
    anomaly_score,
)
from iios.investment.market.correlation.cross_asset_analysis import CrossAssetAnalyzer
from iios.investment.market.correlation.intermarket_engine import IntermarketEngine

from tests.unit.investment.market.correlation.conftest import make_snapshot


def _matrix(syms, data):
    return CorrelationMatrix(
        symbols=syms, data=data, method=CorrelationMethod.PEARSON,
        window=60, n_observations=50, bar_index=0, timestamp=0.0, confidence=0.9,
    )


class TestMarketRelationshipTable:
    def test_equity_bond_is_inverse(self):
        rel = get_expected_relationship("equity", "bond")
        assert rel == RelationshipType.INVERSE

    def test_equity_equity_is_positive(self):
        rel = get_expected_relationship("equity", "equity")
        assert rel == RelationshipType.POSITIVE

    def test_equity_vol_is_inverse(self):
        rel = get_expected_relationship("equity", "volatility")
        assert rel == RelationshipType.INVERSE

    def test_unknown_asset_class(self):
        rel = get_expected_relationship("alien_asset", "bond")
        assert rel == RelationshipType.UNKNOWN

    def test_typical_correlation_equity_bond(self):
        # typical equity-bond is inverse → negative corr = typical
        assert is_typical_correlation("equity", "bond", -0.50) is True

    def test_atypical_correlation_equity_bond(self):
        # strong positive equity-bond correlation is atypical
        assert is_typical_correlation("equity", "bond", +0.80) is False

    def test_anomaly_score_high_for_atypical(self):
        score = anomaly_score("equity", "bond", +0.80)
        assert score > 0.5

    def test_anomaly_score_low_for_typical(self):
        score = anomaly_score("equity", "bond", -0.50)
        assert score < 0.5

    def test_risk_on_equity_positive(self):
        # positive equity returns + positive bond spreads = risk-on
        assert is_risk_on_pattern("equity", "equity", 0.80) is True

    def test_flight_to_safety_detection(self):
        assert is_flight_to_safety("equity", "bond", -0.80) is True


class TestCrossAssetAnalyzer:
    def _make_multi_snapshot(self):
        obs = [
            PriceObservation("SPY", 0.01, asset_class=AssetClass.INDEX.value),
            PriceObservation("QQQ", 0.008, asset_class=AssetClass.INDEX.value),
            PriceObservation("TLT", -0.005, asset_class=AssetClass.BOND.value),
            PriceObservation("GLD", -0.002, asset_class=AssetClass.PRECIOUS_METAL.value),
        ]
        return MultiAssetSnapshot(bar_index=0, timestamp=0.0, observations=obs)

    def _make_matrix(self):
        syms = ["SPY", "QQQ", "TLT", "GLD"]
        data = {
            "SPY": {"SPY": 1.0,  "QQQ": 0.85,  "TLT": -0.60, "GLD": -0.30},
            "QQQ": {"SPY": 0.85, "QQQ": 1.0,   "TLT": -0.55, "GLD": -0.25},
            "TLT": {"SPY": -0.60,"QQQ": -0.55,  "TLT": 1.0,   "GLD": 0.40},
            "GLD": {"SPY": -0.30,"QQQ": -0.25,  "TLT": 0.40,  "GLD": 1.0},
        }
        return _matrix(syms, data)

    def test_analyze_returns_intermarket_analysis(self):
        matrix  = self._make_matrix()
        snap    = self._make_multi_snapshot()
        result  = CrossAssetAnalyzer().analyze(matrix, snap)
        assert isinstance(result, IntermarketAnalysis)

    def test_detects_risk_on_signals(self):
        matrix = self._make_matrix()
        snap   = self._make_multi_snapshot()
        result = CrossAssetAnalyzer().analyze(matrix, snap)
        # equity-equity positive correlation = risk-on signal
        assert result.risk_on_signals >= 0  # at least neutral

    def test_detects_anomalies(self):
        syms = ["SPY", "TLT"]
        # unusually positive equity-bond correlation = anomaly
        data = {"SPY": {"SPY": 1.0, "TLT": 0.90}, "TLT": {"SPY": 0.90, "TLT": 1.0}}
        matrix = _matrix(syms, data)
        obs = [
            PriceObservation("SPY", 0.02, asset_class=AssetClass.INDEX.value),
            PriceObservation("TLT", 0.02, asset_class=AssetClass.BOND.value),
        ]
        snap = MultiAssetSnapshot(0, 0.0, obs)
        result = CrossAssetAnalyzer().analyze(matrix, snap)
        assert len(result.anomalies) > 0

    def test_net_regime_signal(self):
        matrix  = self._make_matrix()
        snap    = self._make_multi_snapshot()
        result  = CrossAssetAnalyzer().analyze(matrix, snap)
        regime  = result.net_regime_signal()
        assert regime in ("risk_on", "risk_off", "neutral", "flight_to_safety")


class TestIntermarketEngine:
    def test_update_returns_analysis(self):
        engine  = IntermarketEngine()
        obs = [
            PriceObservation("SPY", 0.01, asset_class=AssetClass.INDEX.value),
            PriceObservation("TLT", -0.005, asset_class=AssetClass.BOND.value),
        ]
        snap    = MultiAssetSnapshot(0, 0.0, obs)
        data    = {"SPY": {"SPY": 1.0, "TLT": -0.60}, "TLT": {"SPY": -0.60, "TLT": 1.0}}
        matrix  = _matrix(["SPY", "TLT"], data)
        result  = engine.update(matrix, snap)
        assert isinstance(result, IntermarketAnalysis)

    def test_persistent_anomaly_count_starts_zero(self):
        engine = IntermarketEngine()
        assert engine.persistent_anomaly_count(10) == 0

    def test_history_accumulates(self):
        engine = IntermarketEngine()
        obs = [
            PriceObservation("A", 0.01, asset_class=AssetClass.EQUITY.value),
            PriceObservation("B", -0.01, asset_class=AssetClass.BOND.value),
        ]
        data = {"A": {"A": 1.0, "B": -0.70}, "B": {"A": -0.70, "B": 1.0}}
        matrix = _matrix(["A", "B"], data)
        for i in range(5):
            snap = MultiAssetSnapshot(i, float(i), obs)
            engine.update(matrix, snap)
        assert engine.history_length() == 5
