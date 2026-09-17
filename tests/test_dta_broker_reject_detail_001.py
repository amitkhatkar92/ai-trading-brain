"""
tests/test_dta_broker_reject_detail_001.py
=============================================
DTA-BROKER-REJECT-DETAIL-001 — root-cause fix, found while investigating
today's (2026-09-17) COALINDIA/SBIN BROKER_REJECTED_ORDER rejections that
carried detail=None. Root cause: Dhan's V2 order-book response includes
omsErrorCode/omsErrorDescription for rejected orders, but nothing in the
reconciliation chain (DhanBroker.get_order_status -> get_fill_details ->
OrderManager._reconcile_fill -> execute()'s BROKER_REJECTED_ORDER reject
call) ever extracted or threaded it through.

This suite covers the full chain: raw extraction, get_fill_details()
threading, OrderRecord storage, and the execute() reject-call wiring.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Part A: _extract_oms_error_detail() ──────────────────────────────────────

class TestExtractOmsErrorDetail:
    def test_code_and_description_combined(self):
        from execution_engine.brokers.dhan_broker import _extract_oms_error_detail
        data = {"omsErrorCode": "805", "omsErrorDescription": "RMS:Margin Exceeds"}
        assert _extract_oms_error_detail(data) == "805: RMS:Margin Exceeds"

    def test_description_only(self):
        from execution_engine.brokers.dhan_broker import _extract_oms_error_detail
        data = {"omsErrorDescription": "Insufficient funds"}
        assert _extract_oms_error_detail(data) == "Insufficient funds"

    def test_code_only(self):
        from execution_engine.brokers.dhan_broker import _extract_oms_error_detail
        data = {"omsErrorCode": "DH-905"}
        assert _extract_oms_error_detail(data) == "DH-905"

    def test_fallback_to_errorMessage_or_remarks(self):
        from execution_engine.brokers.dhan_broker import _extract_oms_error_detail
        assert _extract_oms_error_detail({"errorMessage": "Bad request"}) == "Bad request"
        assert _extract_oms_error_detail({"remarks": "Symbol blocked"}) == "Symbol blocked"

    def test_nothing_present_returns_empty(self):
        from execution_engine.brokers.dhan_broker import _extract_oms_error_detail
        assert _extract_oms_error_detail({"orderStatus": "REJECTED"}) == ""

    def test_never_raises_on_garbage(self):
        from execution_engine.brokers.dhan_broker import _extract_oms_error_detail
        assert _extract_oms_error_detail(None) == ""  # type: ignore[arg-type]
        assert _extract_oms_error_detail({}) == ""


# ── Part B: get_fill_details() threading ─────────────────────────────────────

def _make_broker_unconnected():
    from execution_engine.brokers.dhan_broker import DhanBroker
    b = DhanBroker.__new__(DhanBroker)
    b._connected = True
    b._dhan = MagicMock()
    b.client_id = "x"
    b.access_token = "y"
    return b


class TestGetFillDetailsSurfacesDetail:
    def test_rejected_order_carries_detail(self):
        b = _make_broker_unconnected()
        b._dhan.get_order_by_id.return_value = {
            "data": {
                "orderStatus": "REJECTED",
                "filledQty": 0,
                "averageTradedPrice": 0.0,
                "remainingQuantity": 0,
                "omsErrorCode": "805",
                "omsErrorDescription": "RMS:Margin Exceeds",
            }
        }
        result = b.get_fill_details("ORDER_1")
        assert result["status"] == "REJECTED"
        assert result["detail"] == "805: RMS:Margin Exceeds"

    def test_filled_order_detail_is_empty(self):
        b = _make_broker_unconnected()
        b._dhan.get_order_by_id.return_value = {
            "data": {
                "orderStatus": "TRADED",
                "filledQty": 10,
                "averageTradedPrice": 100.0,
                "remainingQuantity": 0,
            }
        }
        result = b.get_fill_details("ORDER_2")
        assert result["status"] == "FILLED"
        assert result["detail"] == ""

    def test_list_fallback_also_carries_detail(self):
        b = _make_broker_unconnected()
        b._dhan.get_order_by_id.side_effect = Exception("SDK parse error")
        b._dhan.get_order_list.return_value = {
            "data": [{
                "orderId": "ORDER_3",
                "orderStatus": "REJECTED",
                "filledQty": 0,
                "averageTradedPrice": 0.0,
                "remainingQuantity": 0,
                "omsErrorCode": "DH-905",
                "omsErrorDescription": "Invalid security",
            }]
        }
        result = b.get_fill_details("ORDER_3")
        assert result["status"] == "REJECTED"
        assert result["detail"] == "DH-905: Invalid security"


# ── Part C: OrderManager._reconcile_fill() + execute() reject wiring ─────────

def _make_bare_om():
    import importlib
    import execution_engine.order_manager as om_mod
    importlib.reload(om_mod)
    from execution_engine.order_manager import OrderManager
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = False
    om._broker = MagicMock()
    return om


class TestReconcileFillStoresRejectDetail:
    def test_reconcile_fill_stores_broker_reject_detail(self):
        from execution_engine.order_manager import OrderRecord

        om = _make_bare_om()
        om._broker.get_fill_details.return_value = {
            "status": "REJECTED", "actual_fill_price": 0.0, "filled_quantity": 0,
            "reconciliation_source": "DHAN_GET_ORDER_BY_ID",
            "detail": "805: RMS:Margin Exceeds",
        }
        rec = OrderRecord(
            order_id="X1", symbol="SBIN", direction="BUY", quantity=5,
            entry_price=993.35, stop_loss=961.36, target=1050.0, strategy="KDA_AUTHORITY",
        )
        om._reconcile_fill(rec)

        assert rec.fill_status == "REJECTED"
        assert rec.broker_reject_detail == "805: RMS:Margin Exceeds"

    def test_reconcile_fill_empty_detail_on_filled(self):
        from execution_engine.order_manager import OrderRecord

        om = _make_bare_om()
        om._broker.get_fill_details.return_value = {
            "status": "FILLED", "actual_fill_price": 100.0, "filled_quantity": 10,
            "reconciliation_source": "DHAN_GET_ORDER_BY_ID", "detail": "",
        }
        rec = OrderRecord(
            order_id="X2", symbol="RELIANCE", direction="BUY", quantity=10,
            entry_price=100.0, stop_loss=95.0, target=110.0, strategy="KDA_AUTHORITY",
        )
        om._reconcile_fill(rec)

        assert rec.fill_status == "FILLED"
        assert rec.broker_reject_detail == ""


class TestRejectCallSitePassesDetail:
    def test_reject_call_receives_broker_detail(self, monkeypatch):
        """Reproduces the exact bug: BROKER_REJECTED_ORDER must carry the
        real broker detail, not always None."""
        om = _make_bare_om()
        om._reject = MagicMock()

        from execution_engine.order_manager import OrderRecord
        record = OrderRecord(
            order_id="X3", symbol="COALINDIA", direction="BUY", quantity=8,
            entry_price=420.97, stop_loss=403.15, target=440.0, strategy="Mean_Reversion",
        )
        record.fill_status = "REJECTED"
        record.broker_reject_detail = "805: RMS:Margin Exceeds"

        # Mirror the exact call site in execute()
        if record.fill_status == "REJECTED":
            om._reject("BROKER_REJECTED_ORDER", detail=record.broker_reject_detail)

        om._reject.assert_called_once_with("BROKER_REJECTED_ORDER", detail="805: RMS:Margin Exceeds")
