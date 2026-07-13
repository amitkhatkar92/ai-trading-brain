"""iios/investment/company/integration/company_intelligence_integration_engine.py
CompanyIntelligenceIntegrationEngine — the single orchestration, validation,
quality assurance, and publishing layer for all Company Intelligence.

Downstream IIOS components must consume ONLY the CompanyIntelligenceSnapshot
produced by this engine.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.aggregation_engine import AggregationEngine
from iios.investment.company.integration.aggregation_history import AggregationHistory
from iios.investment.company.integration.aggregation_state import AggregationState
from iios.investment.company.integration.company_confidence import (
    compute_confidence, explain_confidence,
)
from iios.investment.company.integration.company_quality import (
    CompanyQualityScore, compute_company_quality, record_quality,
)
from iios.investment.company.integration.company_snapshot import CompanyIntelligenceSnapshot
from iios.investment.company.integration.company_state import KNOWN_ENGINES, SCORED_ENGINES
from iios.investment.company.integration.company_statistics import clamp
from iios.investment.company.integration.conflict_engine import ConflictEngine
from iios.investment.company.integration.consistency_validator import ConsistencyValidator
from iios.investment.company.integration.health_monitor import HealthMonitor
from iios.investment.company.integration.quality_history import QualityHistory
from iios.investment.company.integration.validation_report import ValidationReport


class CompanyIntelligenceIntegrationEngine:
    """
    Single orchestration, validation, quality assurance, and publishing layer
    for all Company Intelligence in IIOS.

    Thread-safe: uses a per-ticker RLock and a global registry lock.

    Primary API:
    - integrate(ticker, **snapshots)  → CompanyIntelligenceSnapshot
    - update(ticker, engine, snapshot) → CompanyIntelligenceSnapshot
    - get_snapshot(ticker)            → Optional[CompanyIntelligenceSnapshot]
    - get_history(ticker)             → List[CompanyIntelligenceSnapshot]

    Query APIs:
    - get_quality(ticker)
    - get_validation_report(ticker)
    - get_conflicts(ticker)
    - get_summary(ticker)
    - get_confidence(ticker)
    - health_report()
    - known_tickers()
    - population_size()
    """

    def __init__(self) -> None:
        self._global_lock   = threading.RLock()
        # Per-ticker locks and state
        self._ticker_locks:  Dict[str, threading.RLock] = {}
        self._states:        Dict[str, AggregationState] = {}
        self._snapshots:     Dict[str, CompanyIntelligenceSnapshot] = {}
        self._metadata:      Dict[str, Dict[str, Any]] = {}

        # Subsystems
        self._aggregator     = AggregationEngine()
        self._validator      = ConsistencyValidator()
        self._conflict_eng   = ConflictEngine()
        self._history        = AggregationHistory()
        self._quality_history = QualityHistory()
        self._health         = HealthMonitor()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_or_create_state(self, ticker: str) -> AggregationState:
        with self._global_lock:
            if ticker not in self._states:
                self._states[ticker]     = AggregationState(ticker)
                self._ticker_locks[ticker] = threading.RLock()
            return self._states[ticker]

    def _ticker_lock(self, ticker: str) -> threading.RLock:
        with self._global_lock:
            if ticker not in self._ticker_locks:
                self._ticker_locks[ticker] = threading.RLock()
            return self._ticker_locks[ticker]

    def _merge_metadata(self, ticker: str, meta: Optional[Dict[str, Any]]) -> None:
        if not meta:
            return
        with self._global_lock:
            existing = self._metadata.setdefault(ticker, {})
            for k, v in meta.items():
                if v is not None:
                    existing[k] = v

    def _get_meta(self, ticker: str, key: str) -> Optional[str]:
        return self._metadata.get(ticker, {}).get(key)

    # ── Core evaluation ───────────────────────────────────────────────────────

    def _evaluate(self, ticker: str) -> CompanyIntelligenceSnapshot:
        """
        Run the full integration pipeline for *ticker* using its current state.
        Called under the per-ticker lock.
        """
        state   = self._get_or_create_state(ticker)
        eval_ct = state.increment_eval()

        snap_map = state.snapshot_map()
        avail    = state.available_engines()
        ages     = state.engine_ages()

        # 1. Aggregate intelligence
        intel = self._aggregator.aggregate(
            ticker=ticker,
            snapshot_map=snap_map,
            company_name=self._get_meta(ticker, "company_name"),
        )

        # 2. Compute overall score
        overall = self._aggregator.overall_score(intel)

        # 3. Consistency validation
        validation_report = self._validator.validate(ticker, intel)

        # 4. Conflict detection and resolution
        conflicts = self._conflict_eng.process(ticker, intel, engine_ages=ages)

        n_conflicts  = len(conflicts)
        n_critical   = self._conflict_eng.critical_count(conflicts)

        # 5. Quality assessment
        quality = compute_company_quality(
            ticker=ticker,
            available_engines=avail,
            engine_ages=ages,
            validation_report=validation_report,
            conflict_count=n_conflicts,
            critical_conflicts=n_critical,
        )

        # 6. Confidence
        confidence = compute_confidence(
            ticker=ticker,
            completeness=quality.completeness,
            consistency=quality.consistency,
            freshness=quality.freshness,
            conflict_count=n_conflicts,
            critical_conflicts=n_critical,
            eval_count=eval_ct,
            history=self._history,
        )

        # 7. Build summary
        summary = self._aggregator.build_summary(
            ticker=ticker,
            company_name=self._get_meta(ticker, "company_name"),
            intel=intel,
            conflicts=conflicts,
        )

        # 8. Assemble snapshot
        missing = [e for e in SCORED_ENGINES if e not in avail]
        conflict_msgs = [
            f"{c.engine_a} vs {c.engine_b}: {c.assertion_a} | {c.assertion_b}"
            for c in conflicts
        ]

        snapshot = CompanyIntelligenceSnapshot(
            ticker=ticker,
            company_name=self._get_meta(ticker, "company_name"),
            sector=self._get_meta(ticker, "sector"),
            industry=self._get_meta(ticker, "industry"),
            exchange=self._get_meta(ticker, "exchange"),
            generated_at=datetime.now(timezone.utc),
            evaluation_count=eval_ct,
            # Scores
            financial_score=intel.financial_score,
            earnings_score=intel.earnings_score,
            business_quality_score=intel.business_quality_score,
            valuation_score=intel.valuation_score,
            growth_score=intel.growth_score,
            management_score=intel.management_score,
            ownership_score=intel.ownership_score,
            opportunity_score=intel.opportunity_score,
            overall_score=overall,
            # Labels
            financial_label=intel.financial_label,
            earnings_label=intel.earnings_label,
            business_quality_label=intel.business_quality_label,
            valuation_label=intel.valuation_label,
            growth_label=intel.growth_label,
            management_label=intel.management_label,
            ownership_label=intel.ownership_label,
            opportunity_label=intel.opportunity_label,
            # Quality
            completeness=quality.completeness,
            consistency_score=quality.consistency,
            freshness_score=quality.freshness,
            reliability_score=quality.reliability,
            quality_score=quality.quality_score,
            confidence=confidence,
            # Validation
            validation_passed=validation_report.validation_passed,
            validation_report=validation_report,
            conflict_count=n_conflicts,
            critical_conflict_count=n_critical,
            conflict_messages=conflict_msgs,
            # Narrative
            summary=summary,
            key_strengths=summary.key_strengths,
            key_risks=summary.key_risks,
            key_opportunities=summary.key_opportunities,
            alerts=summary.all_alerts(),
            # Coverage
            available_engines=avail,
            missing_engines=missing,
            engine_staleness=ages,
        )

        # 9. Persist
        record_quality(self._quality_history, quality, confidence)
        self._history.record(snapshot)
        self._health.on_evaluation(ticker, avail)

        with self._global_lock:
            self._snapshots[ticker] = snapshot

        return snapshot

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        ticker:      str,
        engine_name: str,
        snapshot:    Any,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> CompanyIntelligenceSnapshot:
        """
        Record a snapshot from a single upstream engine, then re-integrate.
        This is the incremental update path — only one engine changes per call.
        """
        if engine_name not in KNOWN_ENGINES:
            raise ValueError(
                f"Unknown engine '{engine_name}'. Known engines: {list(KNOWN_ENGINES)}"
            )
        state = self._get_or_create_state(ticker)
        state.record_update(engine_name, snapshot)
        self._health.on_engine_update(engine_name)
        self._merge_metadata(ticker, metadata)

        with self._ticker_lock(ticker):
            return self._evaluate(ticker)

    def integrate(
        self,
        ticker:             str,
        financial_snapshot: Any = None,
        earnings_snapshot:  Any = None,
        business_quality:   Any = None,
        valuation_snapshot: Any = None,
        growth_snapshot:    Any = None,
        management_snapshot: Any = None,
        ownership_snapshot: Any = None,
        opportunity_snapshot: Any = None,
        profile_snapshot:   Any = None,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> CompanyIntelligenceSnapshot:
        """
        Convenience method — provide multiple snapshots in one call.
        Records all provided snapshots then runs the integration pipeline once.
        """
        state = self._get_or_create_state(ticker)
        self._merge_metadata(ticker, metadata)

        # Record all provided snapshots (None = skip)
        engine_map: Dict[str, Any] = {
            "financials":       financial_snapshot,
            "earnings":         earnings_snapshot,
            "business_quality": business_quality,
            "valuation":        valuation_snapshot,
            "growth":           growth_snapshot,
            "management":       management_snapshot,
            "ownership":        ownership_snapshot,
            "opportunity":      opportunity_snapshot,
            "profile":          profile_snapshot,
        }
        for engine_name, snap in engine_map.items():
            if snap is not None:
                state.record_update(engine_name, snap)
                self._health.on_engine_update(engine_name)

        with self._ticker_lock(ticker):
            return self._evaluate(ticker)

    # ── Snapshot queries ──────────────────────────────────────────────────────

    def get_snapshot(self, ticker: str) -> Optional[CompanyIntelligenceSnapshot]:
        with self._global_lock:
            return self._snapshots.get(ticker)

    def get_history(
        self,
        ticker: str,
        n:      int = 10,
    ) -> List[CompanyIntelligenceSnapshot]:
        return self._history.get_history(ticker, n=n)

    def get_summary(self, ticker: str):
        snap = self.get_snapshot(ticker)
        return snap.summary if snap else None

    def get_validation_report(self, ticker: str) -> Optional[ValidationReport]:
        snap = self.get_snapshot(ticker)
        return snap.validation_report if snap else None

    def get_conflicts(self, ticker: str, n: int = 10) -> List:
        return self._conflict_eng.get_history(ticker, n=n)

    def get_quality(self, ticker: str) -> Optional[CompanyQualityScore]:
        record = self._quality_history.latest(ticker)
        if record is None:
            return None
        return CompanyQualityScore(
            ticker=record.ticker,
            completeness=record.completeness,
            consistency=record.consistency,
            freshness=record.freshness,
            reliability=record.reliability,
            quality_score=record.quality_score,
            quality_grade="",
            available_engines=record.available_engines,
            conflict_count=record.conflict_count,
        )

    def get_confidence(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.confidence if snap else None

    def get_overall_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.overall_score if snap else None

    def compare(self, tickers: List[str]) -> Dict[str, Optional[CompanyIntelligenceSnapshot]]:
        with self._global_lock:
            return {t: self._snapshots.get(t) for t in tickers}

    def top_tickers(self, n: int = 20) -> List[str]:
        """Return top *n* tickers by overall_score."""
        with self._global_lock:
            scored = sorted(
                self._snapshots.items(),
                key=lambda kv: kv[1].overall_score,
                reverse=True,
            )
            return [ticker for ticker, _ in scored[:n]]

    def search(
        self,
        min_score:    float = 0.0,
        min_quality:  float = 0.0,
        min_confidence: float = 0.0,
        sector:       Optional[str] = None,
        require_complete: bool = False,
    ) -> List[CompanyIntelligenceSnapshot]:
        with self._global_lock:
            results = []
            for snap in self._snapshots.values():
                if snap.overall_score < min_score:
                    continue
                if snap.quality_score < min_quality:
                    continue
                if snap.confidence < min_confidence:
                    continue
                if sector and snap.sector != sector:
                    continue
                if require_complete and not snap.is_complete:
                    continue
                results.append(snap)
            return sorted(results, key=lambda s: s.overall_score, reverse=True)

    # ── Registry queries ──────────────────────────────────────────────────────

    def known_tickers(self) -> List[str]:
        with self._global_lock:
            return list(self._states.keys())

    def population_size(self) -> int:
        with self._global_lock:
            return len(self._states)

    def score_distribution(self) -> Dict[str, float]:
        with self._global_lock:
            if not self._snapshots:
                return {"count": 0}
            scores = [s.overall_score for s in self._snapshots.values()]
            return {
                "count": len(scores),
                "min":   min(scores),
                "max":   max(scores),
                "mean":  round(sum(scores) / len(scores), 2),
            }

    # ── Health APIs ───────────────────────────────────────────────────────────

    def health_report(self) -> Dict[str, Any]:
        return self._health.health_report()

    def engine_health(self, engine_name: str):
        return self._health.engine_health(engine_name)

    def register_consistency_rule(self, rule) -> None:
        """Register a custom cross-engine consistency rule."""
        self._validator.register_rule(rule)
