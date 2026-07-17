"""iios/execution/risk/rules/builtin/duplicate_order_rule.py
Duplicate order rule — detects repeated/duplicate orders.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:execution:duplicate_order_v1"
_RULE_NAME = "Duplicate Order Rule"


class DuplicateOrderRule(BaseRule):
    """
    Detects orders that appear to be duplicates of recently submitted orders.

    Callers should populate the execution snapshot with a unique order hash
    and the list of recent order hashes for comparison.

    Context keys
    ------------
    execution_snapshot.order_hash          str   Unique hash for this order
    execution_snapshot.recent_order_hashes list  Hashes of recent orders
    execution_snapshot.order_id            str   Current order ID
    execution_snapshot.recent_order_ids    list  IDs of recent orders
    """

    _version = "1.0.0"

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.EXECUTION

    def priority(self) -> RulePriority:
        return RulePriority.HIGH

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        order_hash    = context.get_exec("order_hash", "")
        recent_hashes = context.get_exec("recent_order_hashes", [])

        order_id      = context.get_exec("order_id", "") or context.order_id
        recent_ids    = context.get_exec("recent_order_ids", [])

        # Check by hash
        if order_hash and order_hash in (recent_hashes or []):
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=(
                    f"Duplicate order detected — hash '{order_hash}' "
                    f"matches a recently submitted order."
                ),
                reason="duplicate_order_hash",
                metadata={"order_hash": order_hash},
            )

        # Check by order ID
        if order_id and order_id in (recent_ids or []):
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=(
                    f"Order ID '{order_id}' appears in recent order list — "
                    f"potential duplicate."
                ),
                reason="duplicate_order_id",
                metadata={"order_id": order_id},
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message="No duplicate order detected.",
        )
