"""enterprise_ai_platform/integration/core/__init__.py"""
from __future__ import annotations

from enterprise_ai_platform.integration.core.data_event import IntegrationEvent
from enterprise_ai_platform.integration.core.data_record import DataRecord, DataRequest, DataResponse
from enterprise_ai_platform.integration.core.integration_result import IntegrationResult, ProviderContract

__all__ = [
    "DataRecord",
    "DataRequest",
    "DataResponse",
    "IntegrationEvent",
    "IntegrationResult",
    "ProviderContract",
]
