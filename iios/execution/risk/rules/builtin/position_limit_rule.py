"""iios/execution/risk/rules/builtin/position_limit_rule.py
Position limit rule — checks open positions vs max allowed.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:position:position_limit_v1"
_RULE_NAME = "Position Limit Rule"

_DEFAULT_MAX_POSITIONS  = 20
_DEFAULT_WARN_POSITIONS = 16


class PositionLimitRule(BaseRule):
    """
    Checks the number of open positions against configured limits.

    Context keys
    ------------
    position_snapshot.open_positions_count    int   Current open positions
    risk_limits.max_open_positions            int   Override max (default 20)
    risk_limits.warn_open_positions           int   Override warn (default 16)
    """

    _version = "1.0.0"

    def __init__(
        self,
        max_positions:  int = _DEFAULT_MAX_POSITIONS,
        warn_positions: int = _DEFAULT_WARN_POSITIONS,
    ) -> None:
        super().__init__()
        self._max  = max_positions
        self._warn = warn_positions

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.POSITION

    def priority(self) -> RulePriority:
        return RulePriority.NORMAL

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        count    = int(context.get_pos("open_positions_count", 0))
        max_pos  = int(context.get_limit("max_open_positions",  self._max))
        warn_pos = int(context.get_limit("warn_open_positions", self._warn))

        if count >= max_pos:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Open positions {count} at or above limit {max_pos}.",
                reason="position_limit_reached",
                metadata={"open_positions": count, "max_positions": max_pos},
            )

        if count >= warn_pos:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Open positions {count} approaching limit {max_pos}.",
                reason="position_limit_warning",
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Open positions {count} within limit {max_pos}.",
        )
