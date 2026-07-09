"""iios/investment/investment_manager.py
InvestmentManager — main pipeline orchestrator.

Pipeline:
  1. Validate request
  2. Resolve applicable workflows
  3. Create InvestmentContext
  4. Execute workflows → list[InvestmentAnalysis]
  5. Aggregate → InvestmentResult
  6. Update statistics + history
  7. Return InvestmentResult
"""
from __future__ import annotations

import threading
import time
import uuid

from iios.investment.investment_constants import (
    AnalysisStatus,
    AssetClass,
    WorkflowStatus,
)
from iios.investment.investment_exceptions import (
    InvestmentNotFoundError,
    RequestValidationError,
)
from iios.investment.models.investment_analysis import InvestmentAnalysis
from iios.investment.models.investment_context_model import InvestmentContext
from iios.investment.models.investment_history import InvestmentHistory
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.models.investment_result import InvestmentResult
from iios.investment.models.investment_session import InvestmentSession
from iios.investment.models.investment_statistics import InvestmentStatistics
from iios.investment.workflow.investment_workflow import InvestmentWorkflow, NoOpWorkflow
from iios.investment.workflow.workflow_executor import WorkflowExecutor


class InvestmentManager:
    """Coordinates the full investment intelligence pipeline."""

    def __init__(self) -> None:
        self._lock:      threading.RLock      = threading.RLock()
        self._executor   = WorkflowExecutor()
        self._history    = InvestmentHistory()
        self._sessions:  dict[str, InvestmentSession] = {}
        self._stats      = InvestmentStatistics()
        self._workflows: list[InvestmentWorkflow] = []

    # ── workflow registration ──────────────────────────────────────────────────

    def register_workflow(
        self,
        workflow: InvestmentWorkflow,
        *,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            existing_ids = {w.workflow_id for w in self._workflows}
            if workflow.workflow_id in existing_ids and not overwrite:
                return
            if overwrite:
                self._workflows = [
                    w for w in self._workflows if w.workflow_id != workflow.workflow_id
                ]
            self._workflows.append(workflow)

    # ── main entry point ──────────────────────────────────────────────────────

    def analyze(
        self,
        request:    InvestmentRequest,
        session_id: str = "",
        parallel:   bool = False,
    ) -> InvestmentResult:
        """Run the investment intelligence pipeline and return a result."""
        self._validate(request)
        t0 = time.time()

        session = self._get_or_create_session(session_id)
        session.add_request(request)

        ctx = InvestmentContext(
            session_id=session.session_id,
            request_id=request.request_id,
            asset_class=request.asset_class,
            symbols=list(request.symbols),
        )

        with self._lock:
            workflows = list(self._workflows) or [NoOpWorkflow()]

        if parallel:
            analyses = self._executor.execute_parallel(request, workflows, ctx)
        else:
            analyses = self._executor.execute(request, workflows, ctx)

        result = self._aggregate(request, analyses, session.session_id)
        result.duration_ms = (time.time() - t0) * 1_000

        self._history.store(result)
        session.add_result(result)
        self._update_stats(request, result)

        return result

    # ── session management ────────────────────────────────────────────────────

    def create_session(self, name: str = "", source_id: str = "") -> InvestmentSession:
        s = InvestmentSession(name=name, source_id=source_id)
        with self._lock:
            self._sessions[s.session_id] = s
        return s

    def get_session(self, session_id: str) -> InvestmentSession:
        with self._lock:
            s = self._sessions.get(session_id)
        if s is None:
            from iios.investment.investment_exceptions import SessionNotFoundError  # noqa: PLC0415
            raise SessionNotFoundError(session_id)
        return s

    def close_session(self, session_id: str) -> None:
        s = self.get_session(session_id)
        s.close()

    # ── result lookup ─────────────────────────────────────────────────────────

    def get(self, result_id: str) -> InvestmentResult:
        return self._history.get(result_id)  # type: ignore[return-value]

    def recent(self, n: int = 10) -> list[InvestmentResult]:
        return self._history.recent(n)  # type: ignore[return-value]

    def by_request(self, request_id: str) -> list[InvestmentResult]:
        return self._history.by_request(request_id)  # type: ignore[return-value]

    # ── statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict:
        with self._lock:
            return self._stats.to_dict()

    def stats_object(self) -> InvestmentStatistics:
        with self._lock:
            return self._stats

    # ── private helpers ───────────────────────────────────────────────────────

    def _validate(self, request: InvestmentRequest) -> None:
        if not isinstance(request.asset_class, AssetClass):
            raise RequestValidationError("asset_class must be an AssetClass enum")
        if request.symbols is None:
            raise RequestValidationError("symbols must not be None")

    def _get_or_create_session(self, session_id: str) -> InvestmentSession:
        if session_id:
            with self._lock:
                s = self._sessions.get(session_id)
            if s:
                return s
        s = InvestmentSession()
        with self._lock:
            self._sessions[s.session_id] = s
        return s

    def _aggregate(
        self,
        request:    InvestmentRequest,
        analyses:   list[InvestmentAnalysis],
        session_id: str,
    ) -> InvestmentResult:
        completed = [a for a in analyses if a.status == AnalysisStatus.COMPLETED]
        failed    = [a for a in analyses if a.status == AnalysisStatus.FAILED]

        if completed:
            confidence = sum(a.confidence for a in completed) / len(completed)
        else:
            confidence = 0.0

        status = (
            AnalysisStatus.COMPLETED
            if completed
            else AnalysisStatus.FAILED
            if failed
            else AnalysisStatus.COMPLETED
        )

        errors   = [e for a in failed for e in a.errors]
        warnings = [f"Workflow {a.workflow_id} failed" for a in failed] if failed else []

        summary = {
            "total_workflows": len(analyses),
            "completed":       len(completed),
            "failed":          len(failed),
            "symbols":         request.symbols,
            "asset_class":     request.asset_class.value,
        }

        return InvestmentResult(
            request_id=request.request_id,
            session_id=session_id,
            analyses=analyses,
            overall_confidence=confidence,
            summary=summary,
            status=status,
            succeeded=not bool(errors) or bool(completed),
            errors=errors,
            warnings=warnings,
        )

    def _update_stats(
        self, request: InvestmentRequest, result: InvestmentResult
    ) -> None:
        with self._lock:
            s = self._stats
            s.total_requests    += 1
            s.total_analyses    += len(result.analyses)
            s.total_duration_ms += result.duration_ms

            if result.status == AnalysisStatus.COMPLETED:
                s.completed += 1
            else:
                s.failed += 1

            ac_key = request.asset_class.value
            s.by_asset_class[ac_key] = s.by_asset_class.get(ac_key, 0) + 1

            for a in result.analyses:
                it_key = a.intelligence_type.value
                s.by_intelligence_type[it_key] = (
                    s.by_intelligence_type.get(it_key, 0) + 1
                )


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock         = threading.Lock()
_instance:       InvestmentManager | None = None


def get_investment_manager() -> InvestmentManager:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = InvestmentManager()
    return _instance


def reset_investment_manager() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
