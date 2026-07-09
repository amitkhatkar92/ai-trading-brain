"""iios/execution/brokers/adapters/zerodha_adapter.py

Skeleton adapter for Zerodha / Kite Connect.
No real API calls.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator

from iios.execution.brokers.broker_constants import (
    AuthMethod,
    BrokerCapabilityType,
    BrokerEnvironment,
)
from iios.execution.brokers.core.base_broker_adapter import (
    BaseBrokerAdapter,
    BrokerAdapterConfig,
)
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse

_ZERODHA_CAPABILITIES = [
    BrokerCapabilityType.CASH_EQUITY,
    BrokerCapabilityType.DERIVATIVES,
    BrokerCapabilityType.FUTURES,
    BrokerCapabilityType.OPTIONS,
    BrokerCapabilityType.CURRENCY,
    BrokerCapabilityType.COMMODITY,
    BrokerCapabilityType.MARGIN,
    BrokerCapabilityType.MARKET_ORDER,
    BrokerCapabilityType.LIMIT_ORDER,
    BrokerCapabilityType.STOP_ORDER,
    BrokerCapabilityType.STREAMING,
    BrokerCapabilityType.HISTORICAL_DATA,
    BrokerCapabilityType.GTT,
    BrokerCapabilityType.BRACKET_ORDER,
    BrokerCapabilityType.COVER_ORDER,
    BrokerCapabilityType.AMO,
    BrokerCapabilityType.ICEBERG_ORDER,
]


def _default_zerodha_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="zerodha",
        broker_name="Zerodha",
        vendor="Zerodha Broking Ltd",
        version="3.0.0",
        environment=BrokerEnvironment.LIVE,
        auth_method=AuthMethod.API_KEY,
        base_url="https://api.kite.trade",
        ws_url="wss://ws.kite.trade",
        supported_capabilities=_ZERODHA_CAPABILITIES,
    )


class ZerodhaAdapter(BaseBrokerAdapter):
    """
    Zerodha Kite Connect adapter skeleton.

    Implement all NotImplementedError methods using the Kite Connect v3 API.
    Reference: https://kite.trade/docs/connect/v3/
    """

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_zerodha_config())

    async def connect(self) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.connect()")

    async def disconnect(self) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.disconnect()")

    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse:
        raise NotImplementedError(
            "ZerodhaAdapter.authenticate() — pass {'api_key': ..., 'request_token': ...}"
        )

    async def place_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.place_order()")

    async def modify_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.modify_order()")

    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.cancel_order()")

    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_order()")

    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_orders()")

    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_positions()")

    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_holdings()")

    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_balance()")

    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_margin()")

    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.fetch_trades()")

    async def stream_market_data(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("ZerodhaAdapter.stream_market_data()")
        yield

    async def stream_order_updates(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("ZerodhaAdapter.stream_order_updates()")
        yield

    async def stream_positions(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("ZerodhaAdapter.stream_positions()")
        yield

    async def health_check(self) -> BrokerResponse:
        raise NotImplementedError("ZerodhaAdapter.health_check()")
