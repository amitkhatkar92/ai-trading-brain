"""iios/execution/brokers/adapters/alpaca_adapter.py — Alpaca Markets skeleton."""
from __future__ import annotations

from typing import Any, AsyncGenerator

from iios.execution.brokers.broker_constants import (
    AuthMethod, BrokerCapabilityType, BrokerEnvironment,
)
from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter, BrokerAdapterConfig
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse

_CAPS = [
    BrokerCapabilityType.CASH_EQUITY, BrokerCapabilityType.CRYPTO,
    BrokerCapabilityType.MARGIN, BrokerCapabilityType.MARKET_ORDER,
    BrokerCapabilityType.LIMIT_ORDER, BrokerCapabilityType.STOP_ORDER,
    BrokerCapabilityType.STOP_LIMIT_ORDER, BrokerCapabilityType.STREAMING,
    BrokerCapabilityType.HISTORICAL_DATA, BrokerCapabilityType.PAPER_TRADING,
    BrokerCapabilityType.MULTI_ACCOUNT,
]


def _default_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="alpaca", broker_name="Alpaca Markets",
        vendor="Alpaca Securities LLC", version="3.0.0",
        environment=BrokerEnvironment.PAPER, auth_method=AuthMethod.API_KEY,
        base_url="https://paper-api.alpaca.markets",
        ws_url="wss://stream.data.alpaca.markets/v2/iex",
        supported_capabilities=_CAPS,
    )


class AlpacaAdapter(BaseBrokerAdapter):
    """
    Alpaca Markets adapter skeleton.
    Reference: https://docs.alpaca.markets/reference/
    """

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_config())

    async def connect(self) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.connect()")
    async def disconnect(self) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.disconnect()")
    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.authenticate()")
    async def place_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.place_order()")
    async def modify_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.modify_order()")
    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.cancel_order()")
    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_order()")
    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_orders()")
    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_positions()")
    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_holdings()")
    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_balance()")
    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_margin()")
    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.fetch_trades()")

    async def stream_market_data(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("AlpacaAdapter.stream_market_data()"); yield  # type: ignore[misc]

    async def stream_order_updates(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("AlpacaAdapter.stream_order_updates()"); yield  # type: ignore[misc]

    async def stream_positions(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("AlpacaAdapter.stream_positions()"); yield  # type: ignore[misc]

    async def health_check(self) -> BrokerResponse: raise NotImplementedError("AlpacaAdapter.health_check()")
