"""iios/investment/company/business_quality/business_quality_engine.py

BusinessQualityEngine — Authoritative source of business quality intelligence
throughout IIOS.

Every downstream engine (Valuation, Growth, Company Opportunity, Portfolio AI,
Risk AI, Decision Layer) MUST consume business quality intelligence from this
engine. No module may independently evaluate business quality.

Capabilities:
  - Ingests FinancialSnapshot + EarningsSnapshot
  - Maintains per-company quality history (versioned snapshots)
  - Detects economic moat from financial signal patterns
  - Evaluates operational excellence and capital efficiency
  - Measures business resilience and cyclicality
  - Assesses competitive position and market leadership
  - Publishes BusinessQualitySnapshot as primary query object
  - Supports peer benchmarking via peer snapshot ingestion
  - Pluggable via BusinessQualityPlugin for future qualitative analysis
  - Thread-safe; supports millions of companies
  - Incremental updates; caches last snapshot per ticker
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from iios.investment.company.business_quality.assessment_context import (
    AssessmentContext, PluginRegistry,
)
from iios.investment.company.business_quality.business_model_analyzer import BusinessModelAnalyzer
from iios.investment.company.business_quality.moat_detector import MoatDetector
from iios.investment.company.business_quality.efficiency_engine import EfficiencyEngine
from iios.investment.company.business_quality.resilience_engine import ResilienceEngine
from iios.investment.company.business_quality.competitive_analysis import CompetitiveAnalyzer
from iios.investment.company.business_quality.business_quality_score import BusinessQualityScorer
from iios.investment.company.business_quality.quality_confidence import QualityConfidenceAnalyzer
from iios.investment.company.business_quality.business_quality_snapshot import (
    BusinessQualitySnapshot,
)

log = logging.getLogger(__name__)


class BusinessQualityEngine:
    """
    Primary business quality intelligence engine.

    Thread-safe; designed for millions of tickers.

    Primary intake:
        engine.ingest(ticker, financial_snapshot, earnings_snapshot)
    or:
        engine.ingest_financial(ticker, financial_snapshot)  # without earnings

    Primary query:
        engine.get_snapshot(ticker) -> BusinessQualitySnapshot
    """

    def __init__(
        self,
        on_snapshot_updated:  Optional[Callable[[BusinessQualitySnapshot], None]] = None,
        max_history:          int = 10,
    ) -> None:
        self._lock             = threading.RLock()
        self._snapshots:       Dict[str, BusinessQualitySnapshot] = {}
        self._history:         Dict[str, deque] = {}           # ticker → deque[snapshot]
        self._max_history      = max_history

        # Analyzers
        self._model_analyzer   = BusinessModelAnalyzer()
        self._moat_detector    = MoatDetector()
        self._efficiency       = EfficiencyEngine()
        self._resilience       = ResilienceEngine()
        self._competitive      = CompetitiveAnalyzer()
        self._scorer           = BusinessQualityScorer()
        self._confidence       = QualityConfidenceAnalyzer()

        # Plugin registry
        self._plugins          = PluginRegistry()

        self._on_snapshot_updated = on_snapshot_updated

    # ──────────────────────────── Primary intake ──────────────────────────────

    def ingest(
        self,
        ticker:             str,
        financial_snapshot: Any = None,   # FinancialSnapshot
        earnings_snapshot:  Any = None,   # EarningsSnapshot
        sector:             Optional[str] = None,
        industry:           Optional[str] = None,
        peer_tickers:       Optional[List[str]] = None,
    ) -> BusinessQualitySnapshot:
        """
        Full analysis intake — the recommended entry point.
        Both financial_snapshot and earnings_snapshot can be None
        (engine will produce a low-confidence snapshot).

        Args:
            ticker:              Company ticker.
            financial_snapshot:  FinancialSnapshot from FinancialStatementEngine.
            earnings_snapshot:   EarningsSnapshot from EarningsIntelligenceEngine.
            sector:              Optional sector label for context.
            industry:            Optional industry label for context.
            peer_tickers:        Optional list of peer tickers for benchmarking.
        Returns:
            BusinessQualitySnapshot
        """
        ctx = AssessmentContext(
            ticker             = ticker,
            financial_snapshot = financial_snapshot,
            earnings_snapshot  = earnings_snapshot,
            sector             = sector,
            industry           = industry,
        )

        # Gather peer snapshots if available
        if peer_tickers:
            with self._lock:
                ctx.peer_snapshots = [
                    self._snapshots[t]
                    for t in peer_tickers
                    if t in self._snapshots
                ]

        snap = self._build_snapshot(ctx)

        with self._lock:
            self._snapshots[ticker] = snap
            hist = self._history.setdefault(ticker, deque(maxlen=self._max_history))
            hist.append(snap)

        if self._on_snapshot_updated is not None:
            try:
                self._on_snapshot_updated(snap)
            except Exception as exc:
                log.warning("on_snapshot_updated callback raised: %s", exc)

        return snap

    def ingest_financial(
        self,
        ticker:             str,
        financial_snapshot: Any,
        sector:             Optional[str] = None,
        industry:           Optional[str] = None,
    ) -> BusinessQualitySnapshot:
        """Convenience: ingest with only financial snapshot (no earnings)."""
        return self.ingest(
            ticker=ticker,
            financial_snapshot=financial_snapshot,
            earnings_snapshot=None,
            sector=sector,
            industry=industry,
        )

    # ──────────────────────────── Query APIs ──────────────────────────────────

    def get_snapshot(self, ticker: str) -> Optional[BusinessQualitySnapshot]:
        with self._lock:
            return self._snapshots.get(ticker)

    def get_history(self, ticker: str) -> List[BusinessQualitySnapshot]:
        with self._lock:
            return list(self._history.get(ticker, deque()))

    def get_moat_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.moat.moat_score if snap else None

    def get_moat_strength(self, ticker: str):
        snap = self.get_snapshot(ticker)
        return snap.moat.moat_strength if snap else None

    def get_operational_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.operational.operational_quality_score if snap else None

    def get_resilience_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.resilience.resilience_score if snap else None

    def get_quality_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.quality_score.overall_score if snap else None

    def get_competitive_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.competitive.competitive_intelligence_score if snap else None

    def get_confidence(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.confidence.score if snap else None

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._snapshots.keys())

    # ──────────────────────────── Plugin management ────────────────────────────

    def register_plugin(self, plugin) -> None:
        """Register a BusinessQualityPlugin for extended assessments."""
        self._plugins.register(plugin)

    def unregister_plugin(self, name: str) -> None:
        self._plugins.unregister(name)

    # ──────────────────────────── Snapshot builder ────────────────────────────

    def _build_snapshot(self, ctx: AssessmentContext) -> BusinessQualitySnapshot:
        snap = BusinessQualitySnapshot(
            ticker   = ctx.ticker,
            sector   = ctx.sector,
            industry = ctx.industry,
        )

        # ── Business model ─────────────────────────────────────────────────────
        try:
            snap.business_model = self._model_analyzer.analyze(ctx)
        except Exception as exc:
            log.warning("[%s] business_model analysis failed: %s", ctx.ticker, exc)

        # ── Economic moat ──────────────────────────────────────────────────────
        try:
            snap.moat = self._moat_detector.analyze(ctx)
        except Exception as exc:
            log.warning("[%s] moat analysis failed: %s", ctx.ticker, exc)

        # ── Operational quality ────────────────────────────────────────────────
        try:
            snap.operational = self._efficiency.analyze(ctx)
        except Exception as exc:
            log.warning("[%s] efficiency analysis failed: %s", ctx.ticker, exc)

        # ── Resilience ─────────────────────────────────────────────────────────
        try:
            snap.resilience = self._resilience.analyze(ctx)
        except Exception as exc:
            log.warning("[%s] resilience analysis failed: %s", ctx.ticker, exc)

        # ── Competitive intelligence ───────────────────────────────────────────
        try:
            snap.competitive = self._competitive.analyze(
                ctx=ctx,
                own_snapshot=snap,
                peers=ctx.peer_snapshots,
            )
        except Exception as exc:
            log.warning("[%s] competitive analysis failed: %s", ctx.ticker, exc)

        # ── Plugin contributions ───────────────────────────────────────────────
        plugin_scores: Dict[str, float] = {}
        for result in self._plugins.run_all(ctx):
            plugin_scores[result.plugin_name] = result.score
        snap.plugin_scores = plugin_scores

        # ── Scoring ────────────────────────────────────────────────────────────
        model_score = self._model_analyzer.score(snap.business_model)
        snap.quality_score = self._scorer.compute(
            moat_score        = snap.moat.moat_score,
            operational_score = snap.operational.operational_quality_score,
            resilience_score  = snap.resilience.resilience_score,
            competitive_score = snap.competitive.competitive_intelligence_score,
            model_score       = model_score,
            plugin_scores     = plugin_scores or None,
        )

        # ── Confidence ─────────────────────────────────────────────────────────
        try:
            snap.confidence = self._confidence.analyze(ctx, snap)
        except Exception as exc:
            log.warning("[%s] confidence analysis failed: %s", ctx.ticker, exc)

        return snap
