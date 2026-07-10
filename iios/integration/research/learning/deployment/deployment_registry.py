"""deployment/deployment_registry.py — Stores active DeploymentRecords."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DEFAULT_MAX_DEPLOYMENTS,
    DeploymentStatus,
    DeploymentStrategy,
)
from iios.integration.research.learning.learning_exceptions import (
    DeploymentError,
    DeploymentNotFoundError,
)


@dataclass
class DeploymentRecord:
    """A live deployment of a specific model version."""
    deployment_id: str
    model_id:      str
    model_version: str
    status:        DeploymentStatus
    strategy:      DeploymentStrategy
    traffic_frac:  float        # 0..1, fraction of traffic served
    deployed_at:   float
    updated_at:    float
    retired_at:    Optional[float]
    metrics:       dict[str, float]
    notes:         str

    @classmethod
    def create(
        cls,
        model_id:      str,
        model_version: str,
        strategy:      DeploymentStrategy,
        *,
        deployment_id: Optional[str]          = None,
        status:        DeploymentStatus        = DeploymentStatus.CHAMPION,
        traffic_frac:  float                   = 1.0,
        metrics:       Optional[dict]          = None,
        notes:         str                     = "",
    ) -> "DeploymentRecord":
        now = time.time()
        return cls(
            deployment_id = deployment_id or f"dep_{uuid.uuid4().hex[:12]}",
            model_id      = model_id,
            model_version = model_version,
            status        = status,
            strategy      = strategy,
            traffic_frac  = traffic_frac,
            deployed_at   = now,
            updated_at    = now,
            retired_at    = None,
            metrics       = metrics or {},
            notes         = notes,
        )

    def retire(self) -> None:
        self.status     = DeploymentStatus.RETIRED
        self.retired_at = time.time()
        self.updated_at = self.retired_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "model_id":      self.model_id,
            "model_version": self.model_version,
            "status":        self.status.value,
            "strategy":      self.strategy.value,
            "traffic_frac":  self.traffic_frac,
            "deployed_at":   self.deployed_at,
            "updated_at":    self.updated_at,
            "retired_at":    self.retired_at,
            "metrics":       self.metrics,
            "notes":         self.notes,
        }


class DeploymentRegistry:
    """Thread-safe store for DeploymentRecord objects."""

    def __init__(self, max_deployments: int = DEFAULT_MAX_DEPLOYMENTS) -> None:
        self._store: dict[str, DeploymentRecord] = {}
        self._max   = max_deployments
        self._lock  = threading.RLock()

    def register(self, record: DeploymentRecord) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                raise DeploymentError(f"Deployment registry capacity ({self._max}) reached")
            self._store[record.deployment_id] = record

    def get(self, deployment_id: str) -> DeploymentRecord:
        with self._lock:
            rec = self._store.get(deployment_id)
        if rec is None:
            raise DeploymentNotFoundError(f"Deployment '{deployment_id}' not found")
        return rec

    def remove(self, deployment_id: str) -> None:
        with self._lock:
            if deployment_id not in self._store:
                raise DeploymentNotFoundError(f"Deployment '{deployment_id}' not found")
            del self._store[deployment_id]

    def all_deployments(self, status: Optional[DeploymentStatus] = None) -> list[DeploymentRecord]:
        with self._lock:
            recs = list(self._store.values())
        if status is not None:
            recs = [r for r in recs if r.status == status]
        return recs

    def for_model(self, model_id: str) -> list[DeploymentRecord]:
        with self._lock:
            return [r for r in self._store.values() if r.model_id == model_id]

    def champion(self, model_id: Optional[str] = None) -> Optional[DeploymentRecord]:
        with self._lock:
            candidates = [r for r in self._store.values()
                          if r.status == DeploymentStatus.CHAMPION]
        if model_id is not None:
            candidates = [r for r in candidates if r.model_id == model_id]
        return candidates[0] if candidates else None

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for r in self._store.values():
                key = r.status.value
                by_status[key] = by_status.get(key, 0) + 1
            return {"total": len(self._store), "by_status": by_status, "capacity": self._max}
