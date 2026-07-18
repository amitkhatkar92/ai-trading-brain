"""
iios/execution/analytics/engine/analytics_validation.py
=======================================================
EngineAnalyticsValidationResult and EngineAnalyticsValidator — validation
for requests, contexts, and pipelines in the Execution Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .analytics_context import EngineAnalyticsContext
    from .analytics_pipeline import AnalyticsPipeline
    from .analytics_request import AnalyticsRequest


@dataclass
class EngineAnalyticsValidationResult:
    """Mutable accumulator of engine-level validation findings."""

    is_valid: bool      = True
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "EngineAnalyticsValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class EngineAnalyticsValidator:
    """
    Validates analytics requests, contexts, and pipeline consistency
    for the Execution Analytics Engine.
    """

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(
        self, request: Optional["AnalyticsRequest"]
    ) -> EngineAnalyticsValidationResult:
        r = EngineAnalyticsValidationResult()
        if request is None:
            r.add_error("request must not be None")
            return r
        if not getattr(request, "request_id", ""):
            r.add_error("request_id is required")
        if not getattr(request, "execution_session_id", ""):
            r.add_error("execution_session_id is required")
        if not getattr(request, "request_type", None):
            r.add_error("request_type is required")
        priority = getattr(request, "priority", 5)
        if not isinstance(priority, int) or not (1 <= priority <= 10):
            r.add_warning("priority should be an integer between 1 and 10")
        return r

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(
        self, context: Optional["EngineAnalyticsContext"]
    ) -> EngineAnalyticsValidationResult:
        r = EngineAnalyticsValidationResult()
        if context is None:
            r.add_error("context must not be None")
            return r
        if not getattr(context, "request_id", ""):
            r.add_error("context.request_id is required")
        if not getattr(context, "execution_session_id", ""):
            r.add_error("context.execution_session_id is required")
        available = getattr(context, "available_snapshot_count", 0)
        if available == 0:
            r.add_warning(
                "No input snapshots are available; analytics will run "
                "without subsystem data."
            )
        return r

    # ── Pipeline validation ───────────────────────────────────────────────────

    def validate_pipeline(
        self, pipeline: Optional["AnalyticsPipeline"]
    ) -> EngineAnalyticsValidationResult:
        r = EngineAnalyticsValidationResult()
        if pipeline is None:
            r.add_error("pipeline must not be None")
            return r
        if not getattr(pipeline, "pipeline_id", ""):
            r.add_error("pipeline_id is required")
        if not getattr(pipeline, "request_id", ""):
            r.add_error("pipeline.request_id is required")
        if not getattr(pipeline, "session_id", ""):
            r.add_error("pipeline.session_id is required")
        if (
            not getattr(pipeline, "has_performance", False)
            and not getattr(pipeline, "has_predictive", False)
        ):
            r.add_warning(
                "Pipeline has neither performance nor predictive delegation "
                "enabled; no framework will be invoked."
            )
        return r

    # ── Lifecycle consistency ─────────────────────────────────────────────────

    def validate_lifecycle_consistency(
        self,
        request: Optional["AnalyticsRequest"],
        context: Optional["EngineAnalyticsContext"],
    ) -> EngineAnalyticsValidationResult:
        r = EngineAnalyticsValidationResult()
        if request is None or context is None:
            r.add_error("Both request and context must be provided for consistency check.")
            return r
        req_id = getattr(request, "request_id", "")
        ctx_req_id = getattr(context, "request_id", "")
        if req_id and ctx_req_id and req_id != ctx_req_id:
            r.add_error(
                f"request.request_id={req_id!r} does not match "
                f"context.request_id={ctx_req_id!r}"
            )
        req_sid = getattr(request, "execution_session_id", "")
        ctx_sid = getattr(context, "execution_session_id", "")
        if req_sid and ctx_sid and req_sid != ctx_sid:
            r.add_error(
                f"request.execution_session_id={req_sid!r} does not match "
                f"context.execution_session_id={ctx_sid!r}"
            )
        return r
