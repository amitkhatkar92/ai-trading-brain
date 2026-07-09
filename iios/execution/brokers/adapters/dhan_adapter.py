"""iios/execution/brokers/adapters/dhan_adapter.py

Skeleton adapter for Dhan broker.
Implements BaseBrokerAdapter interface structure only.
No real API calls are made.
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

_DHAN_CAPABILITIES = [
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
    BrokerCapabilityType.STOP_LIMIT_ORDER,
    BrokerCapabilityType.STREAMING,
    BrokerCapabilityType.HISTORICAL_DATA,
    BrokerCapabilityType.GTT,
    BrokerCapabilityType.BRACKET_ORDER,
    BrokerCapabilityType.COVER_ORDER,
    BrokerCapabilityType.AMO,
]


def _default_dhan_config() -> BrokerAdapterConfig:
    return BrokerAdapterConfig(
        broker_id="dhan",
        broker_name="Dhan",
        vendor="Dhan HQ Pvt Ltd",
        version="2.0.0",
        environment=BrokerEnvironment.LIVE,
        auth_method=AuthMethod.API_KEY,
        base_url="https://api.dhan.co",
        ws_url="wss://api-order-update.dhan.co",
        supported_capabilities=_DHAN_CAPABILITIES,
    )


class DhanAdapter(BaseBrokerAdapter):
    """
    Dhan broker adapter skeleton.

    Inherit this class and implement all NotImplementedError methods
    using the Dhan REST/WebSocket API.
    Reference: https://dhanhq.co/docs/v2/
    """

    def __init__(self, config: BrokerAdapterConfig | None = None) -> None:
        super().__init__(config or _default_dhan_config())

    async def connect(self) -> BrokerResponse:
        raise NotImplementedError(
            "DhanAdapter.connect() — implement using Dhan API credentials"
        )

    async def disconnect(self) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.disconnect()")

    async def authenticate(self, credentials: dict[str, Any]) -> BrokerResponse:
        raise NotImplementedError(
            "DhanAdapter.authenticate() — pass {'client_id': ..., 'access_token': ...}"
        )

    async def place_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.place_order()")

    async def modify_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.modify_order()")

    async def cancel_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.cancel_order()")

    async def fetch_order(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_order()")

    async def fetch_orders(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_orders()")

    async def fetch_positions(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_positions()")

    async def fetch_holdings(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_holdings()")

    async def fetch_balance(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_balance()")

    async def fetch_margin(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_margin()")

    async def fetch_trades(self, request: BrokerRequest) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.fetch_trades()")

    async def stream_market_data(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("DhanAdapter.stream_market_data()")
        yield  # make generator syntax valid

    async def stream_order_updates(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("DhanAdapter.stream_order_updates()")
        yield

    async def stream_positions(
        self, request: BrokerRequest
    ) -> AsyncGenerator[BrokerResponse, None]:
        raise NotImplementedError("DhanAdapter.stream_positions()")
        yield

    async def health_check(self) -> BrokerResponse:
        raise NotImplementedError("DhanAdapter.health_check()")
