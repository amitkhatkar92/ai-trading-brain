"""
portfolio_policy_response.py — iios.portfolio.policies
=======================================================
Top-level response object returned by the Portfolio Policy Engine.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    APPROVAL_ACTIONS,
    VERSION,
    PolicyAction,
)
from .portfolio_policy_result import PortfolioPolicyResult


@dataclass(frozen=True)
class PortfolioPolicyResponse:
    """
    Immutable top-level response returned by PortfolioPolicyEngine.submit().

    Always returned — evaluation failures are captured in error_message
    rather than raised as exceptions (for predictable control flow).

    Fields
    ------
    response_id :      Unique identifier for this response.
    request_id :       Identifier of the originating request.
    portfolio_id :     Portfolio that was evaluated.
    final_action :     Resolved final governance outcome.
    result :           Full evaluation result (None on engine errors).
    audit_id :         Identifier of the associated audit report.
    is_error :         True when the engine encountered an unrecoverable error.
    error_message :    Non-empty when is_error is True.
    elapsed_s :        Total wall-clock seconds from request to response.
    metadata :         Supplementary free-form data.
    created_at :       Wall-clock creation timestamp.
    framework_version: Framework version string.
    """
    response_id:       str
    request_id:        str
    portfolio_id:      str
    final_action:      PolicyAction
    result:            Optional[PortfolioPolicyResult]
    audit_id:          str
    is_error:          bool
    error_message:     str
    elapsed_s:         float
    metadata:          Dict[str, Any]
    created_at:        float
    framework_version: str

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.final_action in APPROVAL_ACTIONS and not self.is_error

    @property
    def is_blocked(self) -> bool:
        return self.final_action == PolicyAction.BLOCK

    @property
    def is_rejected(self) -> bool:
        return self.final_action == PolicyAction.REJECT

    @property
    def requires_escalation(self) -> bool:
        return self.final_action == PolicyAction.ESCALATE

    @property
    def requires_manual_review(self) -> bool:
        return self.final_action == PolicyAction.REQUIRE_MANUAL_REVIEW

    @property
    def is_failure(self) -> bool:
        return self.is_error

    @property
    def has_result(self) -> bool:
        return self.result is not None

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def create_success(
        cls,
        request_id:   str,
        portfolio_id: str,
        result:       PortfolioPolicyResult,
        *,
        audit_id:  str = "",
        elapsed_s: float = 0.0,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> "PortfolioPolicyResponse":
        """Create a successful response wrapping a full evaluation result."""
        return cls(
            response_id       = str(uuid.uuid4()),
            request_id        = request_id,
            portfolio_id      = portfolio_id,
            final_action      = result.final_action,
            result            = result,
            audit_id          = audit_id,
            is_error          = False,
            error_message     = "",
            elapsed_s         = elapsed_s,
            metadata          = dict(metadata or {}),
            created_at        = time.time(),
            framework_version = VERSION,
        )

    @classmethod
    def create_failure(
        cls,
        request_id:    str,
        portfolio_id:  str,
        error_message: str,
        *,
        elapsed_s: float = 0.0,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> "PortfolioPolicyResponse":
        """Create a failure response for engine-level errors."""
        return cls(
            response_id       = str(uuid.uuid4()),
            request_id        = request_id,
            portfolio_id      = portfolio_id,
            final_action      = PolicyAction.BLOCK,
            result            = None,
            audit_id          = "",
            is_error          = True,
            error_message     = error_message,
            elapsed_s         = elapsed_s,
            metadata          = dict(metadata or {}),
            created_at        = time.time(),
            framework_version = VERSION,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":      self.response_id,
            "request_id":       self.request_id,
            "portfolio_id":     self.portfolio_id,
            "final_action":     self.final_action.value,
            "has_result":       self.has_result,
            "audit_id":         self.audit_id,
            "is_error":         self.is_error,
            "error_message":    self.error_message,
            "elapsed_s":        self.elapsed_s,
            "metadata":         dict(self.metadata),
            "created_at":       self.created_at,
            "framework_version": self.framework_version,
        }
