"""
iios/intelligence/reasoning/confidence/confidence_engine.py
===========================================================
ConfidenceEngine — orchestrates confidence calculation for sessions.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from ..reasoning_constants import (
    ConfidenceLevel,
    CONFIDENCE_THRESHOLD_MODERATE,
)
from .confidence_calculator import ConfidenceCalculator
from .confidence_model import ConfidenceModel
from .confidence_report import ConfidenceReport

if TYPE_CHECKING:
    from ..evidence.evidence_registry import Evidence
    from ..debate.debate_summary import DebateSummary
    from ..reasoning_result import ReasoningOutput


class ConfidenceEngine:
    """
    Computes and caches ConfidenceReport for each reasoning session.

    Injects:
    --------
    calculator : ConfidenceCalculator (stateless dimension calculator)
    """

    def __init__(
        self,
        calculator: ConfidenceCalculator | None = None,
    ) -> None:
        self._calc:    ConfidenceCalculator           = calculator or ConfidenceCalculator()
        self._reports: dict[str, ConfidenceReport]    = {}
        self._lock:    threading.RLock                = threading.RLock()

    # -- Core calculation ──────────────────────────────────────────────────────

    def calculate(
        self,
        session_id:       str,
        evidence_items:   list[Evidence]       | None = None,
        reasoning_outputs: list[ReasoningOutput] | None = None,
        debate_summary:   DebateSummary         | None = None,
        source_weights:   dict[str, float]      | None = None,
        hit_rate:         float | None           = None,
        sample_size:      int                    = 0,
        volatility:       float                  = 0.0,
        uncertainty:      float                  = 0.0,
    ) -> ConfidenceReport:
        """
        Compute a full ConfidenceReport for a reasoning session.

        Parameters
        ----------
        session_id        : Owning reasoning session.
        evidence_items    : Evidence items collected in the session.
        reasoning_outputs : Outputs from individual reasoning steps.
        debate_summary    : DebateSummary if a debate was conducted.
        source_weights    : Mapping of source name → reliability [0, 1].
        hit_rate          : Historical hit rate for similar conclusions.
        sample_size       : Historical sample size for hit_rate smoothing.
        volatility        : Environmental volatility estimate [0, 1].
        uncertainty       : Environmental uncertainty estimate [0, 1].
        """
        items     = evidence_items    or []
        outputs   = reasoning_outputs or []
        sources   = list({e.source for e in items if e.source})

        ev_conf   = self._calc.evidence_confidence(items)
        src_conf  = self._calc.source_confidence(sources, source_weights)
        rsn_conf  = self._calc.reasoning_confidence(outputs)
        con_conf  = self._calc.consensus_confidence(debate_summary)
        hist_rel  = self._calc.historical_reliability(hit_rate, sample_size)
        risk_adj  = self._calc.risk_adjustment(volatility, uncertainty)

        model = ConfidenceModel(
            evidence_confidence    = ev_conf,
            source_confidence      = src_conf,
            reasoning_confidence   = rsn_conf,
            consensus_confidence   = con_conf,
            historical_reliability = hist_rel,
            risk_adjustment        = risk_adj,
        )
        model.compute()
        level      = ConfidenceModel.score_to_level(model.final_score)
        is_reliable = model.final_score >= CONFIDENCE_THRESHOLD_MODERATE

        warnings: list[str]        = []
        recommendations: list[str] = []

        if ev_conf < 0.3:
            warnings.append("Low evidence confidence — consider adding stronger evidence")
            recommendations.append("Add high-strength evidence items from reliable sources")
        if len(items) == 0:
            warnings.append("No evidence provided")
            recommendations.append("Add at least one evidence item before concluding")
        if debate_summary and debate_summary.is_deadlocked:
            warnings.append("Debate deadlocked — no consensus reached")
            recommendations.append("Add more participants or expand evidence base")
        if risk_adj < 0.7:
            warnings.append(f"High risk environment: adjustment factor = {risk_adj:.2f}")

        report = ConfidenceReport(
            session_id       = session_id,
            model            = model,
            confidence_level = level,
            is_reliable      = is_reliable,
            warnings         = warnings,
            recommendations  = recommendations,
        )
        with self._lock:
            self._reports[session_id] = report
        return report

    # -- Retrieval ─────────────────────────────────────────────────────────────

    def get_report(self, session_id: str) -> ConfidenceReport | None:
        with self._lock:
            return self._reports.get(session_id)

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_level: dict[str, int] = {}
            for r in self._reports.values():
                lv = r.confidence_level.value
                by_level[lv] = by_level.get(lv, 0) + 1
            return {
                "total":    len(self._reports),
                "by_level": by_level,
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK   = threading.Lock()
_ENGINE: ConfidenceEngine | None = None


def get_confidence_engine() -> ConfidenceEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = ConfidenceEngine()
    return _ENGINE


def reset_confidence_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
