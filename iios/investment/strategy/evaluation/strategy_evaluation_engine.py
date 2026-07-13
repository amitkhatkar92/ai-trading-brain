"""iios/investment/strategy/evaluation/strategy_evaluation_engine.py
StrategyEvaluationEngine — authoritative entry point for institutional
strategy evaluation.  All sub-engines are composed here.

This engine:
  - Evaluates strategy quality, robustness, performance, and risk
  - Produces deterministic, auditable EvaluationReport objects
  - Does NOT execute trades, generate signals, or allocate portfolio

Thread-safe: evaluation runs may be submitted in parallel.
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
from iios.investment.strategy.evaluation.performance_engine import PerformanceEngine
from iios.investment.strategy.evaluation.performance_metrics import PerformanceMetrics
from iios.investment.strategy.evaluation.performance_history import PerformanceHistory
from iios.investment.strategy.evaluation.risk_evaluation import RiskEvaluator, RiskMetrics
from iios.investment.strategy.evaluation.trade_quality import (
    TradeQualityAnalyzer, TradeQualityReport
)
from iios.investment.strategy.evaluation.robustness_engine import (
    RobustnessEngine, RobustnessReport
)
from iios.investment.strategy.evaluation.strategy_explanation import (
    StrategyExplainer, StrategyExplanation
)
from iios.investment.strategy.evaluation.institutional_score import (
    InstitutionalStrategyScore
)
from iios.investment.strategy.evaluation.confidence_score import (
    ConfidenceScoreCalculator, ConfidenceFactors
)
from iios.investment.strategy.evaluation.approval_engine import (
    ApprovalEngine, ApprovalCriteria, ApprovalResult, ApprovalStatus
)
from iios.investment.strategy.evaluation.evaluation_grade import (
    EvaluationGrade, grade_from_score
)
from iios.investment.strategy.evaluation.decision_trace import DecisionTrace

logger = logging.getLogger(__name__)


# ── Report ────────────────────────────────────────────────────────────────────

@dataclass
class EvaluationReport:
    """
    Complete evaluation output for one strategy.
    Immutable after construction — all fields set during __post_init__.
    """
    report_id:          str
    strategy_id:        str
    strategy_name:      str
    evaluated_at:       datetime

    performance:        PerformanceMetrics
    risk:               RiskMetrics
    trade_quality:      TradeQualityReport
    robustness:         RobustnessReport
    explanation:        StrategyExplanation
    confidence:         ConfidenceFactors
    score:              InstitutionalStrategyScore
    approval:           ApprovalResult
    trace:              DecisionTrace
    metadata:           Dict[str, Any] = field(default_factory=dict)

    # ── convenience ─────────────────────────────────────────────────────────

    @property
    def overall_score(self) -> float:
        return self.score.overall_score

    @property
    def grade(self) -> EvaluationGrade:
        return self.score.grade

    @property
    def approval_status(self) -> ApprovalStatus:
        return self.approval.status

    @property
    def is_approved(self) -> bool:
        return self.approval.status == ApprovalStatus.APPROVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "evaluated_at":  self.evaluated_at.isoformat(),
            "performance":   self.performance.to_dict(),
            "risk":          self.risk.to_dict(),
            "trade_quality": self.trade_quality.to_dict(),
            "robustness":    self.robustness.to_dict(),
            "explanation":   self.explanation.to_dict(),
            "confidence":    self.confidence.to_dict(),
            "score":         self.score.to_dict(),
            "approval":      self.approval.to_dict(),
            "metadata":      self.metadata,
        }


# ── Engine ────────────────────────────────────────────────────────────────────

class StrategyEvaluationEngine:
    """
    Institutional Strategy Evaluation Engine.

    Usage::

        engine = StrategyEvaluationEngine()
        report = engine.evaluate(inp)

    For parallel evaluation of multiple strategies::

        futures = {sid: engine.evaluate_async(inp) for sid, inp in inputs.items()}
        reports = {sid: f.result() for sid, f in futures.items()}

    """

    def __init__(
        self,
        approval_criteria: Optional[ApprovalCriteria] = None,
        wf_folds: int = 4,
        mc_simulations: int = 1000,
        mc_seed: int = 42,
        max_workers: int = 8,
        max_history: int = 200,
    ) -> None:
        self._perf_engine    = PerformanceEngine()
        self._risk_evaluator = RiskEvaluator()
        self._tq_analyzer    = TradeQualityAnalyzer()
        self._rob_engine     = RobustnessEngine(
            wf_folds=wf_folds,
            mc_simulations=mc_simulations,
            mc_seed=mc_seed,
        )
        self._explainer      = StrategyExplainer()
        self._conf_calc      = ConfidenceScoreCalculator()
        self._approval       = ApprovalEngine(
            approval_criteria or ApprovalCriteria()
        )
        self._pool           = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="eval-"
        )

        # History store per strategy_id
        self._history: Dict[str, Deque[EvaluationReport]] = {}
        self._max_history = max_history
        self._lock = threading.RLock()

        # Listener hooks for downstream systems
        self._listeners: List[Callable[[EvaluationReport], None]] = []

        logger.info("StrategyEvaluationEngine initialised (workers=%d)", max_workers)

    # ── primary API ─────────────────────────────────────────────────────────

    def evaluate(self, inp: EvaluationInput) -> EvaluationReport:
        """
        Synchronous full evaluation.  Blocks until complete.
        Safe to call from any thread.
        """
        report = self._run(inp)
        self._store(report)
        self._notify(report)
        return report

    def evaluate_async(self, inp: EvaluationInput) -> Future:
        """Submit evaluation to thread pool.  Returns a Future[EvaluationReport]."""
        return self._pool.submit(self.evaluate, inp)

    # ── query API ────────────────────────────────────────────────────────────

    def latest_report(self, strategy_id: str) -> Optional[EvaluationReport]:
        with self._lock:
            buf = self._history.get(strategy_id)
            return buf[-1] if buf else None

    def history(
        self, strategy_id: str, n: int = 10
    ) -> List[EvaluationReport]:
        with self._lock:
            buf = list(self._history.get(strategy_id, []))
            return buf[-n:] if len(buf) > n else buf

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._history.keys())

    def is_approved(self, strategy_id: str) -> bool:
        r = self.latest_report(strategy_id)
        return r.is_approved if r else False

    # ── listeners ────────────────────────────────────────────────────────────

    def add_listener(
        self, callback: Callable[[EvaluationReport], None]
    ) -> None:
        with self._lock:
            self._listeners.append(callback)

    # ── shutdown ─────────────────────────────────────────────────────────────

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)
        logger.info("StrategyEvaluationEngine shut down")

    # ── internal pipeline ────────────────────────────────────────────────────

    def _run(self, inp: EvaluationInput) -> EvaluationReport:
        report_id = str(uuid.uuid4())
        trace = DecisionTrace(
            strategy_id=inp.strategy_id,
            evaluation_id=report_id,
        )

        # 1. Performance
        perf = self._perf_engine.compute(inp)
        trace.record("performance", "computed", perf.sharpe_ratio,
                     {"sharpe": perf.sharpe_ratio, "ann_return": perf.annualized_return})

        # 2. Risk
        risk = self._risk_evaluator.evaluate(inp, ann_return=perf.annualized_return)
        trace.record("risk", "computed", risk.max_drawdown,
                     {"max_dd": risk.max_drawdown})

        # 3. Trade quality
        tq = self._tq_analyzer.analyze(inp)
        trace.record("trade_quality", "computed", tq.win_rate,
                     {"win_rate": tq.win_rate})

        # 4. Robustness
        rob = self._rob_engine.evaluate(inp)
        trace.record("robustness", "computed", rob.overall_robustness,
                     {"wf": rob.walk_forward_stability, "mc": rob.mc_robustness})

        # 5. Confidence
        conf = self._conf_calc.compute(
            n_trades=len(inp.trades),
            duration_years=inp.duration_years,
            trade_consistency=tq.statistics.trade_consistency,
        )
        trace.record("confidence", "computed", conf.overall)

        # 6. Score
        approval_result = self._approval.decide(
            overall_score=0.0,   # placeholder — computed below
            sharpe=perf.sharpe_ratio,
            win_rate=tq.win_rate,
            max_drawdown=risk.max_drawdown,
            profit_factor=perf.profit_factor,
            n_trades=len(inp.trades),
            confidence_score=conf.overall,
        )
        score = InstitutionalStrategyScore.compute(
            strategy_id=inp.strategy_id,
            strategy_name=inp.strategy_name,
            sharpe=perf.sharpe_ratio,
            ann_return=perf.annualized_return,
            max_drawdown=risk.max_drawdown,
            win_rate=tq.win_rate,
            profit_factor=perf.profit_factor,
            robustness=rob.overall_robustness,
            exec_efficiency=tq.execution_efficiency,
            confidence=conf.overall,
            approval_status=approval_result.status,
        )
        # Re-run approval with the final overall score
        approval_result = self._approval.decide(
            overall_score=score.overall_score,
            sharpe=perf.sharpe_ratio,
            win_rate=tq.win_rate,
            max_drawdown=risk.max_drawdown,
            profit_factor=perf.profit_factor,
            n_trades=len(inp.trades),
            confidence_score=conf.overall,
        )
        trace.record("approval", "decided", approval_result.status.value)

        # 7. Explanation
        explanation = self._explainer.explain(
            inp,
            sharpe=perf.sharpe_ratio,
            max_drawdown=risk.max_drawdown,
            win_rate=tq.win_rate,
            profit_factor=perf.profit_factor,
            mc_robustness=rob.mc_robustness,
            wf_stability=rob.walk_forward_stability,
            stress_survival=rob.stress_survival,
            overall_score=score.overall_score,
        )

        return EvaluationReport(
            report_id=report_id,
            strategy_id=inp.strategy_id,
            strategy_name=inp.strategy_name,
            evaluated_at=datetime.now(timezone.utc),
            performance=perf,
            risk=risk,
            trade_quality=tq,
            robustness=rob,
            explanation=explanation,
            confidence=conf,
            score=score,
            approval=approval_result,
            trace=trace,
            metadata=dict(inp.metadata),
        )

    def _store(self, report: EvaluationReport) -> None:
        with self._lock:
            sid = report.strategy_id
            if sid not in self._history:
                self._history[sid] = deque(maxlen=self._max_history)
            self._history[sid].append(report)

    def _notify(self, report: EvaluationReport) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(report)
            except Exception:
                logger.exception("Listener error for %s", report.strategy_id)
