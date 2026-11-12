"""Regression coverage for rotation churn and live-journal learning context."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import execution_engine.order_manager as om_module
import learning_system.live_journal_trade_recovery as recovery
from execution_engine.order_manager import OrderManager, OrderRecord


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(om_module, "_RECENT_CLOSE_TIMES", {})
    monkeypatch.setattr(om_module, "LIVE_ORDER_LOG", str(tmp_path / "live.jsonl"))
    monkeypatch.setattr(om_module, "_LIVE_DIR", str(tmp_path))
    monkeypatch.setattr(recovery, "_LIVE_JOURNAL_PATH", str(tmp_path / "live.jsonl"))
    monkeypatch.setattr(recovery, "_STATE_PATH", str(tmp_path / "recovery.json"))


def manager():
    mgr = OrderManager.__new__(OrderManager)
    mgr._paper_mode = False
    mgr._broker = None
    mgr._orders = {}
    mgr._portfolio = SimpleNamespace(positions={}, realised_pnl=0.0)
    mgr._restore_stats = {}
    mgr._swap_rotation_date = None
    return mgr


def record(**kwargs):
    values = dict(
        order_id="O1", symbol="SBIN", direction="BUY", quantity=4,
        entry_price=100, stop_loss=100, initial_stop_loss=95,
        target=115, strategy="KDA_AUTHORITY", actual_fill_price=100,
        signal_regime="range_market", confidence_score=7.4, product_type="CNC",
        placed_at=datetime.now() - timedelta(days=1),
    )
    values.update(kwargs)
    return OrderRecord(**values)


@pytest.mark.parametrize("pnl_r", [-0.5, 0.0, 1.0])
def test_rotation_blocks_same_day_reentry_even_if_profitable(pnl_r):
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now(), "r": pnl_r, "reason": "LATE_CAP_SWAP",
    }
    assert manager()._entry_cooldown_reason("SBIN") == "ROTATION_REENTRY_COOLDOWN"


def test_rotation_win_can_reenter_next_session():
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now() - timedelta(days=1), "r": 1.0, "reason": "LATE_CAP_SWAP",
    }
    assert manager()._entry_cooldown_reason("SBIN") is None


def test_rotation_loss_keeps_original_30_hour_protection():
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now() - timedelta(days=1), "r": -1.0, "reason": "LATE_CAP_SWAP",
    }
    assert manager()._entry_cooldown_reason("SBIN") == "EARLY_LOSS_COOLDOWN"


def test_non_rotation_winner_is_not_blocked():
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now(), "r": 1.0, "reason": "TARGET_HIT",
    }
    assert manager()._entry_cooldown_reason("SBIN") is None


def test_execute_checks_rotation_before_any_eviction(monkeypatch):
    mgr = manager()
    mgr._symbol_has_open_position = MagicMock(return_value=False)
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now(), "r": 1.0, "reason": "LATE_CAP_SWAP",
    }
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz).replace(hour=10, minute=0)
    monkeypatch.setattr(om_module, "datetime", Clock)
    result = mgr.execute(SimpleNamespace(symbol="SBIN"), SimpleNamespace(confidence_score=8))
    assert result is None
    assert mgr.last_rejection_reason == "ROTATION_REENTRY_COOLDOWN"
    mgr._symbol_has_open_position.assert_not_called()


def test_late_cap_never_evicts_for_already_held_admission():
    mgr = manager()
    mgr._symbol_has_open_position = MagicMock(return_value=True)
    mgr._smart_swap_check = MagicMock(return_value=("O1", "SBIN", 3))
    mgr.close_position = MagicMock(return_value=True)
    assert not mgr.execute_late_cap_swap("SBIN", 8, 100, 95, 115)
    mgr.close_position.assert_not_called()


def test_late_cap_never_evicts_for_cooling_target():
    mgr = manager()
    mgr._symbol_has_open_position = MagicMock(return_value=False)
    mgr._smart_swap_check = MagicMock(return_value=("O1", "WEAK", 3))
    mgr.close_position = MagicMock(return_value=True)
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now(), "r": -1, "reason": "STOP_HIT",
    }
    assert not mgr.execute_late_cap_swap("SBIN", 8, 100, 95, 115)
    mgr.close_position.assert_not_called()


@pytest.mark.parametrize("hour,score", [(9, 8), (15, 8), (14, 6.5)])
def test_late_cap_checks_entry_window_before_eviction(monkeypatch, hour, score):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz).replace(hour=hour, minute=0)
    monkeypatch.setattr(om_module, "datetime", Clock)
    mgr = manager()
    mgr._symbol_has_open_position = MagicMock(return_value=False)
    mgr._smart_swap_check = MagicMock(return_value=("O1", "WEAK", 3))
    mgr.close_position = MagicMock(return_value=True)
    assert not mgr.execute_late_cap_swap("SBIN", score, 100, 95, 115)
    mgr.close_position.assert_not_called()


def test_live_journal_roundtrip_preserves_entry_governance():
    mgr = manager()
    rec = record()
    mgr._append_live_journal("OPEN", rec)
    restored = manager()
    restored._restore_from_live_journal()
    actual = restored._orders["O1"]
    assert actual.confidence_score == 7.4
    assert actual.signal_regime == "range_market"
    assert actual.initial_stop_loss == 95


def test_recovery_retains_regime_risk_and_close_semantics():
    mgr = manager()
    mgr._append_live_journal("CLOSE", record(), extra={
        "exit_price": 110, "pnl": 40, "reason": "LATE_CAP_SWAP",
    })
    recovered = recovery.recover_missed_closed_trades(set())
    assert len(recovered) == 1
    rec = recovered[0]
    assert rec.signal_regime == "range_market"
    assert rec.initial_stop_loss == 95
    assert rec.r_multiple == pytest.approx(2)
    assert rec.close_reason == "LATE_CAP_SWAP"
    assert rec.closed_at is not None
    assert rec.product_type == "CNC"


def test_recovery_uses_open_context_when_old_close_omits_it():
    mgr = manager()
    rec = record()
    mgr._append_live_journal("OPEN", rec)
    path = om_module.LIVE_ORDER_LOG
    row = {
        "event": "CLOSE", "timestamp": datetime.now(timezone.utc).isoformat(),
        "order_id": "O1", "symbol": "SBIN", "entry_price": 100,
        "stop_loss": 100, "quantity": 4, "pnl": 40, "reason": "TARGET_HIT",
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    rec = recovery.recover_missed_closed_trades(set())[0]
    assert rec.signal_regime == "range_market"
    assert rec.r_multiple == pytest.approx(2)


def test_close_persists_r_and_deregisters_rotated_position(monkeypatch):
    mgr = manager()
    mgr._broker_place = MagicMock(return_value="EXIT")
    mgr._trade_monitor = MagicMock()
    rec = record()
    mgr._orders[rec.order_id] = rec
    monkeypatch.setattr("opportunity_engine.company_growth_signal.compute_company_growth_score",
                        lambda symbol: None)
    monkeypatch.setattr("opportunity_engine.corporate_event_signal.compute_corporate_event_score",
                        lambda symbol: None)
    notifier = MagicMock()
    monkeypatch.setattr("notifications.notifier_manager.get_notifier", lambda: notifier)
    monkeypatch.setattr("communication.event_bus.get_bus", MagicMock())
    monkeypatch.setattr("learning_system.exit_analytics.record_exit", MagicMock())
    cost_model = MagicMock()
    cost_model.compute.return_value = SimpleNamespace(total_cost=0)
    monkeypatch.setattr("models.transaction_costs.get_cost_model", lambda: cost_model)
    assert mgr.close_position(rec.order_id, 110, reason="LATE_CAP_SWAP")
    assert rec.r_multiple == pytest.approx(round(rec.pnl / 20, 3))
    mgr._trade_monitor.deregister.assert_called_once_with(rec.order_id)
    assert notifier.trade_closed.call_args.kwargs["r_multiple"] == rec.r_multiple
    row = json.loads(open(om_module.LIVE_ORDER_LOG, encoding="utf-8").readline())
    assert row["r_multiple"] == rec.r_multiple


def test_restart_rotation_guard_and_cancel_does_not_clear_loss():
    mgr = manager()
    mgr._append_live_journal("CLOSE", record(), extra={
        "pnl": -10, "reason": "LATE_CAP_SWAP",
    })
    mgr._append_live_journal("CANCELLED", record(order_id="O2"), extra={
        "reason": "limit_expired",
    })
    mgr._restore_from_live_journal()
    assert mgr._entry_cooldown_reason("SBIN") == "ROTATION_REENTRY_COOLDOWN"
    assert om_module._RECENT_CLOSE_TIMES["SBIN"]["r"] == -0.5


def test_smart_swap_does_not_treat_missing_entry_score_as_weak():
    mgr = manager()
    mgr._orders["O1"] = record(confidence_score=0)
    assert mgr._smart_swap_check("NEW", 9, 100, 95, 115) is None


def test_restored_utc_placement_is_local_naive():
    mgr = manager()
    mgr._append_live_journal("OPEN", record())
    row = json.loads(open(om_module.LIVE_ORDER_LOG, encoding="utf-8").readline())
    expected = datetime.fromisoformat(row["timestamp"]).astimezone().replace(tzinfo=None)
    mgr._restore_from_live_journal()
    assert mgr._orders["O1"].placed_at == expected


@pytest.mark.parametrize("deferred", [True, False])
def test_pending_entry_paths_cannot_bypass_rotation_guard(deferred):
    mgr = manager()
    mgr._risk_guardian = None
    mgr._broker_place = MagicMock()
    om_module._RECENT_CLOSE_TIMES["SBIN"] = {
        "time": datetime.now(), "r": 1.0, "reason": "LATE_CAP_SWAP",
    }
    if deferred:
        mgr._aet_pending = {"S": SimpleNamespace(
            candles_waited=0, max_wait=5, signal=SimpleNamespace(symbol="SBIN"),
            signal_regime="",
        )}
        assert mgr.attempt_aet_confirmations() == []
        assert mgr._aet_pending == {}
    else:
        mgr._reentry_slots = {"S": SimpleNamespace(
            symbol="SBIN", window_expires_at=datetime.now() + timedelta(hours=1),
            retry_count=0, max_retries=2, signal_regime="", signal_vix=15,
        )}
        assert mgr.attempt_all_reentries() == []
        assert mgr._reentry_slots == {}
    mgr._broker_place.assert_not_called()


def test_meta_learning_outcome_survives_restart_before_weekly_retrain(tmp_path):
    from meta_learning import MetaLearningEngine
    from meta_learning.performance_dataset import PerformanceDataset
    engine = MetaLearningEngine.__new__(MetaLearningEngine)
    path = str(tmp_path / "dataset.json")
    engine._dataset = PerformanceDataset(path)
    engine._last_snapshot = SimpleNamespace(regime="range_market", volatility="low")
    engine._extractor = MagicMock()
    engine._extractor.extract.return_value = SimpleNamespace(regime="range_market")
    engine._trainer = MagicMock()
    engine.record_result("KDA_AUTHORITY", None, 1.2, 2.0, True)
    restored = PerformanceDataset(path)
    assert restored.record_count() == 1
    assert restored.get_all()[0].r_multiple == 1.2
    engine._trainer.train_if_due.assert_not_called()
