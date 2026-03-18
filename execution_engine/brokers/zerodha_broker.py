"""
Zerodha Broker Adapter
=======================
Wraps KiteConnect API for order placement, position management,
and market data retrieval.

Docs: https://kite.trade/docs/connect/v3/
Install: pip install kiteconnect
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from utils import get_logger

log = get_logger(__name__)


class ZerodhaBroker:
    """
    KiteConnect adapter.
    Initialise with api_key + access_token (obtained via login flow).
    """

    def __init__(self, api_key: str, access_token: str):
        self.api_key      = api_key
        self.access_token = access_token
        self._kite        = None
        self._connected   = False
        self._connect()

    def _connect(self):
        try:
            from kiteconnect import KiteConnect
            self._kite = KiteConnect(api_key=self.api_key)
            self._kite.set_access_token(self.access_token)
            self._connected = True
            log.info("[ZerodhaBroker] Connected.")
        except ImportError:
            log.warning("[ZerodhaBroker] kiteconnect not installed — running in SIMULATION mode.")
        except Exception as exc:
            log.error("[ZerodhaBroker] Connection failed: %s", exc)

    # ─────────────────────────────────────────────
    # ORDER PLACEMENT
    # ─────────────────────────────────────────────

    def place_order(self, symbol: str, exchange: str, transaction_type: str,
                    quantity: int, price: float = 0.0,
                    order_type: str = "MARKET",
                    product: str = "MIS") -> Optional[str]:
        """
        Place an order. Returns order_id or None on failure.
        transaction_type: "BUY" | "SELL"
        order_type:       "MARKET" | "LIMIT" | "SL" | "SL-M"
        product:          "MIS" (intraday) | "CNC" (delivery) | "NRML" (F&O)
        """
        if not self._connected or self._kite is None:
            log.info("[ZerodhaBroker] [SIM] PLACE ORDER %s %s %s qty=%d @ %.2f",
                     transaction_type, symbol, exchange, quantity, price)
            return f"SIM_ORDER_{symbol}_{transaction_type}"

        try:
            order_id = self._kite.place_order(
                variety           = self._kite.VARIETY_REGULAR,
                exchange          = exchange,
                tradingsymbol     = symbol,
                transaction_type  = transaction_type,
                quantity          = quantity,
                price             = price if order_type == "LIMIT" else 0,
                order_type        = order_type,
                product           = product,
            )
            log.info("[ZerodhaBroker] Order placed: %s", order_id)
            return str(order_id)
        except Exception as exc:
            log.error("[ZerodhaBroker] Order failed for %s: %s", symbol, exc)
            return None

    def place_sl_order(self, symbol: str, exchange: str,
                       transaction_type: str, quantity: int,
                       trigger_price: float, price: float,
                       product: str = "MIS") -> Optional[str]:
        """Place a stop-loss order."""
        if not self._connected or self._kite is None:
            log.info("[ZerodhaBroker] [SIM] SL ORDER %s %s trigger=%.2f",
                     symbol, transaction_type, trigger_price)
            return f"SIM_SL_{symbol}"

        try:
            order_id = self._kite.place_order(
                variety           = self._kite.VARIETY_REGULAR,
                exchange          = exchange,
                tradingsymbol     = symbol,
                transaction_type  = transaction_type,
                quantity          = quantity,
                price             = price,
                trigger_price     = trigger_price,
                order_type        = self._kite.ORDER_TYPE_SL,
                product           = product,
            )
            return str(order_id)
        except Exception as exc:
            log.error("[ZerodhaBroker] SL order failed for %s: %s", symbol, exc)
            return None

    def cancel_order(self, order_id: str) -> bool:
        if not self._connected or self._kite is None:
            log.info("[ZerodhaBroker] [SIM] CANCEL ORDER %s", order_id)
            return True
        try:
            self._kite.cancel_order(variety=self._kite.VARIETY_REGULAR, order_id=order_id)
            return True
        except Exception as exc:
            log.error("[ZerodhaBroker] Cancel failed %s: %s", order_id, exc)
            return False

    def get_positions(self) -> Dict[str, Any]:
        if not self._connected or self._kite is None:
            return {"net": [], "day": []}
        return self._kite.positions()

    def get_portfolio(self) -> Dict[str, Any]:
        if not self._connected or self._kite is None:
            return {}
        return {"holdings": self._kite.holdings(),
                "positions": self._kite.positions()}
