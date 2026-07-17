"""iios/execution/monitoring/alerts/alert_policy.py
==================================================
AlertPolicy — immutable alert firing policy configuration.
PolicyEvaluator — stateful policy evaluation engine per rule.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    AlertPolicyType,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_MAX_ESCALATIONS,
)


# ── Policy configuration DTO (immutable) ──────────────────────────────────────

@dataclass(frozen=True)
class AlertPolicy:
    """
    Immutable configuration for how and when an alert should fire.

    Fields
    ------
    policy_id            : unique ID for this policy
    policy_type          : evaluation strategy
    consecutive_failures : for CONSECUTIVE_FAILURE — number of consecutive
                           condition hits required before firing
    window_seconds       : for ROLLING_WINDOW — size of the rolling window
    min_hits_in_window   : for ROLLING_WINDOW — minimum condition hits in
                           the window required to fire
    duration_seconds     : for DURATION_THRESHOLD — condition must hold for
                           at least this many seconds before firing
    failure_rate         : for RATE_THRESHOLD — fraction of evaluations that
                           must be failures in the window
    cooldown_seconds     : suppress duplicate alerts for this period after a
                           previous alert fired for the same rule
    max_escalations      : maximum number of automatic escalations
    description          : human-readable description
    """

    policy_id:            str
    policy_type:          AlertPolicyType

    consecutive_failures: int   = 1
    window_seconds:       float = 60.0
    min_hits_in_window:   int   = 1
    duration_seconds:     float = 0.0
    failure_rate:         float = 0.5
    cooldown_seconds:     float = DEFAULT_COOLDOWN_SECONDS
    max_escalations:      int   = DEFAULT_MAX_ESCALATIONS
    description:          str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":            self.policy_id,
            "policy_type":          self.policy_type.value,
            "consecutive_failures": self.consecutive_failures,
            "window_seconds":       self.window_seconds,
            "min_hits_in_window":   self.min_hits_in_window,
            "duration_seconds":     self.duration_seconds,
            "failure_rate":         self.failure_rate,
            "cooldown_seconds":     self.cooldown_seconds,
            "max_escalations":      self.max_escalations,
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_alert_policy(
    policy_type: AlertPolicyType,
    *,
    consecutive_failures: int          = 1,
    window_seconds:       float        = 60.0,
    min_hits_in_window:   int          = 1,
    duration_seconds:     float        = 0.0,
    failure_rate:         float        = 0.5,
    cooldown_seconds:     float        = DEFAULT_COOLDOWN_SECONDS,
    max_escalations:      int          = DEFAULT_MAX_ESCALATIONS,
    description:          str          = "",
    policy_id:            Optional[str] = None,
) -> AlertPolicy:
    return AlertPolicy(
        policy_id            = policy_id or str(uuid.uuid4()),
        policy_type          = policy_type,
        consecutive_failures = consecutive_failures,
        window_seconds       = window_seconds,
        min_hits_in_window   = min_hits_in_window,
        duration_seconds     = duration_seconds,
        failure_rate         = failure_rate,
        cooldown_seconds     = cooldown_seconds,
        max_escalations      = max_escalations,
        description          = description,
    )


# ── Stateful policy evaluator ─────────────────────────────────────────────────

@dataclass
class _PolicyState:
    """Mutable per-rule state tracked by PolicyEvaluator."""
    consecutive_count:  int              = 0
    window_hits:        List[float]      = field(default_factory=list)  # timestamps
    condition_start:    Optional[float]  = None
    last_fired_at:      Optional[float]  = None
    evaluation_history: List[bool]       = field(default_factory=list)  # for rate


class PolicyEvaluator:
    """
    Stateful evaluator for a single AlertPolicy.

    Thread-safe.  One instance is created per registered rule.
    """

    def __init__(self, policy: AlertPolicy) -> None:
        self._policy = policy
        self._state  = _PolicyState()
        self._lock   = threading.RLock()  # re-entrant: should_fire() calls in_cooldown()

    @property
    def policy(self) -> AlertPolicy:
        return self._policy

    def should_fire(self, condition_met: bool, now: Optional[float] = None) -> bool:
        """
        Update internal state and return whether an alert should fire.

        Returns ``True`` at most once per cooldown period.
        """
        if now is None:
            now = time.time()

        with self._lock:
            # Always update state regardless of policy type
            self._update_state(condition_met, now)

            # Check cooldown — never fire twice in the cooldown window
            if self.in_cooldown(now):
                return False

            result = self._evaluate(condition_met, now)
            if result:
                self._state.last_fired_at = now
                # Reset consecutive count after firing
                if self._policy.policy_type == AlertPolicyType.CONSECUTIVE_FAILURE:
                    self._state.consecutive_count = 0
            return result

    def in_cooldown(self, now: Optional[float] = None) -> bool:
        """Return ``True`` if the rule is still in its cooldown period."""
        if now is None:
            now = time.time()
        with self._lock:
            if self._state.last_fired_at is None:
                return False
            return (now - self._state.last_fired_at) < self._policy.cooldown_seconds

    def reset(self) -> None:
        """Reset all state (e.g. when alert is resolved)."""
        with self._lock:
            self._state = _PolicyState()

    # ── Private ───────────────────────────────────────────────────────────────

    def _update_state(self, condition_met: bool, now: float) -> None:
        """Update mutable state based on condition outcome."""
        p = self._policy

        # Consecutive count
        if condition_met:
            self._state.consecutive_count += 1
        else:
            self._state.consecutive_count = 0

        # Rolling window: prune old hits, add new if condition met
        cutoff = now - p.window_seconds if p.window_seconds > 0 else 0.0
        self._state.window_hits = [t for t in self._state.window_hits if t >= cutoff]
        if condition_met:
            self._state.window_hits.append(now)

        # Duration: track when condition first became True
        if condition_met:
            if self._state.condition_start is None:
                self._state.condition_start = now
        else:
            self._state.condition_start = None

        # Rate history: bounded at 1000 to prevent unbounded growth
        self._state.evaluation_history.append(condition_met)
        if len(self._state.evaluation_history) > 1_000:
            self._state.evaluation_history = self._state.evaluation_history[-1_000:]

    def _evaluate(self, condition_met: bool, now: float) -> bool:
        """Apply policy logic to determine if alert should fire."""
        p    = self._policy
        ptype = p.policy_type

        if ptype == AlertPolicyType.IMMEDIATE:
            return condition_met

        if ptype == AlertPolicyType.CONSECUTIVE_FAILURE:
            return (
                condition_met
                and self._state.consecutive_count >= max(1, p.consecutive_failures)
            )

        if ptype == AlertPolicyType.ROLLING_WINDOW:
            return len(self._state.window_hits) >= max(1, p.min_hits_in_window)

        if ptype == AlertPolicyType.RATE_THRESHOLD:
            hist = self._state.evaluation_history
            if not hist:
                return False
            rate = sum(1 for v in hist if v) / len(hist)
            return rate >= p.failure_rate

        if ptype == AlertPolicyType.DURATION_THRESHOLD:
            start = self._state.condition_start
            if start is None or not condition_met:
                return False
            return (now - start) >= p.duration_seconds

        if ptype in (AlertPolicyType.COMPOSITE, AlertPolicyType.CUSTOM):
            # Default: fire immediately — callers override via subclass
            return condition_met

        return condition_met  # fallback


# ── Pre-built policy factories ────────────────────────────────────────────────

def make_immediate_policy(*, cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS) -> AlertPolicy:
    """Fire on first condition breach."""
    return make_alert_policy(
        AlertPolicyType.IMMEDIATE,
        cooldown_seconds=cooldown_seconds,
    )


def make_consecutive_policy(
    n: int,
    *,
    cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
) -> AlertPolicy:
    """Fire after N consecutive breaches."""
    return make_alert_policy(
        AlertPolicyType.CONSECUTIVE_FAILURE,
        consecutive_failures=n,
        cooldown_seconds=cooldown_seconds,
    )


def make_rolling_window_policy(
    window_seconds:     float,
    min_hits_in_window: int,
    *,
    cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
) -> AlertPolicy:
    """Fire after min_hits_in_window breaches within window_seconds."""
    return make_alert_policy(
        AlertPolicyType.ROLLING_WINDOW,
        window_seconds=window_seconds,
        min_hits_in_window=min_hits_in_window,
        cooldown_seconds=cooldown_seconds,
    )
