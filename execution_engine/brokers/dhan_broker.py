"""
Dhan Broker Adapter
====================
Wraps DhanHQ SDK for order routing, portfolio queries, and market data.

Docs: https://dhanhq.co/docs/v2/
Install: pip install dhanhq
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from utils import get_logger

log = get_logger(__name__)


class DhanBroker:
    """
    DhanHQ adapter.
    Requires client_id and access_token from DhanHQ developer console.
    """

    def __init__(self, client_id: str, access_token: str):
        self.client_id    = client_id
        self.access_token = access_token
        self._dhan        = None
        self._connected   = False
        self._connect()

    def _connect(self):
        try:
            from dhanhq import dhanhq as _DhanHQ
            try:
                from dhanhq import DhanContext  # v2.1+
                ctx        = DhanContext(self.client_id, self.access_token)
                self._dhan = _DhanHQ(ctx)
            except ImportError:
                self._dhan = _DhanHQ(self.client_id, self.access_token)
            self._connected = True
            log.info("[DhanBroker] Connected.")
        except ImportError:
            log.warning("[DhanBroker] dhanhq not installed — running in SIMULATION mode.")
        except Exception as exc:
            log.error("[DhanBroker] Connection failed: %s", exc)

    # ─────────────────────────────────────────────
    # ORDER PLACEMENT
    # ─────────────────────────────────────────────

    def place_order(self, security_id: str, exchange_segment: str,
                    transaction_type: str, quantity: int,
                    price: float = 0.0, order_type: str = "MARKET",
                    product_type: str = "INTRADAY") -> Optional[str]:
        """
        transaction_type:  "BUY" | "SELL"
        order_type:        "MARKET" | "LIMIT" | "STOP_LOSS" | "STOP_LOSS_MARKET"
        product_type:      "INTRADAY" | "CNC" | "MARGIN" | "MTF"
        exchange_segment:  "NSE_EQ" | "BSE_EQ" | "NSE_FNO"
        """
        if not self._connected or self._dhan is None:
            log.info("[DhanBroker] [SIM] PLACE ORDER %s %s qty=%d @ %.2f",
                     transaction_type, security_id, quantity, price)
            return f"SIM_DHAN_{security_id}_{transaction_type}"

        try:
            response = self._dhan.place_order(
                security_id       = security_id,
                exchange_segment  = exchange_segment,
                transaction_type  = transaction_type,
                quantity          = quantity,
                order_type        = order_type,
                product_type      = product_type,
                price             = price,
            )
            order_id = response.get("data", {}).get("orderId")
            log.info("[DhanBroker] Order placed: %s", order_id)
            return str(order_id) if order_id else None
        except Exception as exc:
            log.error("[DhanBroker] Order failed %s: %s", security_id, exc)
            return None

    def place_sl_order(self, symbol: str, exchange: str, transaction_type: str,
                       quantity: int, trigger_price: float, price: float) -> Optional[str]:
        """
        Place a stop-loss order for an open position.

        symbol:           bare NSE symbol (e.g. "TATASTEEL") — resolved via DHAN_SECURITY_MAP
        exchange:         "NSE" (resolved to NSE_EQ / segment internally)
        transaction_type: "BUY" | "SELL"
        trigger_price:    stop trigger level (exchange activates order at this price)
        price:            limit price (slightly worse than trigger — ensures fill)

        SIM-safe: returns SIM_SL_* string when not connected.
        Returns None if symbol not in DHAN_SECURITY_MAP (safe — software SL still active).
        """
        if not self._connected or self._dhan is None:
            log.info("[DhanBroker] [SIM] SL_ORDER %s %s qty=%d trigger=%.2f",
                     transaction_type, symbol, quantity, trigger_price)
            return f"SIM_SL_{symbol}_{transaction_type}"
        from data_feeds.dhan_feed import DHAN_SECURITY_MAP as _DSM
        _sym = str(symbol).upper().replace(".NS", "").replace(".BO", "")
        _meta = _DSM.get(_sym)
        if not _meta:
            log.error(
                "[DhanBroker] [MISSING_DHAN_MAPPING] SL order for %s blocked — "
                "not in DHAN_SECURITY_MAP. Software SL still active via monitor.",
                symbol,
            )
            return None
        try:
            response = self._dhan.place_order(
                security_id      = _meta["security_id"],
                exchange_segment = _meta["segment"],
                transaction_type = transaction_type,
                quantity         = quantity,
                order_type       = "STOP_LOSS",
                product_type     = "INTRADAY",
                price            = price,
                trigger_price    = trigger_price,
            )
            order_id = response.get("data", {}).get("orderId")
            log.info("[DhanBroker] SL order placed: %s  symbol=%s trigger=%.2f",
                     order_id, symbol, trigger_price)
            return str(order_id) if order_id else None
        except Exception as exc:
            log.error("[DhanBroker] SL order failed for %s: %s", symbol, exc)
            return None

    def cancel_order(self, order_id: str) -> bool:
        if not self._connected or self._dhan is None:
            log.info("[DhanBroker] [SIM] CANCEL %s", order_id)
            return True
        try:
            self._dhan.cancel_order(order_id=order_id)
            return True
        except Exception as exc:
            log.error("[DhanBroker] Cancel failed %s: %s", order_id, exc)
            return False

    def get_positions(self) -> Dict[str, Any]:
        if not self._connected or self._dhan is None:
            return {}
        return self._dhan.get_positions()

    def get_portfolio(self) -> Dict[str, Any]:
        if not self._connected or self._dhan is None:
            return {}
        return self._dhan.get_holdings()

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Return fill status for order_id (ARCH-004 LIVE-003/004: fill reconciliation).
        Returns dict with status, filled_qty, avg_fill_price, remaining_qty.
        Safe to call in paper mode — returns SIM sentinel."""
        if not self._connected or self._dhan is None:
            return {"status": "SIM", "filled_qty": 0, "avg_fill_price": 0.0, "remaining_qty": 0}
        try:
            resp = self._dhan.get_order_by_id(order_id=order_id)
            data = resp.get("data", {}) if isinstance(resp, dict) else {}
            # V2 Order Book uses filledQty / averageTradedPrice (not tradedQty / tradedPrice)
            return {
                "status":          data.get("orderStatus", "UNKNOWN"),
                "filled_qty":      int(data.get("filledQty", data.get("tradedQty", 0)) or 0),
                "avg_fill_price":  float(data.get("averageTradedPrice", data.get("tradedPrice", 0.0)) or 0.0),
                "remaining_qty":   int(data.get("remainingQuantity", 0) or 0),
                "order_id":        order_id,
            }
        except Exception as exc:
            log.warning("[DhanBroker] get_order_status failed %s: %s", order_id, exc)
            return {}

    def get_fill_details(self, order_id: str) -> Dict[str, Any]:
        """
        Canonical fill-detail query for fill reconciliation (matches DhanFeed interface).
        Delegates to get_order_status() — no new Dhan API calls.
        Never raises; fails safe (never assumes FILLED on error).
        """
        result: Dict[str, Any] = {
            "status":                "API_ERROR",
            "broker_order_id":       order_id,
            "requested_price":       0.0,
            "actual_fill_price":     0.0,
            "filled_quantity":       0,
            "requested_qty":         0,
            "order_status_raw":      "",
            "fill_timestamp":        "",
            "reconciliation_source": "DHAN_BROKER",
        }
        try:
            raw = self.get_order_status(order_id)
            if not raw:
                return result
            raw_status = str(raw.get("status", "")).upper()
            if raw_status == "SIM":
                result["status"] = "SIM"
                return result
            # Map Dhan raw statuses to canonical values (same mapping as DhanFeed)
            if raw_status in ("TRADED", "COMPLETE", "FULLY_EXECUTED", "FILLED"):
                canonical = "FILLED"
            elif raw_status in ("PARTIALLY_TRADED", "PART_TRADED", "PARTIAL",
                                "PARTIALLY_FILLED"):
                canonical = "PARTIALLY_FILLED"
            elif raw_status in ("REJECTED", "INVALID_REQUEST"):
                canonical = "REJECTED"
            elif raw_status in ("CANCELLED", "CANCELED", "EXPIRED"):
                canonical = "CANCELLED"
            elif raw_status in ("PENDING", "TRANSIT", "OPEN",
                                "TRIGGER_PENDING", "UNKNOWN"):
                canonical = "PENDING"
            else:
                canonical = "PENDING"  # fail safe — never assume filled
            avg_price = float(raw.get("avg_fill_price", 0.0) or 0.0)
            result.update({
                "status":            canonical,
                "actual_fill_price": avg_price if canonical in (
                    "FILLED", "PARTIALLY_FILLED") else 0.0,
                "filled_quantity":   int(raw.get("filled_qty", 0) or 0),
                "order_status_raw":  raw_status,
            })
        except Exception as exc:
            log.warning("[DhanBroker] get_fill_details failed %s: %s", order_id, exc)
        return result
