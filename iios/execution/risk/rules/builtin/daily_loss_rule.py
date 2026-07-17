"""iios/execution/risk/rules/builtin/daily_loss_rule.py
Daily loss rule — blocks execution when daily PnL exceeds max loss limit.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:operational:daily_loss_v1"
_RULE_NAME = "Daily Loss Rule"

_DEFAULT_MAX_LOSS_PCT  = 0.02   # -2% of portfolio → BLOCK
_DEFAULT_WARN_LOSS_PCT = 0.015  # -1.5% of portfolio → WARNING


class DailyLossRule(BaseRule):
    """
    Blocks execution when intraday PnL drawdown exceeds configured limit.

    Context keys
    ------------
    position_snapshot.daily_pnl          float  Today's realised+unrealised PnL
    position_snapshot.portfolio_value     float  Portfolio NAV
    risk_limits.max_daily_loss_pct        float  Override max loss (default 0.02)
    risk_limits.warn_daily_loss_pct       float  Override warn (default 0.015)
    """

    _version = "1.0.0"

    def __init__(
        self,
        max_loss_pct:  float = _DEFAULT_MAX_LOSS_PCT,
        warn_loss_pct: float = _DEFAULT_WARN_LOSS_PCT,
    ) -> None:
        super().__init__()
        self._max_pct  = max_loss_pct
        self._warn_pct = warn_loss_pct

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.OPERATIONAL

    def priority(self) -> RulePriority:
        return RulePriority.HIGH

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        daily_pnl       = float(context.get_pos("daily_pnl", 0.0))
        portfolio_value = float(context.get_pos("portfolio_value", 0.0))

        max_pct  = float(context.get_limit("max_daily_loss_pct",  self._max_pct))
        warn_pct = float(context.get_limit("warn_daily_loss_pct", self._warn_pct))

        if portfolio_value <= 0 or daily_pnl >= 0:
            return make_pass_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Daily PnL is non-negative — no loss limit breach.",
            )

        loss_pct = abs(daily_pnl) / portfolio_value

        if loss_pct >= max_pct:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=(
                    f"Daily loss {loss_pct:.2%} exceeds limit {max_pct:.2%}. "
                    f"PnL: {daily_pnl:,.2f}"
                ),
                reason="daily_loss_limit_exceeded",
                metadata={"loss_pct": loss_pct, "max_loss_pct": max_pct,
                          "daily_pnl": daily_pnl},
            )

        if loss_pct >= warn_pct:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Daily loss {loss_pct:.2%} approaching limit {max_pct:.2%}.",
                reason="daily_loss_warning",
                metadata={"loss_pct": loss_pct},
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Daily loss {loss_pct:.2%} within limit {max_pct:.2%}.",
        )
