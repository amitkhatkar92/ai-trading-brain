"""
market_integration_response.py — iios.market.integration
==========================================================
Immutable market integration response value object.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    IntegrationRequestType,
    IntegrationStatus,
    SUCCESSFUL_STATUSES,
)


@dataclass(frozen=True)
class MarketIntegrationResponse:
    """
    Immutable response returned by
    :meth:`~.market_integration_engine.MarketIntegrationEngine.submit`.

    Fields
    ------
    response_id :          Unique response identifier.
    request_id :           Originating request identifier.
    integration_id :       Integration correlation identifier.
    exchange :             Target exchange.
    request_type :         Request type that was processed.
    status :               Processing outcome status.
    market_analysis_id :   Market analysis identifier.
    snapshot_id :          MarketSnapshot identifier (if one was published).
    elapsed_s :            Wall-clock processing duration.
    error_message :        Non-empty when status is FAILED or REJECTED.
    metadata :             Supplementary metadata.
    responded_at :         Wall-clock response creation time.
    framework_version :    Framework version string.
    """
    response_id:         str
    request_id:          str
    integration_id:      str
    exchange:            str
    request_type:        IntegrationRequestType
    status:              IntegrationStatus
    market_analysis_id:  str
    snapshot_id:         str
    elapsed_s:           float
    error_message:       str
    metadata:            Dict[str, Any]
    responded_at:        float
    framework_version:   str

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_successful(self) -> bool:
        return self.status in SUCCESSFUL_STATUSES

    @property
    def is_failed(self) -> bool:
        return self.status == IntegrationStatus.FAILED

    @property
    def is_rejected(self) -> bool:
        return self.status == IntegrationStatus.REJECTED

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_id)

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def create_success(
        cls,
        request_id:         str,
        integration_id:     str,
        exchange:           str,
        request_type:       IntegrationRequestType,
        *,
        response_id:        Optional[str]            = None,
        market_analysis_id: str                      = "",
        snapshot_id:        str                      = "",
        elapsed_s:          float                    = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "MarketIntegrationResponse":
        return cls(
            response_id        = response_id or str(uuid.uuid4()),
            request_id         = request_id,
            integration_id     = integration_id,
            exchange           = exchange,
            request_type       = request_type,
            status             = IntegrationStatus.COMPLETED,
            market_analysis_id = market_analysis_id,
            snapshot_id        = snapshot_id,
            elapsed_s          = elapsed_s,
            error_message      = "",
            metadata           = dict(metadata or {}),
            responded_at       = time.time(),
            framework_version  = VERSION,
        )

    @classmethod
    def create_failure(
        cls,
        request_id:         str,
        integration_id:     str,
        exchange:           str,
        request_type:       IntegrationRequestType,
        *,
        response_id:        Optional[str]            = None,
        market_analysis_id: str                      = "",
        error_message:      str                      = "",
        elapsed_s:          float                    = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "MarketIntegrationResponse":
        return cls(
            response_id        = response_id or str(uuid.uuid4()),
            request_id         = request_id,
            integration_id     = integration_id,
            exchange           = exchange,
            request_type       = request_type,
            status             = IntegrationStatus.FAILED,
            market_analysis_id = market_analysis_id,
            snapshot_id        = "",
            elapsed_s          = elapsed_s,
            error_message      = error_message,
            metadata           = dict(metadata or {}),
            responded_at       = time.time(),
            framework_version  = VERSION,
        )

    @classmethod
    def create_rejected(
        cls,
        request_id:     str,
        integration_id: str,
        exchange:       str,
        request_type:   IntegrationRequestType,
        *,
        reason:         str                      = "",
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> "MarketIntegrationResponse":
        return cls(
            response_id        = str(uuid.uuid4()),
            request_id         = request_id,
            integration_id     = integration_id,
            exchange           = exchange,
            request_type       = request_type,
            status             = IntegrationStatus.REJECTED,
            market_analysis_id = "",
            snapshot_id        = "",
            elapsed_s          = 0.0,
            error_message      = reason,
            metadata           = dict(metadata or {}),
            responded_at       = time.time(),
            framework_version  = VERSION,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":        self.response_id,
            "request_id":         self.request_id,
            "integration_id":     self.integration_id,
            "exchange":           self.exchange,
            "request_type":       self.request_type.value,
            "status":             self.status.value,
            "market_analysis_id": self.market_analysis_id,
            "snapshot_id":        self.snapshot_id,
            "elapsed_s":          round(self.elapsed_s, 4),
            "error_message":      self.error_message,
            "is_successful":      self.is_successful,
            "responded_at":       self.responded_at,
            "framework_version":  self.framework_version,
        }
