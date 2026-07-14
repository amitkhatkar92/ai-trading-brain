"""iios/investment/decision/core/decision_session.py
DecisionSession — groups related decisions into a logical unit of work.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class DecisionSession:
    """
    A session groups decisions that share a common analytical context
    (e.g. all decisions from one portfolio review cycle).
    Thread-safe.
    """

    def __init__(
        self,
        session_id:   Optional[str] = None,
        name:         str           = "",
        created_by:   str           = "system",
    ) -> None:
        self._lock        = threading.RLock()
        self.session_id   = session_id or str(uuid.uuid4())
        self.name         = name or f"session-{self.session_id[:8]}"
        self.created_by   = created_by
        self.created_at   = datetime.now(timezone.utc)
        self.closed_at:   Optional[datetime]  = None
        self._decision_ids: List[str]         = []
        self._tags:         List[str]         = []

    def add_decision(self, decision_id: str) -> None:
        with self._lock:
            if decision_id not in self._decision_ids:
                self._decision_ids.append(decision_id)

    def remove_decision(self, decision_id: str) -> None:
        with self._lock:
            try:
                self._decision_ids.remove(decision_id)
            except ValueError:
                pass

    def close(self) -> None:
        with self._lock:
            if self.closed_at is None:
                self.closed_at = datetime.now(timezone.utc)

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    @property
    def decision_count(self) -> int:
        with self._lock:
            return len(self._decision_ids)

    @property
    def decision_ids(self) -> List[str]:
        with self._lock:
            return list(self._decision_ids)

    def add_tag(self, tag: str) -> None:
        with self._lock:
            if tag not in self._tags:
                self._tags.append(tag)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":     self.session_id,
                "name":           self.name,
                "created_by":     self.created_by,
                "created_at":     self.created_at.isoformat(),
                "closed_at":      self.closed_at.isoformat() if self.closed_at else None,
                "is_open":        self.is_open,
                "decision_count": len(self._decision_ids),
                "decision_ids":   list(self._decision_ids),
                "tags":           list(self._tags),
            }
