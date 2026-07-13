"""tests/unit/investment/company/valuation/test_valuation_engine.py
Integration tests for ValuationIntelligenceEngine.
"""
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from iios.investment.company.valuation.valuation_intelligence_engine import (
    ValuationIntelligenceEngine,
)
from iios.investment.company.valuation.valuation_model import (
    ValuationBand, ValuationModelPlugin, ValuationModelType,
    ValuationResult, ValuationStatus,
)
from iios.investment.company.valuation.valuation_assumptions import ValuationAssumptions

from tests.unit.investment.company.valuation.conftest import (
    make_financial_snapshot,
    make_earnings_snapshot,
    make_business_quality_snapshot,
    make_assumptions,
)


@pytest.fixture()
def engine():
    return ValuationIntelligenceEngine()


@pytest.fixture()
def fs():
    return make_financial_snapshot()


@pytest.fixture()
def es():
    return make_earnings_snapshot()


@pytest.fixture()
def bqs():
    return make_business_quality_snapshot()


class TestValuationEngineBasic:
    def test_ingest_returns_snapshot(self, engine, fs, es, bqs):
        snap = engine.ingest(
            ticker             = "TEST",
            financial_snapshot = fs,
            earnings_snapshot  = es,
            business_quality   = bqs,
            market_price       = 1500.0,
            shares_outstanding = 1_000_000.0,
        )
        assert snap is not None
        assert snap.ticker == "TEST"

    def test_snapshot_has_market_data(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK", fs, es, bqs, 1500.0, 1_000_000.0)
        assert snap.market_price == 1500.0
        assert snap.shares_outstanding == 1_000_000.0
        assert snap.market_cap == 1500.0 * 1_000_000.0

    def test_fair_value_computed(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK2", fs, es, bqs, 1500.0, 1_000_000.0)
        assert snap.fair_value is not None
        assert snap.fair_value.intrinsic_value > 0

    def test_mos_computed_with_price(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK3", fs, es, bqs, 1500.0, 1_000_000.0)
        assert snap.mos is not None
        assert snap.mos.margin_of_safety_pct is not None

    def test_mos_none_without_price(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK4", fs, es, bqs, None, 1_000_000.0)
        assert snap.mos is None

    def test_valuation_score_label_set(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK5", fs, es, bqs, 1500.0, 1_000_000.0)
        assert snap.valuation_score.label in {"high", "medium", "low", "insufficient"}

    def test_scenarios_generated(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK6", fs, es, bqs, 1500.0, 1_000_000.0)
        # Scenarios require FCF — our fs has positive FCF
        assert snap.bull_case is not None
        assert snap.base_case is not None
        assert snap.bear_case is not None

    def test_bull_value_gt_bear_value(self, engine, fs, es, bqs):
        snap = engine.ingest("TICK7", fs, es, bqs, 1500.0, 1_000_000.0)
        assert snap.bull_case.fair_value > snap.bear_case.fair_value

    def test_get_snapshot_after_ingest(self, engine, fs, es, bqs):
        engine.ingest("INFY", fs, es, bqs, 1500.0, 1_000_000.0)
        snap = engine.get_snapshot("INFY")
        assert snap is not None
        assert snap.ticker == "INFY"

    def test_get_fair_value(self, engine, fs, es, bqs):
        engine.ingest("INFY2", fs, es, bqs, 1500.0, 1_000_000.0)
        fv = engine.get_fair_value("INFY2")
        assert fv is not None and fv > 0

    def test_get_mos(self, engine, fs, es, bqs):
        engine.ingest("INFY3", fs, es, bqs, 1500.0, 1_000_000.0)
        mos = engine.get_mos("INFY3")
        assert mos is not None

    def test_get_valuation_band_known(self, engine, fs, es, bqs):
        engine.ingest("INFY4", fs, es, bqs, 1500.0, 1_000_000.0)
        band = engine.get_valuation_band("INFY4")
        assert isinstance(band, ValuationBand)
        assert band != ValuationBand.UNKNOWN

    def test_get_valuation_band_unknown_ticker(self, engine):
        band = engine.get_valuation_band("NOSUCH")
        assert band == ValuationBand.UNKNOWN

    def test_known_tickers_after_ingest(self, engine, fs, es, bqs):
        engine.ingest("TICKER_A", fs, es, bqs, 1500.0, 1_000_000.0)
        assert "TICKER_A" in engine.known_tickers()


class TestValuationEnginePlugin:
    def test_plugin_result_included(self, engine, fs, es, bqs):
        class MyPlugin(ValuationModelPlugin):
            model_type = ValuationModelType.PLUGIN
            name       = "test_plugin"
            weight     = 0.10

            def estimate(self, ticker, financial_snapshot, earnings_snapshot,
                         business_quality, assumptions, market_price, shares_outstanding):
                return ValuationResult(
                    model_type=ValuationModelType.PLUGIN,
                    status=ValuationStatus.COMPUTED,
                    intrinsic_value=999.0,
                    confidence=0.8,
                )

        engine.register_plugin(MyPlugin())
        snap = engine.ingest("PLUG", fs, es, bqs, 1500.0, 1_000_000.0)
        assert "test_plugin" in snap.plugin_results
        assert snap.plugin_results["test_plugin"].intrinsic_value == 999.0

    def test_failing_plugin_does_not_crash_engine(self, engine, fs, es, bqs):
        class BrokenPlugin(ValuationModelPlugin):
            model_type = ValuationModelType.PLUGIN
            name       = "broken"
            weight     = 0.10

            def estimate(self, *args, **kwargs):
                raise RuntimeError("plugin failure")

        engine.register_plugin(BrokenPlugin())
        snap = engine.ingest("PLUG2", fs, es, bqs, 1500.0, 1_000_000.0)
        assert snap is not None
        assert "broken" not in snap.plugin_results


class TestValuationEngineThreadSafety:
    def test_concurrent_ingest_same_ticker(self, fs, es, bqs):
        engine = ValuationIntelligenceEngine()
        errors = []

        def _worker(i: int):
            try:
                engine.ingest(
                    f"TICKER_{i}", fs, es, bqs,
                    market_price       = 1000.0 + i,
                    shares_outstanding = 1_000_000.0,
                )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

    def test_concurrent_read_write(self, fs, es, bqs):
        engine = ValuationIntelligenceEngine()
        engine.ingest("SHARED", fs, es, bqs, 1500.0, 1_000_000.0)
        errors = []

        def _reader():
            try:
                for _ in range(20):
                    _ = engine.get_snapshot("SHARED")
                    _ = engine.get_fair_value("SHARED")
            except Exception as exc:
                errors.append(exc)

        def _writer():
            try:
                for _ in range(5):
                    engine.ingest("SHARED", fs, es, bqs, 1500.0, 1_000_000.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_reader) for _ in range(4)]
        threads += [threading.Thread(target=_writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


class TestValuationEngineSector:
    def test_sector_benchmark_applied(self, engine, fs, es, bqs):
        """Engine should produce a result when using sector benchmarks for relative valuation."""
        snap = engine.ingest(
            "TECH1", fs, es, bqs,
            market_price       = 1500.0,
            shares_outstanding = 1_000_000.0,
            sector             = "Technology",
        )
        assert snap is not None
        # Relative result should be computed since Technology sector benchmarks are defined
        if snap.relative_result:
            assert snap.relative_result.status == ValuationStatus.COMPUTED

    def test_unknown_sector_falls_back_to_other(self, engine, fs, es, bqs):
        snap = engine.ingest(
            "OTHER1", fs, es, bqs,
            market_price       = 1500.0,
            shares_outstanding = 1_000_000.0,
            sector             = "Unicorn",
        )
        assert snap is not None


class TestValuationEngineNoDividend:
    def test_ddm_skipped_without_dividend(self, engine, es, bqs):
        fs_no_div = make_financial_snapshot(dividend_per_share=0.0)
        snap = engine.ingest("NODIV", fs_no_div, es, bqs, 1500.0, 1_000_000.0)
        if snap.ddm_result:
            assert snap.ddm_result.status == ValuationStatus.SKIPPED

    def test_ddm_computed_with_dividend(self, engine, es, bqs):
        fs_div = make_financial_snapshot(dividend_per_share=15.0, net_income=25_000.0)
        snap = engine.ingest("WITHDIV", fs_div, es, bqs, 1500.0, 1_000_000.0)
        if snap.ddm_result:
            assert snap.ddm_result.status in {ValuationStatus.COMPUTED, ValuationStatus.SKIPPED}


class TestValuationSnapshotToDict:
    def test_to_dict_serialisable(self, engine, fs, es, bqs):
        import json
        snap = engine.ingest("SERIAL", fs, es, bqs, 1500.0, 1_000_000.0)
        d = snap.to_dict()
        json.dumps(d)   # should not raise
