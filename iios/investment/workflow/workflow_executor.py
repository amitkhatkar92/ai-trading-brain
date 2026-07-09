"""iios/investment/workflow/workflow_executor.py
WorkflowExecutor — sequential and parallel workflow execution.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from iios.investment.investment_constants import (
    AnalysisStatus,
    DEFAULT_MAX_WORKERS,
    DEFAULT_WORKFLOW_TIMEOUT_SEC,
)
from iios.investment.models.investment_analysis import InvestmentAnalysis
from iios.investment.models.investment_context_model import InvestmentContext
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.workflow.investment_workflow import InvestmentWorkflow


class WorkflowExecutor:
    """
    Executes InvestmentWorkflows against an InvestmentRequest.

    - ``execute()``          — sequential, priority-ordered
    - ``execute_parallel()`` — concurrent via ThreadPoolExecutor
    """

    def execute(
        self,
        request:   InvestmentRequest,
        workflows: list[InvestmentWorkflow],
        context:   InvestmentContext | None = None,
    ) -> list[InvestmentAnalysis]:
        """Run workflows sequentially in priority order."""
        from iios.investment.models.investment_context_model import InvestmentContext as _IC  # noqa: PLC0415
        ctx = context or _IC(
            request_id=request.request_id,
            asset_class=request.asset_class,
            symbols=list(request.symbols),
        )

        ordered    = sorted(workflows, key=lambda w: w.priority)
        applicable = [w for w in ordered if w.supports(request.asset_class)]
        analyses:  list[InvestmentAnalysis] = []

        for workflow in applicable:
            analysis = self._run_one(workflow, request, ctx)
            analyses.append(analysis)
            # Feed completed result back into context
            if analysis.status == AnalysisStatus.COMPLETED:
                ctx.set_result(workflow.intelligence_type, analysis.findings)

        return analyses

    def execute_parallel(
        self,
        request:     InvestmentRequest,
        workflows:   list[InvestmentWorkflow],
        context:     InvestmentContext | None = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> list[InvestmentAnalysis]:
        """Run all applicable workflows in parallel."""
        from iios.investment.models.investment_context_model import InvestmentContext as _IC  # noqa: PLC0415
        ctx = context or _IC(
            request_id=request.request_id,
            asset_class=request.asset_class,
            symbols=list(request.symbols),
        )
        applicable = [w for w in workflows if w.supports(request.asset_class)]

        if not applicable:
            return []

        analyses: list[InvestmentAnalysis] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._run_one, wf, request, ctx): wf
                for wf in applicable
            }
            for future in as_completed(futures):
                try:
                    analyses.append(future.result())
                except Exception as exc:  # noqa: BLE001
                    wf = futures[future]
                    a  = InvestmentAnalysis(
                        request_id=request.request_id,
                        workflow_id=wf.workflow_id,
                        intelligence_type=wf.intelligence_type,
                        asset_class=request.asset_class,
                        status=AnalysisStatus.FAILED,
                        errors=[str(exc)],
                    )
                    analyses.append(a)

        # Sort back into priority order
        id_order = {w.workflow_id: w.priority for w in applicable}
        analyses.sort(key=lambda a: id_order.get(a.workflow_id, 0))
        return analyses

    # ── internals ─────────────────────────────────────────────────────────────

    def _run_one(
        self,
        workflow: InvestmentWorkflow,
        request:  InvestmentRequest,
        context:  InvestmentContext,
    ) -> InvestmentAnalysis:
        t0 = time.time()
        try:
            analysis = workflow.execute(request, context)
            if analysis.status == AnalysisStatus.PENDING:
                analysis.mark_completed()
        except Exception as exc:  # noqa: BLE001
            analysis = InvestmentAnalysis(
                request_id=request.request_id,
                workflow_id=workflow.workflow_id,
                intelligence_type=workflow.intelligence_type,
                asset_class=request.asset_class,
                symbols=list(request.symbols),
                status=AnalysisStatus.FAILED,
                errors=[str(exc)],
            )
            analysis.completed_at = time.time()
        analysis.duration_ms = (time.time() - t0) * 1_000
        return analysis
