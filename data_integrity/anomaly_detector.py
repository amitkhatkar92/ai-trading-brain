"""
Data Integrity Engine — AnomalyDetector
=========================================
Statistical anomaly detection using a rolling Z-score window.

Detects:
  • VIX z-score anomaly   — sudden VIX jump/crash vs rolling mean
  • PCR z-score anomaly   — PCR deviating far from recent baseline
  • Breadth reversal      — sudden reversal in advance-decline ratio
  • Multi-asset divergence — when ALL assets move in same direction
    simultaneously (>95% breadth AND VIX low → suspicious data)
  • Flat feed detection   — same value received N times in a row

Each detected anomaly returns an Anomaly namedtuple with:
  field, value, z_score, severity ("LOW"/"MEDIUM"/"HIGH"), message
"""

from __future__ import annotations
import collections
import math
import statistics
from dataclasses import dataclass, field
from typing import Deque

from utils import get_logger

log = get_logger(__name__)

WINDOW_SIZE:  int   = 20    # rolling observations for mean/std
Z_WARN:       float = 2.0   # |z| ≥ 2 → warning
Z_ALERT:      float = 3.5   # |z| ≥ 3.5 → high severity
FLAT_REPEATS: int   = 5     # same value this many times → flat-feed alert


@dataclass
class Anomaly:
    field:    str
    value:    float
    z_score:  float
    severity: str        # "LOW" | "MEDIUM" | "HIGH"
    message:  str


@dataclass
class AnomalyReport:
    anomalies:    list[Anomaly] = field(default_factory=list)
    is_anomalous: bool = False

    def summary(self) -> str:
        if not self.anomalies:
            return "[AnomalyDetector] No anomalies detected."
        details = " | ".join(f"{a.field}(z={a.z_score:.1f},{a.severity})"
                             for a in self.anomalies)
        return f"[AnomalyDetector] {len(self.anomalies)} anomaly(ies): {details}"


class AnomalyDetector:
    """
    Maintains a rolling history of market metrics and flags z-score outliers.

    Usage::
        detector = AnomalyDetector()
        report   = detector.detect(raw_dict)
    """

    def __init__(self, window: int = WINDOW_SIZE) -> None:
        self._window  = window
        self._history: dict[str, Deque[float]] = {
            "vix":     collections.deque(maxlen=window),
            "pcr":     collections.deque(maxlen=window),
            "breadth": collections.deque(maxlen=window),
        }
        self._flat_counters: dict[str, int]   = {}
        self._last_values:   dict[str, float] = {}
        log.info("[AnomalyDetector] Initialised. Window=%d | Z-warn=%.1f | "
                 "Z-alert=%.1f", window, Z_WARN, Z_ALERT)

    # ── Public API ────────────────────────────────────────────────────────
    def detect(self, raw: dict) -> AnomalyReport:
        anomalies: list[Anomaly] = []

        for field_name in ("vix", "pcr", "breadth"):
            val = raw.get(field_name)
            if val is None or not isinstance(val, (int, float)):
                continue
            val = float(val)

            # Flat-feed detection
            flat_anomaly = self._check_flat(field_name, val)
            if flat_anomaly:
                anomalies.append(flat_anomaly)

            # Z-score anomaly
            z_anomaly = self._check_zscore(field_name, val)
            if z_anomaly:
                anomalies.append(z_anomaly)

            # Update rolling history
            self._history[field_name].append(val)
            self._last_values[field_name] = val

        # Multi-asset divergence check
        div_anomaly = self._check_divergence(raw)
        if div_anomaly:
            anomalies.append(div_anomaly)

        is_anomalous = any(a.severity in ("MEDIUM", "HIGH") for a in anomalies)

        report = AnomalyReport(anomalies=anomalies, is_anomalous=is_anomalous)
        if anomalies:
            for a in anomalies:
                if a.severity == "HIGH":
                    log.error("[AnomalyDetector] HIGH anomaly — %s", a.message)
                else:
                    log.warning("[AnomalyDetector] %s anomaly — %s",
                                a.severity, a.message)
        else:
            log.info("[AnomalyDetector] No anomalies detected.")
        return report

    # ── Private helpers ───────────────────────────────────────────────────
    def _check_zscore(self, field_name: str, value: float) -> Anomaly | None:
        history = list(self._history[field_name])
        if len(history) < 5:      # need at least 5 observations
            return None
        try:
            mu    = statistics.mean(history)
            sigma = statistics.stdev(history)
        except statistics.StatisticsError:
            return None
        if sigma < 1e-9:
            return None
        z = (value - mu) / sigma
        if abs(z) >= Z_ALERT:
            severity = "HIGH"
        elif abs(z) >= Z_WARN:
            severity = "MEDIUM"
        else:
            return None
        return Anomaly(
            field=field_name,
            value=value,
            z_score=round(z, 2),
            severity=severity,
            message=(f"{field_name.upper()}={value:.2f} is {abs(z):.1f}σ "
                     f"from rolling mean {mu:.2f} ({severity} anomaly)"),
        )

    def _check_flat(self, field_name: str, value: float) -> Anomaly | None:
        last = self._last_values.get(field_name)
        if last is not None and math.isclose(value, last, rel_tol=1e-6):
            self._flat_counters[field_name] = \
                self._flat_counters.get(field_name, 1) + 1
        else:
            self._flat_counters[field_name] = 0

        count = self._flat_counters.get(field_name, 0)
        if count >= FLAT_REPEATS:
            return Anomaly(
                field=field_name,
                value=value,
                z_score=0.0,
                severity="MEDIUM",
                message=(f"{field_name.upper()}={value:.3f} has been identical "
                         f"for {count} successive readings — possible frozen feed"),
            )
        return None

    @staticmethod
    def _check_divergence(raw: dict) -> Anomaly | None:
        """
        Breadth > 0.95 AND VIX > 25 simultaneously is structurally inconsistent:
        it means 95%+ stocks are advancing but the fear index is elevated —
        this signals either a data error or a very unusual flash-recovery event.
        """
        breadth = raw.get("breadth", 0.0)
        vix     = raw.get("vix",     15.0)
        if isinstance(breadth, (int, float)) and isinstance(vix, (int, float)):
            if breadth > 0.95 and vix > 25:
                return Anomaly(
                    field="multi_asset",
                    value=breadth,
                    z_score=0.0,
                    severity="MEDIUM",
                    message=(f"Structural divergence: breadth={breadth:.0%} (euphoric) "
                             f"with VIX={vix:.1f} (fearful) — verify data integrity"),
                )
        return None
