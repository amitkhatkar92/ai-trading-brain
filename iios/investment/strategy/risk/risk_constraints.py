"""iios/investment/strategy/risk/risk_constraints.py
RiskConstraints — hard-gate checks against RiskLimits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from iios.investment.strategy.risk.risk_input import StrategyRiskInput
from iios.investment.strategy.risk.risk_limits import RiskLimits, DEFAULT_LIMITS
from iios.investment.strategy.risk.risk_statistics import expected_daily_loss, expected_weekly_loss, expected_monthly_loss


class ConstraintStatus(str, Enum):
    PASS    = "pass"
    WARN    = "warn"
    BREACH  = "breach"


@dataclass(frozen=True)
class ConstraintCheck:
    """Result of a single constraint evaluation."""
    name:    str
    status:  ConstraintStatus
    actual:  float
    limit:   float
    message: str

    @property
    def passed(self) -> bool:
        return self.status != ConstraintStatus.BREACH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":    self.name,
            "status":  self.status.value,
            "actual":  round(self.actual, 6),
            "limit":   round(self.limit, 6),
            "message": self.message,
        }


@dataclass(frozen=True)
class ConstraintCheckResult:
    """Aggregate constraint evaluation for a strategy."""
    strategy_id:   str
    all_passed:    bool
    breaches:      List[ConstraintCheck]
    warnings:      List[ConstraintCheck]
    passed:        List[ConstraintCheck]
    emergency_stop: bool

    @property
    def breach_count(self) -> int:
        return len(self.breaches)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":   self.strategy_id,
            "all_passed":    self.all_passed,
            "emergency_stop": self.emergency_stop,
            "breach_count":  self.breach_count,
            "breaches":      [c.to_dict() for c in self.breaches],
            "warnings":      [c.to_dict() for c in self.warnings],
        }


class RiskConstraints:
    """
    Evaluates a StrategyRiskInput against RiskLimits.
    Returns ConstraintCheckResult with PASS / WARN / BREACH per rule.
    """

    def check(
        self,
        inp:             StrategyRiskInput,
        risk_score:      float,              # from RiskScoreCalculator
        stress_pass_rate: float = 1.0,       # from StressTestingEngine
        stress_agg_score: float = 0.0,       # from StressTestingEngine
        limits:          RiskLimits = DEFAULT_LIMITS,
    ) -> ConstraintCheckResult:
        checks: List[ConstraintCheck] = []

        # 1. Overall risk score
        checks.append(self._check(
            "overall_risk_score",
            risk_score, limits.max_risk_score,
            warn_at=limits.max_risk_score * 0.85,
        ))

        # 2. Volatility
        checks.append(self._check(
            "annualized_vol",
            inp.annualized_vol, limits.max_annualized_vol,
            warn_at=limits.max_annualized_vol * 0.85,
        ))

        # 3. Drawdown
        checks.append(self._check(
            "max_drawdown",
            inp.max_drawdown, limits.max_drawdown_limit,
            warn_at=limits.max_drawdown_limit * 0.85,
        ))

        # 4. Daily loss (expected 95%)
        daily_loss = expected_daily_loss(inp.annualized_vol)
        checks.append(self._check(
            "expected_daily_loss_95",
            daily_loss, limits.daily_loss_limit,
            warn_at=limits.daily_loss_limit * 0.85,
        ))

        # 5. Weekly loss (expected 95%)
        weekly_loss = expected_weekly_loss(inp.annualized_vol)
        checks.append(self._check(
            "expected_weekly_loss_95",
            weekly_loss, limits.weekly_loss_limit,
            warn_at=limits.weekly_loss_limit * 0.85,
        ))

        # 6. Monthly loss (expected 95%)
        monthly_loss = expected_monthly_loss(inp.annualized_vol)
        checks.append(self._check(
            "expected_monthly_loss_95",
            monthly_loss, limits.monthly_loss_limit,
            warn_at=limits.monthly_loss_limit * 0.85,
        ))

        # 7. Portfolio weight
        if inp.portfolio_weight > 0.0:
            checks.append(self._check(
                "portfolio_weight",
                inp.portfolio_weight, limits.max_portfolio_weight,
                warn_at=limits.max_portfolio_weight * 0.85,
            ))

        # 8. Stress pass rate
        checks.append(self._check(
            "stress_pass_rate",
            limits.min_stress_pass_rate, stress_pass_rate,  # actual >= limit → OK
            warn_at=None, lower_is_better=False,
        ))

        # 9. Aggregate stress score
        checks.append(self._check(
            "aggregate_stress_score",
            stress_agg_score, limits.max_aggregate_stress,
            warn_at=limits.max_aggregate_stress * 0.85,
        ))

        breaches = [c for c in checks if c.status == ConstraintStatus.BREACH]
        warnings = [c for c in checks if c.status == ConstraintStatus.WARN]
        passed   = [c for c in checks if c.status == ConstraintStatus.PASS]
        all_pass = len(breaches) == 0

        emergency = (
            limits.enable_emergency_stop
            and risk_score >= limits.emergency_stop_score
        )

        return ConstraintCheckResult(
            strategy_id=inp.strategy_id,
            all_passed=all_pass,
            breaches=breaches,
            warnings=warnings,
            passed=passed,
            emergency_stop=emergency,
        )

    def _check(
        self,
        name:           str,
        actual:         float,
        limit:          float,
        warn_at:        Any = None,
        lower_is_better: bool = True,
    ) -> ConstraintCheck:
        if lower_is_better:
            if actual > limit:
                status = ConstraintStatus.BREACH
                msg = f"{name}: {actual:.4f} exceeds limit {limit:.4f}"
            elif warn_at is not None and actual > warn_at:
                status = ConstraintStatus.WARN
                msg = f"{name}: {actual:.4f} approaching limit {limit:.4f}"
            else:
                status = ConstraintStatus.PASS
                msg = f"{name}: {actual:.4f} within limit {limit:.4f}"
        else:
            # "actual" must be >= limit (e.g. stress pass rate)
            if actual < limit:
                status = ConstraintStatus.BREACH
                msg = f"{name}: {actual:.4f} below minimum {limit:.4f}"
            else:
                status = ConstraintStatus.PASS
                msg = f"{name}: {actual:.4f} meets minimum {limit:.4f}"

        return ConstraintCheck(name=name, status=status, actual=actual, limit=limit, message=msg)
