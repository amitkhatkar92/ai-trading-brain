"""iios/investment/strategy/risk/strategy_risk_engine.py
StrategyRiskEngine — authoritative strategy risk intelligence engine for IIOS.

Responsibilities:
  • Evaluate and continuously monitor risk for every registered strategy
  • Produce deterministic, auditable, institutional-grade risk scores
  • Publish risk events consumed by downstream engines
  • Track risk evolution over time

Constraints:
  • Does NOT independently evaluate markets or companies
  • Does NOT generate Buy/Sell/Hold recommendations
  • Does NOT execute trades
  • Consumes intelligence from EvaluationEngine, OpportunityEngine,
    PortfolioEngine, and Market Intelligence — never independently derives it

Public API:
  register_strategy()          → StrategyRiskProfile
  evaluate()                   → StrategyRiskProfile (full evaluation)
  get_risk_score()             → Optional[RiskScore]
  get_health()                 → Optional[RiskHealth]
  get_drawdown_report()        → Optional[DrawdownReport]
  get_stress_report()          → Optional[StressTestReport]
  get_constraints()            → Optional[ConstraintCheckResult]
  get_confidence()             → Optional[RiskConfidence]
  risk_history()               → List[StrategyRiskSnapshot]
  risk_score_trend()           → List[float]
  take_snapshot()              → StrategyRiskSnapshot
  batch_evaluate()             → Dict[str, StrategyRiskProfile]
  compare_strategies()         → Dict[str, RiskScore]
  operational_strategies()     → List[str]
  stats()                      → Dict[str, Any]
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.strategy_risk_profile import StrategyRiskProfile
from iios.investment.strategy.risk.strategy_risk_history import StrategyRiskHistory
from iios.investment.strategy.risk.strategy_risk_snapshot import StrategyRiskSnapshot
from iios.investment.strategy.risk.risk_analysis import RiskAnalysis
from iios.investment.strategy.risk.drawdown_engine import DrawdownEngine, DrawdownReport
from iios.investment.strategy.risk.stress_testing import StressTestingEngine, StressTestReport
from iios.investment.strategy.risk.risk_score import RiskScore, RiskScoreCalculator
from iios.investment.strategy.risk.risk_confidence import RiskConfidence
from iios.investment.strategy.risk.risk_quality import RiskQuality
from iios.investment.strategy.risk.risk_health import RiskHealth
from iios.investment.strategy.risk.risk_constraints import ConstraintCheckResult
from iios.investment.strategy.risk.limit_monitor import LimitMonitor, LimitBreachEvent
from iios.investment.strategy.risk.risk_policy import RiskPolicy, DEFAULT_POLICY
from iios.investment.strategy.risk.risk_events import (
    RiskEventBus, RiskEventType, RiskEvent
)
import uuid


class StrategyRiskEngine:
    """
    Central facade for all strategy risk intelligence.
    Thread-safe; all mutations are guarded by per-strategy RLocks.
    """

    def __init__(
        self,
        policy:       Optional[RiskPolicy]       = None,
        event_bus:    Optional[RiskEventBus]     = None,
        max_workers:  int = 4,
    ) -> None:
        self._policy    = policy or DEFAULT_POLICY
        self._bus       = event_bus or RiskEventBus()
        self._workers   = max_workers

        # Sub-engines
        self._analysis  = RiskAnalysis()
        self._drawdown  = DrawdownEngine()
        self._stress    = StressTestingEngine(
            scenarios=self._policy.stress_scenarios,
            max_workers=max_workers,
        )
        self._scorer    = RiskScoreCalculator(
            risk_analysis=self._analysis,
            drawdown_engine=self._drawdown,
            stress_engine=self._stress,
            max_risk_threshold=self._policy.limits.max_risk_score,
        )
        self._monitor   = LimitMonitor(limits=self._policy.limits)
        self._history   = StrategyRiskHistory()

        # Registry: strategy_id → StrategyRiskProfile
        self._registry: Dict[str, StrategyRiskProfile] = {}
        self._locks:    Dict[str, threading.RLock]     = {}
        self._reg_lock  = threading.Lock()

    # ── registration ──────────────────────────────────────────────────────────

    def register_strategy(
        self, strategy_id: str, strategy_name: str = ""
    ) -> StrategyRiskProfile:
        """Pre-register a strategy before evaluation data is available."""
        with self._reg_lock:
            if strategy_id not in self._registry:
                self._registry[strategy_id] = StrategyRiskProfile(
                    strategy_id=strategy_id,
                    strategy_name=strategy_name or strategy_id,
                )
                self._locks[strategy_id] = threading.RLock()
        return self._registry[strategy_id]

    def unregister_strategy(self, strategy_id: str) -> None:
        with self._reg_lock:
            self._registry.pop(strategy_id, None)
            self._locks.pop(strategy_id, None)
        self._history.purge(strategy_id)

    # ── evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, inp: StrategyRiskInput) -> StrategyRiskProfile:
        """
        Full risk evaluation for a strategy.  Thread-safe per strategy_id.
        Updates the profile in-place and captures a history snapshot.
        """
        # Ensure registered
        self.register_strategy(inp.strategy_id, inp.strategy_name)
        lock = self._locks[inp.strategy_id]

        with lock:
            profile = self._registry[inp.strategy_id]
            profile.strategy_name = inp.strategy_name or profile.strategy_name

            # 1. Risk analysis
            analysis = self._analysis.analyse(inp)

            # 2. Drawdown
            drawdown = self._drawdown.evaluate(inp)

            # 3. Stress test
            stress = self._stress.run(inp)

            # 4. Risk score
            risk_score = self._scorer.score(inp, analysis, drawdown, stress)

            # 5. Confidence
            confidence = RiskConfidence.compute(inp)

            # 6. Constraints / limits
            constraints = self._monitor.check_and_record(
                inp,
                risk_score.overall_risk_score,
                stress.pass_rate,
                stress.aggregate_stress_score,
            )

            # 7. Quality
            quality = RiskQuality.assess(inp, risk_score, confidence)

            # 8. Health
            health = RiskHealth.assess(inp, risk_score, confidence, quality, constraints)

            # Update profile
            profile.update(
                risk_score=risk_score,
                health=health,
                drawdown=drawdown,
                stress_report=stress,
                constraints=constraints,
                confidence=confidence,
            )

            # Capture history snapshot
            self._history.capture(profile)

            # Publish events
            self._publish_events(inp, profile, constraints, stress)

        return profile

    def batch_evaluate(
        self, inputs: List[StrategyRiskInput]
    ) -> Dict[str, StrategyRiskProfile]:
        """
        Evaluate multiple strategies in parallel.
        Returns {strategy_id → StrategyRiskProfile}.
        """
        results: Dict[str, StrategyRiskProfile] = {}
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            futures = {pool.submit(self.evaluate, inp): inp for inp in inputs}
            for fut in as_completed(futures):
                inp = futures[fut]
                try:
                    results[inp.strategy_id] = fut.result()
                except Exception:
                    pass
        return results

    # ── queries ───────────────────────────────────────────────────────────────

    def get_profile(self, strategy_id: str) -> Optional[StrategyRiskProfile]:
        return self._registry.get(strategy_id)

    def get_risk_score(self, strategy_id: str) -> Optional[RiskScore]:
        p = self._registry.get(strategy_id)
        return p.risk_score if p else None

    def get_health(self, strategy_id: str) -> Optional[RiskHealth]:
        p = self._registry.get(strategy_id)
        return p.health if p else None

    def get_drawdown_report(self, strategy_id: str) -> Optional[DrawdownReport]:
        p = self._registry.get(strategy_id)
        return p.drawdown if p else None

    def get_stress_report(self, strategy_id: str) -> Optional[StressTestReport]:
        p = self._registry.get(strategy_id)
        return p.stress_report if p else None

    def get_constraints(self, strategy_id: str) -> Optional[ConstraintCheckResult]:
        p = self._registry.get(strategy_id)
        return p.constraints if p else None

    def get_confidence(self, strategy_id: str) -> Optional[RiskConfidence]:
        p = self._registry.get(strategy_id)
        return p.confidence if p else None

    def compare_strategies(
        self, strategy_ids: List[str]
    ) -> Dict[str, Optional[RiskScore]]:
        return {sid: self.get_risk_score(sid) for sid in strategy_ids}

    def operational_strategies(self) -> List[str]:
        """Return strategy IDs that are safe to trade (not in emergency stop)."""
        return [
            sid for sid, p in self._registry.items()
            if p.is_operational
        ]

    def list_strategies(self) -> List[str]:
        return list(self._registry.keys())

    # ── history ───────────────────────────────────────────────────────────────

    def take_snapshot(self, strategy_id: str) -> Optional[StrategyRiskSnapshot]:
        p = self._registry.get(strategy_id)
        if p and p.is_evaluated:
            return self._history.capture(p)
        return None

    def risk_history(
        self, strategy_id: str, n: int = 20
    ) -> List[StrategyRiskSnapshot]:
        return self._history.history(strategy_id, n)

    def risk_score_trend(self, strategy_id: str, n: int = 10) -> List[float]:
        return self._history.risk_score_trend(strategy_id, n)

    # ── limit monitoring ──────────────────────────────────────────────────────

    def breach_history(
        self, strategy_id: str, n: int = 50
    ) -> List[LimitBreachEvent]:
        return self._monitor.breach_history(strategy_id, n)

    def strategies_with_breaches(self) -> List[str]:
        return self._monitor.all_strategy_ids_with_breaches()

    # ── event bus ─────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> RiskEventBus:
        return self._bus

    # ── stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        profiles = list(self._registry.values())
        evaluated = [p for p in profiles if p.is_evaluated]
        operational = [p for p in evaluated if p.is_operational]
        grades: Dict[str, int] = {}
        for p in evaluated:
            g = p.risk_grade
            grades[g] = grades.get(g, 0) + 1

        return {
            "total_strategies":     len(profiles),
            "evaluated_strategies": len(evaluated),
            "operational":          len(operational),
            "by_grade":             grades,
            "strategies_with_breaches": len(self.strategies_with_breaches()),
            "timestamp":            datetime.now(timezone.utc).isoformat(),
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    def _publish_events(
        self,
        inp:         StrategyRiskInput,
        profile:     StrategyRiskProfile,
        constraints: ConstraintCheckResult,
        stress:      StressTestReport,
    ) -> None:
        sid = inp.strategy_id

        self._bus.emit_simple(
            RiskEventType.RISK_EVALUATED, sid,
            {"risk_score": profile.overall_risk_score, "grade": profile.risk_grade},
        )
        if constraints.emergency_stop:
            self._bus.emit_simple(RiskEventType.EMERGENCY_STOP, sid,
                                  {"risk_score": profile.overall_risk_score})
        elif not constraints.all_passed:
            self._bus.emit_simple(RiskEventType.LIMIT_BREACHED, sid,
                                  {"breach_count": constraints.breach_count})
        if stress.overall_stress_rating in ("VULNERABLE", "FRAGILE"):
            self._bus.emit_simple(RiskEventType.STRESS_TEST_FAILED, sid,
                                  {"rating": stress.overall_stress_rating})
        if inp.regime_mismatch:
            self._bus.emit_simple(RiskEventType.REGIME_MISMATCH, sid,
                                  {"current_regime": inp.current_regime})
