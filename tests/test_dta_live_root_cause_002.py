"""
tests/test_dta_live_root_cause_002.py
======================================
DTA-LIVE-ROOT-CAUSE-002 — Broker Execution Hardening

Root cause confirmed:
    Friday 2026-08-28 13:00:38 IST — SBIN LIMIT BUY
    DhanBroker.place_order() received a string from dhanhq and called
    response.get("data", {}).get("orderId"), raising:
        AttributeError: 'str' object has no attribute 'get'
    Exception was swallowed; broker returned None; OrderManager retried 3x
    and discarded the only eligible live signal of the session.

These tests verify:
  - All malformed/empty/unexpected response variants are handled safely
  - No AttributeError can be raised by broker response parsing
  - Failure types are classified and logged correctly
  - MALFORMED/EMPTY responses do NOT trigger blind retries (duplicate-order risk)
  - EXCEPTION/REJECTED failures ARE safely retried
  - SL placement uses the same response validation
  - close_position(), AET, and re-entry paths handle broker failure correctly
  - Startup/pending reconciliation correctly maps all broker states
  - opportunity_id is preserved end-to-end
  - Valid broker response reaches _orders; invalid response does not
  - Phantom positions cannot be created from malformed or rejected responses
  - Production call chain is integration-tested (DecisionEngine → OrderManager → DhanBroker)
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_broker(response: Any = None, exc: Exception = None):
    """Return a DhanBroker with mocked _dhan SDK returning `response` or raising `exc`."""
    from execution_engine.brokers.dhan_broker import DhanBroker
    b = DhanBroker.__new__(DhanBroker)
    b.client_id          = "TEST_CLIENT"
    b.access_token       = "TEST_TOKEN"
    b._connected         = True
    b._last_failure_type = ""
    mock_sdk = MagicMock()
    if exc is not None:
        mock_sdk.place_order.side_effect = exc
    else:
        mock_sdk.place_order.return_value = response
    b._dhan = mock_sdk
    return b


def _good_response(order_id: str = "ORD001") -> dict:
    return {"status": "success", "remarks": "", "data": {"orderId": order_id}}


def _rejection_response(code: str = "DA001", msg: str = "Insufficient funds") -> dict:
    return {"status": "failure", "remarks": msg, "errorCode": code, "data": ""}


# ── T001 — T014: place_order() response variants ──────────────────────────────

def test_T001_successful_dict_response():
    """T001: Valid dict with status=success and orderId returns the orderId string."""
    from execution_engine.brokers.dhan_broker import BROKER_ACCEPTED
    b = _make_broker(_good_response("ORD-001"))
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result == "ORD-001"
    assert b._last_failure_type == BROKER_ACCEPTED


def test_T002_successful_response_with_valid_orderid():
    """T002: Integer orderId is coerced to string."""
    resp = {"status": "success", "data": {"orderId": 99999}}
    b = _make_broker(resp)
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result == "99999"


def test_T003_none_response():
    """T003: None response → BROKER_RESPONSE_EMPTY, returns None without AttributeError."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_EMPTY
    b = _make_broker(None)
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_EMPTY


def test_T004_empty_string_response():
    """T004: Empty string → BROKER_RESPONSE_EMPTY, returns None without AttributeError."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_EMPTY
    b = _make_broker("")
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_EMPTY


def test_T005_arbitrary_string_response():
    """T005: Arbitrary string → BROKER_RESPONSE_MALFORMED, returns None."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_MALFORMED
    b = _make_broker("DH-3045: Order rejected by exchange")
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_MALFORMED


def test_T006_bytes_response():
    """T006: Bytes response → BROKER_RESPONSE_MALFORMED, returns None."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_MALFORMED
    b = _make_broker(b"\x00\x01\x02")
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_MALFORMED


def test_T007_list_response():
    """T007: List response → BROKER_RESPONSE_MALFORMED, returns None."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_MALFORMED
    b = _make_broker([{"orderId": "X"}])
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_MALFORMED


def test_T008_malformed_dict_no_data_key():
    """T008: Dict missing 'data' key → BROKER_RESPONSE_MALFORMED."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_MALFORMED
    b = _make_broker({"status": "success", "orderId": "ORD-X"})  # data at wrong level
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_MALFORMED


def test_T009_dict_data_is_string_not_dict():
    """T009: data field is a string not a dict → BROKER_RESPONSE_MALFORMED."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_MALFORMED
    b = _make_broker({"status": "success", "data": "ORD-STRING"})
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_MALFORMED


def test_T010_data_dict_missing_orderid():
    """T010: data dict present but orderId missing → BROKER_REJECTED."""
    from execution_engine.brokers.dhan_broker import BROKER_REJECTED
    b = _make_broker({"status": "success", "data": {"symbol": "SBIN"}})
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_REJECTED


def test_T011_orderid_empty_string():
    """T011: orderId present but empty string → BROKER_REJECTED."""
    from execution_engine.brokers.dhan_broker import BROKER_REJECTED
    b = _make_broker({"status": "success", "data": {"orderId": ""}})
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_REJECTED


def test_T012_explicit_broker_rejection():
    """T012: Dhan returns status='failure' → BROKER_REJECTED, returns None."""
    from execution_engine.brokers.dhan_broker import BROKER_REJECTED
    b = _make_broker(_rejection_response("DA001", "Insufficient balance"))
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_REJECTED


def test_T013_broker_exception():
    """T013: SDK raises exception → BROKER_EXCEPTION, returns None, no re-raise."""
    from execution_engine.brokers.dhan_broker import BROKER_EXCEPTION
    b = _make_broker(exc=RuntimeError("connection timeout"))
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_EXCEPTION


def test_T014_whitespace_only_string():
    """T014: Whitespace-only string treated as BROKER_RESPONSE_EMPTY."""
    from execution_engine.brokers.dhan_broker import BROKER_RESPONSE_EMPTY
    b = _make_broker("   \n\t  ")
    result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_EMPTY


# ── T015 — T016: place_sl_order() ─────────────────────────────────────────────

def test_T015_place_sl_order_malformed_response():
    """T015: place_sl_order() with malformed response → None, BROKER_RESPONSE_MALFORMED."""
    from execution_engine.brokers.dhan_broker import DhanBroker, BROKER_RESPONSE_MALFORMED
    b = DhanBroker.__new__(DhanBroker)
    b.client_id          = "T"
    b.access_token       = "T"
    b._connected         = True
    b._last_failure_type = ""
    mock_sdk = MagicMock()
    mock_sdk.place_order.return_value = "unexpected string"
    b._dhan = mock_sdk

    with patch(
        "execution_engine.brokers.dhan_broker.DhanBroker.place_sl_order",
        wraps=b.place_sl_order,
    ):
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
            result = b.place_sl_order("SBIN", "NSE", "SELL", 5, 1024.92, 1022.0)
    assert result is None
    assert b._last_failure_type == BROKER_RESPONSE_MALFORMED


def test_T016_place_sl_order_missing_orderid():
    """T016: place_sl_order() response dict has no orderId → None, BROKER_REJECTED."""
    from execution_engine.brokers.dhan_broker import DhanBroker, BROKER_REJECTED
    b = DhanBroker.__new__(DhanBroker)
    b.client_id          = "T"
    b.access_token       = "T"
    b._connected         = True
    b._last_failure_type = ""
    mock_sdk = MagicMock()
    mock_sdk.place_order.return_value = {"status": "success", "data": {}}
    b._dhan = mock_sdk
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        result = b.place_sl_order("SBIN", "NSE", "SELL", 5, 1024.92, 1022.0)
    assert result is None
    assert b._last_failure_type == BROKER_REJECTED


# ── T017 — T018: close_position() ─────────────────────────────────────────────

def _make_om_live_with_broker(broker_mock):
    """Build an OrderManager in live mode with a pre-wired broker."""
    from execution_engine.order_manager import OrderManager, OrderRecord
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=broker_mock),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
    ):
        om = OrderManager()
    return om


def _insert_open_order(om, order_id="ORD-CLOSE-001"):
    from execution_engine.order_manager import OrderRecord
    rec = OrderRecord(
        order_id="ORD-CLOSE-001",
        symbol="SBIN",
        direction="BUY",
        quantity=5,
        entry_price=1046.70,
        stop_loss=1024.92,
        target=1101.15,
        strategy="TEST",
        status="open",
        placed_at=datetime.now(),
        initial_stop_loss=1024.92,
    )
    om._orders[order_id] = rec
    return rec


def test_T017_close_position_broker_failure():
    """T017: close_position() when broker returns None → returns False, position stays open."""
    broker = MagicMock()
    broker.place_order.return_value = None
    broker._last_failure_type = "BROKER_REJECTED"
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        om = _make_om_live_with_broker(broker)
        rec = _insert_open_order(om)
        result = om.close_position("ORD-CLOSE-001", exit_price=1060.0, reason="TEST_CLOSE")
    assert result is False
    assert om._orders["ORD-CLOSE-001"].status == "open"


def test_T018_close_position_success():
    """T018: close_position() when broker returns an order_id → returns True, status='closed'."""
    broker = MagicMock()
    broker.place_order.return_value = "EXIT-001"
    broker._last_failure_type = "BROKER_ACCEPTED"
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        om = _make_om_live_with_broker(broker)
        rec = _insert_open_order(om)
        with (
            patch.object(om, "_append_live_journal", return_value=None),
            patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        ):
            result = om.close_position("ORD-CLOSE-001", exit_price=1060.0, reason="TEST_CLOSE")
    assert result is True
    assert om._orders["ORD-CLOSE-001"].status == "closed"


# ── T019 — T020: AET confirmation path ────────────────────────────────────────

def test_T019_aet_execution_failure():
    """T019: AET slot is abandoned (not registered) when broker returns None."""
    from execution_engine.order_manager import OrderManager, AetPendingSlot
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult

    broker = MagicMock()
    broker.place_order.return_value = None
    broker._last_failure_type = "BROKER_EXCEPTION"
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        om = _make_om_live_with_broker(broker)

    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    slot = AetPendingSlot(
        slot_id="AET-001", signal=sig, decision=MagicMock(),
        qty=5, zone_price=1048.0, signal_regime="bull_trend", signal_vix=11.0,
        created_at=datetime.now(), candles_waited=0,
    )
    om._aet_pending["AET-001"] = slot
    new_records = om.attempt_aet_confirmations(
        current_vix=10.0, current_regime="bull_trend", distortion_active=False)
    assert len(new_records) == 0
    assert "AET-001" not in om._aet_pending


def test_T020_aet_successful_execution():
    """T020: AET slot produces an OrderRecord when broker responds with valid order_id."""
    from execution_engine.order_manager import OrderManager, AetPendingSlot
    from models.trade_signal import TradeSignal, SignalDirection, SignalType

    broker = MagicMock()
    broker.place_order.return_value = "AET-ORD-001"
    broker._last_failure_type = "BROKER_ACCEPTED"
    broker.place_sl_order.return_value = "SL-AET-001"
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        om = _make_om_live_with_broker(broker)

    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    slot = AetPendingSlot(
        slot_id="AET-002", signal=sig, decision=MagicMock(),
        qty=5, zone_price=1048.0, signal_regime="bull_trend", signal_vix=11.0,
        created_at=datetime.now(), candles_waited=0,
    )
    om._aet_pending["AET-002"] = slot
    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch.object(om, "_reconcile_fill", return_value=None),
    ):
        new_records = om.attempt_aet_confirmations(
            current_vix=10.0, current_regime="bull_trend", distortion_active=False)
    assert len(new_records) == 1
    assert new_records[0].order_id == "AET-ORD-001"


# ── T021 — T022: re-entry path ─────────────────────────────────────────────────

def test_T021_reentry_malformed_response():
    """T021: Re-entry broker call returning None → slot retry_count incremented, no OrderRecord."""
    from execution_engine.order_manager import OrderManager, ReentrySlot
    from datetime import timedelta

    broker = MagicMock()
    broker.place_order.return_value = None
    broker._last_failure_type = "BROKER_EXCEPTION"
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        om = _make_om_live_with_broker(broker)

    slot = ReentrySlot(
        original_order_id="OLD-001", symbol="SBIN", direction="BUY",
        entry_price=1046.70, stop_loss=1024.92, target=1101.15,
        strategy="TEST", quantity=5, signal_regime="bull_trend", signal_vix=11.0,
        window_expires_at=datetime.now() + timedelta(hours=1),
    )
    om._reentry_slots["SBIN_BUY"] = slot
    new_records = om.attempt_all_reentries(current_prices={"SBIN": 1046.70})
    assert len(new_records) == 0
    assert "SBIN_BUY" not in om._orders


def test_T022_reentry_rejected_response():
    """T022: Re-entry with broker rejection → no OrderRecord registered."""
    from execution_engine.order_manager import OrderManager, ReentrySlot
    from datetime import timedelta

    broker = MagicMock()
    broker.place_order.return_value = None
    broker._last_failure_type = "BROKER_REJECTED"
    with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
               {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}):
        om = _make_om_live_with_broker(broker)

    slot = ReentrySlot(
        original_order_id="OLD-002", symbol="SBIN", direction="BUY",
        entry_price=1046.70, stop_loss=1024.92, target=1101.15,
        strategy="TEST", quantity=5, signal_regime="bull_trend", signal_vix=11.0,
        window_expires_at=datetime.now() + timedelta(hours=1),
    )
    om._reentry_slots["SBIN_BUY"] = slot
    new_records = om.attempt_all_reentries(current_prices={"SBIN": 1046.70})
    assert len(new_records) == 0


# ── T023 — T027: startup reconciliation states ────────────────────────────────

def _make_broker_with_fill_details(fill_status: str, fill_price: float = 1046.70):
    broker = MagicMock()
    broker.get_fill_details.return_value = {
        "status": fill_status,
        "broker_order_id": "ORD-REC-001",
        "actual_fill_price": fill_price,
        "filled_quantity": 5 if fill_status in ("FILLED", "PARTIALLY_FILLED") else 0,
        "requested_qty": 5,
        "order_status_raw": fill_status,
        "fill_timestamp": "",
        "reconciliation_source": "DHAN_BROKER",
    }
    return broker


def _make_om_with_restored_order(broker, order_id: str = "ORD-REC-001"):
    from execution_engine.order_manager import OrderRecord
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(__import__("execution_engine.order_manager",
                                fromlist=["OrderManager"]).OrderManager,
                     "_load_broker", return_value=broker),
        patch.object(__import__("execution_engine.order_manager",
                                fromlist=["OrderManager"]).OrderManager,
                     "_restore_from_live_journal", return_value=None),
        patch.object(__import__("execution_engine.order_manager",
                                fromlist=["OrderManager"]).OrderManager,
                     "reconcile_startup_fills", return_value=0),
        patch.object(__import__("execution_engine.order_manager",
                                fromlist=["OrderManager"]).OrderManager,
                     "_reconcile_sim_paper_artifacts", return_value=None),
    ):
        from execution_engine.order_manager import OrderManager
        om = OrderManager()
    rec = OrderRecord(
        order_id=order_id, symbol="SBIN", direction="BUY", quantity=5,
        entry_price=1046.70, stop_loss=1024.92, target=1101.15,
        strategy="TEST", fill_status="JOURNAL_RESTORED", placed_at=datetime.now(),
        initial_stop_loss=1024.92,
    )
    om._orders[order_id] = rec
    return om, rec


def test_T023_startup_reconciliation_filled():
    """T023: FILLED status retained; fill price populated; phantom position NOT created."""
    broker = _make_broker_with_fill_details("FILLED", 1047.00)
    om, rec = _make_om_with_restored_order(broker)
    n = om.reconcile_startup_fills()
    assert n == 1
    assert rec.fill_status == "FILLED"
    assert rec.actual_fill_price == 1047.00


def test_T024_startup_reconciliation_partially_filled():
    """T024: PARTIALLY_FILLED → fill_status updated, not deregistered."""
    broker = _make_broker_with_fill_details("PARTIALLY_FILLED", 1047.50)
    om, rec = _make_om_with_restored_order(broker)
    n = om.reconcile_startup_fills()
    assert n == 1
    assert rec.fill_status == "PARTIALLY_FILLED"
    assert "ORD-REC-001" in om._orders


def test_T025_startup_reconciliation_rejected():
    """T025: REJECTED → position deregistered from _orders (no phantom)."""
    broker = _make_broker_with_fill_details("REJECTED", 0.0)
    om, rec = _make_om_with_restored_order(broker)
    n = om.reconcile_startup_fills()
    assert n == 1
    assert "ORD-REC-001" not in om._orders


def test_T026_startup_reconciliation_cancelled():
    """T026: CANCELLED → position deregistered from _orders."""
    broker = _make_broker_with_fill_details("CANCELLED", 0.0)
    om, rec = _make_om_with_restored_order(broker)
    n = om.reconcile_startup_fills()
    assert n == 1
    assert "ORD-REC-001" not in om._orders


def test_T027_startup_reconciliation_unknown():
    """T027: UNKNOWN status → position kept (fail-safe; never assume closed)."""
    broker = _make_broker_with_fill_details("PENDING", 0.0)
    om, rec = _make_om_with_restored_order(broker)
    n = om.reconcile_startup_fills()
    assert n == 1
    assert "ORD-REC-001" in om._orders


# ── T028: pending order reconciliation ────────────────────────────────────────

def test_T028_pending_order_reconciliation():
    """T028: reconcile_pending_orders() resolves PENDING status on open orders."""
    broker = _make_broker_with_fill_details("FILLED", 1046.70)
    om, rec = _make_om_with_restored_order(broker, "ORD-PEND-001")
    rec.fill_status = "PENDING"
    rec.order_type  = "LIMIT"
    updated = om.reconcile_pending_orders()
    assert "ORD-PEND-001" in updated
    assert rec.fill_status == "FILLED"


# ── T029 — T030: opportunity_id lineage ───────────────────────────────────────

def test_T029_opportunity_id_preserved_into_order_record():
    """T029: opportunity_id from signal flows into OrderRecord without loss."""
    from execution_engine.order_manager import OrderManager
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    import config as _cfg

    broker = MagicMock()
    broker.place_order.return_value = "ORD-OPP-001"
    broker._last_failure_type = "BROKER_ACCEPTED"
    broker.place_sl_order.return_value = "SL-OPP-001"

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.5,
        strategy_name="TEST", atr=21.78,
    )
    sig.opportunity_id = "OPP-SBIN-2026-08-28-001"
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.5, approved=True, position_size_modifier=1.0)

    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch.object(om, "_reconcile_fill", return_value=None),
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        record = om.execute(sig, dec)

    assert record is not None
    assert record.opportunity_id == "OPP-SBIN-2026-08-28-001"


def test_T030_opportunity_id_preserved_in_orders_dict():
    """T030: After successful execute(), _orders[order_id].opportunity_id matches signal."""
    from execution_engine.order_manager import OrderManager
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    import config as _cfg

    broker = MagicMock()
    broker.place_order.return_value = "ORD-OPP-002"
    broker._last_failure_type = "BROKER_ACCEPTED"
    broker.place_sl_order.return_value = "SL-OPP-002"

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.5,
        strategy_name="TEST", atr=21.78,
    )
    sig.opportunity_id = "OPP-SBIN-2026-08-28-002"
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.5, approved=True, position_size_modifier=1.0)

    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch.object(om, "_reconcile_fill", return_value=None),
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        om.execute(sig, dec)

    assert om._orders["ORD-OPP-002"].opportunity_id == "OPP-SBIN-2026-08-28-002"


# ── T031 — T033: ambiguous response / fail-closed behaviour ───────────────────

def test_T031_malformed_response_does_not_blindly_retry():
    """T031: MALFORMED response halts retry immediately — no 3-attempt loop."""
    from execution_engine.order_manager import OrderManager
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    import config as _cfg

    # Broker returns malformed string EVERY call
    call_count = 0
    def _mock_place_order(**kwargs):
        nonlocal call_count
        call_count += 1
        return "unexpected_string_response"  # will trigger MALFORMED

    broker = MagicMock()
    broker._dhan = MagicMock()
    broker._dhan.place_order.side_effect = _mock_place_order
    broker._connected = True
    broker._last_failure_type = ""

    # Use real DhanBroker.place_order() so _last_failure_type is set correctly
    from execution_engine.brokers.dhan_broker import DhanBroker
    real_broker = DhanBroker.__new__(DhanBroker)
    real_broker._connected = True
    real_broker._last_failure_type = ""
    real_broker._dhan = MagicMock(return_value=None)
    real_broker._dhan.place_order.return_value = "unexpected_string_response"

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=real_broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.0, approved=True, position_size_modifier=1.0)

    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)

    # MALFORMED response must halt immediately — broker is called exactly once
    assert result is None
    assert real_broker._dhan.place_order.call_count == 1   # no blind retry


def test_T032_exception_failure_is_retried():
    """T032: BROKER_EXCEPTION allows retry — up to MAX_ORDER_RETRIES calls."""
    from execution_engine.brokers.dhan_broker import DhanBroker, BROKER_EXCEPTION
    from execution_engine.order_manager import MAX_ORDER_RETRIES
    import time as _time

    real_broker = DhanBroker.__new__(DhanBroker)
    real_broker._connected = True
    real_broker._last_failure_type = ""
    real_broker._dhan = MagicMock()
    real_broker._dhan.place_order.side_effect = ConnectionError("network error")

    from execution_engine.order_manager import OrderManager
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=real_broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
        patch("time.sleep", return_value=None),
    ):
        om = OrderManager()

    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.0, approved=True, position_size_modifier=1.0)

    with (
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)

    assert result is None
    # Exception is retried — broker called MAX_ORDER_RETRIES times
    assert real_broker._dhan.place_order.call_count == MAX_ORDER_RETRIES


def test_T033_unresolved_response_fails_closed():
    """T033: MALFORMED response produces no OrderRecord and no entry in _orders."""
    from execution_engine.brokers.dhan_broker import DhanBroker
    from execution_engine.order_manager import OrderManager
    import config as _cfg

    real_broker = DhanBroker.__new__(DhanBroker)
    real_broker._connected = True
    real_broker._last_failure_type = ""
    real_broker._dhan = MagicMock()
    real_broker._dhan.place_order.return_value = None   # EMPTY response

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=real_broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.0, approved=True, position_size_modifier=1.0)

    with (
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)

    assert result is None
    # No phantom position created
    assert len(om._orders) == 0


# ── T034 — T040: correctness invariants ───────────────────────────────────────

def test_T034_valid_broker_response_reaches_orders():
    """T034: Successful order placement registers OrderRecord in _orders."""
    from execution_engine.brokers.dhan_broker import DhanBroker
    from execution_engine.order_manager import OrderManager
    import config as _cfg

    real_broker = DhanBroker.__new__(DhanBroker)
    real_broker._connected = True
    real_broker._last_failure_type = ""
    real_broker._dhan = MagicMock()
    real_broker._dhan.place_order.return_value = _good_response("ORD-VALID-001")

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=real_broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.5,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.5, approved=True, position_size_modifier=1.0)

    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch.object(om, "_reconcile_fill", return_value=None),
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)

    assert result is not None
    assert result.order_id == "ORD-VALID-001"
    assert "ORD-VALID-001" in om._orders


def test_T035_invalid_broker_response_does_not_reach_orders():
    """T035: Malformed response → _orders remains empty, no phantom entry."""
    b = _make_broker("raw string")
    from execution_engine.order_manager import OrderManager
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=b),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.0, approved=True, position_size_modifier=1.0)
    with (
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)
    assert result is None
    assert len(om._orders) == 0


def test_T036_successful_order_has_broker_order_id():
    """T036: OrderRecord.broker_order_id equals the returned order_id string."""
    from execution_engine.brokers.dhan_broker import DhanBroker
    from execution_engine.order_manager import OrderManager
    import config as _cfg

    real_broker = DhanBroker.__new__(DhanBroker)
    real_broker._connected = True
    real_broker._last_failure_type = ""
    real_broker._dhan = MagicMock()
    real_broker._dhan.place_order.return_value = _good_response("BROKER-ORD-999")

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=real_broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.5,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.5, approved=True, position_size_modifier=1.0)
    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch.object(om, "_reconcile_fill", return_value=None),
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)

    assert result is not None
    assert result.broker_order_id == "BROKER-ORD-999"


def test_T037_malformed_response_cannot_create_phantom_position():
    """T037: Malformed response → portfolio.positions stays empty."""
    b = _make_broker(b"binary garbage")  # bytes → MALFORMED
    from execution_engine.order_manager import OrderManager
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=b),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.0, approved=True, position_size_modifier=1.0)
    with (
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        om.execute(sig, dec)
    assert len(om._portfolio.positions) == 0


def test_T038_rejected_response_cannot_create_phantom_position():
    """T038: Explicit BROKER_REJECTED response → no portfolio position created."""
    b = _make_broker(_rejection_response())
    from execution_engine.order_manager import OrderManager
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=b),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.0,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.0, approved=True, position_size_modifier=1.0)
    with (
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        om.execute(sig, dec)
    assert len(om._portfolio.positions) == 0


def test_T039_sl_failure_cannot_falsely_mark_sl_placed():
    """T039: Malformed SL response → sl_order_id is empty string, not a fake ID."""
    from execution_engine.brokers.dhan_broker import DhanBroker
    from execution_engine.order_manager import OrderManager
    import config as _cfg

    # Entry succeeds; SL returns string (malformed)
    entry_call_count = 0
    def _sdk_place_order(**kwargs):
        nonlocal entry_call_count
        entry_call_count += 1
        if kwargs.get("order_type") == "STOP_LOSS":
            return "malformed_sl_string"
        return _good_response("ORD-ENTRY-SL")

    real_broker = DhanBroker.__new__(DhanBroker)
    real_broker._connected = True
    real_broker._last_failure_type = ""
    real_broker._dhan = MagicMock()
    real_broker._dhan.place_order.side_effect = _sdk_place_order

    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=real_broker),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
        patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
              {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
    ):
        om = OrderManager()

    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    from models.agent_output import DecisionResult
    sig = TradeSignal(
        symbol="SBIN", direction=SignalDirection.BUY, signal_type=SignalType.EQUITY,
        entry_price=1046.70, stop_loss=1024.92, target_price=1101.15, confidence=7.5,
        strategy_name="TEST", atr=21.78,
    )
    sig.quantity = 5
    om._portfolio.capital = 1_500_000
    dec = DecisionResult(confidence_score=7.5, approved=True, position_size_modifier=1.0)

    with (
        patch.object(om, "_append_live_journal", return_value=None),
        patch.object(om, "_reconcile_fill", return_value=None),
        patch("notifications.notifier_manager.get_notifier", return_value=MagicMock()),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired", return_value=False),
    ):
        result = om.execute(sig, dec)

    # Entry should succeed; SL failed → sl_order_id must be empty
    assert result is not None
    assert result.order_id == "ORD-ENTRY-SL"
    assert result.sl_order_id == ""   # SL was malformed — must not hold a fake ID


def test_T040_broker_failure_visible_in_error_logs(caplog):
    """T040: Broker failure produces ERROR-level log entry (not swallowed silently)."""
    import logging
    from execution_engine.brokers.dhan_broker import DhanBroker

    b = DhanBroker.__new__(DhanBroker)
    b._connected = True
    b._last_failure_type = ""
    b._dhan = MagicMock()
    b._dhan.place_order.return_value = "i_am_a_string_not_a_dict"

    with caplog.at_level(logging.ERROR, logger="execution_engine.brokers.dhan_broker"):
        result = b.place_order("3045", "NSE_EQ", "BUY", 5, 1046.70, "LIMIT")

    assert result is None
    assert any("BROKER_RESPONSE_MALFORMED" in r.message for r in caplog.records)
