"""drift/data_monitor.py — Continuous data quality and drift monitoring."""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import AlertSeverity
from iios.integration.research.learning.drift.drift_detector import DriftDetector, DriftResult
from iios.integration.research.learning.drift.alert_manager  import AlertManager


class DataMonitor:
    """
    Monitors live inference data against a stored baseline for drift.

    Call ``set_baseline`` once after initial training, then ``check`` on each
    new batch of inference records.
    """

    def __init__(
        self,
        detector:      DriftDetector,
        alert_manager: AlertManager,
    ) -> None:
        self._detector  = detector
        self._alerts    = alert_manager
        self._baselines: dict[str, list[dict[str, Any]]] = {}  # model_id → baseline records
        self._lock       = threading.RLock()

    def set_baseline(self, model_id: str, records: list[dict[str, Any]]) -> None:
        with self._lock:
            self._baselines[model_id] = list(records)

    def check(
        self,
        model_id:     str,
        current_data: list[dict[str, Any]],
    ) -> Optional[DriftResult]:
        with self._lock:
            baseline = self._baselines.get(model_id)

        if baseline is None:
            return None

        result = self._detector.check_data_drift(model_id, baseline, current_data)
        if result.is_drifted:
            self._alerts.raise_alert(
                AlertSeverity.WARNING,
                "drift",
                f"Data drift detected for model '{model_id}' (PSI={result.drift_score:.3f})",
                model_id = model_id,
                detail   = result.to_dict(),
            )
        return result

    def has_baseline(self, model_id: str) -> bool:
        with self._lock:
            return model_id in self._baselines

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "models_monitored": len(self._baselines),
                "detector":         self._detector.stats(),
            }
