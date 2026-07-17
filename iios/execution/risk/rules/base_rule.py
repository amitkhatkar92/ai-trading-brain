"""iios/execution/risk/rules/base_rule.py
==================================================
BaseRule — abstract base class for all execution risk rules.

Every rule in the framework (built-in or plugin) must extend this class.
BaseRule provides:
  * Structured rule identity (rule_id, rule_name, category, priority)
  * Lifecycle hooks (enable / disable)
  * Last-result caching
  * Per-rule statistics
  * M2 RiskEngine bridge (RuleEngineAdapter)

Non-responsibilities
--------------------
* BaseRule does NOT execute trades.
* BaseRule does NOT communicate with brokers.
* BaseRule does NOT modify positions.
* Rules return results ONLY.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .constants import RuleOutcome
from .rule_category import RuleCategory
from .rule_context import RuleContext, make_rule_context_from_engine
from .rule_priority import RulePriority
from .rule_result import (
    RuleResult,
    make_failed_result,
    make_skip_result,
)


class BaseRule(ABC):
    """
    Abstract base class for all IIOS execution risk rules.

    Subclasses MUST implement
    -------------------------
    * ``rule_id``   — unique string identifier
    * ``rule_name`` — human-readable name
    * ``category``  — RuleCategory
    * ``priority``  — RulePriority or int (default NORMAL)
    * ``_evaluate`` — core evaluation logic → returns RuleResult

    Subclasses MAY override
    -----------------------
    * ``is_applicable``   — return False to skip this rule for certain requests
    * ``validate_context`` — pre-evaluation validation
    * ``metadata``         — static rule metadata for observability
    """

    def __init__(self) -> None:
        self._enabled:     bool                 = True
        self._last_result: Optional[RuleResult] = None

    # ── Abstract interface ────────────────────────────────────────────────────

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Globally unique identifier for this rule (e.g., 'exposure_v1')."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Human-readable name (e.g., 'Exposure Limit Rule')."""

    @abstractmethod
    def category(self) -> RuleCategory:
        """Risk category this rule evaluates."""

    def priority(self) -> RulePriority:
        """Execution priority. Override to change from default NORMAL."""
        return RulePriority.NORMAL

    @abstractmethod
    def _evaluate(self, context: RuleContext) -> RuleResult:
        """
        Core evaluation logic.

        Implementations MUST:
        * Return a ``RuleResult`` — never raise.
        * Catch all internal exceptions and return FAILED result.
        * Not perform IO, broker calls, or order execution.
        """

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def enabled(self) -> bool:
        """True if this rule is active and should be evaluated."""
        return self._enabled

    def enable(self) -> None:
        """Enable this rule."""
        self._enabled = True

    def disable(self) -> None:
        """Disable this rule — it will be skipped by the executor."""
        self._enabled = False

    # ── Optional overrides ────────────────────────────────────────────────────

    def is_applicable(self, context: RuleContext) -> bool:
        """
        Return True if this rule applies to *context*.

        Default: True.  Override to filter by category, order type, etc.
        """
        return True

    def validate_context(self, context: RuleContext) -> Optional[str]:
        """
        Pre-evaluation validation.

        Return an error message string if the context is invalid for
        this rule, or None to proceed.
        Override for custom pre-checks.
        """
        return None

    def metadata(self) -> Dict[str, Any]:
        """Static metadata for observability / configuration."""
        return {
            "rule_id":    self.rule_id,
            "rule_name":  self.rule_name,
            "category":   self.category().value,
            "priority":   int(self.priority()),
            "enabled":    self._enabled,
            "version":    getattr(self, "_version", "1.0.0"),
        }

    # ── Public evaluate ───────────────────────────────────────────────────────

    def evaluate(self, context: RuleContext) -> RuleResult:
        """
        Evaluate the rule against *context*.

        Handles:
        * Disabled rules → SKIPPED
        * ``is_applicable`` → SKIPPED if False
        * ``validate_context`` → FAILED if error returned
        * Wraps ``_evaluate`` exceptions → FAILED result
        """
        t0 = time.time()

        if not self._enabled:
            result = make_skip_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=0.0,
                message="Rule is disabled.",
            )
            self._last_result = result
            return result

        if not self.is_applicable(context):
            result = make_skip_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=0.0,
                message="Rule not applicable to this context.",
            )
            self._last_result = result
            return result

        validation_error = self.validate_context(context)
        if validation_error:
            elapsed_ms = (time.time() - t0) * 1_000.0
            result = make_failed_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed_ms,
                message=f"Context validation failed: {validation_error}",
                reason=validation_error,
            )
            self._last_result = result
            return result

        try:
            result = self._evaluate(context)
        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1_000.0
            result = make_failed_result(
                self.rule_id, self.rule_name, self.category(),
                elapsed_ms=elapsed_ms,
                message=f"Rule raised exception: {exc}",
                reason=str(exc),
            )

        self._last_result = result
        return result

    def result(self) -> Optional[RuleResult]:
        """Return the last evaluation result, or None if never evaluated."""
        return self._last_result

    # ── M2 RiskEngine bridge ──────────────────────────────────────────────────
    # These properties satisfy M2's RiskRuleProtocol if rules are wrapped
    # in RuleEngineAdapter.

    @property
    def risk_category(self):
        """M2 bridge — maps M3 category to M1 RiskCategory."""
        return self.category().to_risk_category()


# ── M2 Engine Adapter ─────────────────────────────────────────────────────────

class RuleEngineAdapter:
    """
    Adapter that wraps a ``BaseRule`` to satisfy M2 ``RiskRuleProtocol``.

    Use this when registering M3 rules with the M2 ``RiskEngine``:

        engine.register_rule(RuleEngineAdapter(my_rule))
    """

    def __init__(self, rule: BaseRule) -> None:
        self._rule = rule

    # ── M2 RiskRuleProtocol ───────────────────────────────────────────────────

    @property
    def rule_name(self) -> str:
        return self._rule.rule_name

    @property
    def risk_category(self):
        return self._rule.category().to_risk_category()

    def is_applicable(self, request: Any) -> bool:
        from .rule_context import make_rule_context_from_engine
        try:
            ctx = make_rule_context_from_engine(request, request)
            return self._rule.enabled() and self._rule.is_applicable(ctx)
        except Exception:
            return self._rule.enabled()

    def evaluate(self, request: Any, eval_context: Any) -> Any:
        ctx = make_rule_context_from_engine(request, eval_context)
        result = self._rule.evaluate(ctx)
        return result.to_engine_result()

    # ── Delegation ────────────────────────────────────────────────────────────

    @property
    def wrapped_rule(self) -> BaseRule:
        return self._rule
