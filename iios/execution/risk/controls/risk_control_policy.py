"""iios/execution/risk/controls/risk_control_policy.py
==================================================
Control Policies — convert rule results into ControlActions.

Policies are stateless.  They NEVER evaluate risk.  They ONLY
map pre-computed rule outcomes to an appropriate ControlAction.

Supported policies
------------------
SingleRulePolicy        — any BLOCK outcome → BLOCK (strictest)
MajorityPolicy          — majority vote of non-skipped results
HighestSeverityPolicy   — highest-priority action wins (default)
WeightedSeverityPolicy  — category-weighted sum of severity scores
EmergencyPolicy         — emergency-stop aware; delegates to Highest
ConfigurablePolicy      — wraps an arbitrary callable

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from .constants import (
    OUTCOME_TO_ACTION,
    ACTION_PRIORITY,
    ControlAction,
    PolicyType,
    highest_priority_action,
)
from .risk_control_context import ControlContext


# ── Base ──────────────────────────────────────────────────────────────────────

class BasePolicy(ABC):
    """Abstract base for all control policies."""

    @property
    @abstractmethod
    def policy_type(self) -> PolicyType:
        """Unique type identifier for this policy."""

    @abstractmethod
    def evaluate(
        self,
        rule_results: List[Any],
        context:      ControlContext,
    ) -> ControlAction:
        """
        Map rule results to a control action.

        Parameters
        ----------
        rule_results : List[RuleResult]   (M3 objects, typed Any)
        context      : ControlContext

        Returns
        -------
        ControlAction
        """

    @property
    def name(self) -> str:
        return self.policy_type.value

    @property
    def description(self) -> str:
        return f"Control policy: {self.policy_type.value}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _outcome_to_action(outcome_value: str) -> ControlAction:
    """Map a M3 RuleOutcome string value to a ControlAction."""
    return OUTCOME_TO_ACTION.get(outcome_value, ControlAction.BLOCK)


def _rule_action(rule_result: Any) -> ControlAction:
    """Derive the ControlAction implied by a single RuleResult."""
    outcome = getattr(rule_result, "outcome", None)
    if outcome is None:
        return ControlAction.BLOCK
    return _outcome_to_action(str(outcome.value) if hasattr(outcome, "value") else str(outcome))


def _non_skipped(rule_results: List[Any]) -> List[Any]:
    """Filter out SKIPPED results."""
    return [r for r in rule_results if not getattr(r, "skipped", False)]


# ── SingleRulePolicy ─────────────────────────────────────────────────────────

class SingleRulePolicy(BasePolicy):
    """
    Strictest policy: any BLOCK (or FAILED) outcome blocks execution.

    Decision table (evaluated in priority order):
      1. Emergency stop active        → EMERGENCY_STOP
      2. Any BLOCK or FAILED result   → BLOCK
      3. Any OVERRIDE_REQUIRED result → REQUIRE_OVERRIDE
      4. Any WARNING result           → ALLOW_WITH_WARNING
      5. All PASS / SKIPPED           → ALLOW
    """

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.SINGLE_RULE

    def evaluate(self, rule_results: List[Any], context: ControlContext) -> ControlAction:
        if context.emergency_stop_active:
            return ControlAction.EMERGENCY_STOP

        active = _non_skipped(rule_results)
        if not active:
            return ControlAction.ALLOW

        has_block    = any(getattr(r, "blocked", False) or getattr(r, "failed", False)
                          for r in active)
        has_override = any(getattr(r, "override_required", False) for r in active)
        has_warning  = any(getattr(r, "warned", False) for r in active)

        if has_block:
            return ControlAction.BLOCK
        if has_override:
            return ControlAction.REQUIRE_OVERRIDE
        if has_warning:
            return ControlAction.ALLOW_WITH_WARNING
        return ControlAction.ALLOW


# ── MajorityPolicy ───────────────────────────────────────────────────────────

class MajorityPolicy(BasePolicy):
    """
    Majority vote: if the pass fraction >= threshold → ALLOW,
    otherwise apply HighestSeverityPolicy to non-passing results.

    Default threshold: 0.50 (configurable).
    """

    def __init__(self, pass_threshold: float = 0.50) -> None:
        if not (0.0 < pass_threshold <= 1.0):
            raise ValueError(
                f"pass_threshold must be in (0, 1]; got {pass_threshold}"
            )
        self._threshold = pass_threshold
        self._fallback  = HighestSeverityPolicy()

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.MAJORITY

    def evaluate(self, rule_results: List[Any], context: ControlContext) -> ControlAction:
        if context.emergency_stop_active:
            return ControlAction.EMERGENCY_STOP

        active = _non_skipped(rule_results)
        if not active:
            return ControlAction.ALLOW

        pass_count = sum(1 for r in active if getattr(r, "passed", False))
        pass_frac  = pass_count / len(active)

        if pass_frac >= self._threshold:
            # Majority pass but still check for any warnings
            if any(getattr(r, "warned", False) for r in active):
                return ControlAction.ALLOW_WITH_WARNING
            return ControlAction.ALLOW

        # Majority not passing — fall back to highest severity
        return self._fallback.evaluate(rule_results, context)


# ── HighestSeverityPolicy ────────────────────────────────────────────────────

class HighestSeverityPolicy(BasePolicy):
    """
    Maps each rule outcome to a ControlAction and returns the
    highest-priority action across all results.  This is the default.
    """

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.HIGHEST_SEVERITY

    def evaluate(self, rule_results: List[Any], context: ControlContext) -> ControlAction:
        if context.emergency_stop_active:
            return ControlAction.EMERGENCY_STOP

        if not rule_results:
            return ControlAction.ALLOW

        actions = [_rule_action(r) for r in rule_results]
        return highest_priority_action(*actions)


# ── WeightedSeverityPolicy ───────────────────────────────────────────────────

class WeightedSeverityPolicy(BasePolicy):
    """
    Weighted-sum policy.

    Each rule's severity score is multiplied by its category weight.
    The total score drives the final action via configurable thresholds.

    Severity scores: ALLOW=0, ALLOW_WITH_WARNING=1, PAUSE=2, RETRY=2,
                     REQUIRE_OVERRIDE=3, CANCEL=4, BLOCK=5, EMERGENCY_STOP=10
    Default thresholds (total score):
      >= emergency_threshold → EMERGENCY_STOP
      >= block_threshold     → BLOCK
      >= override_threshold  → REQUIRE_OVERRIDE
      >= pause_threshold     → PAUSE
      >= warning_threshold   → ALLOW_WITH_WARNING
      else                   → ALLOW
    """

    _SEVERITY_SCORE: Dict[ControlAction, float] = {
        ControlAction.ALLOW:              0.0,
        ControlAction.ALLOW_WITH_WARNING: 1.0,
        ControlAction.RETRY:              2.0,
        ControlAction.PAUSE:              2.0,
        ControlAction.REQUIRE_OVERRIDE:   3.0,
        ControlAction.CANCEL:             4.0,
        ControlAction.BLOCK:              5.0,
        ControlAction.EMERGENCY_STOP:     10.0,
    }

    def __init__(
        self,
        category_weights:    Optional[Dict[str, float]] = None,
        emergency_threshold: float = 8.0,
        block_threshold:     float = 4.0,
        override_threshold:  float = 2.5,
        pause_threshold:     float = 1.5,
        warning_threshold:   float = 0.5,
    ) -> None:
        self._weights            = category_weights or {}
        self._emergency_threshold = emergency_threshold
        self._block_threshold     = block_threshold
        self._override_threshold  = override_threshold
        self._pause_threshold     = pause_threshold
        self._warning_threshold   = warning_threshold

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.WEIGHTED_SEVERITY

    def evaluate(self, rule_results: List[Any], context: ControlContext) -> ControlAction:
        if context.emergency_stop_active:
            return ControlAction.EMERGENCY_STOP

        if not rule_results:
            return ControlAction.ALLOW

        total_score = 0.0
        total_weight = 0.0

        for r in rule_results:
            action   = _rule_action(r)
            score    = self._SEVERITY_SCORE.get(action, 0.0)
            category = str(getattr(getattr(r, "category", None), "value", ""))
            weight   = self._weights.get(category, 1.0)
            total_score  += score * weight
            total_weight += weight

        if total_weight == 0:
            return ControlAction.ALLOW

        weighted_avg = total_score / total_weight

        if weighted_avg >= self._emergency_threshold:
            return ControlAction.EMERGENCY_STOP
        if weighted_avg >= self._block_threshold:
            return ControlAction.BLOCK
        if weighted_avg >= self._override_threshold:
            return ControlAction.REQUIRE_OVERRIDE
        if weighted_avg >= self._pause_threshold:
            return ControlAction.PAUSE
        if weighted_avg >= self._warning_threshold:
            return ControlAction.ALLOW_WITH_WARNING
        return ControlAction.ALLOW


# ── EmergencyPolicy ──────────────────────────────────────────────────────────

class EmergencyPolicy(BasePolicy):
    """
    Emergency-aware policy.

    Always returns EMERGENCY_STOP if:
      • context.emergency_stop_active is True, or
      • any rule result is BLOCK or FAILED

    Otherwise delegates to HighestSeverityPolicy.
    """

    def __init__(self) -> None:
        self._fallback = HighestSeverityPolicy()

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.EMERGENCY

    def evaluate(self, rule_results: List[Any], context: ControlContext) -> ControlAction:
        if context.emergency_stop_active:
            return ControlAction.EMERGENCY_STOP

        has_critical = any(
            getattr(r, "blocked", False) or getattr(r, "failed", False)
            for r in rule_results
        )
        if has_critical:
            return ControlAction.EMERGENCY_STOP

        return self._fallback.evaluate(rule_results, context)


# ── ConfigurablePolicy ───────────────────────────────────────────────────────

class ConfigurablePolicy(BasePolicy):
    """
    Wraps a callable that maps (rule_results, context) → ControlAction.

    Allows embedding arbitrary policy logic without subclassing BasePolicy.
    """

    def __init__(
        self,
        fn: Callable[[List[Any], ControlContext], ControlAction],
        *,
        description: str = "Configurable policy",
    ) -> None:
        self._fn          = fn
        self._description = description

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.CONFIGURABLE

    @property
    def description(self) -> str:
        return self._description

    def evaluate(self, rule_results: List[Any], context: ControlContext) -> ControlAction:
        return self._fn(rule_results, context)
