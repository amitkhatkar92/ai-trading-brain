"""iios/decision_policies/rules/rule.py — Abstract Rule base + concrete implementations."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable

from ..policy_constants import DEFAULT_RULE_PRIORITY, RuleStatus, RuleType
from ..policy_context import EvaluationContext
from .rule_result import RuleResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_result(
    rule:   "Rule",
    status: RuleStatus,
    reason: str,
    t0:     float,
    score:  float | None = None,
) -> RuleResult:
    if score is None:
        score = (
            1.0 if status in (RuleStatus.PASS, RuleStatus.SKIP)
            else 0.5 if status == RuleStatus.WARN
            else 0.0
        )
    return RuleResult(
        rule_id     = rule.rule_id,
        rule_name   = rule.name,
        rule_type   = rule.rule_type,
        status      = status,
        reason      = reason,
        score       = score,
        duration_ms = (time.perf_counter() - t0) * 1_000,
    )


# ── Abstract base ─────────────────────────────────────────────────────────────

class Rule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def rule_type(self) -> RuleType:
        return RuleType.STATIC

    @property
    def priority(self) -> int:
        return DEFAULT_RULE_PRIORITY

    @property
    def mandatory(self) -> bool:
        return True

    @property
    def enabled(self) -> bool:
        return True

    @property
    def dependencies(self) -> list[str]:
        return []

    @property
    def tags(self) -> list[str]:
        return []

    def is_applicable(self, context: EvaluationContext) -> bool:
        return self.enabled

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> RuleResult: ...

    def to_dict(self) -> dict:
        return {
            "rule_id":   self.rule_id,
            "name":      self.name,
            "rule_type": self.rule_type.value,
            "priority":  self.priority,
            "mandatory": self.mandatory,
            "enabled":   self.enabled,
            "tags":      self.tags,
        }


# ── StaticRule ────────────────────────────────────────────────────────────────

class StaticRule(Rule):
    """Rule backed by a fixed evaluator callable."""

    def __init__(
        self,
        rule_id:      str,
        name:         str,
        evaluator:    Callable[[EvaluationContext], tuple[RuleStatus, str]],
        *,
        priority:     int = DEFAULT_RULE_PRIORITY,
        mandatory:    bool = True,
        enabled:      bool = True,
        dependencies: list[str] | None = None,
        condition:    Callable[[EvaluationContext], bool] | None = None,
        tags:         list[str] | None = None,
    ) -> None:
        self._rule_id    = rule_id
        self._name       = name
        self._evaluator  = evaluator
        self._priority   = priority
        self._mandatory  = mandatory
        self._enabled    = enabled
        self._deps       = dependencies or []
        self._condition  = condition
        self._tags       = tags or []

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def rule_type(self) -> RuleType:
        return RuleType.STATIC

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def dependencies(self) -> list[str]:
        return list(self._deps)

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def is_applicable(self, context: EvaluationContext) -> bool:
        if not self._enabled:
            return False
        if self._condition is not None:
            return bool(self._condition(context))
        return True

    def evaluate(self, context: EvaluationContext) -> RuleResult:
        t0 = time.perf_counter()
        if not self.is_applicable(context):
            return _make_result(self, RuleStatus.SKIP, "not applicable", t0)
        try:
            status, reason = self._evaluator(context)
        except Exception as exc:  # noqa: BLE001
            return _make_result(self, RuleStatus.ERROR, str(exc), t0, score=0.0)
        return _make_result(self, status, reason, t0)


# ── DynamicRule ───────────────────────────────────────────────────────────────

class DynamicRule(Rule):
    """Rule whose evaluator callable can be swapped at runtime (thread-safe)."""

    def __init__(
        self,
        rule_id:   str,
        name:      str,
        evaluator: Callable[[EvaluationContext], tuple[RuleStatus, str]],
        *,
        priority:  int = DEFAULT_RULE_PRIORITY,
        mandatory: bool = True,
        tags:      list[str] | None = None,
    ) -> None:
        import threading
        self._rule_id   = rule_id
        self._name      = name
        self._evaluator = evaluator
        self._priority  = priority
        self._mandatory = mandatory
        self._tags      = tags or []
        self._lock      = threading.Lock()

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def rule_type(self) -> RuleType:
        return RuleType.DYNAMIC

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    @property
    def tags(self) -> list[str]:
        return list(self._tags)

    def update_evaluator(
        self,
        evaluator: Callable[[EvaluationContext], tuple[RuleStatus, str]],
    ) -> None:
        with self._lock:
            self._evaluator = evaluator

    def evaluate(self, context: EvaluationContext) -> RuleResult:
        t0 = time.perf_counter()
        with self._lock:
            fn = self._evaluator
        try:
            status, reason = fn(context)
        except Exception as exc:  # noqa: BLE001
            return _make_result(self, RuleStatus.ERROR, str(exc), t0, score=0.0)
        return _make_result(self, status, reason, t0)


# ── ConditionalRule ───────────────────────────────────────────────────────────

class ConditionalRule(Rule):
    """Evaluates inner rule only when condition is true; otherwise SKIPs."""

    def __init__(
        self,
        rule_id:    str,
        name:       str,
        condition:  Callable[[EvaluationContext], bool],
        inner_rule: Rule,
        *,
        priority:   int  = DEFAULT_RULE_PRIORITY,
        mandatory:  bool = True,
    ) -> None:
        self._rule_id   = rule_id
        self._name      = name
        self._condition = condition
        self._inner     = inner_rule
        self._priority  = priority
        self._mandatory = mandatory

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def rule_type(self) -> RuleType:
        return RuleType.CONDITIONAL

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    def is_applicable(self, context: EvaluationContext) -> bool:
        return bool(self._condition(context))

    def evaluate(self, context: EvaluationContext) -> RuleResult:
        t0 = time.perf_counter()
        if not self._condition(context):
            return _make_result(self, RuleStatus.SKIP, "condition not met", t0)
        inner = self._inner.evaluate(context)
        return RuleResult(
            rule_id     = self._rule_id,
            rule_name   = self._name,
            rule_type   = self.rule_type,
            status      = inner.status,
            reason      = inner.reason,
            score       = inner.score,
            duration_ms = (time.perf_counter() - t0) * 1_000,
        )


# ── CompositeRule ─────────────────────────────────────────────────────────────

class CompositeRule(Rule):
    """Composes multiple child rules with AND / OR semantics."""

    def __init__(
        self,
        rule_id:       str,
        name:          str,
        children:      list[Rule],
        *,
        operator:      str  = "and",   # "and" | "or"
        priority:      int  = DEFAULT_RULE_PRIORITY,
        mandatory:     bool = True,
        short_circuit: bool = True,
    ) -> None:
        self._rule_id   = rule_id
        self._name      = name
        self._children  = list(children)
        self._operator  = operator.lower()
        self._priority  = priority
        self._mandatory = mandatory
        self._short     = short_circuit

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def rule_type(self) -> RuleType:
        return RuleType.COMPOSITE

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    def evaluate(self, context: EvaluationContext) -> RuleResult:
        t0      = time.perf_counter()
        results = []

        for child in self._children:
            r = child.evaluate(context)
            results.append(r)
            if self._short:
                if self._operator == "and" and r.failed:
                    return _make_result(
                        self, RuleStatus.FAIL,
                        f"AND: {child.rule_id!r} failed — {r.reason}", t0,
                    )
                if self._operator == "or" and r.passed:
                    return _make_result(
                        self, RuleStatus.PASS,
                        f"OR: {child.rule_id!r} passed", t0,
                    )

        if self._operator == "and":
            failed = [r for r in results if r.failed]
            if failed:
                reasons = "; ".join(r.reason for r in failed)
                return _make_result(self, RuleStatus.FAIL, f"AND failed: {reasons}", t0)
            return _make_result(self, RuleStatus.PASS, "AND all passed", t0)

        # OR
        if any(r.passed for r in results):
            return _make_result(self, RuleStatus.PASS, "OR: at least one passed", t0)
        return _make_result(self, RuleStatus.FAIL, "OR: no children passed", t0)


# ── PriorityRule ──────────────────────────────────────────────────────────────

class PriorityRule(Rule):
    """Wraps another rule with an explicit priority override."""

    def __init__(self, inner: Rule, priority: int) -> None:
        self._inner    = inner
        self._priority = priority

    @property
    def rule_id(self) -> str:
        return self._inner.rule_id

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def rule_type(self) -> RuleType:
        return RuleType.PRIORITY

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def mandatory(self) -> bool:
        return self._inner.mandatory

    @property
    def tags(self) -> list[str]:
        return self._inner.tags

    def evaluate(self, context: EvaluationContext) -> RuleResult:
        return self._inner.evaluate(context)
