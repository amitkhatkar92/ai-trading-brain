"""iios/execution/risk/rules/builtin/order_size_rule.py
Order size rule — checks order quantity vs min/max limits.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result

_RULE_ID   = "builtin:execution:order_size_v1"
_RULE_NAME = "Order Size Rule"

_DEFAULT_MIN_ORDER_SIZE = 1
_DEFAULT_MAX_ORDER_SIZE = 10_000


class OrderSizeRule(BaseRule):
    """
    Checks that the order quantity is within acceptable bounds.

    Context keys
    ------------
    execution_snapshot.quantity     float/int  Order size
    risk_limits.min_order_size      float      Override min (default 1)
    risk_limits.max_order_size      float      Override max (default 10,000)
    """

    _version = "1.0.0"

    def __init__(
        self,
        min_order_size: float = _DEFAULT_MIN_ORDER_SIZE,
        max_order_size: float = _DEFAULT_MAX_ORDER_SIZE,
    ) -> None:
        super().__init__()
        self._min = min_order_size
        self._max = max_order_size

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

        qty       = float(context.get_exec("quantity", 0.0))
        min_size  = float(context.get_limit("min_order_size", self._min))
        max_size  = float(context.get_limit("max_order_size", self._max))

        if qty < min_size:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Order size {qty} is below minimum {min_size}.",
                reason="order_too_small",
                metadata={"quantity": qty, "min_size": min_size},
            )

        if qty > max_size:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Order size {qty} exceeds maximum {max_size}.",
                reason="order_too_large",
                metadata={"quantity": qty, "max_size": max_size},
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Order size {qty} within bounds [{min_size}, {max_size}].",
        )
