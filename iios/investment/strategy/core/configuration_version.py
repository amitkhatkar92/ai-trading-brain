"""iios/investment/strategy/core/configuration_version.py
Versioned in-memory configuration store for institutional strategies.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from .strategy_configuration import StrategyConfiguration


@dataclass
class ConfigVersion:
    """A single historical version of a strategy's configuration."""
    version: int
    config: StrategyConfiguration
    reason: str = ""
    applied_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "reason": self.reason,
            "applied_at": self.applied_at.isoformat(),
            "config": self.config.to_dict(),
        }


class ConfigurationVersionStore:
    """
    Maintains a versioned in-memory history of configurations per strategy.
    Thread-safe ring buffer; oldest entries are dropped when max_versions
    is reached.
    """

    def __init__(self, max_versions: int = 20) -> None:
        self._lock = threading.RLock()
        self._max = max_versions
        self._versions: Dict[str, Deque[ConfigVersion]] = {}
        self._counters: Dict[str, int] = {}

    def save(
        self, config: StrategyConfiguration, reason: str = ""
    ) -> ConfigVersion:
        sid = config.strategy_id
        with self._lock:
            if sid not in self._versions:
                self._versions[sid] = deque(maxlen=self._max)
                self._counters[sid] = 0
            self._counters[sid] += 1
            cv = ConfigVersion(
                version=self._counters[sid],
                config=config,
                reason=reason,
            )
            self._versions[sid].append(cv)
        return cv

    def latest(self, strategy_id: str) -> Optional[ConfigVersion]:
        with self._lock:
            buf = self._versions.get(strategy_id)
            if not buf:
                return None
            return buf[-1]

    def at_version(
        self, strategy_id: str, version: int
    ) -> Optional[ConfigVersion]:
        with self._lock:
            for cv in self._versions.get(strategy_id, []):
                if cv.version == version:
                    return cv
            return None

    def history(
        self, strategy_id: str, n: int = 10
    ) -> List[ConfigVersion]:
        with self._lock:
            return list(self._versions.get(strategy_id, []))[-n:]

    def current_version_number(self, strategy_id: str) -> int:
        with self._lock:
            return self._counters.get(strategy_id, 0)

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._versions.keys())
