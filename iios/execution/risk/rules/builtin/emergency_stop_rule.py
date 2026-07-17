"""iios/execution/risk/rules/builtin/emergency_stop_rule.py
Emergency stop rule — highest priority safety check.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result

_RULE_ID   = "builtin:safety:emergency_stop_v1"
_RULE_NAME = "Emergency Stop Rule"


class EmergencyStopRule(BaseRule):
    """
    Blocks ALL execution when an emergency stop flag is active.

    Context keys checked
    --------------------
    risk_limits.emergency_stop_active    bool  (default False)
    system_info.emergency_stop           bool  (default False)
    """

    _version = "1.0.0"

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.SAFETY

    def priority(self) -> RulePriority:
        return RulePriority.CRITICAL

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        if context.emergency_stop_active:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="EMERGENCY STOP is active — all execution blocked.",
                reason="emergency_stop_active",
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message="Emergency stop not active.",
        )
