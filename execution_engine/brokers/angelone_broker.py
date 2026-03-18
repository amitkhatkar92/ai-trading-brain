"""
AngelOne Broker Adapter (SmartAPI)
=====================================
Wraps AngelOne's SmartAPI (SmartConnect) for live order execution.

Docs: https://smartapi.angelbroking.com/docs
Install: pip install smartapi-python pyotp
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from utils import get_logger

log = get_logger(__name__)


class AngelOneBroker:
    """
    AngelOne SmartAPI adapter.
    Uses API key + client credentials + TOTP for secure login.
    """

    def __init__(self, api_key: str, client_id: str,
                 password: str, totp_secret: str):
        self.api_key     = api_key
        self.client_id   = client_id
        self.password    = password
        self.totp_secret = totp_secret
        self._smart      = None
        self._connected  = False
        self._connect()

    def _connect(self):
        try:
            import pyotp
            from SmartApi import SmartConnect
            totp = pyotp.TOTP(self.totp_secret).now()
            self._smart = SmartConnect(api_key=self.api_key)
            data = self._smart.generateSession(self.client_id, self.password, totp)
            if data.get("status"):
                self._connected = True
                log.info("[AngelOneBroker] Connected. ClientID=%s", self.client_id)
            else:
                log.error("[AngelOneBroker] Login failed: %s", data)
        except ImportError:
            log.warning("[AngelOneBroker] SmartApi/pyotp not installed — SIMULATION mode.")
        except Exception as exc:
            log.error("[AngelOneBroker] Connection failed: %s", exc)

    # ─────────────────────────────────────────────
    # ORDER PLACEMENT
    # ─────────────────────────────────────────────

    def place_order(self, symbol: str, token: str, exchange: str,
                    transaction_type: str, quantity: int,
                    price: float = 0.0, order_type: str = "MARKET",
                    product_type: str = "INTRADAY",
                    variety: str = "NORMAL") -> Optional[str]:
        """
        transaction_type: "BUY" | "SELL"
        order_type:       "MARKET" | "LIMIT" | "STOPLOSS_LIMIT" | "STOPLOSS_MARKET"
        product_type:     "INTRADAY" | "DELIVERY" | "CARRYFORWARD" | "MARGIN"
        variety:          "NORMAL" | "STOPLOSS" | "AMO" | "ROBO"
        """
        if not self._connected or self._smart is None:
            log.info("[AngelOneBroker] [SIM] %s %s qty=%d @ %.2f",
                     transaction_type, symbol, quantity, price)
            return f"SIM_ANGEL_{symbol}_{transaction_type}"

        try:
            order_params = {
                "variety":          variety,
                "tradingsymbol":    symbol,
                "symboltoken":      token,
                "transactiontype":  transaction_type,
                "exchange":         exchange,
                "ordertype":        order_type,
                "producttype":      product_type,
                "duration":         "DAY",
                "price":            price,
                "squareoff":        "0",
                "stoploss":         "0",
                "quantity":         str(quantity),
            }
            response = self._smart.placeOrder(order_params)
            order_id = response.get("data", {}).get("orderid")
            log.info("[AngelOneBroker] Order placed: %s", order_id)
            return str(order_id) if order_id else None
        except Exception as exc:
            log.error("[AngelOneBroker] Order failed %s: %s", symbol, exc)
            return None

    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> bool:
        if not self._connected or self._smart is None:
            log.info("[AngelOneBroker] [SIM] CANCEL %s", order_id)
            return True
        try:
            self._smart.cancelOrder(order_id, variety)
            return True
        except Exception as exc:
            log.error("[AngelOneBroker] Cancel failed %s: %s", order_id, exc)
            return False

    def get_positions(self) -> Dict[str, Any]:
        if not self._connected or self._smart is None:
            return {}
        return self._smart.position()

    def get_portfolio(self) -> Dict[str, Any]:
        if not self._connected or self._smart is None:
            return {}
        return self._smart.holding()
