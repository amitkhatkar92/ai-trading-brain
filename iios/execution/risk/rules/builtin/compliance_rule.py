"""iios/execution/risk/rules/builtin/compliance_rule.py
Compliance rule — checks regulatory and internal compliance markers.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:compliance:compliance_check_v1"
_RULE_NAME = "Compliance Rule"


class ComplianceRule(BaseRule):
    """
    Checks compliance flags set by upstream compliance systems.

    Context keys
    ------------
    execution_snapshot.compliance_cleared    bool   All checks passed upstream (default True)
    execution_snapshot.restricted_instrument bool   Instrument is on restricted list (default False)
    execution_snapshot.insider_trading_flag  bool   Potential insider trading flag (default False)
    execution_snapshot.sanction_check_passed bool   Sanction screening passed (default True)
    """

    _version = "1.0.0"

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.COMPLIANCE

    def priority(self) -> RulePriority:
        return RulePriority.CRITICAL

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        compliance_cleared    = bool(context.get_exec("compliance_cleared",    True))
        restricted_instrument = bool(context.get_exec("restricted_instrument", False))
        insider_flag          = bool(context.get_exec("insider_trading_flag",  False))
        sanction_passed       = bool(context.get_exec("sanction_check_passed", True))

        if insider_flag:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Insider trading flag is set — execution blocked.",
                reason="insider_trading_flag",
            )

        if not sanction_passed:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Sanction screening failed — execution blocked.",
                reason="sanction_check_failed",
            )

        if restricted_instrument:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Instrument is on restricted list — execution blocked.",
                reason="restricted_instrument",
            )

        if not compliance_cleared:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Compliance pre-check not confirmed — proceed with caution.",
                reason="compliance_not_cleared",
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message="All compliance checks passed.",
        )
