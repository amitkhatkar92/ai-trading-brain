"""iios/investment/workflow/institutional_investment_workflow.py
InstitutionalInvestmentWorkflow — the canonical end-to-end intelligence pipeline.

Chains:
  Market Intelligence
    ↓
  Company Intelligence
    ↓
  Strategy Intelligence
    ↓
  Decision Intelligence
    ↓
  Portfolio Intelligence
    → publishes one PortfolioIntelligenceSnapshot

This class ONLY orchestrates via public integration-engine interfaces.
It NEVER analyses markets, analyses companies, evaluates strategies,
makes investment decisions, or constructs portfolios.

Usage::

    from iios.investment.workflow.institutional_investment_workflow import (
        InstitutionalWorkflowOrchestrator,
    )
    orchestrator = InstitutionalWorkflowOrchestrator()
    result = orchestrator.run(request, portfolio_id="P-001")
    snapshot = result.portfolio_snapshot
"""
from __future__ import annotations

import logging
import time
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.investment_constants import IntelligenceType
from iios.investment.models.investment_analysis import InvestmentAnalysis
from iios.investment.models.investment_context_model import InvestmentContext
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.workflow.investment_workflow import InvestmentWorkflow
from iios.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters
from iios.investment.workflow.workflow_events import WorkflowEvent, WorkflowEventPublisher
from iios.investment.workflow.workflow_history import WorkflowHistory, WorkflowRunRecord
from iios.investment.workflow.workflow_state import WorkflowState
from iios.investment.workflow.workflow_statistics import (
    WorkflowRunMetric,
    WorkflowStatistics,
    WorkflowStatisticsSnapshot,
)
from iios.investment.workflow.workflow_types import (
    PIPELINE_STAGES,
    WORKFLOW_VERSION,
    WorkflowStage,
)
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

_log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_quality(snap: Any, *attrs: str) -> Optional[float]:
    """Extract a quality/score float from a snapshot; return None if absent."""
    for attr in attrs:
        val = getattr(snap, attr, None)
        if val is not None:
            try:
                f = float(val)
                if 0.0 <= f <= 1.0:
                    return f
                if 0.0 <= f <= 100.0:
                    return f / 100.0
            except (TypeError, ValueError):
                pass
    return None


def _snap_id(snap: Any) -> Optional[str]:
    """Extract the canonical identifier from a snapshot object."""
    for attr in ("snapshot_id", "run_id", "decision_id"):
        val = getattr(snap, attr, None)
        if isinstance(val, str) and val:
            return val
    return None


# ── WorkflowResult ─────────────────────────────────────────────────────────────

class WorkflowResult:
    """
    Final result of one pipeline run.

    Attributes:
        succeeded:            True when PortfolioIntelligenceSnapshot was published.
        portfolio_snapshot:   The final canonical output (or None on failure).
        workflow_id:          Execution identifier.
        request_id:           Originating request identifier.
        portfolio_id:         Target portfolio identifier.
        stage_snapshots:      Dict mapping WorkflowStage → upstream snapshot.
        state:                The WorkflowState at termination.
        run_record:           Immutable audit record.
    """

    def __init__(
        self,
        *,
        succeeded:          bool,
        portfolio_snapshot: Any,
        workflow_id:        str,
        request_id:         str,
        portfolio_id:       str,
        stage_snapshots:    Dict[WorkflowStage, Any],
        state:              WorkflowState,
        run_record:         WorkflowRunRecord,
    ) -> None:
        self.succeeded          = succeeded
        self.portfolio_snapshot = portfolio_snapshot
        self.workflow_id        = workflow_id
        self.request_id         = request_id
        self.portfolio_id       = portfolio_id
        self.stage_snapshots    = stage_snapshots
        self.state              = state
        self.run_record         = run_record

    def to_dict(self) -> dict:
        return {
            "succeeded":    self.succeeded,
            "workflow_id":  self.workflow_id,
            "request_id":   self.request_id,
            "portfolio_id": self.portfolio_id,
            "run_id":       self.run_record.run_id,
            "terminal_stage": self.run_record.terminal_stage.value,
            "total_duration_ms": self.run_record.total_duration_ms,
            "n_stages_completed": self.run_record.n_stages_completed,
            "n_retries":    self.run_record.n_retries,
            "errors":       list(self.run_record.errors),
            "warnings":     list(self.run_record.warnings),
        }


# ── Stage validation helpers ────────────────────────────────────────────────────

class _StageValidator:
    """
    Validates pre-conditions before entering each pipeline stage.
    Returns (is_valid, reason_or_empty_string).
    """

    def check_previous_completed(
        self, required: WorkflowStage, state: WorkflowState
    ) -> tuple[bool, str]:
        done = state.completed_stages
        if required not in done:
            return False, f"Required stage '{required.value}' not completed"
        return True, ""

    def check_snapshot_present(
        self, stage: WorkflowStage, state: WorkflowState
    ) -> tuple[bool, str]:
        snap = state.get_snapshot(stage)
        if snap is None:
            return False, f"No snapshot from stage '{stage.value}'"
        return True, ""

    def check_snapshot_not_failed(
        self, snap: Any, stage_label: str
    ) -> tuple[bool, str]:
        failed_attrs = ("is_failed", "has_blocking_error")
        for attr in failed_attrs:
            if getattr(snap, attr, False):
                return False, f"{stage_label} snapshot has blocking failure"
        return True, ""

    def validate_stage_entry(
        self,
        target_stage:    WorkflowStage,
        required_stages: List[WorkflowStage],
        state:           WorkflowState,
    ) -> tuple[bool, str]:
        if state.is_cancelled:
            return False, "Workflow has been cancelled"
        for req in required_stages:
            ok, reason = self.check_previous_completed(req, state)
            if not ok:
                return False, reason
            snap = state.get_snapshot(req)
            if snap is not None:
                ok2, reason2 = self.check_snapshot_not_failed(snap, req.value)
                if not ok2:
                    return False, reason2
        return True, ""


# ── Main workflow ───────────────────────────────────────────────────────────────

class InstitutionalInvestmentWorkflow(InvestmentWorkflow):
    """
    Concrete implementation of the end-to-end IIOS intelligence pipeline.

    Extends ``InvestmentWorkflow`` so it can be registered with
    ``InvestmentRegistry`` and executed via ``WorkflowExecutor``.
    For full orchestration features (retries, events, history) use
    ``InstitutionalWorkflowOrchestrator`` directly.
    """

    WORKFLOW_ID = "institutional_investment_pipeline"
    VERSION     = WORKFLOW_VERSION

    @property
    def workflow_id(self) -> str:
        return self.WORKFLOW_ID

    @property
    def name(self) -> str:
        return "Institutional Investment Workflow"

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.PORTFOLIO

    @property
    def priority(self) -> int:
        return 0

    def execute(
        self,
        request: InvestmentRequest,
        context: InvestmentContext,
    ) -> InvestmentAnalysis:
        """
        Execute the full pipeline via InstitutionalWorkflowOrchestrator.

        Returns an InvestmentAnalysis whose ``findings`` dict contains:
          - "portfolio_snapshot": the final PortfolioIntelligenceSnapshot
          - "workflow_result": a summary dict
        """
        portfolio_id = (
            request.metadata.get("portfolio_id")
            or context.metadata.get("portfolio_id")  # type: ignore[union-attr]
            or f"P-{request.request_id[:8]}"
        )

        orchestrator = InstitutionalWorkflowOrchestrator()
        result = orchestrator.run(request, portfolio_id=portfolio_id)

        analysis = InvestmentAnalysis(
            request_id        = request.request_id,
            workflow_id       = self.workflow_id,
            intelligence_type = self.intelligence_type,
            asset_class       = request.asset_class,
            symbols           = list(request.symbols),
            confidence        = 1.0 if result.succeeded else 0.0,
            findings          = {
                "portfolio_snapshot": result.portfolio_snapshot,
                "workflow_result":    result.to_dict(),
                "succeeded":          result.succeeded,
            },
        )
        if result.succeeded:
            analysis.mark_completed()
        else:
            analysis.mark_failed("; ".join(result.run_record.errors))
        return analysis


# ── Orchestrator ────────────────────────────────────────────────────────────────

class InstitutionalWorkflowOrchestrator(LifecycleAwareMixin):
    """
    Standalone orchestrator for the IIOS Intelligence Pipeline.

    Responsibilities:
    - Run the five-stage pipeline sequentially.
    - Validate stage pre-conditions and post-conditions.
    - Retry failed stages up to ``params.max_retries`` times.
    - Emit lifecycle events via WorkflowEventPublisher.
    - Maintain WorkflowHistory and WorkflowStatistics.
    - Provide APIs: run(), cancel(), status(), timeline(), current_snapshot(),
      history(), statistics().

    This class ONLY calls public integration-engine methods.
    It performs no domain intelligence computation itself.
    """

    VERSION   = WORKFLOW_VERSION
    SYSTEM_ID = "iios:workflow:institutional"

    def __init__(
        self,
        *,
        params:          Optional[WorkflowParameters]    = None,
        engines:         Optional[WorkflowEngines]       = None,
        event_publisher: Optional[WorkflowEventPublisher] = None,
        history:         Optional[WorkflowHistory]       = None,
        statistics:      Optional[WorkflowStatistics]    = None,
    ) -> None:
        self._params    = params    or WorkflowParameters()
        self._engines   = engines   or WorkflowEngines()
        self._publisher = event_publisher or WorkflowEventPublisher()
        self._history   = history   or WorkflowHistory()
        self._stats     = statistics or WorkflowStatistics()
        self._validator = _StageValidator()

        # Active state lock — only one pipeline execution per orchestrator at a time
        self._run_lock:      threading.Lock         = threading.Lock()
        self._active_state:  Optional[WorkflowState] = None
        self._active_result: Optional[WorkflowResult] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        request:      InvestmentRequest,
        *,
        portfolio_id: str,
        strategy_id:  str = "",
        decision_id:  str = "",
    ) -> WorkflowResult:
        """
        Execute the full C1→C2→C3→C4→C5 intelligence pipeline.

        Parameters:
            request:      The originating InvestmentRequest.
            portfolio_id: Target portfolio in the Portfolio Intelligence engine.
            strategy_id:  Strategy context for C3 (auto-generated if empty).
            decision_id:  Decision context for C4 (auto-generated if empty).

        Returns:
            WorkflowResult with ``succeeded=True`` and a valid
            ``PortfolioIntelligenceSnapshot`` on success.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id is required")

        # Resolve engine defaults lazily
        self._engines.ensure_defaults()

        sid = strategy_id or f"STRAT-{request.request_id[:8]}"
        did = decision_id or f"DEC-{request.request_id[:8]}"

        state = WorkflowState(
            workflow_id = InstitutionalInvestmentWorkflow.WORKFLOW_ID,
            request_id  = request.request_id,
        )

        with self._run_lock:
            self._active_state  = state
            self._active_result = None

        _log.info(
            "Workflow %s starting — request=%s portfolio=%s",
            state.workflow_id, request.request_id, portfolio_id,
        )
        self._publisher.emit_workflow_started(
            state.workflow_id, request.request_id, portfolio_id,
        )

        try:
            result = self._execute_pipeline(
                request, state, portfolio_id, sid, did,
            )
        except Exception as exc:
            _log.exception("Workflow pipeline raised unexpected exception: %s", exc)
            state.transition_terminal(WorkflowStage.FAILED)
            self._publisher.emit_workflow_failed(
                state.workflow_id, request.request_id,
                state.current_stage, str(exc),
            )
            result = self._build_result(
                state, request.request_id, portfolio_id, None,
            )

        with self._run_lock:
            self._active_result = result

        self._history.add(result.run_record)
        self._stats.record(self._to_metric(result))
        return result

    def cancel(self) -> bool:
        """
        Cancel the currently running pipeline.
        Returns True if a pipeline was active and has been flagged for cancellation.
        """
        with self._run_lock:
            state = self._active_state
        if state is not None and not state.is_terminal:
            state.cancel()
            self._publisher.emit_workflow_cancelled(
                state.workflow_id, state.request_id,
            )
            _log.info("Workflow %s cancelled", state.workflow_id)
            return True
        return False

    def status(self) -> Optional[dict]:
        """Return current pipeline state as a dict, or None if no run active."""
        with self._run_lock:
            state = self._active_state
        if state is None:
            return None
        return state.to_dict()

    def timeline(self) -> Optional[List[dict]]:
        """Return the list of stage records for the active run."""
        with self._run_lock:
            state = self._active_state
        if state is None:
            return None
        return [r.to_dict() for r in state.stage_records]

    def current_stage(self) -> Optional[WorkflowStage]:
        """Return the active pipeline stage, or None."""
        with self._run_lock:
            state = self._active_state
        return state.current_stage if state else None

    def current_snapshot(self) -> Optional[Any]:
        """Return the most recently published PortfolioIntelligenceSnapshot."""
        with self._run_lock:
            result = self._active_result
        if result is not None:
            return result.portfolio_snapshot
        return None

    def register_event_callback(
        self, callback: Callable[[WorkflowEvent], None]
    ) -> None:
        self._publisher.register(callback)

    def unregister_event_callback(
        self, callback: Callable[[WorkflowEvent], None]
    ) -> None:
        self._publisher.unregister(callback)

    def history(self, n: int = 20) -> List[WorkflowRunRecord]:
        return self._history.recent(n)

    def history_for_portfolio(
        self, portfolio_id: str, n: int = 20
    ) -> List[WorkflowRunRecord]:
        return self._history.for_portfolio(portfolio_id, n)

    def statistics(self) -> WorkflowStatisticsSnapshot:
        return self._stats.summary()

    # ── Pipeline execution ─────────────────────────────────────────────────────

    def _execute_pipeline(
        self,
        request:      InvestmentRequest,
        state:        WorkflowState,
        portfolio_id: str,
        strategy_id:  str,
        decision_id:  str,
    ) -> WorkflowResult:

        # ── Stage 1: Market Intelligence ───────────────────────────────────────
        market_snap = self._run_stage(
            stage        = WorkflowStage.MARKET,
            state        = state,
            required     = [],
            fn           = lambda: self._stage_market(request),
        )
        if market_snap is None:
            return self._build_result(state, request.request_id, portfolio_id, None)

        # ── Stage 2: Company Intelligence ──────────────────────────────────────
        if self._params.skip_company_stage:
            state.skip_stage(WorkflowStage.COMPANY)
            company_snap = None
        else:
            company_snap = self._run_stage(
                stage        = WorkflowStage.COMPANY,
                state        = state,
                required     = [WorkflowStage.MARKET],
                fn           = lambda: self._stage_company(request, market_snap),
            )
            if company_snap is None:
                return self._build_result(state, request.request_id, portfolio_id, None)

        # ── Stage 3: Strategy Intelligence ─────────────────────────────────────
        if self._params.skip_strategy_stage:
            state.skip_stage(WorkflowStage.STRATEGY)
            strategy_snap = None
        else:
            prev = [s for s in [WorkflowStage.MARKET] if not self._params.skip_company_stage]
            strategy_snap = self._run_stage(
                stage        = WorkflowStage.STRATEGY,
                state        = state,
                required     = prev,
                fn           = lambda: self._stage_strategy(
                    request, strategy_id, market_snap, company_snap,
                ),
            )
            if strategy_snap is None:
                return self._build_result(state, request.request_id, portfolio_id, None)

        # ── Stage 4: Decision Intelligence ─────────────────────────────────────
        if self._params.skip_decision_stage:
            state.skip_stage(WorkflowStage.DECISION)
            decision_snap = None
        else:
            decision_snap = self._run_stage(
                stage        = WorkflowStage.DECISION,
                state        = state,
                required     = [WorkflowStage.MARKET],
                fn           = lambda: self._stage_decision(
                    request, decision_id, market_snap, company_snap, strategy_snap,
                ),
            )
            if decision_snap is None:
                return self._build_result(state, request.request_id, portfolio_id, None)

        # ── Stage 5: Portfolio Intelligence ────────────────────────────────────
        portfolio_snap = self._run_stage(
            stage        = WorkflowStage.PORTFOLIO,
            state        = state,
            required     = [WorkflowStage.MARKET],
            fn           = lambda: self._stage_portfolio(
                request, portfolio_id,
                market_snap, company_snap, strategy_snap, decision_snap,
            ),
        )
        if portfolio_snap is None:
            return self._build_result(state, request.request_id, portfolio_id, None)

        # ── Publish ────────────────────────────────────────────────────────────
        state.transition_terminal(WorkflowStage.PUBLISHED)
        snap_id = _snap_id(portfolio_snap)
        _log.info(
            "Workflow %s: portfolio snapshot published snapshot_id=%s",
            state.workflow_id, snap_id,
        )
        self._publisher.emit_snapshot_published(
            state.workflow_id, request.request_id, portfolio_id, snap_id,
        )
        self._publisher.emit_workflow_completed(
            state.workflow_id, request.request_id, portfolio_id,
            state.total_duration_ms(), snap_id,
        )
        return self._build_result(
            state, request.request_id, portfolio_id, portfolio_snap,
        )

    # ── Stage runner with retry ────────────────────────────────────────────────

    def _run_stage(
        self,
        *,
        stage:    WorkflowStage,
        state:    WorkflowState,
        required: List[WorkflowStage],
        fn:       Callable[[], Any],
    ) -> Optional[Any]:
        """
        Run a single pipeline stage with retry logic.

        Returns the produced snapshot on success, or None on final failure.
        """
        # Pre-condition validation
        ok, reason = self._validator.validate_stage_entry(stage, required, state)
        if not ok:
            state.fail_stage(stage, f"Pre-condition failed: {reason}")
            state.transition_terminal(WorkflowStage.FAILED)
            self._publisher.emit_stage_failed(
                state.workflow_id, state.request_id, stage, reason,
            )
            return None

        max_attempts = 1 + self._params.max_retries
        last_error   = ""

        for attempt in range(1, max_attempts + 1):
            if state.is_cancelled:
                return None

            state.begin_stage(stage)
            self._publisher.emit_stage_started(
                state.workflow_id, state.request_id, stage, attempt,
            )
            _log.info(
                "Workflow %s: stage=%s attempt=%d/%d",
                state.workflow_id, stage.value, attempt, max_attempts,
            )

            try:
                snap = fn()
                if snap is None:
                    raise ValueError(f"Stage {stage.value} returned None snapshot")

                rec = state.complete_stage(
                    stage,
                    snapshot    = snap,
                    snapshot_id = _snap_id(snap),
                )
                self._publisher.emit_stage_completed(
                    state.workflow_id, state.request_id, stage,
                    rec.duration_ms, rec.snapshot_id,
                )
                _log.info(
                    "Workflow %s: stage=%s completed in %.1fms",
                    state.workflow_id, stage.value, rec.duration_ms,
                )
                return snap

            except Exception as exc:
                last_error = str(exc)
                is_final   = attempt >= max_attempts
                state.fail_stage(stage, last_error, is_retry=not is_final)

                if not is_final:
                    _log.warning(
                        "Workflow %s: stage=%s attempt=%d FAILED (%s), retrying in %.1fs",
                        state.workflow_id, stage.value, attempt, last_error,
                        self._params.retry_delay_sec,
                    )
                    self._publisher.emit_stage_retrying(
                        state.workflow_id, state.request_id, stage,
                        attempt, last_error,
                    )
                    if self._params.retry_delay_sec > 0:
                        time.sleep(self._params.retry_delay_sec)
                else:
                    _log.error(
                        "Workflow %s: stage=%s all %d attempts exhausted: %s",
                        state.workflow_id, stage.value, max_attempts, last_error,
                    )
                    state.transition_terminal(WorkflowStage.FAILED)
                    self._publisher.emit_stage_failed(
                        state.workflow_id, state.request_id, stage, last_error,
                    )
                    self._publisher.emit_workflow_failed(
                        state.workflow_id, state.request_id, stage, last_error,
                    )
                    return None

        return None  # unreachable but satisfies type checker

    # ── Stage adapters ─────────────────────────────────────────────────────────
    # Each adapter translates the InvestmentRequest into the domain-specific
    # input required by the corresponding Integration Engine.
    # NO domain calculations are performed here.

    def _stage_market(self, request: InvestmentRequest) -> Any:
        """
        Stage 1 — Market Intelligence.

        Packages the request's market data metadata into an IntelligenceBundle
        and calls MarketIntelligenceIntegrationEngine.update().
        """
        from iios.investment.market.integration.market_intelligence_integration_engine import (
            MarketIntelligenceIntegrationEngine,
        )

        engine: MarketIntelligenceIntegrationEngine = self._engines.market_engine
        bundle = engine.make_bundle(
            bar_index = request.metadata.get("bar_index", 0),
            timestamp = request.created_at,
            payloads  = request.metadata.get("market_payloads", {}),
        )
        return engine.update(bundle)

    def _stage_company(
        self,
        request:     InvestmentRequest,
        market_snap: Any,
    ) -> Any:
        """
        Stage 2 — Company Intelligence.

        For each symbol in the request, calls
        CompanyIntelligenceIntegrationEngine.update() with available
        sub-engine snapshots from the request metadata.
        Returns the snapshot for the primary symbol (first in list).
        """
        from iios.investment.company.integration.company_intelligence_integration_engine import (
            CompanyIntelligenceIntegrationEngine,
        )

        engine: CompanyIntelligenceIntegrationEngine = self._engines.company_engine
        primary_ticker = (request.symbols[0] if request.symbols
                          else request.metadata.get("ticker", "UNKNOWN"))
        company_payloads: dict = request.metadata.get("company_payloads", {})

        snap = engine.integrate(
            primary_ticker,
            financial_snapshot  = company_payloads.get("financial"),
            earnings_snapshot   = company_payloads.get("earnings"),
            business_quality    = company_payloads.get("business_quality"),
            valuation_snapshot  = company_payloads.get("valuation"),
            growth_snapshot     = company_payloads.get("growth"),
            management_snapshot = company_payloads.get("management"),
            ownership_snapshot  = company_payloads.get("ownership"),
            opportunity_snapshot = company_payloads.get("opportunity"),
            profile_snapshot    = company_payloads.get("profile"),
            metadata            = {
                "market_snapshot_id": _snap_id(market_snap),
                "request_id":         request.request_id,
            },
        )
        return snap

    def _stage_strategy(
        self,
        request:      InvestmentRequest,
        strategy_id:  str,
        market_snap:  Any,
        company_snap: Optional[Any],
    ) -> Any:
        """
        Stage 3 — Strategy Intelligence.

        Submits one update per available intelligence source using
        StrategyIntelligenceIntegrationEngine.submit_update_sync(),
        then retrieves the integrated StrategySnapshot.
        """
        from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
            StrategyIntelligenceIntegrationEngine,
        )
        from iios.investment.strategy.integration.aggregation_state import make_update
        from iios.investment.strategy.integration.integration_constants import IntelligenceSource

        engine: StrategyIntelligenceIntegrationEngine = self._engines.strategy_engine
        strategy_payloads: dict = request.metadata.get("strategy_payloads", {})

        # Submit the market context as the market intelligence source
        market_payload: dict = strategy_payloads.get("market") or {}
        if market_snap is not None and not market_payload:
            market_payload = {
                "snapshot_id": _snap_id(market_snap),
                "request_id":  request.request_id,
            }
        if market_payload:
            upd = make_update(
                source       = IntelligenceSource.MARKET,
                strategy_id  = strategy_id,
                payload      = market_payload,
                confidence   = 75.0,
                correlation_id = request.request_id,
            )
            engine.submit_update_sync(upd)

        # Submit company context if available
        company_payload: dict = strategy_payloads.get("company") or {}
        if company_snap is not None and not company_payload:
            company_payload = {
                "snapshot_id": _snap_id(company_snap),
                "request_id":  request.request_id,
            }
        if company_payload:
            upd = make_update(
                source       = IntelligenceSource.COMPANY,
                strategy_id  = strategy_id,
                payload      = company_payload,
                confidence   = 75.0,
                correlation_id = request.request_id,
            )
            engine.submit_update_sync(upd)

        # Submit any explicitly provided strategy framework intelligence
        for src_name, src_enum in [
            ("strategy_framework", IntelligenceSource.STRATEGY_FRAMEWORK),
            ("lifecycle",          IntelligenceSource.LIFECYCLE),
            ("evaluation",         IntelligenceSource.EVALUATION),
            ("opportunity",        IntelligenceSource.OPPORTUNITY),
            ("risk",               IntelligenceSource.RISK),
            ("learning",           IntelligenceSource.LEARNING),
            ("debate",             IntelligenceSource.DEBATE),
        ]:
            payload = strategy_payloads.get(src_name) or {}
            if payload:
                upd = make_update(
                    source       = src_enum,
                    strategy_id  = strategy_id,
                    payload      = payload,
                    confidence   = 75.0,
                    correlation_id = request.request_id,
                )
                engine.submit_update_sync(upd)

        snap = engine.get_snapshot_sync(strategy_id)
        if snap is None:
            # No prior snapshot exists — return a minimal placeholder dict
            # so the pipeline does not block on absence of strategy data.
            # The portfolio engine receives this as metadata only.
            return _MinimalStrategyProxy(strategy_id=strategy_id)
        return snap

    def _stage_decision(
        self,
        request:       InvestmentRequest,
        decision_id:   str,
        market_snap:   Any,
        company_snap:  Optional[Any],
        strategy_snap: Optional[Any],
    ) -> Any:
        """
        Stage 4 — Decision Intelligence.

        Calls DecisionIntelligenceIntegrationEngine.integrate_sync() with
        available upstream snapshots from request metadata.
        """
        from iios.investment.decision.integration.decision_intelligence_integration_engine import (
            DecisionIntelligenceIntegrationEngine,
        )

        engine: DecisionIntelligenceIntegrationEngine = self._engines.decision_engine
        decision_payloads: dict = request.metadata.get("decision_payloads", {})

        return engine.integrate_sync(
            decision_id  = decision_id,
            subject_id   = request.symbols[0] if request.symbols else decision_id,
            subject_type = request.asset_class.value,
            version      = 1,
            evidence     = decision_payloads.get("evidence"),
            reasoning    = decision_payloads.get("reasoning"),
            confidence   = decision_payloads.get("confidence"),
            risk         = decision_payloads.get("risk"),
            explanation  = decision_payloads.get("explanation"),
            committee    = decision_payloads.get("committee"),
            recommendation = decision_payloads.get("recommendation"),
        )

    def _stage_portfolio(
        self,
        request:       InvestmentRequest,
        portfolio_id:  str,
        market_snap:   Any,
        company_snap:  Optional[Any],
        strategy_snap: Optional[Any],
        decision_snap: Optional[Any],
    ) -> Any:
        """
        Stage 5 — Portfolio Intelligence.

        Feeds all available upstream intelligence into
        PortfolioIntelligenceIntegrationEngine via receive() calls,
        then calls integrate() to produce the final snapshot.
        """
        from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
            PortfolioIntelligenceIntegrationEngine,
        )
        from iios.investment.portfolio.integration.integration_types import EngineId

        engine: PortfolioIntelligenceIntegrationEngine = self._engines.portfolio_engine
        portfolio_payloads: dict = request.metadata.get("portfolio_payloads", {})

        # Helper: feed a payload if non-empty
        def _feed(eid: EngineId, data: dict) -> None:
            if data:
                engine.receive(portfolio_id, eid, data)

        # Framework
        _feed(EngineId.FRAMEWORK, portfolio_payloads.get("framework") or {
            "request_id":       request.request_id,
            "market_snap_id":   _snap_id(market_snap),
            "objective":        request.objective.value,
            "risk_profile":     request.risk_profile.value,
            "time_horizon":     request.time_horizon.value,
        })

        # Construction
        _feed(EngineId.CONSTRUCTION,  portfolio_payloads.get("construction", {}))
        # Allocation
        _feed(EngineId.ALLOCATION,    portfolio_payloads.get("allocation", {}))
        # Optimization
        _feed(EngineId.OPTIMIZATION,  portfolio_payloads.get("optimization", {}))
        # Diversification
        _feed(EngineId.DIVERSIFICATION, portfolio_payloads.get("diversification", {}))
        # Risk
        _feed(EngineId.RISK,          portfolio_payloads.get("risk", {}))
        # Performance
        _feed(EngineId.PERFORMANCE,   portfolio_payloads.get("performance", {}))
        # Rebalancing
        _feed(EngineId.REBALANCING,   portfolio_payloads.get("rebalancing", {}))
        # Recommendation (informed by decision snapshot if available)
        rec_payload = portfolio_payloads.get("recommendation", {})
        if not rec_payload and decision_snap is not None:
            rec_payload = {
                "source_decision_id": _snap_id(decision_snap),
                "request_id":         request.request_id,
            }
        _feed(EngineId.RECOMMENDATION, rec_payload)

        return engine.integrate(
            portfolio_id,
            publish = self._params.publish_portfolio_snapshot,
        )

    # ── Result construction ────────────────────────────────────────────────────

    def _build_result(
        self,
        state:        WorkflowState,
        request_id:   str,
        portfolio_id: str,
        portfolio_snap: Optional[Any],
    ) -> WorkflowResult:
        terminal = state.current_stage
        succeeded = (terminal == WorkflowStage.PUBLISHED)

        # Collect per-stage quality scores
        def _qof(stage: WorkflowStage, *attrs: str) -> Optional[float]:
            snap = state.get_snapshot(stage)
            return _extract_quality(snap, *attrs) if snap else None

        market_q   = _qof(WorkflowStage.MARKET,   "quality_score", "overall_score")
        company_q  = _qof(WorkflowStage.COMPANY,  "quality_score", "overall_score")
        strategy_q = _qof(WorkflowStage.STRATEGY, "quality_score")
        decision_q = _qof(WorkflowStage.DECISION, "quality_score")
        portfolio_q = _qof(WorkflowStage.PORTFOLIO, "quality_score")

        records   = state.stage_records
        retries   = sum(state.retry_count(s) for s in PIPELINE_STAGES)
        durations = {
            r.stage.value: r.duration_ms
            for r in records
            if r.duration_ms > 0
        }

        run_record = WorkflowRunRecord(
            run_id              = str(uuid.uuid4()),
            workflow_id         = InstitutionalInvestmentWorkflow.WORKFLOW_ID,
            request_id          = request_id,
            portfolio_id        = portfolio_id,
            started_at          = state.started_at,
            completed_at        = state.completed_at or _now_iso(),
            terminal_stage      = terminal,
            total_duration_ms   = state.total_duration_ms(),
            n_stages_completed  = len(state.completed_stages),
            n_retries           = retries,
            n_errors            = len(state.errors),
            n_warnings          = len(state.warnings),
            snapshot_id         = _snap_id(portfolio_snap) if portfolio_snap else None,
            market_quality      = market_q,
            company_quality     = company_q,
            strategy_quality    = strategy_q,
            decision_quality    = decision_q,
            portfolio_quality   = portfolio_q,
            is_published        = succeeded,
            errors              = tuple(state.errors),
            warnings            = tuple(state.warnings),
            stage_durations_ms  = durations,
        )

        stage_snaps: Dict[WorkflowStage, Any] = {}
        for s in PIPELINE_STAGES:
            snap = state.get_snapshot(s)
            if snap is not None:
                stage_snaps[s] = snap

        return WorkflowResult(
            succeeded          = succeeded,
            portfolio_snapshot = portfolio_snap,
            workflow_id        = InstitutionalInvestmentWorkflow.WORKFLOW_ID,
            request_id         = request_id,
            portfolio_id       = portfolio_id,
            stage_snapshots    = stage_snaps,
            state              = state,
            run_record         = run_record,
        )

    # ── Metric conversion ──────────────────────────────────────────────────────

    @staticmethod
    def _to_metric(result: WorkflowResult) -> WorkflowRunMetric:
        rr = result.run_record
        return WorkflowRunMetric(
            workflow_id       = rr.workflow_id,
            portfolio_id      = rr.portfolio_id,
            succeeded         = rr.succeeded,
            total_duration_ms = rr.total_duration_ms,
            n_stages_done     = rr.n_stages_completed,
            n_retries         = rr.n_retries,
            n_errors          = rr.n_errors,
            n_warnings        = rr.n_warnings,
            market_quality    = rr.market_quality,
            company_quality   = rr.company_quality,
            strategy_quality  = rr.strategy_quality,
            decision_quality  = rr.decision_quality,
            portfolio_quality = rr.portfolio_quality,
            snapshot_id       = rr.snapshot_id,
        )


# ── Minimal proxy for absent strategy snapshot ─────────────────────────────────

class _MinimalStrategyProxy:
    """
    Returned by _stage_strategy when no prior StrategySnapshot exists.
    Carries only the strategy_id so downstream stages can reference it.
    This is NOT a StrategySnapshot — it is a graceful-degradation sentinel.
    """

    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id
        self.snapshot_id = f"proxy-{strategy_id}"
        self.quality_score: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "snapshot_id": self.snapshot_id,
            "is_proxy":    True,
        }
