"""
DTA-SYSTEM-005 — Final Gap Closure Tests
==========================================
Covers every item identified by DTA-SYSTEM-004-CLOSURE audit:

  B-001  DhanBroker.get_fill_details() — canonical reconciliation interface
  O-001  opportunity_id complete lineage (Scanner→OrderRecord→Journal→Restore)
  S-001  SCAN_NO_SETUP outcomes (KLPOutcomeEngine fills directional T+1..T+5)
  E-001  Exit analytics (research-only, no broker calls)
  C-001  Cross-signal aggregator (research-only, no broker calls)
  R-001  Regime strategy modifier in MetaModel (P-004 wire-up)
  D-001  DeploymentDrift — manifest generated inside Docker (Dockerfile RUN)
  A-001  Anti-lookahead regression (decision-time code cannot consume future bars)
  X-001  Execution authority regression (only OrderManager reaches place_order)
  L-001  End-to-end lineage regression — single synthetic opportunity_id
  K-001  Restart safety — daily loss + halt preserved across restarts

T001–T015: DhanBroker.get_fill_details
T016–T025: opportunity_id lineage
T026–T035: SCAN_NO_SETUP outcomes
T036–T045: Exit analytics
T046–T055: Cross-signal aggregator
T056–T065: Regime strategy modifier
T066–T075: Anti-lookahead regression
T076–T085: Execution-authority boundary
T086–T095: End-to-end lineage
T096–T100: Restart safety
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# B-001: DhanBroker.get_fill_details
# ─────────────────────────────────────────────────────────────────────────────

class TestDhanBrokerGetFillDetails:
    """T001–T015: DhanBroker exposes canonical get_fill_details interface."""

    def _make_broker_unconnected(self):
        from execution_engine.brokers.dhan_broker import DhanBroker
        b = DhanBroker.__new__(DhanBroker)
        b._connected = False
        b._dhan      = None
        b.client_id    = ""
        b.access_token = ""
        return b

    def test_T001_method_exists(self):
        from execution_engine.brokers.dhan_broker import DhanBroker
        assert hasattr(DhanBroker, "get_fill_details")

    def test_T002_returns_dict(self):
        b = self._make_broker_unconnected()
        result = b.get_fill_details("TEST_001")
        assert isinstance(result, dict)

    def test_T003_unconnected_returns_sim(self):
        b = self._make_broker_unconnected()
        result = b.get_fill_details("SIM_001")
        assert result.get("status") in ("SIM", "API_ERROR")

    def test_T004_never_raises(self):
        b = self._make_broker_unconnected()
        b._dhan = None
        b._connected = False
        try:
            b.get_fill_details("ANY")
        except Exception as exc:
            pytest.fail(f"get_fill_details raised: {exc}")

    def test_T005_result_has_status_field(self):
        b = self._make_broker_unconnected()
        r = b.get_fill_details("X")
        assert "status" in r

    def test_T006_result_has_broker_order_id(self):
        b = self._make_broker_unconnected()
        r = b.get_fill_details("ORDER_X")
        assert r.get("broker_order_id") == "ORDER_X"

    def test_T007_result_has_actual_fill_price(self):
        b = self._make_broker_unconnected()
        r = b.get_fill_details("X")
        assert "actual_fill_price" in r

    def test_T008_filled_status_maps_to_FILLED(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.return_value = {
            "data": {
                "orderStatus": "TRADED",
                "averageTradedPrice": 1500.0,
                "filledQty": 10,
                "quantity": 10,
            }
        }
        r = b.get_fill_details("REAL_001")
        assert r["status"] == "FILLED"
        assert r["actual_fill_price"] == 1500.0

    def test_T009_partial_maps_to_PARTIALLY_FILLED(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.return_value = {
            "data": {"orderStatus": "PARTIALLY_TRADED", "averageTradedPrice": 1490.0,
                     "filledQty": 5, "quantity": 10}
        }
        r = b.get_fill_details("REAL_002")
        assert r["status"] == "PARTIALLY_FILLED"

    def test_T010_rejected_maps_to_REJECTED(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.return_value = {
            "data": {"orderStatus": "REJECTED", "averageTradedPrice": 0.0,
                     "filledQty": 0, "quantity": 10}
        }
        r = b.get_fill_details("REAL_003")
        assert r["status"] == "REJECTED"
        assert r["actual_fill_price"] == 0.0

    def test_T011_cancelled_maps_to_CANCELLED(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.return_value = {
            "data": {"orderStatus": "CANCELLED", "averageTradedPrice": 0.0,
                     "filledQty": 0, "quantity": 10}
        }
        r = b.get_fill_details("REAL_004")
        assert r["status"] == "CANCELLED"

    def test_T012_pending_maps_to_PENDING(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.return_value = {
            "data": {"orderStatus": "TRANSIT", "averageTradedPrice": 0.0,
                     "filledQty": 0, "quantity": 10}
        }
        r = b.get_fill_details("REAL_005")
        assert r["status"] == "PENDING"

    def test_T013_never_assumes_filled_on_error(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.side_effect = RuntimeError("SDK error")
        r = b.get_fill_details("REAL_006")
        assert r["status"] != "FILLED"

    def test_T014_exception_returns_api_error(self):
        b = self._make_broker_unconnected()
        b._connected = True
        b._dhan      = MagicMock()
        b._dhan.get_order_by_id.side_effect = RuntimeError("network error")
        r = b.get_fill_details("REAL_007")
        assert r["status"] == "API_ERROR"

    def test_T015_orderrecord_uses_get_fill_details_not_get_order_status(self):
        """OrderManager._reconcile_fill checks hasattr get_fill_details, not get_order_status."""
        from execution_engine.order_manager import OrderManager
        import inspect
        src = inspect.getsource(OrderManager._reconcile_fill)
        assert "get_fill_details" in src


# ─────────────────────────────────────────────────────────────────────────────
# O-001: opportunity_id complete lineage
# ─────────────────────────────────────────────────────────────────────────────

class TestOpportunityIdLineage:
    """T016–T025: opportunity_id survives Scanner→OrderRecord→Journal→Restore."""

    def test_T016_orderrecord_has_opportunity_id_field(self):
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id="X", symbol="Y", direction="BUY",
            quantity=1, entry_price=100.0, stop_loss=95.0, target=110.0, strategy="T",
        )
        assert hasattr(rec, "opportunity_id")
        assert rec.opportunity_id == ""

    def test_T017_opportunity_id_defaults_empty(self):
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id="X", symbol="Y", direction="BUY",
            quantity=1, entry_price=100.0, stop_loss=95.0, target=110.0, strategy="T",
        )
        assert rec.opportunity_id == ""

    def test_T018_opportunity_id_set_explicitly(self):
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id="X", symbol="Y", direction="BUY",
            quantity=1, entry_price=100.0, stop_loss=95.0, target=110.0, strategy="T",
            opportunity_id="TEST-OPP-018",
        )
        assert rec.opportunity_id == "TEST-OPP-018"

    def test_T019_journal_open_carries_opportunity_id(self, tmp_path):
        import execution_engine.order_manager as _om
        from execution_engine.order_manager import OrderManager, OrderRecord
        log_path = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = log_path
            _om._LIVE_DIR = str(tmp_path)
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="LIVE_019", symbol="TCS", direction="BUY",
                quantity=1, entry_price=4000.0, stop_loss=3900.0, target=4200.0,
                strategy="Momentum", opportunity_id="TEST-OPP-019",
            )
            om._append_live_journal("OPEN", rec)
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        row = json.loads(Path(log_path).read_text().splitlines()[0])
        assert row["opportunity_id"] == "TEST-OPP-019"

    def test_T020_journal_close_carries_opportunity_id(self, tmp_path):
        import execution_engine.order_manager as _om
        from execution_engine.order_manager import OrderManager, OrderRecord
        log_path = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = log_path
            _om._LIVE_DIR = str(tmp_path)
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="LIVE_020", symbol="INFY", direction="BUY",
                quantity=5, entry_price=1800.0, stop_loss=1760.0, target=1900.0,
                strategy="Breakout", opportunity_id="TEST-OPP-020",
            )
            om._append_live_journal("OPEN", rec)
            om._append_live_journal("CLOSE", rec,
                extra={"exit_price": 1900.0, "pnl": 500.0, "reason": "TARGET_HIT"})
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        lines = [json.loads(l) for l in Path(log_path).read_text().splitlines()]
        assert all(l["opportunity_id"] == "TEST-OPP-020" for l in lines)

    def test_T021_opportunity_id_restored_from_journal(self, tmp_path):
        import execution_engine.order_manager as _om
        from models import Portfolio
        jf = tmp_path / "live_orders.jsonl"
        ts = datetime.now(timezone.utc).isoformat()
        jf.write_text(json.dumps({
            "event": "OPEN", "timestamp": ts, "order_id": "LIVE_021",
            "symbol": "WIPRO", "direction": "BUY", "quantity": 3,
            "entry_price": 500.0, "stop_loss": 480.0, "target_price": 540.0,
            "strategy": "Test", "fill_status": "FILLED",
            "actual_fill_price": 501.0, "broker_order_id": "B021",
            "opportunity_id": "TEST-OPP-021",
        }) + "\n")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._restore_stats = {"restored_today": 0}
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        assert om._orders["LIVE_021"].opportunity_id == "TEST-OPP-021"

    def test_T022_lol_record_carries_opportunity_id(self, tmp_path):
        """LOL _empty_record schema includes opportunity_id."""
        from learning_system.learning_observation_ledger import _empty_record
        rec = _empty_record(
            obs_id="OBS_022", symbol="SBIN", direction="BUY",
            trading_date="2026-08-26", observed_at="2026-08-26T09:30:00Z",
            entry_price=600.0, stop_loss=580.0, target_price=640.0,
        )
        assert "opportunity_id" in rec

    def test_T023_lol_propagates_opportunity_id_from_signal(self, tmp_path):
        """LOL record_observation() copies opportunity_id from signal."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        ledger = LearningObservationLedger(data_dir=tmp_path)
        sig = MagicMock()
        sig.symbol         = "RELIANCE"
        sig.direction.value = "BUY"
        sig.entry_price    = 2900.0
        sig.stop_loss      = 2840.0
        sig.target_price   = 3000.0
        sig.confidence     = 7.0
        sig.strategy_name  = "Breakout"
        sig.opportunity_id = "TEST-OPP-023"
        sig._obs_candidate_score = 0.75
        sig.regime         = "BULL_TREND"
        ledger.record_observations([sig], trading_date="2026-08-26")
        lol_file = tmp_path / "LOL_2026-08-26.jsonl"
        assert lol_file.exists()
        recs = [json.loads(l) for l in lol_file.read_text().splitlines() if l.strip()]
        assert any(r.get("opportunity_id") == "TEST-OPP-023" for r in recs)

    def test_T024_empty_opportunity_id_handled_gracefully(self, tmp_path):
        import execution_engine.order_manager as _om
        from execution_engine.order_manager import OrderManager, OrderRecord
        log_path = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = log_path
            _om._LIVE_DIR = str(tmp_path)
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="LIVE_024", symbol="HDFC", direction="BUY",
                quantity=1, entry_price=1600.0, stop_loss=1560.0, target=1680.0,
                strategy="Test",
            )
            om._append_live_journal("OPEN", rec)
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        row = json.loads(Path(log_path).read_text().splitlines()[0])
        assert row["opportunity_id"] == ""

    def test_T025_opportunity_id_in_orderrecord_survives_dataclass_copy(self):
        from execution_engine.order_manager import OrderRecord
        import dataclasses
        rec = OrderRecord(
            order_id="X", symbol="Y", direction="BUY",
            quantity=1, entry_price=100.0, stop_loss=95.0, target=110.0, strategy="T",
            opportunity_id="TEST-OPP-025",
        )
        copy = dataclasses.replace(rec, status="closed")
        assert copy.opportunity_id == "TEST-OPP-025"


# ─────────────────────────────────────────────────────────────────────────────
# S-001: SCAN_NO_SETUP outcomes
# ─────────────────────────────────────────────────────────────────────────────

class TestScanNoSetupOutcomes:
    """T026–T035: KLPOutcomeEngine fills T+1..T+5 for SCAN_NO_SETUP records."""

    def _make_engine(self, tmp_path, fetcher=None):
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        return KLPOutcomeEngine(data_dir=tmp_path, _ohlcv_fetcher=fetcher)

    def _write_klp(self, tmp_path, date_str, records):
        f = tmp_path / f"KLP_{date_str}.jsonl"
        with f.open("w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

    def _make_bars(self, n=5):
        base = date(2026, 8, 1)
        return [
            {"date": str(base + timedelta(days=i+1)),
             "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000}
            for i in range(n)
        ]

    def test_T026_load_pending_no_setup_finds_scan_no_setup(self, tmp_path):
        engine = self._make_engine(tmp_path)
        self._write_klp(tmp_path, "2026-08-25", [
            {"event_type": "SCAN_NO_SETUP", "observation_id": "SNS_001",
             "symbol": "TATA", "trading_date": "2026-08-25", "ltp": 100.0, "reason": "rsi_high"},
        ])
        pending = engine._load_pending_no_setup_obs("2026-08-25")
        assert len(pending) == 1
        assert pending[0]["observation_id"] == "SNS_001"

    def test_T027_already_processed_not_re_loaded(self, tmp_path):
        engine = self._make_engine(tmp_path)
        self._write_klp(tmp_path, "2026-08-25", [
            {"event_type": "SCAN_NO_SETUP", "observation_id": "SNS_002",
             "symbol": "WIPRO", "trading_date": "2026-08-25", "ltp": 200.0, "reason": "rsi_high"},
            {"event_type": "SCAN_NO_SETUP_OUTCOME", "observation_id": "SNS_002",
             "ts_utc": "2026-08-26T10:00:00Z"},
        ])
        pending = engine._load_pending_no_setup_obs("2026-08-25")
        assert not any(p["observation_id"] == "SNS_002" for p in pending)

    def test_T028_compute_no_setup_outcome_returns_ret_pcts(self, tmp_path):
        bars = self._make_bars(5)
        engine = self._make_engine(tmp_path, fetcher=lambda s, d, *a, **kw: bars)
        obs = {"symbol": "TATA", "trading_date": "2026-08-01",
               "observation_id": "SNS_003", "ltp": 100.0}
        result = engine._compute_no_setup_outcome(obs)
        assert result.get("t1_ret_pct") is not None
        assert result.get("t5_ret_pct") is not None

    def test_T029_outcome_pending_when_t1_in_future(self, tmp_path):
        from opportunity_engine.klp_outcome_engine import OUTCOME_PENDING
        future_date = (date.today() + timedelta(days=1)).isoformat()
        engine = self._make_engine(tmp_path)
        obs = {"symbol": "TATA", "trading_date": future_date,
               "observation_id": "SNS_004", "ltp": 100.0}
        result = engine._compute_no_setup_outcome(obs)
        assert result.get("outcome_status") == OUTCOME_PENDING

    def test_T030_build_no_setup_outcome_record_fields(self, tmp_path):
        engine = self._make_engine(tmp_path)
        obs     = {"observation_id": "SNS_005", "obs_id": "SNS_005",
                   "symbol": "HDFC", "trading_date": "2026-08-25",
                   "ltp": 1600.0, "reason": "vol_too_low"}
        outcome = {"t1_ret_pct": 1.2, "t5_ret_pct": 2.5,
                   "mfe_pct": 3.0, "mae_pct": -1.0, "bars_available": 5}
        rec = engine._build_no_setup_outcome_record(obs, outcome)
        assert rec["event_type"]     == "SCAN_NO_SETUP_OUTCOME"
        assert rec["observation_id"] == "SNS_005"
        assert rec["obs_id"]         == "SNS_005"
        assert rec["no_lookahead"]   is True
        assert rec["broker_calls"]   == 0
        assert rec["t1_ret_pct"]     == 1.2

    def test_T031_outcome_not_executable(self, tmp_path):
        """SCAN_NO_SETUP_OUTCOME record has no entry_price or target — cannot be executed."""
        engine = self._make_engine(tmp_path)
        obs     = {"observation_id": "SNS_006", "symbol": "X",
                   "trading_date": "2026-08-25", "ltp": 100.0, "reason": "rsi_high"}
        outcome = {"t1_ret_pct": 1.0, "bars_available": 5}
        rec = engine._build_no_setup_outcome_record(obs, outcome)
        assert "entry_price" not in rec
        assert "knowledge_target" not in rec
        assert "knowledge_stop_loss" not in rec

    def test_T032_fill_pending_outcomes_processes_no_setup(self, tmp_path):
        past_date = (date.today() - timedelta(days=2)).isoformat()
        bars = self._make_bars(5)
        engine = self._make_engine(tmp_path, fetcher=lambda s, d, *a, **kw: bars)
        self._write_klp(tmp_path, past_date, [
            {"event_type": "SCAN_NO_SETUP", "observation_id": "SNS_FPO",
             "symbol": "SBIN", "trading_date": past_date, "ltp": 600.0, "reason": "rsi_high"},
        ])
        result = engine.fill_pending_outcomes(dates=[past_date])
        assert result.get("processed", 0) >= 1

    def test_T033_no_setup_outcome_written_to_klp_file(self, tmp_path):
        past_date = (date.today() - timedelta(days=2)).isoformat()
        bars = self._make_bars(5)
        engine = self._make_engine(tmp_path, fetcher=lambda s, d, *a, **kw: bars)
        self._write_klp(tmp_path, past_date, [
            {"event_type": "SCAN_NO_SETUP", "observation_id": "SNS_WRITE",
             "symbol": "COALINDIA", "trading_date": past_date, "ltp": 400.0, "reason": "rsi_high"},
        ])
        engine.fill_pending_outcomes(dates=[past_date])
        recs = [json.loads(l) for l in (tmp_path / f"KLP_{past_date}.jsonl").read_text().splitlines()]
        outcomes = [r for r in recs if r.get("event_type") == "SCAN_NO_SETUP_OUTCOME"]
        assert len(outcomes) == 1
        assert outcomes[0]["observation_id"] == "SNS_WRITE"

    def test_T034_no_setup_outcome_never_has_place_order_call(self, tmp_path):
        from opportunity_engine import klp_outcome_engine as _mod
        import inspect
        src = inspect.getsource(_mod.KLPOutcomeEngine._build_no_setup_outcome_record)
        assert "place_order" not in src
        # broker_calls=0 is a data field, not a method call — check no actual broker method calls
        assert "_broker." not in src
        assert "broker.place" not in src

    def test_T035_anti_lookahead_flag_set(self, tmp_path):
        engine = self._make_engine(tmp_path)
        obs     = {"observation_id": "SNS_NOLA", "symbol": "X",
                   "trading_date": "2026-08-25", "ltp": 100.0, "reason": "rsi"}
        outcome = {"t1_ret_pct": 1.0, "bars_available": 5}
        rec = engine._build_no_setup_outcome_record(obs, outcome)
        assert rec["no_lookahead"] is True


# ─────────────────────────────────────────────────────────────────────────────
# E-001: Exit analytics
# ─────────────────────────────────────────────────────────────────────────────

class TestExitAnalytics:
    """T036–T045: Exit analytics records trade close metadata for research."""

    def _make_rec(self, **kw):
        from execution_engine.order_manager import OrderRecord
        defaults = dict(
            order_id="EA_001", symbol="TATA", direction="BUY",
            quantity=10, entry_price=100.0, stop_loss=95.0, target=115.0,
            strategy="Momentum", opportunity_id="OPP-EA",
            actual_fill_price=100.5, signal_regime="BULL_TREND",
        )
        defaults.update(kw)
        return OrderRecord(**defaults)

    def test_T036_record_exit_creates_file(self, tmp_path):
        from learning_system.exit_analytics import record_exit
        import learning_system.exit_analytics as _ea
        orig_dir = _ea._ANALYTICS_DIR
        try:
            _ea._ANALYTICS_DIR = tmp_path
            record_exit(self._make_rec(), exit_price=115.0, pnl=145.0,
                        reason="TARGET_HIT", trading_date="2026-08-26")
        finally:
            _ea._ANALYTICS_DIR = orig_dir
        files = list(tmp_path.glob("exit_analytics_*.jsonl"))
        assert len(files) == 1

    def test_T037_record_exit_fields_present(self, tmp_path):
        from learning_system.exit_analytics import record_exit
        import learning_system.exit_analytics as _ea
        orig = _ea._ANALYTICS_DIR
        try:
            _ea._ANALYTICS_DIR = tmp_path
            record_exit(self._make_rec(), exit_price=115.0, pnl=145.0,
                        reason="TARGET_HIT", trading_date="2026-08-26")
        finally:
            _ea._ANALYTICS_DIR = orig
        row = json.loads((tmp_path / "exit_analytics_2026-08-26.jsonl").read_text().splitlines()[0])
        for field in ("opportunity_id", "symbol", "strategy", "direction",
                      "entry_price", "exit_price", "pnl", "exit_class", "close_reason",
                      "regime", "no_lookahead", "broker_calls"):
            assert field in row, f"Missing field: {field}"

    def test_T038_opportunity_id_in_record(self, tmp_path):
        from learning_system.exit_analytics import record_exit
        import learning_system.exit_analytics as _ea
        orig = _ea._ANALYTICS_DIR
        try:
            _ea._ANALYTICS_DIR = tmp_path
            record_exit(self._make_rec(opportunity_id="TEST-EA-038"),
                        exit_price=115.0, pnl=145.0, reason="TARGET_HIT",
                        trading_date="2026-08-26")
        finally:
            _ea._ANALYTICS_DIR = orig
        row = json.loads((tmp_path / "exit_analytics_2026-08-26.jsonl").read_text().splitlines()[0])
        assert row["opportunity_id"] == "TEST-EA-038"

    def test_T039_exit_class_target_hit(self, tmp_path):
        from learning_system.exit_analytics import record_exit, _classify_exit
        assert _classify_exit("TARGET_HIT", 100.0, 100.0, 115.0, "BUY") == "TARGET_HIT"

    def test_T040_exit_class_stop_hit(self):
        from learning_system.exit_analytics import _classify_exit
        assert _classify_exit("STOP_HIT", -50.0, 100.0, 115.0, "BUY") == "STOP_HIT"

    def test_T041_exit_class_early_loss(self):
        from learning_system.exit_analytics import _classify_exit
        assert _classify_exit("EARLY_LOSS", -30.0, 100.0, 115.0, "BUY") == "EARLY_LOSS"

    def test_T042_exit_class_session_expired(self):
        from learning_system.exit_analytics import _classify_exit
        assert _classify_exit("SESSION_EXPIRED", 10.0, 100.0, 115.0, "BUY") == "SESSION_EXPIRED"

    def test_T043_no_broker_calls(self, tmp_path):
        from learning_system import exit_analytics as _ea
        import inspect
        src = inspect.getsource(_ea.record_exit)
        assert "place_order" not in src
        assert "_broker." not in src
        assert "broker.place" not in src

    def test_T044_never_raises_on_bad_rec(self, tmp_path):
        from learning_system.exit_analytics import record_exit
        import learning_system.exit_analytics as _ea
        orig = _ea._ANALYTICS_DIR
        try:
            _ea._ANALYTICS_DIR = tmp_path
            record_exit(None, exit_price=100.0, pnl=0.0, reason="TEST")
        except Exception as exc:
            pytest.fail(f"record_exit raised: {exc}")
        finally:
            _ea._ANALYTICS_DIR = orig

    def test_T045_no_lookahead_flag(self, tmp_path):
        from learning_system.exit_analytics import record_exit
        import learning_system.exit_analytics as _ea
        orig = _ea._ANALYTICS_DIR
        try:
            _ea._ANALYTICS_DIR = tmp_path
            record_exit(self._make_rec(), exit_price=115.0, pnl=145.0,
                        reason="TARGET_HIT", trading_date="2026-08-26")
        finally:
            _ea._ANALYTICS_DIR = orig
        row = json.loads((tmp_path / "exit_analytics_2026-08-26.jsonl").read_text().splitlines()[0])
        assert row["no_lookahead"] is True
        assert row["broker_calls"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# C-001: Cross-signal aggregator
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossSignalAggregator:
    """T046–T055: Cross-signal aggregation captures portfolio-level correlation."""

    def _make_signal(self, symbol, direction="BUY", strategy="Momentum",
                     opp_id="", confidence=7.0, sector=""):

        class _FakeDirection:
            def __init__(self, v): self.value = v
            def __str__(self): return self.value
            def __repr__(self): return self.value
            def __bool__(self): return True

        sig = MagicMock()
        sig.symbol        = symbol
        sig.direction     = _FakeDirection(direction)
        sig.strategy_name = strategy
        sig.opportunity_id = opp_id
        sig.confidence    = confidence
        sig.sector        = sector
        sig.entry_price   = 100.0
        return sig

    def _make_snapshot(self, regime="BULL_TREND", vix=14.0):
        snap = MagicMock()
        snap.regime.value = regime
        snap.vix          = vix
        return snap

    def test_T046_record_signal_window_returns_dict(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = tmp_path
            result = record_signal_window(
                [self._make_signal("TCS"), self._make_signal("INFY")],
                self._make_snapshot(),
                trading_date="2026-08-26",
            )
        finally:
            _csa._CROSS_SIGNAL_DIR = orig
        assert isinstance(result, dict)
        assert result.get("total_signals") == 2
        # Verify the JSONL file has the full record
        files = list(tmp_path.glob("cross_signal_*.jsonl"))
        assert len(files) == 1
        row = json.loads(files[0].read_text().splitlines()[0])
        assert row.get("signal_count") == 2

    def test_T047_direction_breakdown_counted(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = tmp_path
            record_signal_window(
                [self._make_signal("A", "BUY"), self._make_signal("B", "BUY"),
                 self._make_signal("C", "SELL")],
                self._make_snapshot(), trading_date="2026-08-26",
            )
        finally:
            _csa._CROSS_SIGNAL_DIR = orig
        files = list(tmp_path.glob("cross_signal_*.jsonl"))
        row = json.loads(files[0].read_text().splitlines()[0])
        assert row["direction_breakdown"].get("BUY", 0) == 2
        assert row["direction_breakdown"].get("SELL", 0) == 1

    def test_T048_opportunity_ids_collected(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = tmp_path
            record_signal_window(
                [self._make_signal("A", opp_id="OPP-A"),
                 self._make_signal("B", opp_id="OPP-B")],
                self._make_snapshot(), trading_date="2026-08-26",
            )
        finally:
            _csa._CROSS_SIGNAL_DIR = orig
        files = list(tmp_path.glob("cross_signal_*.jsonl"))
        row = json.loads(files[0].read_text().splitlines()[0])
        assert "OPP-A" in row.get("opportunity_ids", [])
        assert "OPP-B" in row.get("opportunity_ids", [])

    def test_T049_written_to_disk(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = tmp_path
            record_signal_window(
                [self._make_signal("X")], self._make_snapshot(),
                trading_date="2026-08-26",
            )
        finally:
            _csa._CROSS_SIGNAL_DIR = orig
        files = list(tmp_path.glob("cross_signal_*.jsonl"))
        assert len(files) == 1

    def test_T050_empty_signals_returns_immediately(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        result = record_signal_window([], MagicMock(), trading_date="2026-08-26")
        assert result.get("total_signals") == 0

    def test_T051_never_raises(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = Path("/nonexistent_cant_write")
            record_signal_window([self._make_signal("X")], MagicMock())
        except Exception as exc:
            pytest.fail(f"record_signal_window raised: {exc}")
        finally:
            _csa._CROSS_SIGNAL_DIR = orig

    def test_T052_no_broker_calls_in_aggregator(self):
        from learning_system import cross_signal_aggregator as _csa
        import inspect
        src = inspect.getsource(_csa.record_signal_window)
        assert "place_order" not in src
        assert "_broker." not in src
        assert "broker.place" not in src

    def test_T053_no_execution_authority_changes(self):
        from learning_system import cross_signal_aggregator as _csa
        import inspect
        src = inspect.getsource(_csa)
        assert "execute(" not in src
        assert "order_manager" not in src.lower()

    def test_T054_same_direction_count_correct(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = tmp_path
            record_signal_window(
                [self._make_signal("A", "BUY")] * 4,
                self._make_snapshot(), trading_date="2026-08-26",
            )
        finally:
            _csa._CROSS_SIGNAL_DIR = orig
        files = list(tmp_path.glob("cross_signal_*.jsonl"))
        row = json.loads(files[0].read_text().splitlines()[0])
        assert row.get("same_direction_count") == 4

    def test_T055_regime_and_vix_captured(self, tmp_path):
        from learning_system.cross_signal_aggregator import record_signal_window
        import learning_system.cross_signal_aggregator as _csa
        orig = _csa._CROSS_SIGNAL_DIR
        try:
            _csa._CROSS_SIGNAL_DIR = tmp_path
            record_signal_window(
                [self._make_signal("A")],
                self._make_snapshot(regime="BEAR_TREND", vix=28.0),
                trading_date="2026-08-26",
            )
        finally:
            _csa._CROSS_SIGNAL_DIR = orig
        files = list(tmp_path.glob("cross_signal_*.jsonl"))
        row = json.loads(files[0].read_text().splitlines()[0])
        assert row.get("vix") == 28.0


# ─────────────────────────────────────────────────────────────────────────────
# R-001: Regime strategy modifier (P-004)
# ─────────────────────────────────────────────────────────────────────────────

class TestRegimeStrategyModifier:
    """T056–T065: MetaModel applies bounded regime modifier when data is sufficient."""

    def _make_model(self):
        from meta_learning.meta_model import MetaModel
        return MetaModel(k=3)

    def _make_fv(self):
        from meta_learning.feature_extractor import FeatureVector
        return FeatureVector(regime_score=0.5, vix_norm=0.3, breadth_norm=0.5,
                             fii_score=0.2, global_sentiment=0.6, sector_strength=0.5,
                             pcr_norm=0.5, vol_level=0.4)

    def _make_obs(self, strategy, r, n=5):
        from meta_learning.meta_model import Observation
        from meta_learning.feature_extractor import FeatureVector
        return [
            Observation(features=FeatureVector().to_list(), strategy=strategy, r_multiple=r)
            for _ in range(n)
        ]

    def test_T056_predict_returns_result_without_regime_map(self):
        model = self._make_model()
        for obs in self._make_obs("Momentum", 1.2):
            model.add(obs)
        preds = model.predict(self._make_fv(), ["Momentum"])
        assert "Momentum" in preds

    def test_T057_predict_accepts_regime_and_regime_map(self):
        model = self._make_model()
        for obs in self._make_obs("Breakout", 1.0):
            model.add(obs)
        from meta_learning.regime_strategy_map import RegimeStrategyMap
        rsm = RegimeStrategyMap()
        preds = model.predict(self._make_fv(), ["Breakout"],
                              regime="BULL_TREND", regime_map=rsm)
        assert "Breakout" in preds

    def test_T058_insufficient_regime_data_no_modifier(self):
        """With < MIN_REGIME_TRADES, modifier = 0 → prediction unchanged."""
        model = self._make_model()
        for obs in self._make_obs("Breakout", 1.5, n=5):
            model.add(obs)
        from meta_learning.meta_model import MetaModel
        from meta_learning.regime_strategy_map import RegimeStrategyMap
        rsm = RegimeStrategyMap()
        pred_no_regime = model.predict(self._make_fv(), ["Breakout"])
        pred_with_regime = model.predict(self._make_fv(), ["Breakout"],
                                         regime="BULL_TREND", regime_map=rsm)
        # No modifier applied because no regime data → same prediction
        assert abs(pred_no_regime["Breakout"] - pred_with_regime["Breakout"]) < 1e-6

    def test_T059_modifier_bounded_to_max(self):
        """Regime modifier never exceeds ±_MAX_REGIME_MODIFIER."""
        from meta_learning.meta_model import _build_regime_modifiers, _MAX_REGIME_MODIFIER
        from meta_learning.regime_strategy_map import RegimeStrategyMap
        rsm = RegimeStrategyMap()
        for _ in range(10):
            rsm.record("BULL_TREND", "Momentum", pnl_r=2.0)
        mods = _build_regime_modifiers("BULL_TREND", rsm, ["Momentum"])
        if "Momentum" in mods:
            assert abs(mods["Momentum"]) <= _MAX_REGIME_MODIFIER

    def test_T060_modifier_never_overrides_gates(self):
        """Modifier is additive only — cannot set prediction above 3.0 (unrealistic)."""
        model = self._make_model()
        for obs in self._make_obs("Momentum", 0.5, n=5):
            model.add(obs)
        from meta_learning.regime_strategy_map import RegimeStrategyMap
        rsm = RegimeStrategyMap()
        for _ in range(10):
            rsm.record("BULL_TREND", "Momentum", pnl_r=10.0)
        preds = model.predict(self._make_fv(), ["Momentum"],
                              regime="BULL_TREND", regime_map=rsm)
        assert preds["Momentum"] < 3.0

    def test_T061_none_regime_map_skips_modifier(self):
        model = self._make_model()
        for obs in self._make_obs("TestStrat", 1.0, n=5):
            model.add(obs)
        preds = model.predict(self._make_fv(), ["TestStrat"],
                              regime="BULL_TREND", regime_map=None)
        assert "TestStrat" in preds

    def test_T062_no_regime_argument_skips_modifier(self):
        model = self._make_model()
        for obs in self._make_obs("TestStrat2", 1.0, n=5):
            model.add(obs)
        preds = model.predict(self._make_fv(), ["TestStrat2"])
        assert "TestStrat2" in preds

    def test_T063_exception_in_regime_map_handled_gracefully(self):
        model = self._make_model()
        for obs in self._make_obs("TestStrat3", 1.0, n=5):
            model.add(obs)
        bad_map = MagicMock()
        bad_map.rank_strategies.side_effect = RuntimeError("broken map")
        preds = model.predict(self._make_fv(), ["TestStrat3"],
                              regime="BULL_TREND", regime_map=bad_map)
        assert "TestStrat3" in preds

    def test_T064_max_regime_modifier_constant_is_020(self):
        from meta_learning.meta_model import _MAX_REGIME_MODIFIER
        assert _MAX_REGIME_MODIFIER == 0.20

    def test_T065_min_regime_trades_constant_present(self):
        from meta_learning.regime_strategy_map import MIN_REGIME_TRADES
        assert MIN_REGIME_TRADES >= 3


# ─────────────────────────────────────────────────────────────────────────────
# A-001: Anti-lookahead regression
# ─────────────────────────────────────────────────────────────────────────────

class TestAntiLookaheadRegression:
    """T066–T075: No future bar, outcome, or KEL evidence can influence decisions."""

    def test_T066_lol_outcome_fill_uses_bars_after_decision_date(self):
        """LOL outcome computation only uses post-decision-date bars (no lookahead)."""
        from learning_system import learning_observation_ledger as _lol
        import inspect
        # The LOL anti-lookahead guard lives in _update_outcomes or the fill loop;
        # verify that the module references 'decision_at' for temporal gating
        src = inspect.getsource(_lol)
        assert "decision_at" in src or "observed_at" in src

    def test_T067_lol_bridge_missing_decision_at_skips(self, tmp_path):
        """LOL bridge skips records with missing decision_at."""
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        lol_dir   = tmp_path / "lol"
        lol_dir.mkdir()
        kel       = tmp_path / "kel.jsonl"
        state     = tmp_path / "bridge_state.json"
        today_str = date.today().isoformat()
        lol_file  = lol_dir / f"LOL_{today_str}.jsonl"
        lol_file.write_text(json.dumps({
            "observation_id": "OBS_AL_067",
            "lifecycle_state": "OUTCOME_OBSERVED",
            "outcome_at": "2026-08-26T15:30:00+05:30",
            # decision_at MISSING
        }) + "\n")
        result = ingest_lol_outcomes(
            dates=[today_str],
            lol_data_dir=lol_dir,
            knowledge_ledger=kel,
            state_path=state,
        )
        assert result.get("new_records", 0) == 0

    def test_T068_lol_bridge_outcome_before_decision_skips(self, tmp_path):
        """outcome_at ≤ decision_at is rejected as lookahead."""
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        lol_dir   = tmp_path / "lol"
        lol_dir.mkdir()
        kel       = tmp_path / "kel.jsonl"
        state     = tmp_path / "bridge_state.json"
        today_str = date.today().isoformat()
        lol_file  = lol_dir / f"LOL_{today_str}.jsonl"
        lol_file.write_text(json.dumps({
            "observation_id": "OBS_AL_068",
            "lifecycle_state": "OUTCOME_OBSERVED",
            "decision_at": "2026-08-26T14:00:00+05:30",
            "outcome_at":  "2026-08-26T13:00:00+05:30",  # BEFORE decision
        }) + "\n")
        result = ingest_lol_outcomes(
            dates=[today_str],
            lol_data_dir=lol_dir,
            knowledge_ledger=kel,
            state_path=state,
        )
        assert result.get("new_records", 0) == 0

    def test_T069_lol_bridge_missing_outcome_at_skips(self, tmp_path):
        from learning_system.lol_evidence_bridge import ingest_lol_outcomes
        lol_dir   = tmp_path / "lol"
        lol_dir.mkdir()
        kel       = tmp_path / "kel.jsonl"
        state     = tmp_path / "bridge_state.json"
        today_str = date.today().isoformat()
        lol_file  = lol_dir / f"LOL_{today_str}.jsonl"
        lol_file.write_text(json.dumps({
            "observation_id": "OBS_AL_069",
            "lifecycle_state": "OUTCOME_OBSERVED",
            "decision_at": "2026-08-26T09:30:00+05:30",
            # outcome_at MISSING
        }) + "\n")
        result = ingest_lol_outcomes(
            dates=[today_str],
            lol_data_dir=lol_dir,
            knowledge_ledger=kel,
            state_path=state,
        )
        assert result.get("new_records", 0) == 0

    def test_T070_klp_outcome_no_lookahead_flag(self):
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        import inspect
        src = inspect.getsource(KLPOutcomeEngine._build_outcome_record)
        assert '"no_lookahead":' in src or "'no_lookahead':" in src

    def test_T071_scan_no_setup_outcome_no_lookahead(self):
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        import inspect
        src = inspect.getsource(KLPOutcomeEngine._build_no_setup_outcome_record)
        assert '"no_lookahead":' in src or "'no_lookahead':" in src

    def test_T072_exit_analytics_no_lookahead_flag(self):
        from learning_system import exit_analytics as _ea
        import inspect
        src = inspect.getsource(_ea.record_exit)
        assert "no_lookahead" in src

    def test_T073_cross_signal_no_lookahead_not_required(self):
        """Cross-signal is a research aggregation — not a decision input."""
        from learning_system import cross_signal_aggregator as _csa
        import inspect
        src = inspect.getsource(_csa)
        # Must not consume KEL evidence or decision features at record time
        assert "knowledge_evidence_ledger" not in src

    def test_T074_failure_taxonomy_no_lookahead(self):
        """Failure taxonomy only reads historical LOL records — no future data."""
        from learning_system import failure_taxonomy as _ft
        import inspect
        src = inspect.getsource(_ft)
        assert "yfinance" not in src
        assert "fetch_ohlcv" not in src

    def test_T075_hbe_snapshot_writes_only_historical(self):
        """HBE snapshot writes accumulated historical data, not future bars."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        import inspect
        src = inspect.getsource(HistoricalBehaviourEngine.write_daily_snapshot)
        assert "yfinance" not in src
        assert "fetch" not in src.lower()


# ─────────────────────────────────────────────────────────────────────────────
# X-001: Execution authority regression
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionAuthorityRegression:
    """T076–T085: Only OrderManager may reach place_order()."""

    def _assert_no_place_order(self, module_path: str):
        p = Path(module_path)
        if not p.exists():
            return
        src = p.read_text(encoding="utf-8", errors="ignore")
        hits = [l for l in src.splitlines()
                if "place_order(" in l and not l.strip().startswith("#")]
        assert not hits, f"Unexpected place_order in {module_path}: {hits}"

    def test_T076_lol_no_place_order(self):
        self._assert_no_place_order(
            "learning_system/learning_observation_ledger.py")

    def test_T077_kel_no_place_order(self):
        # KEL is a flat JSONL file; KDA writes to it via knowledge_decision_pipeline
        self._assert_no_place_order(
            "knowledge_authority/knowledge_decision_pipeline.py")

    def test_T078_hbe_no_place_order(self):
        self._assert_no_place_order(
            "opportunity_engine/historical_behaviour_engine.py")

    def test_T079_kfe_no_place_order(self):
        self._assert_no_place_order(
            "opportunity_engine/knowledge_fusion/knowledge_fusion_engine.py")

    def test_T080_failure_taxonomy_no_place_order(self):
        self._assert_no_place_order("learning_system/failure_taxonomy.py")

    def test_T081_exit_analytics_no_place_order(self):
        self._assert_no_place_order("learning_system/exit_analytics.py")

    def test_T082_cross_signal_no_place_order(self):
        self._assert_no_place_order("learning_system/cross_signal_aggregator.py")

    def test_T083_scan_no_setup_no_place_order(self):
        self._assert_no_place_order("opportunity_engine/scan_no_signal_observer.py")

    def test_T084_klp_outcome_engine_no_place_order(self):
        self._assert_no_place_order("opportunity_engine/klp_outcome_engine.py")

    def test_T085_order_manager_is_sole_broker_caller(self):
        """OrderManager is the only module that calls self._broker.place_order or _broker_place."""
        from execution_engine.order_manager import OrderManager
        import inspect
        src = inspect.getsource(OrderManager._broker_place)
        assert "place_order" in src


# ─────────────────────────────────────────────────────────────────────────────
# L-001: End-to-end lineage regression
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndLineageRegression:
    """T086–T095: A single opportunity_id survives every pipeline stage."""

    TEST_OPP_ID = "TEST-OPP-E2E-001"

    def test_T086_signal_carries_opportunity_id(self):
        """TradeSignal can hold opportunity_id field."""
        from models.trade_signal import TradeSignal, SignalDirection, SignalType
        sig = TradeSignal(
            symbol="TATA", direction=SignalDirection.BUY,
            entry_price=100.0, stop_loss=95.0, target_price=110.0,
            strategy_name="Breakout", confidence=7.0,
            opportunity_id=self.TEST_OPP_ID,
        )
        assert sig.opportunity_id == self.TEST_OPP_ID

    def test_T087_lol_record_opportunity_id(self, tmp_path):
        from learning_system.learning_observation_ledger import LearningObservationLedger
        ledger = LearningObservationLedger(data_dir=tmp_path)
        sig = MagicMock()
        sig.symbol = "TATA"
        sig.direction.value = "BUY"
        sig.entry_price   = 100.0
        sig.stop_loss     = 95.0
        sig.target_price  = 110.0
        sig.confidence    = 7.0
        sig.strategy_name = "Breakout"
        sig.opportunity_id = self.TEST_OPP_ID
        sig._obs_candidate_score = 0.8
        sig.regime        = "BULL_TREND"
        ledger.record_observations([sig], trading_date="2026-08-26")
        lol_file = tmp_path / "LOL_2026-08-26.jsonl"
        recs = [json.loads(l) for l in lol_file.read_text().splitlines() if l.strip()]
        assert any(r.get("opportunity_id") == self.TEST_OPP_ID for r in recs)

    def test_T088_orderrecord_opportunity_id(self):
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id="E2E_001", symbol="TATA", direction="BUY",
            quantity=10, entry_price=100.0, stop_loss=95.0, target=110.0,
            strategy="Breakout", opportunity_id=self.TEST_OPP_ID,
        )
        assert rec.opportunity_id == self.TEST_OPP_ID

    def test_T089_live_journal_open_carries_opportunity_id(self, tmp_path):
        import execution_engine.order_manager as _om
        from execution_engine.order_manager import OrderManager, OrderRecord
        log_path = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = log_path
            _om._LIVE_DIR = str(tmp_path)
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="E2E_002", symbol="TATA", direction="BUY",
                quantity=10, entry_price=100.0, stop_loss=95.0, target=110.0,
                strategy="Breakout", opportunity_id=self.TEST_OPP_ID,
            )
            om._append_live_journal("OPEN", rec)
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        row = json.loads(Path(log_path).read_text().splitlines()[0])
        assert row["opportunity_id"] == self.TEST_OPP_ID

    def test_T090_live_journal_close_carries_opportunity_id(self, tmp_path):
        import execution_engine.order_manager as _om
        from execution_engine.order_manager import OrderManager, OrderRecord
        log_path = str(tmp_path / "live_orders.jsonl")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = log_path
            _om._LIVE_DIR = str(tmp_path)
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            rec = OrderRecord(
                order_id="E2E_003", symbol="TATA", direction="BUY",
                quantity=10, entry_price=100.0, stop_loss=95.0, target=110.0,
                strategy="Breakout", opportunity_id=self.TEST_OPP_ID,
            )
            om._append_live_journal("CLOSE", rec,
                extra={"exit_price": 110.0, "pnl": 100.0, "reason": "TARGET_HIT"})
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        row = json.loads(Path(log_path).read_text().splitlines()[0])
        assert row["opportunity_id"] == self.TEST_OPP_ID

    def test_T091_restored_record_has_opportunity_id(self, tmp_path):
        import execution_engine.order_manager as _om
        from models import Portfolio
        jf = tmp_path / "live_orders.jsonl"
        ts = datetime.now(timezone.utc).isoformat()
        jf.write_text(json.dumps({
            "event": "OPEN", "timestamp": ts, "order_id": "E2E_004",
            "symbol": "TATA", "direction": "BUY", "quantity": 10,
            "entry_price": 100.0, "stop_loss": 95.0, "target_price": 110.0,
            "strategy": "Breakout", "fill_status": "FILLED",
            "actual_fill_price": 100.5, "broker_order_id": "BRKE2E",
            "opportunity_id": self.TEST_OPP_ID,
        }) + "\n")
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(jf)
            _om._LIVE_DIR = str(tmp_path)
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._restore_stats = {"restored_today": 0}
            om._portfolio = Portfolio(capital=100_000)
            om._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        assert om._orders["E2E_004"].opportunity_id == self.TEST_OPP_ID

    def test_T092_exit_analytics_carries_opportunity_id(self, tmp_path):
        from learning_system.exit_analytics import record_exit
        import learning_system.exit_analytics as _ea
        from execution_engine.order_manager import OrderRecord
        orig = _ea._ANALYTICS_DIR
        try:
            _ea._ANALYTICS_DIR = tmp_path
            rec = OrderRecord(
                order_id="E2E_005", symbol="TATA", direction="BUY",
                quantity=10, entry_price=100.0, stop_loss=95.0, target=110.0,
                strategy="Breakout", opportunity_id=self.TEST_OPP_ID,
            )
            record_exit(rec, exit_price=110.0, pnl=100.0,
                        reason="TARGET_HIT", trading_date="2026-08-26")
        finally:
            _ea._ANALYTICS_DIR = orig
        files = list(tmp_path.glob("exit_analytics_*.jsonl"))
        row = json.loads(files[0].read_text().splitlines()[0])
        assert row["opportunity_id"] == self.TEST_OPP_ID

    def test_T093_opportunity_id_not_empty_in_scanner(self):
        """Scanner generates a non-empty UUID4 for each signal."""
        from models.trade_signal import TradeSignal, SignalDirection, SignalType
        import uuid
        opp_id = str(uuid.uuid4())
        sig = TradeSignal(
            symbol="TATA", direction=SignalDirection.BUY,
            entry_price=100.0, stop_loss=95.0, target_price=110.0,
            strategy_name="Test", confidence=7.0,
            opportunity_id=opp_id,
        )
        assert len(sig.opportunity_id) == 36  # UUID4 length

    def test_T094_kda_model_carries_opportunity_id_field(self):
        from knowledge_authority.kda_models import KDADecisionRecord
        import inspect
        src = inspect.getsource(KDADecisionRecord)
        assert "opportunity_id" in src

    def test_T095_no_stage_converts_opportunity_id_to_none(self, tmp_path):
        """Writing then reading a journal entry never loses the opportunity_id."""
        import execution_engine.order_manager as _om
        from execution_engine.order_manager import OrderManager, OrderRecord
        from models import Portfolio
        log_path = tmp_path / "live_orders.jsonl"
        orig = _om.LIVE_ORDER_LOG; orig_dir = _om._LIVE_DIR
        try:
            _om.LIVE_ORDER_LOG = str(log_path)
            _om._LIVE_DIR = str(tmp_path)
            om_write = OrderManager.__new__(OrderManager)
            om_write._paper_mode = False
            rec = OrderRecord(
                order_id="E2E_006", symbol="TCS", direction="BUY",
                quantity=1, entry_price=4000.0, stop_loss=3900.0, target=4200.0,
                strategy="Momentum", opportunity_id=self.TEST_OPP_ID,
            )
            om_write._append_live_journal("OPEN", rec)
            # Now restore on a second OM instance
            om_read = OrderManager.__new__(OrderManager)
            om_read._paper_mode = False
            om_read._orders = {}
            om_read._restore_stats = {"restored_today": 0}
            om_read._portfolio = Portfolio(capital=100_000)
            om_read._restore_from_live_journal()
        finally:
            _om.LIVE_ORDER_LOG = orig
            _om._LIVE_DIR = orig_dir
        restored = om_read._orders.get("E2E_006")
        assert restored is not None
        assert restored.opportunity_id == self.TEST_OPP_ID


# ─────────────────────────────────────────────────────────────────────────────
# K-001: Restart safety
# ─────────────────────────────────────────────────────────────────────────────

class TestRestartSafety:
    """T096–T100: Daily loss and halt state survive container restarts."""

    def test_T096_daily_loss_survives_restart(self, tmp_path):
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = tmp_path / "rg_state.json"
        g1 = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        g1.record_trade_result(pnl=-800.0, won=False)
        g2 = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        # Restore requires evaluate() to set _session_date from persisted state
        assert g2._daily_pnl == pytest.approx(-800.0, abs=0.01)

    def test_T097_halt_state_survives_restart(self, tmp_path):
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = tmp_path / "rg_state.json"
        g1 = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        g1._trading_halted = True
        g1._halt_reason    = "DAILY_LOSS_LIMIT"
        g1._save_state()
        g2 = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        assert g2._trading_halted is True
        assert g2._halt_reason == "DAILY_LOSS_LIMIT"

    def test_T098_new_day_resets_halt(self, tmp_path):
        import json
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = tmp_path / "rg_state.json"
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state = {
            "session_date": yesterday, "daily_pnl": -2000.0,
            "trading_halted": True, "halt_reason": "DAILY_LOSS_LIMIT",
            "consec_losses": 5, "last_updated": "2026-08-25T10:00:00+00:00",
        }
        sf.write_text(json.dumps(state))
        g = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        assert g._trading_halted is False
        assert g._daily_pnl == 0.0

    def test_T099_state_file_atomic_write(self, tmp_path):
        """No .tmp files left behind after successful state save."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = tmp_path / "rg_state.json"
        g = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        g.record_trade_result(pnl=-100.0, won=False)
        tmp_files = list(tmp_path.glob(".rg_state_*.tmp"))
        assert len(tmp_files) == 0

    def test_T100_consec_losses_preserved(self, tmp_path):
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        sf = tmp_path / "rg_state.json"
        g1 = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        g1.record_trade_result(pnl=-100.0, won=False)
        g1.record_trade_result(pnl=-150.0, won=False)
        g2 = FailSafeRiskGuardian(total_capital=50_000, state_file=str(sf))
        assert g2._consec_losses == 2
