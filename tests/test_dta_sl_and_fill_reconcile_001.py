"""
Prior-day carry fills (API_ERROR forever) and broker-side stop-loss upkeep.

API_ERROR: Dhan's order-by-id / order-list endpoints only cover the current day, so a carry
placed on an earlier day could never be looked up; it sat in API_ERROR with three failing
broker calls every five minutes, and the journal never recorded a fill that happened after
the OPEN row was written as PENDING.

Stop-loss: SL orders are DAY orders and the exchange can cancel one mid-day (SBIN
2026-11-18, accepted 13:04, cancelled 15:15 "ST Orders are not allowed in preopen"), but
nothing re-placed them, tracked their status, or cancelled them before a system exit.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import execution_engine.order_manager as om_mod
from execution_engine.order_manager import OrderManager, OrderRecord
from models import Portfolio

SBIN = {"security_id": "3045", "segment": "NSE_EQ"}


def _om(broker=None):
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = False
    om._broker = broker or MagicMock()
    om._orders = {}
    om._portfolio = Portfolio(capital=100_000)
    om._append_live_journal = MagicMock()
    om._trade_monitor = None
    return om


def _rec(oid="A", symbol="SBIN", qty=4, days_old=1, fill="PENDING", **kw):
    base = dict(order_id=oid, symbol=symbol, direction="BUY", quantity=qty, entry_price=1100.0,
                stop_loss=1060.0, target=1180.0, strategy="KDA_AUTHORITY", status="open",
                fill_status=fill, placed_at=datetime.now() - timedelta(days=days_old),
                initial_stop_loss=1060.0, product_type="CNC")
    base.update(kw)
    return OrderRecord(**base)


def _broker(positions=None, holdings=None):
    broker = MagicMock()
    broker.get_positions.return_value = {"status": "success", "data": positions or []}
    broker.get_portfolio.return_value = {"status": "success", "data": holdings or []}
    return broker


def _held(qty):
    return {"securityId": "3045", "totalQty": qty}


def _patch_map():
    return patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", {"SBIN": SBIN})


# ── held quantity ───────────────────────────────────────────────────────────

def test_held_quantity_uses_the_larger_book_and_is_none_when_unreadable():
    with _patch_map():
        om = _om(_broker(positions=[{"securityId": "3045", "netQty": 4}], holdings=[_held(8)]))
        assert om._broker_held_quantity("SBIN") == 8
        broken = MagicMock()
        broken.get_positions.return_value = {"status": "failure"}
        broken.get_portfolio.return_value = {}
        assert _om(broken)._broker_held_quantity("SBIN") is None
        assert _om(_broker())._broker_held_quantity("UNMAPPED") is None


# ── API_ERROR fix ───────────────────────────────────────────────────────────

def test_prior_day_pending_order_is_confirmed_filled_from_holdings_and_journaled():
    with _patch_map():
        om = _om(_broker(holdings=[_held(8)]))
        rec = _rec()
        om._orders["A"] = rec
        assert om._resolve_cross_day_fill(rec) is True
    assert rec.fill_status == "FILLED" and rec.filled_quantity == 4
    assert rec.actual_fill_price == 1100.0 and rec.reconciliation_source == "BROKER_HOLDINGS_CONFIRMED"
    om._append_live_journal.assert_called_once_with("OPEN", rec)


def test_shares_already_claimed_by_other_open_orders_are_not_double_counted():
    with _patch_map():
        om = _om(_broker(holdings=[_held(7)]))
        first, second = _rec("A", qty=3, fill="FILLED"), _rec("B", qty=5)
        om._orders.update({"A": first, "B": second})
        assert om._resolve_cross_day_fill(second) is False         # 3 + 5 > 7 held
        om._broker.get_portfolio.return_value = {"status": "success", "data": [_held(8)]}
        assert om._resolve_cross_day_fill(second) is True


def test_same_day_orders_shorts_and_unreadable_books_are_left_alone():
    with _patch_map():
        om = _om(_broker(holdings=[_held(8)]))
        assert om._resolve_cross_day_fill(_rec(days_old=0)) is False
        assert om._resolve_cross_day_fill(_rec(direction="SELL")) is False
        om._broker.get_positions.return_value = {}
        om._broker.get_portfolio.return_value = {}
        assert om._resolve_cross_day_fill(_rec()) is False


def test_startup_reconcile_settles_an_unresolvable_prior_day_order_from_holdings():
    with _patch_map():
        broker = _broker(holdings=[_held(8)])
        broker.get_fill_details.return_value = {"status": "API_ERROR", "actual_fill_price": 0.0, "filled_quantity": 0}
        om = _om(broker)
        om._orders["A"] = _rec(fill="JOURNAL_RESTORED", actual_fill_price=1078.65)
        assert om.reconcile_startup_fills() == 1
        assert om._orders["A"].fill_status == "FILLED"
        assert om._orders["A"].actual_fill_price == 1078.65             # the journal's fill, not the entry price


def test_a_prior_day_order_the_broker_reports_rejected_is_never_filled_from_holdings():
    with _patch_map():
        broker = _broker(holdings=[_held(8)])
        broker.get_fill_details.return_value = {"status": "REJECTED", "actual_fill_price": 0.0, "filled_quantity": 0}
        om = _om(broker)
        om._orders["A"] = _rec(fill="JOURNAL_RESTORED")
        om.reconcile_startup_fills()
        assert "A" not in om._orders


def test_pending_reconcile_settles_prior_day_orders_and_journals_a_later_same_day_fill():
    with _patch_map():
        broker = _broker(holdings=[_held(8)])
        broker.get_fill_details.return_value = {"status": "API_ERROR", "actual_fill_price": 0.0, "filled_quantity": 0}
        om = _om(broker)
        om._orders["A"] = _rec(fill="API_ERROR")
        assert om.reconcile_pending_orders() == ["A"]
        assert om._orders["A"].fill_status == "FILLED"
        om.reconcile_pending_orders()
        assert broker.get_fill_details.call_count == 1                  # resolved: no more broker polling
    same_day = _om(MagicMock())
    same_day._orders["B"] = _rec("B", days_old=0, fill="PENDING")
    same_day._broker.get_fill_details.return_value = {
        "status": "FILLED", "actual_fill_price": 1099.0, "filled_quantity": 4}
    same_day.reconcile_pending_orders()
    same_day._append_live_journal.assert_any_call("OPEN", same_day._orders["B"])


def _restore(tmp_path, fill_status, days_old):
    stamp = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    journal = tmp_path / "live_orders.jsonl"
    journal.write_text(json.dumps({
        "event": "OPEN", "timestamp": stamp, "order_id": "R1", "broker_order_id": "R1", "symbol": "SBIN",
        "direction": "BUY", "quantity": 3, "entry_price": 1082.45, "stop_loss": 1049.76,
        "target_price": 1149.41, "strategy": "KDA_AUTHORITY", "fill_status": fill_status,
        "actual_fill_price": 1078.65, "product_type": "CNC"}) + "\n", encoding="utf-8")
    with patch.object(om_mod, "LIVE_ORDER_LOG", str(journal)), patch.object(om_mod, "_LIVE_DIR", str(tmp_path)), \
         patch.object(om_mod, "PAPER_TRADE_LOG", str(tmp_path / "none.csv")):
        om = OrderManager.__new__(OrderManager)
        om._paper_mode, om._orders, om._restore_stats = False, {}, {"restored_today": 0}
        om._portfolio = Portfolio(capital=100_000)
        om._restore_from_live_journal()
    return om._orders["R1"]


def test_restore_trusts_a_prior_day_journal_fill_but_still_reverifies_same_day_orders(tmp_path):
    assert _restore(tmp_path, "FILLED", 2).fill_status == "FILLED"
    assert _restore(tmp_path, "PENDING", 2).fill_status == "JOURNAL_RESTORED"
    assert _restore(tmp_path, "FILLED", 0).fill_status == "JOURNAL_RESTORED"


# ── broker stop-loss upkeep ─────────────────────────────────────────────────

def _at(hour, minute):
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 19, hour, minute, 0)
    return patch.object(om_mod, "datetime", _Frozen)


def _sl_om(holdings=8):
    broker = _broker(holdings=[_held(holdings)])
    broker.place_sl_order.return_value = "SL-1"
    om = _om(broker)
    om._orders["A"] = _rec(days_old=1, fill="FILLED")
    return om


def test_a_missing_stop_is_placed_for_a_held_carry_with_the_current_stop_level():
    with _patch_map(), _at(10, 0):
        om = _sl_om()
        assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 1
    kwargs = om._broker.place_sl_order.call_args.kwargs
    assert kwargs["transaction_type"] == "SELL" and kwargs["quantity"] == 4 and kwargs["product_type"] == "CNC"
    assert abs(kwargs["trigger_price"] - 1060.0) < 0.06
    assert om._orders["A"].sl_order_id == "SL-1" and om._orders["A"].sl_placed_date == "2026-11-19"


def test_no_stop_is_placed_in_the_pre_open_after_15_10_or_without_a_safe_state():
    with _patch_map():
        for hour, minute in ((9, 5), (9, 19), (15, 11)):
            with _at(hour, minute):
                om = _sl_om()
                assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0
        with _at(10, 0):
            assert _sl_om().ensure_broker_stop_losses({}) == 0                    # no live price
            assert _sl_om().ensure_broker_stop_losses({"SBIN": 1050.0}) == 0     # stop already crossed
            assert _sl_om(holdings=2).ensure_broker_stop_losses({"SBIN": 1135.0}) == 0   # shares not held
            unfilled = _sl_om()
            unfilled._orders["A"].fill_status = "PENDING"
            assert unfilled.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0
    om = _om(_broker())
    om._paper_mode = True
    assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0


def test_a_working_stop_is_left_alone_but_a_cancelled_or_old_one_is_replaced():
    with _patch_map(), _at(10, 0):
        om = _sl_om()
        rec = om._orders["A"]
        rec.sl_order_id, rec.sl_placed_date = "SL-OLD", "2026-11-19"
        om._broker.get_order_status.return_value = {"status": "TRIGGER_PENDING"}
        assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0
        om._broker.get_order_status.return_value = {"status": "CANCELLED"}
        assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 1
        old = _sl_om()
        old._orders["A"].sl_order_id, old._orders["A"].sl_placed_date = "SL-Y", "2026-11-18"
        assert old.ensure_broker_stop_losses({"SBIN": 1135.0}) == 1          # DAY order from yesterday
        old._broker.get_order_status.assert_not_called()


def test_placement_failures_are_throttled_and_capped_per_day():
    with _patch_map():
        om = _sl_om()
        om._broker.place_sl_order.return_value = None
        with _at(10, 0):
            assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0
            om.ensure_broker_stop_losses({"SBIN": 1135.0})                   # inside the 30-minute throttle
        assert om._broker.place_sl_order.call_count == 1
        for minute in (31, 62):
            with _at(10, minute) if minute < 60 else _at(11, minute - 60):
                om.ensure_broker_stop_losses({"SBIN": 1135.0})
        with _at(13, 0):
            om.ensure_broker_stop_losses({"SBIN": 1135.0})
        assert om._broker.place_sl_order.call_count == 3                     # capped at three a day


def test_the_broker_stop_is_cancelled_before_the_system_exits_the_position():
    with _patch_map():
        om = _sl_om()
        rec = om._orders["A"]
        rec.sl_order_id, rec.sl_placed_date = "SL-1", datetime.now().date().isoformat()
        calls = []
        om._broker.get_order_status.return_value = {"status": "PENDING"}
        om._broker.cancel_order.side_effect = lambda order_id: calls.append(("cancel", order_id))
        with patch.object(OrderManager, "_broker_place", side_effect=lambda *a, **k: calls.append(("exit",)) or "EXIT-1"), \
             patch.object(OrderManager, "_broker_confirms_no_open_position", return_value=False):
            om.close_position("A", 1130.0, reason="EARLY_LOSS")
    assert calls[0] == ("cancel", "SL-1") and calls[1] == ("exit",)
    assert rec.sl_order_id == ""


def test_a_stop_already_working_at_the_broker_is_adopted_not_duplicated():
    with _patch_map(), _at(10, 0):
        om = _sl_om()
        om._broker.get_working_stop_orders.return_value = [
            {"order_id": "SL-EXIST", "security_id": "3045", "symbol": "SBIN", "quantity": 4, "trigger_price": 1060.0}]
        assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0
        om._broker.place_sl_order.assert_not_called()
        assert om._orders["A"].sl_order_id == "SL-EXIST"
        small = _sl_om()
        small._broker.get_working_stop_orders.return_value = [
            {"order_id": "SL-SMALL", "security_id": "3045", "symbol": "SBIN", "quantity": 2, "trigger_price": 1060.0}]
        assert small.ensure_broker_stop_losses({"SBIN": 1135.0}) == 1       # too small to cover this position


def test_the_smallest_sufficient_working_stop_is_adopted_for_each_position():
    with _patch_map(), _at(10, 0):
        om = _sl_om(holdings=12)
        om._orders["B"] = _rec("B", qty=3, days_old=1, fill="FILLED")
        om._broker.get_working_stop_orders.return_value = [
            {"order_id": "SL-4", "security_id": "3045", "symbol": "SBIN", "quantity": 4, "trigger_price": 1113.4},
            {"order_id": "SL-3", "security_id": "3045", "symbol": "SBIN", "quantity": 3, "trigger_price": 1082.4}]
        assert om.ensure_broker_stop_losses({"SBIN": 1135.0}) == 0
        om._broker.place_sl_order.assert_not_called()
        assert om._orders["A"].sl_order_id == "SL-4" and om._orders["B"].sl_order_id == "SL-3"


def test_the_orchestrator_calls_the_stop_upkeep_each_monitor_cycle():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py").read_text(encoding="utf-8")
    assert "ensure_broker_stop_losses(" in source
