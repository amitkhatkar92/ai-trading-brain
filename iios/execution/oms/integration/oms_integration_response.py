"""iios/execution/oms/integration/oms_integration_response.py
==================================================
IntegrationResponse — immutable output from an OMS integration query.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import (
    ComponentType,
    IntegrationQueryType,
)


@dataclass(frozen=True)
class IntegrationResponse:
    """
    Immutable response from OMSIntegrationEngine.query().

    On success:
      - `succeeded` is True
      - `data` contains the query result as a dict
    On failure:
      - `succeeded` is False
      - `error_code` and `error_message` describe the failure
      - `data` is empty
    """
    response_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:     str   = ""
    query_type:     IntegrationQueryType = IntegrationQueryType.FULL_HEALTH
    component_type: ComponentType | None = None
    succeeded:      bool  = True
    data:           dict[str, Any] = field(default_factory=dict)
    elapsed_ms:     float = 0.0
    error_code:     str   = ""
    error_message:  str   = ""
    result_count:   int   = 0
    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return not self.succeeded

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":    self.response_id,
            "request_id":     self.request_id,
            "query_type":     self.query_type.value,
            "component_type": self.component_type.value if self.component_type else None,
            "succeeded":      self.succeeded,
            "elapsed_ms":     round(self.elapsed_ms, 3),
            "error_code":     self.error_code,
            "error_message":  self.error_message,
            "result_count":   self.result_count,
        }
