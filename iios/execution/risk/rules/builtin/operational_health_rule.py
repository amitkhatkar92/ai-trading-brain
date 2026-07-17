"""iios/execution/risk/rules/builtin/operational_health_rule.py
Operational health rule — checks system / data feed health before execution.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:operational:system_health_v1"
_RULE_NAME = "Operational Health Rule"


class OperationalHealthRule(BaseRule):
    """
    Blocks execution if critical system components are unhealthy.

    Context keys
    ------------
    system_info.system_healthy          bool  All systems operational (default True)
    system_info.data_feed_healthy       bool  Market data feed healthy (default True)
    system_info.broker_connection       bool  Broker connection active (default True)
    system_info.latency_ok              bool  Latency within threshold (default True)
    system_info.degraded_mode           bool  System in degraded mode (default False)
    """

    _version = "1.0.0"

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.OPERATIONAL

    def priority(self) -> RulePriority:
        return RulePriority.CRITICAL

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        system_healthy      = bool(context.system_info.get("system_healthy",    True))
        data_feed_healthy   = bool(context.system_info.get("data_feed_healthy", True))
        broker_connection   = bool(context.system_info.get("broker_connection", True))
        latency_ok          = bool(context.system_info.get("latency_ok",        True))
        degraded_mode       = bool(context.system_info.get("degraded_mode",     False))

        if not system_healthy:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="System health check failed — execution blocked.",
                reason="system_unhealthy",
            )

        if not broker_connection:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Broker connection is down — execution blocked.",
                reason="broker_disconnected",
            )

        if not data_feed_healthy:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Data feed is degraded — execution proceeds with caution.",
                reason="data_feed_degraded",
            )

        if not latency_ok or degraded_mode:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="System is operating in degraded mode.",
                reason="degraded_mode",
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message="All operational health checks passed.",
        )
