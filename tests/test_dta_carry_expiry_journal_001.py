"""
Carry expiry wrote SESSION_EXPIRED to the paper CSV only. In live mode restart
recovery reads only the live journal, so every restart (each deploy) restored the
already-closed order as open and expired it again, sending a real CNC SELL against
whatever shares the symbol held by then (ITC 2026-11-18: the 09:49 buy was sold at
11:20 by the resurrected 13-Nov order).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import execution_engine.order_manager as om_mod
from execution_engine.order_manager import OrderManager, OrderRecord
from models import Portfolio


def _live_om(tmp_path):
    import config as _cfg
    broker = MagicMock()
    broker.place_order.return_value = "EXIT-1"
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
    ):
        om = OrderManager()
    om._append_live_journal = MagicMock()
    return om


def _expiring_order(om):
    om._orders["ORD-1"] = OrderRecord(
        order_id="ORD-1", symbol="ITC", direction="BUY", quantity=16, entry_price=284.65,
        stop_loss=276.88, target=300.67, strategy="Mean_Reversion", status="open",
        fill_status="FILLED", placed_at=datetime.now() - timedelta(days=10),
        initial_stop_loss=276.88, product_type="CNC",
    )


def test_live_carry_expiry_writes_a_close_to_the_live_journal(tmp_path):
    om = _live_om(tmp_path)
    _expiring_order(om)
    with patch.object(om_mod, "PAPER_TRADE_LOG", str(tmp_path / "paper.csv")), \
         patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", {"ITC": {"security_id": "1660", "segment": "NSE_EQ"}}), \
         patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None), \
         patch.object(OrderManager, "_broker_confirms_no_open_position", return_value=False):
        assert om.check_and_expire_carries(live_prices={"ITC": 291.0}) == 1
    event, rec = om._append_live_journal.call_args.args[:2]
    extra = om._append_live_journal.call_args.kwargs["extra"]
    assert event == "CLOSE" and rec.order_id == "ORD-1"
    assert extra["reason"] == "SESSION_EXPIRED" and extra["exit_price"] == 291.0


def test_paper_mode_carry_expiry_does_not_touch_the_live_journal(tmp_path):
    om = _live_om(tmp_path)
    om._paper_mode = True
    _expiring_order(om)
    om._orders["ORD-1"].product_type = "INTRADAY"
    with patch.object(om_mod, "PAPER_TRADE_LOG", str(tmp_path / "paper.csv")), \
         patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None):
        assert om.check_and_expire_carries(live_prices={"ITC": 291.0}) == 1
    om._append_live_journal.assert_not_called()


def _restore(tmp_path, csv_lines):
    journal = tmp_path / "live_orders.jsonl"
    open_row = {
        "event": "OPEN", "timestamp": datetime.now(timezone.utc).isoformat(), "order_id": "ORD-1",
        "broker_order_id": "ORD-1", "symbol": "ITC", "direction": "BUY", "quantity": 16,
        "entry_price": 284.65, "stop_loss": 276.88, "target_price": 300.67, "strategy": "Mean_Reversion",
        "fill_status": "FILLED", "actual_fill_price": 284.3, "product_type": "CNC",
    }
    journal.write_text(json.dumps(open_row) + "\n", encoding="utf-8")
    paper = tmp_path / "paper.csv"
    paper.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")
    with patch.object(om_mod, "LIVE_ORDER_LOG", str(journal)), patch.object(om_mod, "_LIVE_DIR", str(tmp_path)), \
         patch.object(om_mod, "PAPER_TRADE_LOG", str(paper)):
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = False
        om._orders = {}
        om._restore_stats = {"restored_today": 0}
        om._portfolio = Portfolio(capital=100_000)
        om._restore_from_live_journal()
    return om


def test_order_closed_only_in_the_csv_is_not_restored_as_open(tmp_path):
    om = _restore(tmp_path, [
        "2026-11-18 09:20:39,ORD-1,ITC,BUY,16,284.65,284.65,300.67,Mean_Reversion,,,CLOSE,291.8,114.4,SESSION_EXPIRED"])
    assert "ORD-1" not in om._orders and "ITC" not in om._portfolio.positions


def test_order_with_no_close_anywhere_is_still_restored(tmp_path):
    om = _restore(tmp_path, [
        "2026-11-18 09:20:39,ORD-2,ITC,BUY,16,284.65,284.65,300.67,Mean_Reversion,,,CLOSE,291.8,114.4,SESSION_EXPIRED"])
    assert "ORD-1" in om._orders
