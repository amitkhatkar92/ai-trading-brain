"""
iios/observation/quality/quality_report.py
==========================================
QualityReport — aggregate quality reporting across observations.

Provides time-windowed summaries, per-source breakdowns, tier
distributions, and identification of outliers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import ObservationQuality
from .quality_metrics        import QualityMetrics, get_quality_metrics
from .quality_score          import QualityScore

__all__ = [
    "QualityReportSection",
    "QualityReportDocument",
    "QualityReporter",
    "get_quality_reporter",
    "reset_quality_reporter",
]

import threading

_lock     = threading.Lock()
_reporter: Optional["QualityReporter"] = None


# ── Section ───────────────────────────────────────────────────────────────────

@dataclass
class QualityReportSection:
    """A single named section of the quality report."""
    title:       str
    data:        dict[str, Any]
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "description": self.description, "data": self.data}


# ── Document ──────────────────────────────────────────────────────────────────

@dataclass
class QualityReportDocument:
    """Complete quality report generated at a point in time."""
    generated_at:  float                    = field(default_factory=time.time)
    since:         float                    = 0.0
    until:         float                    = field(default_factory=time.time)
    sections:      list[QualityReportSection] = field(default_factory=list)
    metadata:      dict[str, Any]           = field(default_factory=dict)

    def add_section(self, section: QualityReportSection) -> None:
        self.sections.append(section)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "since":        self.since,
            "until":        self.until,
            "sections":     [s.to_dict() for s in self.sections],
            "metadata":     self.metadata,
        }

    def section(self, title: str) -> Optional[QualityReportSection]:
        for s in self.sections:
            if s.title == title:
                return s
        return None


# ── Reporter ──────────────────────────────────────────────────────────────────

class QualityReporter:
    """Generates :class:`QualityReportDocument` from :class:`QualityMetrics`.

    Parameters
    ----------
    metrics:
        :class:`QualityMetrics` instance.  Defaults to global singleton.
    """

    def __init__(self, metrics: Optional[QualityMetrics] = None) -> None:
        self._metrics = metrics or get_quality_metrics()

    def generate(
        self,
        since:    Optional[float] = None,
        until:    Optional[float] = None,
        title:    str             = "Observation Quality Report",
    ) -> QualityReportDocument:
        """Build a full quality report document."""
        now   = time.time()
        since = since or (now - 86_400.0)
        until = until or now

        doc = QualityReportDocument(
            since = since,
            until = until,
            metadata = {"title": title},
        )

        # ── Section 1: Global summary ─────────────────────────────────────────
        global_w = self._metrics.window("_global")
        doc.add_section(QualityReportSection(
            title       = "Global Summary",
            description = "Aggregate quality across all observations",
            data        = global_w.to_dict() if global_w else {"count": 0},
        ))

        # ── Section 2: Tier distribution ─────────────────────────────────────
        tier_dist = global_w.tier_distribution() if global_w else {
            t.value: 0 for t in ObservationQuality
        }
        total = sum(tier_dist.values()) or 1
        doc.add_section(QualityReportSection(
            title       = "Tier Distribution",
            description = "Count and percentage of observations per quality tier",
            data        = {
                t: {"count": n, "pct": round(n / total * 100, 1)}
                for t, n in tier_dist.items()
            },
        ))

        # ── Section 3: Per-source breakdown ───────────────────────────────────
        all_windows = self._metrics.all_windows()
        source_data: dict[str, Any] = {}
        for key, stats in all_windows.items():
            if key.startswith("source:"):
                src = key[len("source:"):]
                source_data[src] = stats
        doc.add_section(QualityReportSection(
            title       = "Source Breakdown",
            description = "Quality statistics by data source",
            data        = source_data,
        ))

        # ── Section 4: Per-type breakdown ──────────────────────────────────────
        type_data: dict[str, Any] = {}
        for key, stats in all_windows.items():
            if key.startswith("type:"):
                obs_type = key[len("type:"):]
                type_data[obs_type] = stats
        doc.add_section(QualityReportSection(
            title       = "Type Breakdown",
            description = "Quality statistics by observation type",
            data        = type_data,
        ))

        # ── Section 5: Metrics summary ────────────────────────────────────────
        doc.add_section(QualityReportSection(
            title       = "Metrics Summary",
            description = "Internal metrics state",
            data        = self._metrics.summary(),
        ))

        return doc

    def quick_summary(self) -> dict[str, Any]:
        """Return a lightweight dict suitable for health checks."""
        global_w = self._metrics.window("_global")
        if not global_w or global_w.count == 0:
            return {"status": "no_data", "count": 0}
        mean = global_w.mean
        return {
            "status":  "healthy" if mean >= 0.60 else "degraded",
            "count":   global_w.count,
            "mean_oqi": round(mean, 4),
            "p50":      round(global_w.percentile(50), 4),
            "p90":      round(global_w.percentile(90), 4),
            "tiers":    global_w.tier_distribution(),
        }


# ── Singletons ────────────────────────────────────────────────────────────────

def get_quality_reporter() -> QualityReporter:
    global _reporter
    if _reporter is None:
        with _lock:
            if _reporter is None:
                _reporter = QualityReporter()
    return _reporter


def reset_quality_reporter() -> None:
    global _reporter
    with _lock:
        _reporter = None
