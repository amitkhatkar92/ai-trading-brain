"""
capability_quota.py -- iios.ai.capability.policy
==================================================
:class:`QuotaEntry`    — per (principal, capability) quota configuration.
:class:`QuotaManager`  — thread-safe quota enforcement.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..exceptions.capability_exceptions import AICapabilityQuotaExceededError


@dataclass(frozen=True)
class QuotaEntry:
    """Quota configuration for a (principal_id, capability_id) pair."""

    principal_id:       str
    capability_id:      str
    max_per_hour:       int    # 0 = unlimited
    max_per_day:        int    # 0 = unlimited


class _UsageCounter:
    """Mutable execution counter for a single quota entry."""

    def __init__(self) -> None:
        self.hour_count: int   = 0
        self.day_count:  int   = 0
        self.last_hour:  float = 0.0
        self.last_day:   float = 0.0

    def _reset_if_needed(self) -> None:
        now = time.time()
        # Reset hourly
        if now - self.last_hour >= 3600:
            self.hour_count = 0
            self.last_hour  = now
        # Reset daily
        if now - self.last_day >= 86400:
            self.day_count = 0
            self.last_day  = now

    def increment(self) -> None:
        self._reset_if_needed()
        self.hour_count += 1
        self.day_count  += 1

    def snapshot(self) -> Dict[str, int]:
        self._reset_if_needed()
        return {"hour_count": self.hour_count, "day_count": self.day_count}


class QuotaManager:
    """
    Thread-safe quota enforcement for capability executions.

    Usage::

        qm = QuotaManager()
        qm.set_quota("agent_x", "cap_id", max_per_hour=100, max_per_day=500)
        qm.record_execution("agent_x", "cap_id")   # raises on excess
    """

    def __init__(self) -> None:
        self._lock:    threading.Lock                           = threading.Lock()
        self._quotas:  Dict[Tuple[str, str], QuotaEntry]       = {}
        self._usage:   Dict[Tuple[str, str], _UsageCounter]    = {}

    def set_quota(
        self,
        principal_id:  str,
        capability_id: str,
        max_per_hour:  int = 0,
        max_per_day:   int = 0,
    ) -> None:
        key = (principal_id, capability_id)
        with self._lock:
            self._quotas[key] = QuotaEntry(
                principal_id  = principal_id,
                capability_id = capability_id,
                max_per_hour  = max_per_hour,
                max_per_day   = max_per_day,
            )
            if key not in self._usage:
                self._usage[key] = _UsageCounter()

    def record_execution(self, principal_id: str, capability_id: str) -> None:
        """
        Record one execution and raise if any quota is exceeded.

        Raises :class:`AICapabilityQuotaExceededError` if the hourly or
        daily limit would be breached.
        """
        key = (principal_id, capability_id)
        with self._lock:
            quota   = self._quotas.get(key)
            counter = self._usage.setdefault(key, _UsageCounter())
            counter._reset_if_needed()

            if quota:
                if quota.max_per_hour > 0 and counter.hour_count >= quota.max_per_hour:
                    raise AICapabilityQuotaExceededError(
                        f"Hourly quota ({quota.max_per_hour}) exceeded for "
                        f"'{principal_id}' on '{capability_id}'"
                    )
                if quota.max_per_day > 0 and counter.day_count >= quota.max_per_day:
                    raise AICapabilityQuotaExceededError(
                        f"Daily quota ({quota.max_per_day}) exceeded for "
                        f"'{principal_id}' on '{capability_id}'"
                    )
            counter.increment()

    def check_quota(self, principal_id: str, capability_id: str) -> bool:
        """
        Return True if the next execution is within quota.

        Does NOT increment the counter.
        """
        key = (principal_id, capability_id)
        with self._lock:
            quota   = self._quotas.get(key)
            counter = self._usage.get(key)
            if quota is None or counter is None:
                return True
            counter._reset_if_needed()
            if quota.max_per_hour > 0 and counter.hour_count >= quota.max_per_hour:
                return False
            if quota.max_per_day > 0 and counter.day_count >= quota.max_per_day:
                return False
        return True

    def get_usage(self, principal_id: str, capability_id: str) -> Dict[str, int]:
        key = (principal_id, capability_id)
        with self._lock:
            counter = self._usage.get(key)
            if counter is None:
                return {"hour_count": 0, "day_count": 0}
            return counter.snapshot()

    def quota_count(self) -> int:
        with self._lock:
            return len(self._quotas)
