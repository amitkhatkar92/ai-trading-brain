"""iios/investment/company/earnings/earnings_intelligence_engine.py

EarningsIntelligenceEngine — Authoritative source of earnings and
profitability intelligence throughout IIOS.

Consumes FinancialSnapshot from FinancialStatementEngine.
Does NOT parse raw financial statements.

All downstream engines (Valuation, Growth, Business Quality, Risk,
Portfolio AI, Decision Layer) MUST obtain earnings intelligence from
this engine. No module may independently evaluate earnings quality.

Capabilities:
  - Ingests EarningsReport derived from FinancialSnapshot
  - Maintains per-company earnings history (ring buffer)
  - Computes earnings quality, profitability, trend, risk, and confidence
  - Tracks restatements and revisions
  - Publishes EarningsSnapshot as the primary query object
  - Thread-safe; supports millions of companies
  - Pluggable profitability metric framework via ProfitabilityEngine
  - All output deterministic, explainable, auditable
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport, TrendDirection
from iios.investment.company.earnings.earnings_snapshot import (
    EarningsSnapshot, EarningsQualityScore, ProfitabilityProfile,
    TrendProfile, EarningsMomentumProfile, EarningsRiskProfile,
    EarningsConfidenceScore,
)
from iios.investment.company.earnings.earnings_history import EarningsHistory
from iios.investment.company.earnings.earnings_revision import EarningsRevisionTracker
from iios.investment.company.earnings.earnings_quality import EarningsQualityAnalyzer
from iios.investment.company.earnings.earnings_reliability import EarningsReliabilityAnalyzer
from iios.investment.company.earnings.profitability_engine import ProfitabilityEngine
from iios.investment.company.earnings.earnings_trend import EarningsTrendAnalyzer
from iios.investment.company.earnings.earnings_momentum import EarningsMomentumAnalyzer
from iios.investment.company.earnings.earnings_risk import EarningsRiskAnalyzer
from iios.investment.company.earnings.earnings_confidence import EarningsConfidenceAnalyzer
from iios.investment.company.earnings.earnings_score import (
    EarningsIntelligenceScore, profitability_to_score, trend_to_score,
)
from iios.investment.company.earnings.earnings_quality_statistics import (
    EarningsQualityStatisticsEngine, EarningsQualityStatistics,
)

log = logging.getLogger(__name__)

# Minimum history to produce full analytics (quality/trend)
_MIN_HISTORY_QUALITY = 3
_MIN_HISTORY_TREND   = 3


class EarningsIntelligenceEngine:
    """
    Primary earnings intelligence engine.

    Thread-safe; designed for millions of companies.

    Primary intake:
        engine.ingest(ticker, snapshot)   → via FinancialSnapshot
    or:
        engine.ingest_report(ticker, report) → via pre-built EarningsReport

    Primary query:
        engine.get_snapshot(ticker) → EarningsSnapshot
    """

    def __init__(
        self,
        on_snapshot_updated: Optional[Callable[[EarningsSnapshot], None]] = None,
        max_history:         int = 24,
    ) -> None:
        self._lock               = threading.RLock()
        self._snapshots:         Dict[str, EarningsSnapshot] = {}
        self._history            = EarningsHistory(max_periods=max_history)
        self._revision_tracker   = EarningsRevisionTracker()

        # Analysis components
        self._quality_analyzer   = EarningsQualityAnalyzer()
        self._reliability        = EarningsReliabilityAnalyzer()
        self._profitability      = ProfitabilityEngine()
        self._trend              = EarningsTrendAnalyzer()
        self._momentum           = EarningsMomentumAnalyzer()
        self._risk               = EarningsRiskAnalyzer()
        self._confidence         = EarningsConfidenceAnalyzer()
        self._stats_engine       = EarningsQualityStatisticsEngine()

        self._on_snapshot_updated = on_snapshot_updated

    # ─────────────────────────── Primary intake ───────────────────────────────

    def ingest(
        self,
        ticker:   str,
        snapshot: Any,    # FinancialSnapshot — imported lazily
        period_type: str = "annual",
    ) -> EarningsSnapshot:
        """
        Ingest a FinancialSnapshot and produce updated EarningsSnapshot.

        Args:
            ticker:      Company ticker symbol.
            snapshot:    FinancialSnapshot from FinancialStatementEngine.
            period_type: "annual" (default) or "ttm".

        Returns:
            Updated EarningsSnapshot.
        """
        report = EarningsReport.from_snapshot(snapshot, period_type)
        if report is None:
            log.warning("EarningsIntelligenceEngine: no earnings data in snapshot for %s", ticker)
            return self._get_or_empty_snapshot(ticker)

        return self.ingest_report(ticker, report)

    def ingest_report(self, ticker: str, report: EarningsReport) -> EarningsSnapshot:
        """
        Ingest a pre-built EarningsReport directly.
        Detects revisions if the period was already stored.
        """
        with self._lock:
            # Detect revision if period already stored
            existing = self._find_existing(ticker, report.period_label)
            if existing is not None:
                self._revision_tracker.detect(
                    ticker, report.period_label, existing, report,
                )

            self._history.push(ticker, report)
            snap = self._build_snapshot(ticker)
            self._snapshots[ticker] = snap

        if self._on_snapshot_updated is not None:
            try:
                self._on_snapshot_updated(snap)
            except Exception as exc:
                log.warning("on_snapshot_updated callback raised: %s", exc)

        return snap

    # ─────────────────────────── Query APIs ───────────────────────────────────

    def get_snapshot(self, ticker: str) -> Optional[EarningsSnapshot]:
        with self._lock:
            return self._snapshots.get(ticker)

    def get_latest_report(self, ticker: str) -> Optional[EarningsReport]:
        return self._history.get_latest(ticker)

    def get_history(self, ticker: str, n: int = 10) -> List[EarningsReport]:
        return self._history.get_history(ticker, n)

    def get_quality_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.quality.overall_score if snap else None

    def get_profitability(self, ticker: str) -> Optional[ProfitabilityProfile]:
        snap = self.get_snapshot(ticker)
        return snap.profitability if snap else None

    def get_trend(self, ticker: str) -> Optional[TrendDirection]:
        snap = self.get_snapshot(ticker)
        return snap.trend.eps_direction if snap else None

    def get_risk_profile(self, ticker: str) -> Optional[EarningsRiskProfile]:
        snap = self.get_snapshot(ticker)
        return snap.risk if snap else None

    def get_confidence(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.confidence.score if snap else None

    def get_quality_statistics(self, ticker: str) -> Optional[EarningsQualityStatistics]:
        history = self.get_history(ticker, n=24)
        if not history:
            return None
        return self._stats_engine.compute(history)

    def revision_summary(self, ticker: str) -> Dict[str, Any]:
        return self._revision_tracker.summary(ticker)

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._snapshots.keys())

    def history_depth(self, ticker: str) -> int:
        return self._history.period_count(ticker)

    # ─────────────────────────── Snapshot Builder ─────────────────────────────

    def _build_snapshot(self, ticker: str) -> EarningsSnapshot:
        history = self._history.get_history(ticker, n=20)
        ttm     = self._history.get_ttm(ticker)
        latest  = ttm or (history[-1] if history else None)

        snap = EarningsSnapshot(
            ticker=ticker,
            latest_report=latest,
            history_depth=len(history),
        )

        if not history and ttm is None:
            return snap

        # Effective history for analysis (annual periods)
        analysis_history = history

        # ── Quality ───────────────────────────────────────────────────────────
        if len(analysis_history) >= _MIN_HISTORY_QUALITY:
            snap.quality = self._quality_analyzer.analyze(analysis_history)
        elif analysis_history:
            # Minimal quality from single period
            snap.quality = self._quality_analyzer.analyze(analysis_history)

        # ── Profitability ─────────────────────────────────────────────────────
        full_prof = self._profitability.analyze(analysis_history, latest)
        snap.profitability = full_prof.as_profitability_profile()

        # ── Trend ──────────────────────────────────────────────────────────────
        if len(analysis_history) >= _MIN_HISTORY_TREND:
            snap.trend = self._trend.analyze(analysis_history)

        # ── Momentum ──────────────────────────────────────────────────────────
        snap.momentum = self._momentum.analyze(analysis_history)

        # ── Risk ──────────────────────────────────────────────────────────────
        snap.risk = self._risk.analyze(ticker, analysis_history, self._revision_tracker)

        # ── Confidence ────────────────────────────────────────────────────────
        snap.confidence = self._confidence.analyze(
            history=analysis_history,
            quality=snap.quality,
            revision_count=self._revision_tracker.revision_count(ticker),
        )

        # ── Overall score ─────────────────────────────────────────────────────
        prof_score = profitability_to_score(
            avg_net_margin=snap.profitability.avg_net_margin,
            avg_roic=snap.profitability.avg_roic,
        )
        t_score = trend_to_score(snap.trend.eps_direction.value)
        intel_score = EarningsIntelligenceScore.from_components(
            quality_score=snap.quality.overall_score,
            profitability_score=prof_score,
            trend_score=t_score,
            risk_stability_score=snap.risk.earnings_stability_score,
            confidence_score=snap.confidence.score,
        )
        snap.overall_score = intel_score.overall_score

        return snap

    # ─────────────────────────── Helpers ──────────────────────────────────────

    def _get_or_empty_snapshot(self, ticker: str) -> EarningsSnapshot:
        with self._lock:
            return self._snapshots.get(ticker, EarningsSnapshot(ticker=ticker))

    def _find_existing(
        self, ticker: str, period_label: str
    ) -> Optional[EarningsReport]:
        for r in self._history.get_history(ticker, n=40):
            if r.period_label == period_label:
                return r
        return None
