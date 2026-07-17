"""iios/execution/risk/rules/builtin/liquidity_rule.py
Liquidity rule — checks order size vs average daily volume.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:liquidity:adv_check_v1"
_RULE_NAME = "Liquidity ADV Rule"

_DEFAULT_MAX_ADV_PCT  = 0.10   # 10% of ADV → BLOCK
_DEFAULT_WARN_ADV_PCT = 0.05   # 5% of ADV → WARNING


class LiquidityRule(BaseRule):
    """
    Checks order quantity vs average daily volume (ADV) ratio.

    Context keys
    ------------
    execution_snapshot.quantity          float  Shares/lots being ordered
    execution_snapshot.avg_daily_volume  float  Instrument ADV
    risk_limits.max_adv_pct              float  Override max (default 0.10)
    risk_limits.warn_adv_pct             float  Override warn (default 0.05)
    """

    _version = "1.0.0"

    def __init__(
        self,
        max_adv_pct:  float = _DEFAULT_MAX_ADV_PCT,
        warn_adv_pct: float = _DEFAULT_WARN_ADV_PCT,
    ) -> None:
        super().__init__()
        self._max_pct  = max_adv_pct
        self._warn_pct = warn_adv_pct

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.LIQUIDITY

    def priority(self) -> RulePriority:
        return RulePriority.NORMAL

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        qty       = float(context.get_exec("quantity", 0.0))
        adv       = float(context.get_exec("avg_daily_volume", 0.0))
        max_pct   = float(context.get_limit("max_adv_pct",  self._max_pct))
        warn_pct  = float(context.get_limit("warn_adv_pct", self._warn_pct))

        if adv <= 0:
            return make_pass_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Liquidity check skipped — ADV not provided.",
            )

        adv_ratio = qty / adv

        if adv_ratio >= max_pct:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Order is {adv_ratio:.1%} of ADV — exceeds limit {max_pct:.1%}.",
                reason="liquidity_limit_exceeded",
                metadata={"adv_ratio": adv_ratio, "max_adv_pct": max_pct},
            )

        if adv_ratio >= warn_pct:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Order is {adv_ratio:.1%} of ADV — approaching limit {max_pct:.1%}.",
                reason="liquidity_warning",
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Order ADV ratio {adv_ratio:.1%} within limit {max_pct:.1%}.",
        )
