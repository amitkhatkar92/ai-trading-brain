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
            return {
                "status":          data.get("orderStatus", "UNKNOWN"),
                "filled_qty":      int(data.get("tradedQty", 0) or 0),
                "avg_fill_price":  float(data.get("tradedPrice", 0.0) or 0.0),
                "remaining_qty":   int(data.get("remainingQuantity", 0) or 0),
                "order_id":        order_id,
            }
        except Exception as exc:
            log.warning("[DhanBroker] get_order_status failed %s: %s", order_id, exc)
            return {}
