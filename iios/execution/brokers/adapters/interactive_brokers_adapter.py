"""iios/execution/brokers/adapters/interactive_brokers_adapter.py — IBKR skeleton."""
from __future__ import annotations

from typing import Any, AsyncGenerator

from iios.execution.brokers.broker_constants import (
    AuthMethod, BrokerCapabilityType, BrokerEnvironment,
)
from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter, BrokerAdapterConfig
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse

_CAPS = [
    BrokerCapabilityType.CASH_EQUITY, BrokerCapabilityType.DERIVATIVES,
    BrokerCapabilityType.FUTURES, BrokerCapabilityType.OPTIONS,
    BrokerCapabilityType.CURRENCY, BrokerCapabilityType.COMMODITY,
    BrokerCapabilityType.CRYPTO, BrokerCapabilityType.MARGIN,
    BrokerCapabilityType.MARKET_ORDER, BrokerCapabilityType.LIMIT_ORDER,
    BrokerCapabilityType.STOP_ORDER, BrokerCapabilityType.STOP_LIMIT_ORDER,
    BrokerCapabilityType.ICEBERG_ORDER, BrokerCapabilityType.BASKET_ORDER,
    BrokerCapabilityType.STREAMING, BrokerCapabilityType.HISTORICAL_DATA,
    BrokerCapabilityType.MULTI_ACCOUNT,
]


def _default_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="interactive_brokers", broker_name="Interactive Brokers",
        vendor="Interactive Brokers LLC", version="1.0.0",
        environment=BrokerEnvironment.LIVE, auth_method=AuthMethod.SESSION_TOKEN,
        base_url="https://localhost:5000/v1/api",
        ws_url="wss://localhost:5000/v1/api/ws",
        supported_capabilities=_CAPS,
    )


class InteractiveBrokersAdapter(BaseBrokerAdapter):
    """
    IBKR Client Portal Gateway adapter skeleton.
    Reference: https://interactivebrokers.github.io/cpwebapi/
    """

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_config())

    async def connect(self) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.connect()")
    async def disconnect(self) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.disconnect()")
    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.authenticate()")
    async def place_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.place_order()")
    async def modify_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.modify_order()")
    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.cancel_order()")
    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_order()")
    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_orders()")
    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_positions()")
    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_holdings()")
    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_balance()")
    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_margin()")
    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.fetch_trades()")

    async def stream_market_data(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("InteractiveBrokersAdapter.stream_market_data()"); yield  # type: ignore[misc]

    async def stream_order_updates(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("InteractiveBrokersAdapter.stream_order_updates()"); yield  # type: ignore[misc]

    async def stream_positions(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("InteractiveBrokersAdapter.stream_positions()"); yield  # type: ignore[misc]

    async def health_check(self) -> BrokerResponse: raise NotImplementedError("InteractiveBrokersAdapter.health_check()")
