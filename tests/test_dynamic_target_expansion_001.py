"""
tests/test_dynamic_target_expansion_001.py
==============================================
Self-learning module #29 -- Dynamic Target Expansion wiring:
TradeMonitor's gate/mechanism + OrderManager's journal persistence and
evidence hook.

T01  No expansion when regime is not bullish
T02  No expansion when VIX exceeds the gate
T03  No expansion when r_multiple is below the trigger threshold
T04  Expansion fires correctly for a BUY position when all conditions
     hold -- sets order.adaptive_target further than order.target, logs
     via journal_write_target_expansion()
T05  Expansion is one-time-only (idempotent) -- does not re-fire
T06  Expansion computes a correctly-LOWER target for a SELL position
T07  _evaluate() uses the expanded (adaptive_target) price as the
     effective target once set, not the original order.target
T08  Adaptive Profit Extension (_can_extend) is skipped once
     order.adaptive_target is set -- mutual exclusivity
T09  A refinement-engine failure falls back to the config default
     multiplier (fail-open)
T10  journal_write_target_expansion() calls _append_live_journal with the
     TARGET_EXPANDED event and the new target in `extra`
T11  _restore_from_live_journal() restores adaptive_target from a
     TARGET_EXPANDED journal row onto the reconstructed OrderRecord
T12  close_position() records the expansion outcome only when
     rec.adaptive_target is set; never when it's None
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from execution_engine.order_manager import OrderRecord
from trade_monitoring.trade_monitor import TradeMonitor


def _make_order(direction="BUY", entry=100.0, sl=90.0, target=130.0,
                 order_id="O1", symbol="TEST", adaptive_target=None) -> OrderRecord:
    return OrderRecord(
        order_id=order_id, symbol=symbol, direction=direction, quantity=10,
        entry_price=entry, stop_loss=sl, target=target, strategy="breakout",
        adaptive_target=adaptive_target,
    )


@pytest.fixture
def monitor():
    tm = TradeMonitor()
    tm.update_market_context("bull_trend", 10.0)   # strongly favorable by default
    return tm


def test_t01_no_expansion_when_regime_not_bullish(monitor):
    monitor.update_market_context("range_market", 10.0)
    order = _make_order()
    monitor._maybe_expand_target(order, r_multiple=3.0)
    assert order.adaptive_target is None


def test_t02_no_expansion_when_vix_too_high(monitor):
    monitor.update_market_context("bull_trend", 25.0)
    order = _make_order()
    monitor._maybe_expand_target(order, r_multiple=3.0)
    assert order.adaptive_target is None


def test_t03_no_expansion_below_trigger_r(monitor):
    order = _make_order()
    monitor._maybe_expand_target(order, r_multiple=1.0)
    assert order.adaptive_target is None


def test_t04_expansion_fires_for_buy(monitor):
    order = _make_order(direction="BUY", entry=100.0, sl=90.0, target=130.0)
    with patch(
        "learning_system.target_expansion_refinement_engine.get_effective_expansion_multiplier",
        return_value=5.0,
    ):
        monitor._maybe_expand_target(order, r_multiple=3.0)
    assert order.adaptive_target == pytest.approx(150.0)   # 100 + 10*5.0
    assert order.adaptive_target > order.target


def test_t05_expansion_is_one_time_only(monitor):
    order = _make_order(adaptive_target=145.0)
    with patch(
        "learning_system.target_expansion_refinement_engine.get_effective_expansion_multiplier",
        return_value=5.0,
    ):
        monitor._maybe_expand_target(order, r_multiple=3.0)
    assert order.adaptive_target == 145.0   # unchanged


def test_t06_expansion_computes_lower_target_for_sell(monitor):
    order = _make_order(direction="SELL", entry=100.0, sl=110.0, target=70.0)
    with patch(
        "learning_system.target_expansion_refinement_engine.get_effective_expansion_multiplier",
        return_value=5.0,
    ):
        monitor._maybe_expand_target(order, r_multiple=3.0)
    assert order.adaptive_target == pytest.approx(50.0)    # 100 - 10*5.0
    assert order.adaptive_target < order.target


def test_t07_evaluate_uses_expanded_target(monitor):
    order = _make_order(direction="BUY", entry=100.0, sl=90.0, target=130.0,
                         adaptive_target=150.0)
    monitor._peak_r[order.order_id] = 0.0
    # LTP is above the ORIGINAL target but below the EXPANDED one -- must
    # NOT close, since the effective target is now 150.
    result = monitor._evaluate(order, ltp=135.0)
    assert result is None
    # LTP reaches the expanded target -- must close.
    result = monitor._evaluate(order, ltp=151.0)
    assert result == "close_target"


def test_t08_adaptive_extension_skipped_once_expanded(monitor):
    order = _make_order(direction="BUY", entry=100.0, sl=90.0, target=130.0,
                         adaptive_target=150.0)
    monitor._peak_r[order.order_id] = 0.0
    with patch.object(monitor, "_can_extend", return_value=True) as mocked:
        result = monitor._evaluate(order, ltp=151.0)
    mocked.assert_not_called()
    assert result == "close_target"


def test_t09_refinement_engine_failure_falls_back_to_default(monitor):
    order = _make_order(direction="BUY", entry=100.0, sl=90.0, target=130.0)
    with patch(
        "learning_system.target_expansion_refinement_engine.get_effective_expansion_multiplier",
        side_effect=RuntimeError("boom"),
    ):
        monitor._maybe_expand_target(order, r_multiple=3.0)
    from trade_monitoring import trade_monitor as tm_mod
    assert order.adaptive_target == pytest.approx(100.0 + 10.0 * tm_mod._TGT_MULTIPLIER)


def test_t10_journal_write_calls_append_live_journal():
    from execution_engine.order_manager import OrderManager
    om = OrderManager.__new__(OrderManager)   # bypass __init__ (broker/paper setup)
    rec = _make_order()
    om._orders = {"O1": rec}
    om._append_live_journal = MagicMock()
    om.journal_write_target_expansion("O1", 150.0)
    om._append_live_journal.assert_called_once()
    args, kwargs = om._append_live_journal.call_args
    assert args[0] == "TARGET_EXPANDED"
    assert kwargs["extra"] == {"adaptive_target": 150.0}


def test_t11_restore_from_live_journal_restores_adaptive_target(tmp_path):
    import json
    from execution_engine import order_manager as om_mod

    journal_path = tmp_path / "live_orders.jsonl"
    now = datetime.now().isoformat()
    rows = [
        {"event": "OPEN", "timestamp": now, "order_id": "O1", "symbol": "TEST",
         "direction": "BUY", "quantity": 10, "entry_price": 100.0,
         "stop_loss": 90.0, "target_price": 130.0, "strategy": "breakout",
         "fill_status": "FILLED", "actual_fill_price": 100.0,
         "product_type": "CNC"},
        {"event": "TARGET_EXPANDED", "timestamp": now, "order_id": "O1",
         "adaptive_target": 150.0},
    ]
    with open(journal_path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    om = om_mod.OrderManager.__new__(om_mod.OrderManager)
    om._paper_mode = False
    om._orders = {}
    om._portfolio = MagicMock()
    om._portfolio.positions = {}
    om._restore_stats = {}

    with patch.object(om_mod, "LIVE_ORDER_LOG", str(journal_path)):
        om._restore_from_live_journal()

    assert om._orders["O1"].adaptive_target == pytest.approx(150.0)


def test_t12_close_position_records_only_when_expanded():
    """Source-inspection guard: close_position() gates the evidence-log
    call on `rec.adaptive_target is not None` (never unconditional)."""
    import inspect
    from execution_engine import order_manager as om_mod

    src = inspect.getsource(om_mod.OrderManager.close_position)
    assert "if rec.adaptive_target is not None:" in src
    assert "record_expansion_outcome" in src
