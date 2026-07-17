"""iios/execution/risk/rules/builtin/session_rule.py
Session rule — blocks execution outside valid trading session.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result
from ..rule_result import make_override_required_result

_RULE_ID   = "builtin:compliance:session_v1"
_RULE_NAME = "Trading Session Rule"


class SessionRule(BaseRule):
    """
    Validates that execution is occurring within a valid trading session.

    Context keys
    ------------
    session_info.session_valid       bool   Whether session is open (default True)
    session_info.session_name        str    e.g. 'NSE_EQUITY'
    session_info.pre_market          bool   True if in pre-market (default False)
    session_info.post_market         bool   True if in post-market (default False)
    risk_limits.allow_pre_market     bool   Allow pre-market execution (default False)
    risk_limits.allow_post_market    bool   Allow post-market execution (default False)
    """

    _version = "1.0.0"

    def __init__(
        self,
        allow_pre_market:  bool = False,
        allow_post_market: bool = False,
    ) -> None:
        super().__init__()
        self._allow_pre  = allow_pre_market
        self._allow_post = allow_post_market

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.COMPLIANCE

    def priority(self) -> RulePriority:
        return RulePriority.HIGH

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        session_valid = bool(context.session_info.get("session_valid", True))
        pre_market    = bool(context.session_info.get("pre_market",    False))
        post_market   = bool(context.session_info.get("post_market",   False))

        allow_pre  = bool(context.get_limit("allow_pre_market",  self._allow_pre))
        allow_post = bool(context.get_limit("allow_post_market", self._allow_post))

        if not session_valid and not pre_market and not post_market:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Trading session is closed — execution blocked.",
                reason="session_closed",
            )

        if pre_market and not allow_pre:
            return make_override_required_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Pre-market execution requires override authorization.",
                reason="pre_market_not_allowed",
            )

        if post_market and not allow_post:
            return make_override_required_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Post-market execution requires override authorization.",
                reason="post_market_not_allowed",
            )

        session_name = context.session_info.get("session_name", "default")
        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Session '{session_name}' is valid for execution.",
        )
