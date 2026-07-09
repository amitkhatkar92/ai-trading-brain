"""iios/execution/brokers/adapters/angelone_adapter.py — Angel One skeleton."""
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
    BrokerCapabilityType.MARGIN, BrokerCapabilityType.MARKET_ORDER,
    BrokerCapabilityType.LIMIT_ORDER, BrokerCapabilityType.STOP_ORDER,
    BrokerCapabilityType.STREAMING, BrokerCapabilityType.HISTORICAL_DATA,
    BrokerCapabilityType.GTT, BrokerCapabilityType.AMO,
]


def _default_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="angelone", broker_name="Angel One", vendor="Angel Broking Ltd",
        version="1.0.0", environment=BrokerEnvironment.LIVE,
        auth_method=AuthMethod.TOTP,
        base_url="https://apiconnect.angelbroking.com",
        ws_url="wss://smartapisocket.angelone.in/smart-stream",
        supported_capabilities=_CAPS,
    )


class AngelOneAdapter(BaseBrokerAdapter):
    """Angel One SmartAPI adapter skeleton. Reference: https://smartapi.angelbroking.com/docs"""

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_config())

    async def connect(self) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.connect()")
    async def disconnect(self) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.disconnect()")
    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.authenticate()")
    async def place_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.place_order()")
    async def modify_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.modify_order()")
    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.cancel_order()")
    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_order()")
    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_orders()")
    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_positions()")
    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_holdings()")
    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_balance()")
    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_margin()")
    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.fetch_trades()")

    async def stream_market_data(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("AngelOneAdapter.stream_market_data()"); yield  # type: ignore[misc]

    async def stream_order_updates(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("AngelOneAdapter.stream_order_updates()"); yield  # type: ignore[misc]

    async def stream_positions(self, request: BrokerRequest) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("AngelOneAdapter.stream_positions()"); yield  # type: ignore[misc]

    async def health_check(self) -> BrokerResponse: raise NotImplementedError("AngelOneAdapter.health_check()")
