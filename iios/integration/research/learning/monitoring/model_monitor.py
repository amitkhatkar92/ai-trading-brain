"""monitoring/model_monitor.py — Per-model runtime performance monitoring."""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import AlertSeverity
from iios.integration.research.learning.models.model_profile import ModelProfile
from iios.integration.research.learning.drift.alert_manager  import AlertManager


class ModelMonitor:
    """
    Tracks per-model prediction latencies, error rates, and prediction counts.

    After each prediction batch, call ``record_batch()`` to update the profile.
    """

    def __init__(
        self,
        alert_manager:   AlertManager,
        error_rate_limit: float = 0.05,
        window_size:      int   = 1000,
    ) -> None:
        self._alerts           = alert_manager
        self._error_rate_limit = error_rate_limit
        self._window           = window_size
        self._profiles: dict[str, ModelProfile] = {}
        self._latencies: dict[str, deque[float]] = {}  # model_id → recent latencies (ms)
        self._errors:    dict[str, deque[bool]]  = {}  # model_id → recent errors
        self._lock  = threading.RLock()

    def register(self, model_id: str, model_version: str, baseline_metrics: Optional[dict] = None) -> ModelProfile:
        with self._lock:
            profile = ModelProfile.create(model_id, model_version, baseline_metrics)
            self._profiles[model_id]  = profile
            self._latencies[model_id] = deque(maxlen=self._window)
            self._errors[model_id]    = deque(maxlen=self._window)
        return profile

    def record_batch(
        self,
        model_id:    str,
        n_predictions: int,
        latency_ms:  float,
        n_errors:    int = 0,
    ) -> None:
        with self._lock:
            profile  = self._profiles.get(model_id)
            if profile is None:
                return
            lats   = self._latencies[model_id]
            errs   = self._errors[model_id]

            for _ in range(n_predictions):
                lats.append(latency_ms / max(n_predictions, 1))
                errs.append(False)
            for _ in range(n_errors):
                errs.append(True)

            profile.total_predictions  += n_predictions
            profile.last_prediction_at  = time.time()
            profile.avg_latency_ms      = sum(lats) / len(lats) if lats else 0.0
            sorted_lats                 = sorted(lats)
            idx95                       = int(len(sorted_lats) * 0.95)
            profile.p95_latency_ms      = sorted_lats[idx95] if sorted_lats else 0.0
            profile.error_rate          = sum(errs) / len(errs) if errs else 0.0

        if profile.error_rate > self._error_rate_limit:
            self._alerts.raise_alert(
                AlertSeverity.CRITICAL,
                "performance",
                f"Model '{model_id}' error rate {profile.error_rate:.1%} exceeds {self._error_rate_limit:.1%}",
                model_id = model_id,
            )

    def get_profile(self, model_id: str) -> Optional[ModelProfile]:
        with self._lock:
            return self._profiles.get(model_id)

    def all_profiles(self) -> list[ModelProfile]:
        with self._lock:
            return list(self._profiles.values())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "models_monitored": len(self._profiles),
                "total_predictions": sum(p.total_predictions for p in self._profiles.values()),
            }
