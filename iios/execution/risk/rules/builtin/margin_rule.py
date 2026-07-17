"""iios/execution/risk/rules/builtin/margin_rule.py
Margin utilization rule — checks margin used vs available.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:margin:margin_utilization_v1"
_RULE_NAME = "Margin Utilization Rule"

_DEFAULT_MAX_MARGIN_PCT  = 0.90   # 90% → BLOCK
_DEFAULT_WARN_MARGIN_PCT = 0.75   # 75% → WARNING


class MarginRule(BaseRule):
    """
    Checks margin utilization against configured thresholds.

    Context keys
    ------------
    position_snapshot.margin_used        float  Margin currently consumed
    position_snapshot.margin_available   float  Total margin available
    risk_limits.max_margin_pct           float  Override max (default 0.90)
    risk_limits.warn_margin_pct          float  Override warn (default 0.75)
    """

    _version = "1.0.0"

    def __init__(
        self,
        max_margin_pct:  float = _DEFAULT_MAX_MARGIN_PCT,
        warn_margin_pct: float = _DEFAULT_WARN_MARGIN_PCT,
    ) -> None:
        super().__init__()
        self._max_pct  = max_margin_pct
        self._warn_pct = warn_margin_pct

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.MARGIN

    def priority(self) -> RulePriority:
        return RulePriority.HIGH

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        margin_used      = float(context.get_pos("margin_used", 0.0))
        margin_available = float(context.get_pos("margin_available", 0.0))

        max_pct  = float(context.get_limit("max_margin_pct",  self._max_pct))
        warn_pct = float(context.get_limit("warn_margin_pct", self._warn_pct))

        if margin_available <= 0:
            return make_pass_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Margin check skipped — no margin data provided.",
            )

        utilization = margin_used / margin_available

        if utilization >= max_pct:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Margin utilization {utilization:.1%} exceeds limit {max_pct:.1%}.",
                reason="margin_limit_exceeded",
                metadata={"utilization": utilization, "limit": max_pct},
            )

        if utilization >= warn_pct:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Margin utilization {utilization:.1%} approaching limit {max_pct:.1%}.",
                reason="margin_warning",
                metadata={"utilization": utilization, "warn": warn_pct},
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Margin utilization {utilization:.1%} within limit {max_pct:.1%}.",
        )
