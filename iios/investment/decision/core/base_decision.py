"""iios/investment/decision/core/base_decision.py
BaseDecision — abstract base class implementing the 12-step decision lifecycle.

Every decision in the framework MUST subclass BaseDecision.
Subclasses implement analysis-domain-specific behaviour by overriding
the 12 abstract async methods.  This base class:
  - Enforces the state machine
  - Dispatches lifecycle events
  - Handles errors and cleanup
  - Provides structured logging
  - Manages metadata and configuration
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.core.decision_constants import (
    ApprovalStatus,
    DecisionEventType,
    DecisionStatus,
    RecommendationType,
    RiskReviewStatus,
)
from iios.investment.decision.core.decision_configuration import DecisionConfiguration
from iios.investment.decision.core.decision_context import DecisionContext
from iios.investment.decision.core.decision_events import DecisionEvent, EventDispatcher, make_event
from iios.investment.decision.core.decision_lifecycle import DecisionLifecycle
from iios.investment.decision.core.decision_metadata import DecisionMetadata
from iios.investment.decision.core.decision_state import DecisionState, InvalidTransitionError

_log = logging.getLogger(__name__)


class BaseDecision(ABC):
    """
    Abstract base for all institutional investment decisions.

    Lifecycle (in order):
      1.  initialize()             — set up resources
      2.  collect_evidence()       — gather raw intelligence inputs
      3.  validate_inputs()        — verify completeness and integrity
      4.  prepare()                — pre-process / normalise
      5.  evaluate()               — apply logic (subclass defines what logic)
      6.  score()          → float — compute a 0–100 quality/confidence score
      7.  risk_review()    → RiskReviewStatus
      8.  generate_recommendation() → RecommendationType
      9.  generate_explanation()  → str
      10. approve()        → ApprovalStatus
      11. publish()                — emit final decision to downstream consumers
      12. archive()                — persist and release resources
    """

    def __init__(
        self,
        context:    DecisionContext,
        config:     Optional[DecisionConfiguration] = None,
        dispatcher: Optional[EventDispatcher]       = None,
    ) -> None:
        self._context    = context
        self._config     = config or DecisionConfiguration()
        self._dispatcher = dispatcher or EventDispatcher()
        self._state      = DecisionState(context.decision_id)
        self._metadata   = DecisionMetadata(context.decision_id, context.source)
        self._lifecycle  = DecisionLifecycle(context.decision_id)
        self._started_at: datetime = datetime.now(timezone.utc)

    # ================================================================
    # Abstract lifecycle methods — MUST be implemented by subclasses
    # ================================================================

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def collect_evidence(self) -> None: ...

    @abstractmethod
    async def validate_inputs(self) -> None: ...

    @abstractmethod
    async def prepare(self) -> None: ...

    @abstractmethod
    async def evaluate(self) -> None: ...

    @abstractmethod
    async def score(self) -> float:
        """Return a decision quality/confidence score 0–100."""

    @abstractmethod
    async def risk_review(self) -> RiskReviewStatus: ...

    @abstractmethod
    async def generate_recommendation(self) -> RecommendationType: ...

    @abstractmethod
    async def generate_explanation(self) -> str: ...

    @abstractmethod
    async def approve(self) -> ApprovalStatus: ...

    @abstractmethod
    async def publish(self) -> None: ...

    @abstractmethod
    async def archive(self) -> None: ...

    # ================================================================
    # Orchestrator
    # ================================================================

    async def run(self) -> DecisionState:
        """
        Execute the full 12-step lifecycle.
        Returns the final DecisionState.
        Raises on unrecoverable errors after transitioning state to FAILED.
        """
        _log.info("Decision %s starting — type=%s subject=%s",
                  self._context.decision_id,
                  self._context.decision_type.value,
                  self._context.subject_id)
        try:
            # Step 1: Initialize
            await self.initialize()
            self._emit(DecisionEventType.CREATED)

            # Step 2: Collect Evidence → COLLECTING_EVIDENCE
            self._transition(DecisionStatus.COLLECTING_EVIDENCE)
            await self.collect_evidence()
            self._emit(DecisionEventType.EVIDENCE_READY)

            # Steps 3-5: Validate / Prepare / Evaluate → UNDER_REVIEW
            self._transition(DecisionStatus.UNDER_REVIEW)
            await self.validate_inputs()
            self._emit(DecisionEventType.VALIDATED)
            await self.prepare()
            self._emit(DecisionEventType.PREPARED)
            await self.evaluate()
            self._emit(DecisionEventType.EVALUATED)

            # Step 6: Score → SCORED
            raw_score = await self.score()
            self._state.update_score(raw_score, raw_score)
            self._transition(DecisionStatus.SCORED)
            self._emit(DecisionEventType.SCORED, {"score": self._state.score})

            # Step 7: Risk Review → RISK_REVIEWED
            risk_status = await self.risk_review()
            self._state.update_risk_review(risk_status)
            self._transition(DecisionStatus.RISK_REVIEWED)
            self._emit(DecisionEventType.RISK_REVIEWED, {"risk_status": risk_status.value})

            # Steps 8-9: Recommendation + Explanation
            recommendation = await self.generate_recommendation()
            explanation    = await self.generate_explanation()
            self._state.update_recommendation(recommendation, explanation)

            # Step 10: Approve → APPROVED | REJECTED
            approval = await self.approve()
            self._state.update_approval(approval)
            self._metadata.record("framework", "approval_decision", approval.value)

            if approval.is_positive:
                self._transition(DecisionStatus.APPROVED)
                self._emit(DecisionEventType.APPROVED, {
                    "recommendation": recommendation.value,
                    "score":          self._state.score,
                })

                # Step 11: Publish → PUBLISHED
                await self.publish()
                self._transition(DecisionStatus.PUBLISHED)
                self._emit(DecisionEventType.PUBLISHED)
            else:
                self._transition(DecisionStatus.REJECTED)
                self._emit(DecisionEventType.REJECTED, {"reason": explanation})

            # Step 12: Archive → ARCHIVED
            await self.archive()
            self._transition(DecisionStatus.ARCHIVED)
            self._emit(DecisionEventType.ARCHIVED)

        except InvalidTransitionError:
            raise
        except Exception as exc:
            self._state.fail(str(exc))
            self._emit(
                DecisionEventType.VALIDATED,
                {"error": str(exc), "phase": self._state.status.value},
            )
            _log.exception("Decision %s failed: %s", self._context.decision_id, exc)
            raise

        return self._state

    def run_sync(self) -> DecisionState:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run())

    # ================================================================
    # Internal helpers
    # ================================================================

    def _transition(self, new_status: DecisionStatus) -> None:
        from_status = self._state.status
        self._lifecycle.record_transition(from_status, new_status)
        self._state.transition_to(new_status)
        self._emit(DecisionEventType.STATE_CHANGED, {
            "from": from_status.value,
            "to":   new_status.value,
        })

    def _emit(
        self,
        event_type: DecisionEventType,
        payload:    Optional[Dict[str, Any]] = None,
    ) -> None:
        self._dispatcher.dispatch(make_event(
            event_type=event_type,
            decision_id=self._context.decision_id,
            payload=payload,
            source=self._context.source,
        ))

    # ================================================================
    # Public accessors
    # ================================================================

    @property
    def decision_id(self) -> str:
        return self._context.decision_id

    @property
    def context(self) -> DecisionContext:
        return self._context

    @property
    def config(self) -> DecisionConfiguration:
        return self._config

    @property
    def state(self) -> DecisionState:
        return self._state

    @property
    def metadata(self) -> DecisionMetadata:
        return self._metadata

    @property
    def lifecycle(self) -> DecisionLifecycle:
        return self._lifecycle

    @property
    def dispatcher(self) -> EventDispatcher:
        return self._dispatcher
