"""tests/unit/investment/company/growth/test_growth_engine.py
Integration tests for GrowthIntelligenceEngine.
"""
from __future__ import annotations

import threading
import pytest

from iios.investment.company.growth.growth_intelligence_engine import GrowthIntelligenceEngine
from iios.investment.company.growth.growth_snapshot import GrowthSnapshot
from iios.investment.company.growth.growth_profile import GrowthTrend, GrowthIntelligenceScore
from iios.investment.company.growth.driver_registry import DriverPlugin
from iios.investment.company.growth.forecast_assumptions import ForecastAssumptions


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    return GrowthIntelligenceEngine()


# ── Basic ingest ───────────────────────────────────────────────────────────────

class TestBasicIngest:
    def test_returns_snapshot(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest(
            ticker="AAPL",
            financial_snapshot=mock_financial_snapshot,
            earnings_snapshot=mock_earnings_snapshot,
            business_quality=mock_business_quality,
        )
        assert isinstance(snap, GrowthSnapshot)
        assert snap.ticker == "AAPL"

    def test_snapshot_has_all_sub_profiles(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest(
            ticker="TEST",
            financial_snapshot=mock_financial_snapshot,
            earnings_snapshot=mock_earnings_snapshot,
            business_quality=mock_business_quality,
        )
        assert snap.revenue is not None
        assert snap.earnings is not None
        assert snap.margin is not None
        assert snap.cashflow is not None
        assert snap.drivers is not None
        assert snap.sustainability is not None
        assert snap.forecast is not None
        assert snap.quality is not None
        assert snap.growth_score is not None

    def test_confidence_in_range(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest("TCS", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        assert 0.0 <= snap.confidence <= 1.0

    def test_growth_score_in_range(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest("INFY", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        assert 0.0 <= snap.growth_score.overall_score <= 100.0

    def test_history_depth_propagated(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        mock_earnings_snapshot.history_depth = 9
        snap = engine.ingest("HDFCBANK", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        assert snap.history_depth == 9


# ── Data quality varies ────────────────────────────────────────────────────────

class TestWithMinimalData:
    def test_minimal_snapshots(
        self, engine,
        mock_financial_snapshot_no_fcf,
        mock_earnings_snapshot_minimal,
        mock_business_quality_minimal,
    ):
        snap = engine.ingest(
            ticker="MINIMAL",
            financial_snapshot=mock_financial_snapshot_no_fcf,
            earnings_snapshot=mock_earnings_snapshot_minimal,
            business_quality=mock_business_quality_minimal,
        )
        assert isinstance(snap, GrowthSnapshot)
        assert snap.quality.quality_label in (
            "insufficient", "poor", "weak", "moderate"
        )
        assert snap.confidence < 0.5


# ── Optional time series ───────────────────────────────────────────────────────

class TestWithTimeSeries:
    def test_revenue_series(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        series = [800_000.0, 880_000.0, 968_000.0, 1_064_800.0, 1_171_280.0]
        snap = engine.ingest(
            ticker="GROWTH",
            financial_snapshot=mock_financial_snapshot,
            earnings_snapshot=mock_earnings_snapshot,
            business_quality=mock_business_quality,
            revenue_series=series,
        )
        assert snap.revenue.cagr.best_available is not None
        assert snap.revenue.cagr.best_available > 0.05

    def test_eps_series(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        eps_series = [1.0, 1.2, 1.44, 1.728, 2.0736]  # 20% CAGR
        snap = engine.ingest(
            ticker="EPSGROWTH",
            financial_snapshot=mock_financial_snapshot,
            earnings_snapshot=mock_earnings_snapshot,
            business_quality=mock_business_quality,
            eps_series=eps_series,
        )
        assert snap.earnings.eps_cagr.best_available is not None
        assert snap.earnings.eps_cagr.best_available > 0.15

    def test_fcf_series(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        fcf_series = [50_000.0, 60_000.0, 72_000.0, 86_400.0]  # 20% CAGR
        snap = engine.ingest(
            ticker="FCFGROWTH",
            financial_snapshot=mock_financial_snapshot,
            earnings_snapshot=mock_earnings_snapshot,
            business_quality=mock_business_quality,
            fcf_series=fcf_series,
        )
        assert snap.cashflow.fcf_cagr.best_available is not None


# ── Retrieval API ──────────────────────────────────────────────────────────────

class TestRetrievalAPI:
    def test_get_snapshot(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        engine.ingest("SNAP1", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        snap = engine.get_snapshot("SNAP1")
        assert snap is not None
        assert snap.ticker == "SNAP1"

    def test_get_snapshot_unknown(self, engine):
        assert engine.get_snapshot("UNKNOWN_TICKER_XYZ") is None

    def test_get_eps_cagr(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        engine.ingest("CAGR1", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        cagr = engine.get_eps_cagr("CAGR1")
        assert cagr is None or (isinstance(cagr, float))

    def test_get_growth_score(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        engine.ingest("SCORE1", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        score = engine.get_growth_score("SCORE1")
        assert score is not None
        assert 0.0 <= score <= 100.0

    def test_known_tickers(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        engine.ingest("T1", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        engine.ingest("T2", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        tickers = engine.known_tickers()
        assert "T1" in tickers
        assert "T2" in tickers

    def test_get_forecast(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        engine.ingest("FC1", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        fc = engine.get_forecast("FC1")
        assert fc is not None

    def test_get_sustainability_score(
        self, engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        engine.ingest("SUS1", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        s = engine.get_sustainability_score("SUS1")
        assert s is not None
        assert 0.0 <= s <= 100.0


# ── Thread safety ──────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_ingest(
        self,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        eng = GrowthIntelligenceEngine()
        errors = []

        def _ingest(ticker):
            try:
                eng.ingest(ticker, mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=_ingest, args=(f"TICKER_{i}",))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(eng.known_tickers()) == 20


# ── Plugin system ──────────────────────────────────────────────────────────────

class TestDriverPlugin:
    def test_plugin_registration(self, engine):
        class MyPlugin(DriverPlugin):
            @property
            def name(self) -> str:
                return "test_plugin"

            def compute(self, inputs):
                return {
                    "detected_drivers": ["custom_driver"],
                    "explanation": ["Custom driver found"],
                }

        engine.register_driver_plugin(MyPlugin())
        assert engine._registry.plugin_count() == 1

    def test_plugin_contributes_to_snapshot(
        self,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        eng = GrowthIntelligenceEngine()

        class NetworkPlugin(DriverPlugin):
            @property
            def name(self) -> str:
                return "network_plugin"

            def compute(self, inputs):
                return {"detected_drivers": ["network_effects_custom"]}

        eng.register_driver_plugin(NetworkPlugin())
        snap = eng.ingest(
            "PLUGIN_TEST",
            mock_financial_snapshot,
            mock_earnings_snapshot,
            mock_business_quality,
        )
        assert "network_effects_custom" in snap.drivers.detected_drivers

    def test_invalid_plugin_rejected(self, engine):
        with pytest.raises(TypeError):
            engine.register_driver_plugin("not_a_plugin")

    def test_plugin_failure_does_not_crash_engine(
        self,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        eng = GrowthIntelligenceEngine()

        class BrokenPlugin(DriverPlugin):
            @property
            def name(self) -> str:
                return "broken_plugin"

            def compute(self, inputs):
                raise RuntimeError("Plugin crashed")

        eng.register_driver_plugin(BrokenPlugin())
        snap = eng.ingest(
            "CRASH_TEST",
            mock_financial_snapshot,
            mock_earnings_snapshot,
            mock_business_quality,
        )
        assert isinstance(snap, GrowthSnapshot)  # engine recovered


# ── Custom forecast assumptions ───────────────────────────────────────────────

class TestForecastAssumptions:
    def test_custom_assumptions(
        self,
        engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        assumptions = ForecastAssumptions(
            horizon_years=5,
            mean_reversion_weight=0.20,
            bull_multiplier=1.60,
            bear_multiplier=0.40,
        )
        snap = engine.ingest(
            "CUSTOM_ASSUME",
            mock_financial_snapshot,
            mock_earnings_snapshot,
            mock_business_quality,
            forecast_assumptions=assumptions,
        )
        assert snap.forecast.forecast_horizon_years == 5


# ── is_growing property ───────────────────────────────────────────────────────

class TestProperties:
    def test_is_growing_positive(
        self,
        engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest("GROWING", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        # With positive EPS CAGR (0.18 in mock), should be growing
        result = snap.is_growing
        assert result is True or result is None

    def test_growth_label_is_string(
        self,
        engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest("LABEL", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        assert isinstance(snap.growth_label, str)
        assert snap.growth_label in (
            "exceptional", "strong", "moderate", "weak", "poor", "insufficient"
        )

    def test_to_dict(
        self,
        engine,
        mock_financial_snapshot,
        mock_earnings_snapshot,
        mock_business_quality,
    ):
        snap = engine.ingest("DICT", mock_financial_snapshot, mock_earnings_snapshot, mock_business_quality)
        d = snap.to_dict()
        assert d["ticker"] == "DICT"
        assert "revenue" in d
        assert "earnings" in d
        assert "growth_score" in d
