"""iios/execution/risk/rules/rule_result.py
==================================================
RuleResult — the immutable result of a single rule evaluation.

Also provides ``to_engine_result()`` for M2 bridge compatibility.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    BLOCKING_OUTCOMES,
    PASSING_OUTCOMES,
    WARNING_OUTCOMES,
    RuleOutcome,
)
from .rule_category import RuleCategory


@dataclass(frozen=True)
class RuleResult:
    """
    Immutable result produced by a single risk rule evaluation.

    Rules return this object from ``evaluate()``.
    The executor collects results and the manager aggregates them.
    """

    rule_id:    str
    rule_name:  str
    category:   RuleCategory
    outcome:    RuleOutcome
    message:    str
    reason:     str
    elapsed_ms: float
    evaluated_at: float = field(default_factory=time.time)
    metadata:   Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def passed(self) -> bool:
        return self.outcome in PASSING_OUTCOMES

    @property
    def blocked(self) -> bool:
        return self.outcome in BLOCKING_OUTCOMES

    @property
    def warned(self) -> bool:
        return self.outcome in WARNING_OUTCOMES

    @property
    def failed(self) -> bool:
        return self.outcome == RuleOutcome.FAILED

    @property
    def skipped(self) -> bool:
        return self.outcome == RuleOutcome.SKIPPED

    @property
    def override_required(self) -> bool:
        return self.outcome == RuleOutcome.OVERRIDE_REQUIRED

    # ── M2 Engine bridge ──────────────────────────────────────────────────────

    def to_engine_result(self) -> Any:
        """
        Convert to M2 ``iios.execution.risk.engine.RuleResult``.

        Used by ``RuleEngineAdapter`` to bridge M3 rules into the M2 engine.
        """
        from iios.execution.risk.engine import (
            RuleResult as EngineRuleResult,
            RuleOutcome as EngineOutcome,
        )

        engine_outcome = _M3_TO_ENGINE_OUTCOME[self.outcome]
        meta = dict(self.metadata)
        if self.outcome == RuleOutcome.OVERRIDE_REQUIRED:
            meta["override_required"] = True

        return EngineRuleResult(
            rule_name=self.rule_name,
            rule_category=self.category.value,
            outcome=engine_outcome,
            message=self.message,
            elapsed_ms=self.elapsed_ms,
            metadata=meta,
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":      self.rule_id,
            "rule_name":    self.rule_name,
            "category":     self.category.value,
            "outcome":      self.outcome.value,
            "message":      self.message,
            "reason":       self.reason,
            "elapsed_ms":   self.elapsed_ms,
            "evaluated_at": self.evaluated_at,
            "metadata":     dict(self.metadata),
        }


# ── Outcome mapping (M3 → M2) ─────────────────────────────────────────────────

def _lazy_engine_outcomes():
    from iios.execution.risk.engine import RuleOutcome as EO
    return {
        RuleOutcome.PASS:              EO.PASSED,
        RuleOutcome.WARNING:           EO.WARNING,
        RuleOutcome.BLOCK:             EO.BLOCKED,
        RuleOutcome.OVERRIDE_REQUIRED: EO.WARNING,
        RuleOutcome.SKIPPED:           EO.SKIPPED,
        RuleOutcome.FAILED:            EO.ERROR,
    }


class _LazyOutcomeMap:
    _cache: dict | None = None

    def __getitem__(self, key: RuleOutcome):
        if self._cache is None:
            self._cache = _lazy_engine_outcomes()
        return self._cache[key]


_M3_TO_ENGINE_OUTCOME = _LazyOutcomeMap()


# ── Convenience constructors ──────────────────────────────────────────────────

def make_pass_result(
    rule_id:    str,
    rule_name:  str,
    category:   RuleCategory,
    elapsed_ms: float,
    *,
    message:  str = "Rule passed.",
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id, rule_name=rule_name, category=category,
        outcome=RuleOutcome.PASS, message=message, reason=reason,
        elapsed_ms=elapsed_ms, metadata=metadata or {},
    )


def make_warning_result(
    rule_id:    str,
    rule_name:  str,
    category:   RuleCategory,
    elapsed_ms: float,
    *,
    message:  str,
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id, rule_name=rule_name, category=category,
        outcome=RuleOutcome.WARNING, message=message, reason=reason,
        elapsed_ms=elapsed_ms, metadata=metadata or {},
    )


def make_block_result(
    rule_id:    str,
    rule_name:  str,
    category:   RuleCategory,
    elapsed_ms: float,
    *,
    message:  str,
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id, rule_name=rule_name, category=category,
        outcome=RuleOutcome.BLOCK, message=message, reason=reason,
        elapsed_ms=elapsed_ms, metadata=metadata or {},
    )


def make_skip_result(
    rule_id:    str,
    rule_name:  str,
    category:   RuleCategory,
    elapsed_ms: float,
    *,
    message:  str = "Rule skipped (not applicable).",
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id, rule_name=rule_name, category=category,
        outcome=RuleOutcome.SKIPPED, message=message, reason=reason,
        elapsed_ms=elapsed_ms, metadata=metadata or {},
    )


def make_failed_result(
    rule_id:    str,
    rule_name:  str,
    category:   RuleCategory,
    elapsed_ms: float,
    *,
    message:  str,
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id, rule_name=rule_name, category=category,
        outcome=RuleOutcome.FAILED, message=message, reason=reason,
        elapsed_ms=elapsed_ms, metadata=metadata or {},
    )


def make_override_required_result(
    rule_id:    str,
    rule_name:  str,
    category:   RuleCategory,
    elapsed_ms: float,
    *,
    message:  str,
    reason:   str = "",
    metadata: Dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id, rule_name=rule_name, category=category,
        outcome=RuleOutcome.OVERRIDE_REQUIRED, message=message, reason=reason,
        elapsed_ms=elapsed_ms, metadata=metadata or {},
    )
