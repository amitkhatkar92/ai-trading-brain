"""iios/execution/risk/rules/rule_manager.py
==================================================
RuleManager — LifecycleAwareMixin coordinator for the Rules Framework.

The manager is the single public interface to rule registration,
evaluation, and observability within the Rules Framework.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

import copy
import threading
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .base_rule import BaseRule
from .constants import (
    DEFAULT_EXECUTION_TIMEOUT_MS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RULES,
    MANAGER_SYSTEM_ID,
    ExecutionMode,
    VERSION,
)
from .exceptions import RuleNotRunningError
from .rule_category import RuleCategory
from .rule_context import RuleContext
from .rule_events import RuleEvent
from .rule_executor import RuleExecutor
from .rule_factory import RuleFactory
from .rule_history import RuleHistory
from .rule_registry import RuleRegistry
from .rule_result import RuleResult
from .rule_statistics import FrameworkStatistics

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


class RuleManager(LifecycleAwareMixin):
    """
    High-level coordinator for the Execution Risk Rules Framework.

    Owns the rule registry, executor, history, and statistics.
    Provides the single public interface for rule management and evaluation.

    Thread safety
    -------------
    All public methods are thread-safe.
    """

    def __init__(
        self,
        max_rules:         int   = DEFAULT_MAX_RULES,
        max_history:       int   = DEFAULT_MAX_HISTORY,
        timeout_ms:        float = DEFAULT_EXECUTION_TIMEOUT_MS,
        default_mode:      ExecutionMode = ExecutionMode.PRIORITY_ORDERED,
    ) -> None:
        super().__init__()
        self._max_rules    = max_rules
        self._default_mode = default_mode
        self._registry     = RuleRegistry(max_rules=max_rules)
        self._statistics   = FrameworkStatistics()
        self._history      = RuleHistory(max_size=max_history)
        self._events:      List[RuleEvent] = []
        self._lock         = threading.Lock()

        # Executor shares the statistics accumulator and event list
        self._executor = RuleExecutor(
            timeout_ms=timeout_ms,
            statistics=self._statistics,
            event_sink=self._events,
        )

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RuleNotRunningError()

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RuleManager started.", max_rules=self._max_rules)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("RuleManager stopped.", rule_count=self._registry.count)
        self._registry.stop()

    # ── Rule management ───────────────────────────────────────────────────────

    def register(self, rule: BaseRule) -> None:
        """Register a rule."""
        self._assert_running()
        self._registry.register(rule)

    def deregister(self, rule_id: str) -> None:
        """Remove a rule by ID."""
        self._assert_running()
        self._registry.deregister(rule_id)

    def enable_rule(self, rule_id: str) -> None:
        """Enable a previously disabled rule."""
        self._assert_running()
        self._registry.require(rule_id).enable()

    def disable_rule(self, rule_id: str) -> None:
        """Disable a rule without removing it from the registry."""
        self._assert_running()
        self._registry.require(rule_id).disable()

    def registered_rule_ids(self) -> List[str]:
        return [r.rule_id for r in self._registry.all()]

    @property
    def rule_count(self) -> int:
        return self._registry.count

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        context:       RuleContext,
        mode:          Optional[ExecutionMode] = None,
        evaluation_id: str = "",
    ) -> List[RuleResult]:
        """
        Evaluate all applicable rules against *context*.

        Parameters
        ----------
        context:       Evaluation context for this request.
        mode:          Override default execution mode.
        evaluation_id: Optional ID for event correlation.

        Returns
        -------
        List[RuleResult]
            One result per executed rule.  Disabled and non-applicable
            rules are excluded unless they produce SKIPPED results.
        """
        self._assert_running()
        exec_mode = mode or self._default_mode

        self._statistics.record_evaluation_started()

        rules = self._registry.enabled()

        results = self._executor.execute(
            rules=rules,
            context=context,
            mode=exec_mode,
            evaluation_id=evaluation_id,
        )

        for r in results:
            self._history.append(r)

        _log.debug(
            "Evaluation complete.",
            rules_executed=len(results),
            mode=exec_mode.value,
        )
        return results

    # ── Built-in rule helpers ─────────────────────────────────────────────────

    def register_all_builtins(self, **config) -> int:
        """
        Register all built-in rules with optional default configuration.

        Returns the number of rules registered.
        """
        self._assert_running()
        rules = RuleFactory.create_all_builtin_rules(**config)
        for rule in rules:
            self._registry.register(rule)
        return len(rules)

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> FrameworkStatistics:
        """Return a shallow copy of current framework statistics."""
        return copy.copy(self._statistics)

    def history(self) -> RuleHistory:
        """Return the rule history store."""
        return self._history

    def events(self) -> List[RuleEvent]:
        """Return all emitted events in order."""
        with self._lock:
            return list(self._events)

    def registry(self) -> RuleRegistry:
        """Return the underlying rule registry."""
        return self._registry
