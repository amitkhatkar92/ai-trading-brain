"""iios/execution/risk/rules/rule_executor.py
==================================================
RuleExecutor — execution engine for risk rule evaluation.

Supports:
  * Sequential execution (registration order)
  * Priority-ordered execution (highest priority first)
  * Conditional execution (stop on first BLOCK)
  * Per-rule execution timeout
  * Exception isolation (failed rule never stops others)

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import concurrent.futures
import time
import threading
from typing import Callable, List, Optional

from .base_rule import BaseRule
from .constants import (
    DEFAULT_EXECUTION_TIMEOUT_MS,
    EXECUTOR_SYSTEM_ID,
    ExecutionMode,
    RuleEventType,
    RuleOutcome,
)
from .exceptions import RuleTimeoutError
from .rule_context import RuleContext
from .rule_events import (
    RuleEvent,
    make_rule_blocked_event,
    make_rule_completed_event,
    make_rule_failed_event,
    make_rule_passed_event,
    make_rule_started_event,
    make_rule_warning_event,
)
from .rule_result import RuleResult, make_failed_result
from .rule_statistics import FrameworkStatistics


class RuleExecutor:
    """
    Executes registered risk rules against a ``RuleContext``.

    The executor is stateless with respect to rule storage; it receives
    the rule list from the manager on each call.

    Thread safety
    -------------
    Each ``execute_*`` call is independent.  Multiple threads may call
    the same executor concurrently.
    """

    def __init__(
        self,
        timeout_ms:  float = DEFAULT_EXECUTION_TIMEOUT_MS,
        statistics:  Optional[FrameworkStatistics] = None,
        event_sink:  Optional[List[RuleEvent]] = None,
    ) -> None:
        self._timeout_ms = max(1.0, timeout_ms)
        self._statistics = statistics
        self._event_sink = event_sink
        self._lock       = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def execute_sequential(
        self,
        rules:        List[BaseRule],
        context:      RuleContext,
        evaluation_id: str = "",
    ) -> List[RuleResult]:
        """Execute *rules* in order, collecting all results."""
        return self._run(rules, context, evaluation_id, stop_on_block=False)

    def execute_priority_ordered(
        self,
        rules:        List[BaseRule],
        context:      RuleContext,
        evaluation_id: str = "",
    ) -> List[RuleResult]:
        """Sort by priority (highest first) then execute."""
        sorted_rules = sorted(rules, key=lambda r: int(r.priority()), reverse=True)
        return self._run(sorted_rules, context, evaluation_id, stop_on_block=False)

    def execute_conditional(
        self,
        rules:        List[BaseRule],
        context:      RuleContext,
        evaluation_id: str = "",
    ) -> List[RuleResult]:
        """
        Sort by priority then execute — STOP immediately on first BLOCK.

        Remaining rules are NOT executed; their results are omitted.
        This mode is ideal for fail-fast safety checks.
        """
        sorted_rules = sorted(rules, key=lambda r: int(r.priority()), reverse=True)
        return self._run(sorted_rules, context, evaluation_id, stop_on_block=True)

    def execute(
        self,
        rules:        List[BaseRule],
        context:      RuleContext,
        mode:         ExecutionMode = ExecutionMode.SEQUENTIAL,
        evaluation_id: str = "",
    ) -> List[RuleResult]:
        """Unified execution entry point; delegates to mode-specific method."""
        if mode == ExecutionMode.SEQUENTIAL:
            return self.execute_sequential(rules, context, evaluation_id)
        if mode == ExecutionMode.PRIORITY_ORDERED:
            return self.execute_priority_ordered(rules, context, evaluation_id)
        if mode == ExecutionMode.CONDITIONAL:
            return self.execute_conditional(rules, context, evaluation_id)
        return self.execute_sequential(rules, context, evaluation_id)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(
        self,
        rules:        List[BaseRule],
        context:      RuleContext,
        evaluation_id: str,
        stop_on_block: bool,
    ) -> List[RuleResult]:
        results: List[RuleResult] = []

        for rule in rules:
            result = self._execute_one(rule, context, evaluation_id)
            results.append(result)

            if self._statistics:
                self._statistics.record_rule_result(
                    rule.rule_id, rule.rule_name,
                    result.elapsed_ms, result.outcome.value,
                )
            self._emit_outcome_event(result, evaluation_id)

            if stop_on_block and result.blocked:
                break

        return results

    def _execute_one(
        self,
        rule:          BaseRule,
        context:       RuleContext,
        evaluation_id: str,
    ) -> RuleResult:
        """Execute a single rule with timeout protection."""
        self._emit(make_rule_started_event(
            rule.rule_id, rule.rule_name, evaluation_id,
            category=rule.category().value,
        ))

        timeout_s = self._timeout_ms / 1_000.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(rule.evaluate, context)
            try:
                result: RuleResult = future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                result = make_failed_result(
                    rule.rule_id, rule.rule_name, rule.category(),
                    elapsed_ms=self._timeout_ms,
                    message=f"Rule timed out after {self._timeout_ms:.1f} ms",
                    reason="timeout",
                )
            except Exception as exc:
                result = make_failed_result(
                    rule.rule_id, rule.rule_name, rule.category(),
                    elapsed_ms=0.0,
                    message=f"Rule executor error: {exc}",
                    reason=str(exc),
                )

        return result

    def _emit_outcome_event(self, result: RuleResult, evaluation_id: str) -> None:
        outcome = result.outcome
        if outcome == RuleOutcome.PASS:
            ev = make_rule_passed_event(result.rule_id, result.rule_name, evaluation_id)
        elif outcome in {RuleOutcome.WARNING, RuleOutcome.OVERRIDE_REQUIRED}:
            ev = make_rule_warning_event(result.rule_id, result.rule_name, evaluation_id)
        elif outcome == RuleOutcome.BLOCK:
            ev = make_rule_blocked_event(result.rule_id, result.rule_name, evaluation_id)
        elif outcome == RuleOutcome.FAILED:
            ev = make_rule_failed_event(
                result.rule_id, result.rule_name, evaluation_id,
                reason=result.reason,
            )
        else:  # SKIPPED
            ev = make_rule_completed_event(
                result.rule_id, result.rule_name, evaluation_id,
                outcome=result.outcome.value,
            )
        self._emit(ev)

    def _emit(self, event: RuleEvent) -> None:
        if self._event_sink is not None:
            with self._lock:
                self._event_sink.append(event)
