"""iios/execution/risk/rules/builtin/price_deviation_rule.py
Price deviation rule — checks order price vs reference price.
"""
from __future__ import annotations
import time
from ..base_rule import BaseRule
from ..rule_category import RuleCategory
from ..rule_context import RuleContext
from ..rule_priority import RulePriority
from ..rule_result import RuleResult, make_block_result, make_pass_result, make_warning_result

_RULE_ID   = "builtin:market:price_deviation_v1"
_RULE_NAME = "Price Deviation Rule"

_DEFAULT_MAX_DEVIATION_PCT  = 0.05   # ±5% → BLOCK
_DEFAULT_WARN_DEVIATION_PCT = 0.02   # ±2% → WARNING


class PriceDeviationRule(BaseRule):
    """
    Checks that the order price does not deviate excessively from
    a reference price (e.g., last trade price, VWAP).

    Context keys
    ------------
    execution_snapshot.price               float  Order price
    execution_snapshot.reference_price     float  Reference / benchmark price
    risk_limits.max_price_deviation_pct    float  Override max (default 0.05)
    risk_limits.warn_price_deviation_pct   float  Override warn (default 0.02)
    """

    _version = "1.0.0"

    def __init__(
        self,
        max_deviation_pct:  float = _DEFAULT_MAX_DEVIATION_PCT,
        warn_deviation_pct: float = _DEFAULT_WARN_DEVIATION_PCT,
    ) -> None:
        super().__init__()
        self._max_pct  = max_deviation_pct
        self._warn_pct = warn_deviation_pct

    @property
    def rule_id(self) -> str:
        return _RULE_ID

    @property
    def rule_name(self) -> str:
        return _RULE_NAME

    def category(self) -> RuleCategory:
        return RuleCategory.MARKET

    def priority(self) -> RulePriority:
        return RulePriority.NORMAL

    def _evaluate(self, context: RuleContext) -> RuleResult:
        t0 = time.time()
        elapsed = lambda: (time.time() - t0) * 1_000.0

        price     = float(context.get_exec("price", 0.0))
        ref_price = float(context.get_exec("reference_price", 0.0))
        max_pct   = float(context.get_limit("max_price_deviation_pct",  self._max_pct))
        warn_pct  = float(context.get_limit("warn_price_deviation_pct", self._warn_pct))

        if ref_price <= 0 or price <= 0:
            return make_pass_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message="Price deviation check skipped — price data not provided.",
            )

        deviation = abs(price - ref_price) / ref_price

        if deviation >= max_pct:
            return make_block_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=(
                    f"Price deviation {deviation:.2%} exceeds limit {max_pct:.2%}. "
                    f"Order: {price}, Reference: {ref_price}"
                ),
                reason="price_deviation_exceeded",
                metadata={"deviation": deviation, "max_deviation": max_pct,
                          "price": price, "reference_price": ref_price},
            )

        if deviation >= warn_pct:
            return make_warning_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed(),
                message=f"Price deviation {deviation:.2%} approaching limit {max_pct:.2%}.",
                reason="price_deviation_warning",
                metadata={"deviation": deviation},
            )

        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=elapsed(),
            message=f"Price deviation {deviation:.2%} within limit {max_pct:.2%}.",
        )
