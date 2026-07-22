"""
portfolio_policy_manager.py — iios.portfolio.policies
======================================================
Internal workflow coordinator for the Portfolio Policy Framework.

PortfolioPolicyManager orchestrates a full evaluation run:
  1. Validate the request.
  2. Load applicable policies from the registry.
  3. Emit lifecycle events.
  4. Evaluate policies via the evaluator.
  5. Build the audit report.
  6. Record to statistics and history.
  7. Return a PortfolioPolicyResponse.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_MANAGER,
    POLICY_SYSTEM_ID,
    VERSION,
    PolicyAction,
    PolicyEventType,
    PolicyType,
)
from .portfolio_policy import PortfolioPolicy
from .portfolio_policy_audit import PolicyAuditEntry, PortfolioPolicyAuditReport
from .portfolio_policy_evaluator import PortfolioPolicyEvaluator
from .portfolio_policy_events import (
    PolicyEngineEvent,
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_evaluation_completed,
    make_policy_evaluation_started,
    make_policy_loaded,
    make_policy_rejected,
    make_policy_validated,
)
from .portfolio_policy_history import PortfolioPolicyHistory
from .portfolio_policy_registry import PortfolioPolicyRegistry
from .portfolio_policy_request import PortfolioPolicyRequest
from .portfolio_policy_response import PortfolioPolicyResponse
from .portfolio_policy_result import PortfolioPolicyResult
from .portfolio_policy_statistics import PortfolioPolicyStatistics
from .portfolio_policy_validator import PortfolioPolicyValidator

_log = get_logger(__name__)


class PortfolioPolicyManager:
    """
    Internal workflow coordinator for portfolio policy evaluation.

    Parameters
    ----------
    registry :      Policy registry to load policies from.
    evaluator :     Core evaluator.
    validator :     Request and policy validator.
    statistics :    Statistics recorder.
    history :       History store.
    dispatch_event: Callable that delivers events to external listeners.
    """

    def __init__(
        self,
        registry:       PortfolioPolicyRegistry,
        evaluator:      PortfolioPolicyEvaluator,
        validator:      PortfolioPolicyValidator,
        statistics:     PortfolioPolicyStatistics,
        history:        PortfolioPolicyHistory,
        dispatch_event: Callable[[PolicyEngineEvent], None],
    ) -> None:
        self._registry  = registry
        self._evaluator = evaluator
        self._validator = validator
        self._stats     = statistics
        self._history   = history
        self._dispatch  = dispatch_event

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def evaluate_portfolio(
        self, request: PortfolioPolicyRequest
    ) -> PortfolioPolicyResponse:
        """
        Run a full policy evaluation for the given request.

        Always returns a PortfolioPolicyResponse — failures are captured
        in the response rather than raised as exceptions.
        """
        t0            = time.monotonic()
        evaluation_id = str(uuid.uuid4())

        # ── Record request ────────────────────────────────────────────
        self._history.record_request(request)

        # ── Validate request ──────────────────────────────────────────
        validation = self._validator.validate_request(request)
        if not validation.is_valid:
            elapsed  = time.monotonic() - t0
            err_msg  = "; ".join(validation.error_messages)
            response = PortfolioPolicyResponse.create_failure(
                request.request_id,
                request.portfolio_id,
                err_msg,
                elapsed_s = elapsed,
            )
            self._stats.record_evaluation_error()
            self._history.record_response(response)
            _log.warning(f"Policy request validation failed: {err_msg}")
            return response

        # ── Create audit report ───────────────────────────────────────
        audit = PortfolioPolicyAuditReport(
            evaluation_id = evaluation_id,
            portfolio_id  = request.portfolio_id,
            actor         = ACTOR_MANAGER,
        )

        # ── Load applicable policies ──────────────────────────────────
        all_policies = self._registry.all_active()
        if request.policy_types:
            requested = set(request.policy_types)
            policies  = [p for p in all_policies if p.policy_type in requested]
        else:
            policies = all_policies

        # ── Emit EVALUATION_STARTED ───────────────────────────────────
        ev_started = make_policy_evaluation_started(
            evaluation_id, request.portfolio_id, policy_count=len(policies)
        )
        self._history.record_event(ev_started)
        self._dispatch(ev_started)

        # ── Emit LOADED + VALIDATED per policy ────────────────────────
        for policy in policies:
            ev_loaded = make_policy_loaded(
                evaluation_id, request.portfolio_id,
                policy.policy_id, policy.name,
            )
            self._history.record_event(ev_loaded)
            self._dispatch(ev_loaded)

            ev_validated = make_policy_validated(
                evaluation_id, request.portfolio_id, policy.policy_id, passed=True
            )
            self._history.record_event(ev_validated)
            self._dispatch(ev_validated)

        # ── Evaluate ──────────────────────────────────────────────────
        try:
            result = self._evaluator.evaluate(request, policies)
        except Exception as exc:
            elapsed  = time.monotonic() - t0
            err_msg  = f"evaluator raised exception: {exc}"
            response = PortfolioPolicyResponse.create_failure(
                request.request_id,
                request.portfolio_id,
                err_msg,
                elapsed_s = elapsed,
            )
            self._stats.record_evaluation_error()
            self._history.record_response(response)
            _log.warning(f"Policy evaluator error: {exc}")
            return response

        # ── Build audit entries ───────────────────────────────────────
        inputs_summary: Dict[str, str] = {k: type(v).__name__ for k, v in request.inputs.items()}
        for outcome in result.outcomes:
            entry = PolicyAuditEntry(
                entry_id          = str(uuid.uuid4()),
                evaluation_id     = evaluation_id,
                portfolio_id      = request.portfolio_id,
                policy_id         = outcome.policy_id,
                policy_name       = outcome.policy_name,
                policy_type       = outcome.policy_type,
                action            = outcome.action,
                reason            = outcome.reason,
                inputs_summary    = inputs_summary,
                conditions_passed = outcome.conditions_passed,
                conditions_failed = outcome.conditions_failed,
                actor             = ACTOR_MANAGER,
                recorded_at       = time.time(),
            )
            audit.add_entry(entry)

        # ── Finalize audit ────────────────────────────────────────────
        audit.finalize(result.final_action)
        self._history.record_audit(audit)

        # ── Emit outcome event ────────────────────────────────────────
        final_action = result.final_action
        if final_action == PolicyAction.APPROVE or \
                final_action == PolicyAction.APPROVE_WITH_CONDITIONS:
            ev_outcome = make_policy_approved(evaluation_id, request.portfolio_id)
        elif final_action == PolicyAction.BLOCK:
            ev_outcome = make_policy_blocked(
                evaluation_id, request.portfolio_id, reason=str(final_action.value)
            )
        elif final_action == PolicyAction.REJECT:
            ev_outcome = make_policy_rejected(
                evaluation_id, request.portfolio_id, reason=str(final_action.value)
            )
        elif final_action == PolicyAction.ESCALATE:
            ev_outcome = make_policy_escalated(
                evaluation_id, request.portfolio_id, reason=str(final_action.value)
            )
        else:
            ev_outcome = make_policy_approved(evaluation_id, request.portfolio_id)

        self._history.record_event(ev_outcome)
        self._dispatch(ev_outcome)

        # ── Emit EVALUATION_COMPLETED ─────────────────────────────────
        elapsed = time.monotonic() - t0
        ev_done = make_policy_evaluation_completed(
            evaluation_id, request.portfolio_id, final_action,
            elapsed_s      = elapsed,
            total_policies = len(policies),
        )
        self._history.record_event(ev_done)
        self._dispatch(ev_done)

        # ── Record statistics ─────────────────────────────────────────
        policy_types_used = [o.policy_type for o in result.outcomes]
        self._stats.record_evaluation_completed(
            final_action, elapsed, policy_types=policy_types_used
        )
        self._stats.record_policy_evaluated(len(result.outcomes))

        # ── Build and return response ─────────────────────────────────
        response = PortfolioPolicyResponse.create_success(
            request.request_id,
            request.portfolio_id,
            result,
            audit_id  = audit.audit_id,
            elapsed_s = elapsed,
        )
        self._history.record_response(response)

        _log.debug(
            f"Policy evaluation completed: portfolio={request.portfolio_id} "
            f"action={final_action.value} policies={len(policies)} "
            f"elapsed={elapsed:.3f}s"
        )
        return response
