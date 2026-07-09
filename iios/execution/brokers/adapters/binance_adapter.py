"""iios/execution/brokers/adapters/binance_adapter.py — Binance skeleton."""
from __future__ import annotations

from typing import Any, AsyncGenerator

from iios.execution.brokers.broker_constants import (
    AuthMethod, BrokerCapabilityType, BrokerEnvironment,
)
from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter, BrokerAdapterConfig
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse

_CAPS = [
    BrokerCapabilityType.CRYPTO, BrokerCapabilityType.DERIVATIVES,
    BrokerCapabilityType.FUTURES, BrokerCapabilityType.OPTIONS,
    BrokerCapabilityType.MARGIN, BrokerCapabilityType.MARKET_ORDER,
    BrokerCapabilityType.LIMIT_ORDER, BrokerCapabilityType.STOP_ORDER,
    BrokerCapabilityType.STOP_LIMIT_ORDER, BrokerCapabilityType.STREAMING,
    BrokerCapabilityType.HISTORICAL_DATA,
]


def _default_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="binance", broker_name="Binance",
        vendor="Binance Holdings Ltd", version="3.0.0",
        environment=BrokerEnvironment.LIVE, auth_method=AuthMethod.API_KEY,
        base_url="https://api.binance.com",
        ws_url="wss://stream.binance.com:9443/ws",
        supported_capabilities=_CAPS,
    )


class BinanceAdapter(BaseBrokerAdapter):
    """
    Binance adapter skeleton.
    Reference: https://binance-docs.github.io/apidocs/spot/en/
    """

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_config())

    async def connect(self) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.connect()")
    async def disconnect(self) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.disconnect()")
    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.authenticate()")
    async def place_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.place_order()")
    async def modify_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.modify_order()")
    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.cancel_order()")
    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_order()")
    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_orders()")
    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_positions()")
    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_holdings()")
    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_balance()")
    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_margin()")
    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.fetch_trades()")

    async def stream_market_data(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("BinanceAdapter.stream_market_data()"); yield  # type: ignore[misc]

    async def stream_order_updates(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("BinanceAdapter.stream_order_updates()"); yield  # type: ignore[misc]

    async def stream_positions(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("BinanceAdapter.stream_positions()"); yield  # type: ignore[misc]

    async def health_check(self) -> BrokerResponse: raise NotImplementedError("BinanceAdapter.health_check()")
