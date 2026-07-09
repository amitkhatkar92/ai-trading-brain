"""iios/execution/brokers/adapters/paper_broker_adapter.py

Functional paper-trading adapter.  No real broker API is called.
All state is maintained in memory.  Suitable for testing and simulation.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, AsyncGenerator

from iios.execution.brokers.broker_constants import (
    AuthMethod,
    BrokerCapabilityType,
    BrokerEnvironment,
    BrokerStatus,
    ConnectionStatus,
)
from iios.execution.brokers.core.base_broker_adapter import (
    BaseBrokerAdapter,
    BrokerAdapterConfig,
)
from iios.execution.brokers.core.broker_connection import BrokerConnection
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse
from iios.execution.brokers.core.broker_session import BrokerSession

_PAPER_CAPABILITIES = [
    BrokerCapabilityType.CASH_EQUITY,
    BrokerCapabilityType.DERIVATIVES,
    BrokerCapabilityType.FUTURES,
    BrokerCapabilityType.OPTIONS,
    BrokerCapabilityType.MARGIN,
    BrokerCapabilityType.MARKET_ORDER,
    BrokerCapabilityType.LIMIT_ORDER,
    BrokerCapabilityType.STOP_ORDER,
    BrokerCapabilityType.STREAMING,
    BrokerCapabilityType.HISTORICAL_DATA,
    BrokerCapabilityType.PAPER_TRADING,
    BrokerCapabilityType.BRACKET_ORDER,
]


def _default_paper_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="paper",
        broker_name="Paper Broker",
        vendor="IIOS",
        version="1.0.0",
        environment=BrokerEnvironment.PAPER,
        auth_method=AuthMethod.NONE,
        supported_capabilities=_PAPER_CAPABILITIES,
    )


class PaperBrokerAdapter(BaseBrokerAdapter):
    """
    In-memory paper-trading adapter.

    Simulates order placement, position tracking, and balance management.
    Does not call any external endpoint.
    """

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_paper_config())
        self._orders:    dict[str, dict[str, Any]] = {}
        self._positions: dict[str, dict[str, Any]] = {}
        self._cash_balance = 1_000_000.0   # 10 lakh INR default
        self._trades:    list[dict[str, Any]] = []

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> BrokerResponse:
        self._set_status(BrokerStatus.CONNECTING)
        conn = self._new_connection()
        conn.mark_connected()
        self._connection = conn
        self._set_status(BrokerStatus.CONNECTED)
        self._record_request(True)
        return BrokerResponse.ok(
            {"connected": True, "broker_id": self._broker_id},
            broker_id=self._broker_id, operation="connect",
        )

    async def disconnect(self) -> BrokerResponse:
        if self._connection:
            self._connection.mark_disconnected("manual disconnect")
        self._set_status(BrokerStatus.DISCONNECTED)
        self._session = None
        self._record_request(True)
        return BrokerResponse.ok(
            {"connected": False},
            broker_id=self._broker_id, operation="disconnect",
        )

    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse:
        # Paper trading accepts any credentials
        self._session = BrokerSession(
            broker_id=self._broker_id,
            user_id=credentials.get("user_id", "paper_user"),
            auth_method=AuthMethod.NONE,
            access_token="paper_token_" + str(uuid.uuid4()),
            expires_at=time.time() + 86_400.0,
        )
        self._record_request(True)
        return BrokerResponse.ok(
            {"authenticated": True, "session_id": self._session.session_id},
            broker_id=self._broker_id, operation="authenticate",
        )

    # ── Orders ────────────────────────────────────────────────────────────────

    async def place_order(self, request: BrokerRequest) -> BrokerResponse:
        order_id = "PAPER-" + str(uuid.uuid4())[:8].upper()
        order = {
            "order_id":   order_id,
            "symbol":     request.payload.get("symbol", ""),
            "side":       request.payload.get("side", "BUY"),
            "quantity":   request.payload.get("quantity", 0),
            "price":      request.payload.get("price", 0.0),
            "order_type": request.payload.get("order_type", "MARKET"),
            "status":     "EXECUTED",
            "placed_at":  time.time(),
            "broker_id":  self._broker_id,
        }
        self._orders[order_id] = order
        # Simulate position update
        symbol = order["symbol"]
        qty    = order["quantity"]
        if order["side"] == "BUY":
            self._positions[symbol] = self._positions.get(symbol, {"symbol": symbol, "quantity": 0})
            self._positions[symbol]["quantity"] += qty
        else:
            if symbol in self._positions:
                self._positions[symbol]["quantity"] -= qty
        self._trades.append({**order, "trade_id": str(uuid.uuid4())})
        self._record_request(True)
        return BrokerResponse.ok(
            {"order_id": order_id, "status": "EXECUTED"},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="place_order",
        )

    async def modify_order(self, request: BrokerRequest) -> BrokerResponse:
        order_id = request.payload.get("order_id", "")
        if order_id not in self._orders:
            return BrokerResponse.fail(
                "BAF-011", f"Order {order_id} not found",
                request_id=request.request_id, broker_id=self._broker_id,
                operation="modify_order",
            )
        self._orders[order_id].update(request.payload)
        self._record_request(True)
        return BrokerResponse.ok(
            {"order_id": order_id, "modified": True},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="modify_order",
        )

    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse:
        order_id = request.payload.get("order_id", "")
        if order_id not in self._orders:
            return BrokerResponse.fail(
                "BAF-011", f"Order {order_id} not found",
                request_id=request.request_id, broker_id=self._broker_id,
                operation="cancel_order",
            )
        self._orders[order_id]["status"] = "CANCELLED"
        self._record_request(True)
        return BrokerResponse.ok(
            {"order_id": order_id, "cancelled": True},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="cancel_order",
        )

    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse:
        order_id = request.payload.get("order_id", "")
        order    = self._orders.get(order_id)
        if order is None:
            return BrokerResponse.fail(
                "BAF-011", f"Order {order_id} not found",
                request_id=request.request_id, broker_id=self._broker_id,
                operation="fetch_order",
            )
        self._record_request(True)
        return BrokerResponse.ok(
            {"order": order},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_order",
        )

    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse:
        self._record_request(True)
        return BrokerResponse.ok(
            {"orders": list(self._orders.values()), "count": len(self._orders)},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_orders",
        )

    # ── Portfolio ─────────────────────────────────────────────────────────────

    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse:
        positions = [p for p in self._positions.values() if p.get("quantity", 0) != 0]
        self._record_request(True)
        return BrokerResponse.ok(
            {"positions": positions, "count": len(positions)},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_positions",
        )

    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse:
        self._record_request(True)
        return BrokerResponse.ok(
            {"holdings": [], "count": 0},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_holdings",
        )

    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse:
        self._record_request(True)
        return BrokerResponse.ok(
            {"available_cash": self._cash_balance, "currency": "INR"},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_balance",
        )

    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse:
        self._record_request(True)
        return BrokerResponse.ok(
            {
                "available_margin": self._cash_balance * 5.0,
                "used_margin": 0.0,
                "currency": "INR",
            },
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_margin",
        )

    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse:
        self._record_request(True)
        return BrokerResponse.ok(
            {"trades": list(self._trades), "count": len(self._trades)},
            request_id=request.request_id, broker_id=self._broker_id,
            operation="fetch_trades",
        )

    # ── Streaming ─────────────────────────────────────────────────────────────

    async def stream_market_data(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        symbols = request.payload.get("symbols", ["NIFTY"])
        for i in range(3):      # emit 3 synthetic ticks then stop
            await asyncio.sleep(0)
            for sym in symbols:
                yield BrokerResponse.ok(
                    {
                        "symbol": sym,
                        "ltp":    100.0 + i,
                        "volume": 1000 * (i + 1),
                        "tick":   i,
                    },
                    broker_id=self._broker_id, operation="stream_market_data",
                )

    async def stream_order_updates(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        for order in list(self._orders.values())[:3]:
            await asyncio.sleep(0)
            yield BrokerResponse.ok(
                {"order_update": order},
                broker_id=self._broker_id, operation="stream_order_updates",
            )

    async def stream_positions(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        for pos in list(self._positions.values())[:3]:
            await asyncio.sleep(0)
            yield BrokerResponse.ok(
                {"position_update": pos},
                broker_id=self._broker_id, operation="stream_positions",
            )

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self) -> BrokerResponse:
        return BrokerResponse.ok(
            {
                "healthy":      True,
                "status":       self._status.value,
                "order_count":  len(self._orders),
                "position_count": len(self._positions),
            },
            broker_id=self._broker_id, operation="health_check",
        )

    # ── Paper-specific helpers ────────────────────────────────────────────────

    def set_cash_balance(self, amount: float) -> None:
        self._cash_balance = amount

    def reset(self) -> None:
        """Reset all paper state (useful between tests)."""
        self._orders.clear()
        self._positions.clear()
        self._trades.clear()
        self._cash_balance = 1_000_000.0
