"""iios/execution/risk/rules/builtin/exposure_rule.py
Exposure limit rule — checks notional exposure vs portfolio limit.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import (
    RuleResult,
    make_block_result, make_pass_result, make_warning_result,
)

_RULE_ID   = "builtin:exposure:exposure_limit_v1"
_RULE_NAME = "Exposure Limit Rule"

# Default thresholds
_DEFAULT_MAX_EXPOSURE_PCT  = 0.20   # 20% of portfolio → BLOCK
_DEFAULT_WARN_EXPOSURE_PCT = 0.15   # 15% of portfolio → WARNING


class ExposureRule(BaseRule):
    """
    Checks order notional vs current portfolio exposure limits.

    Context keys
    ------------
    execution_snapshot.notional_value      float  Order notional (required)
    position_snapshot.total_exposure       float  Current total exposure
    position_snapshot.portfolio_value      float  Total portfolio NAV
    risk_limits.max_exposure_pct           float  Override max (default 0.20)
    risk_limits.warn_exposure_pct          float  Override warn (default 0.15)
    """

    _version = "1.0.0"

    def __init__(
        self,
        max_exposure_pct:  float = _DEFAULT_MAX_EXPOSURE_PCT,
        warn_exposure_pct: float = _DEFAULT_WARN_EXPOSURE_PCT,
    ) -> None:
        super().__init__()
        self._max_pct  = max_exposure_pct
        self._warn_pct = warn_exposure_pct

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.EXPOSURE

    def priority(self) -> RulePriority:
        return RulePriority.HIGH

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        notional        = float(context.get_exec("notional_value", 0.0))
        current_exp     = float(context.get_pos("total_exposure", 0.0))
        portfolio_value = float(context.get_pos("portfolio_value", 0.0))

        max_pct  = float(context.get_limit("max_exposure_pct",  self._max_pct))
        warn_pct = float(context.get_limit("warn_exposure_pct", self._warn_pct))

        if portfolio_value <= 0:
            return make_pass_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Exposure check skipped — no portfolio value provided.",
            )

        projected_exp_pct = (current_exp + notional) / portfolio_value

        if projected_exp_pct >= max_pct:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=(
                    f"Projected exposure {projected_exp_pct:.1%} exceeds "
                    f"limit {max_pct:.1%}."
                ),
                reason="exposure_limit_exceeded",
                metadata={"projected_pct": projected_exp_pct, "limit_pct": max_pct},
            )

        if projected_exp_pct >= warn_pct:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=(
                    f"Projected exposure {projected_exp_pct:.1%} approaching "
                    f"limit {max_pct:.1%}."
                ),
                reason="exposure_warning",
                metadata={"projected_pct": projected_exp_pct, "warn_pct": warn_pct},
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Exposure {projected_exp_pct:.1%} within limit {max_pct:.1%}.",
            metadata={"projected_pct": projected_exp_pct},
        )
