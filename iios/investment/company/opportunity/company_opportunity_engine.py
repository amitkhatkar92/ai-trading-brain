"""iios/investment/company/opportunity/company_opportunity_engine.py
PRIMARY ENGINE — Institutional Company Opportunity Intelligence Engine.

Consumes from:
  • FinancialSnapshot         (iios.investment.company.financials)
  • EarningsSnapshot          (iios.investment.company.earnings)
  • BusinessQualitySnapshot   (iios.investment.company.business_quality)
  • ValuationSnapshot         (iios.investment.company.valuation)    [optional]
  • GrowthSnapshot            (iios.investment.company.growth)       [optional]
  • ManagementSnapshot        (iios.investment.company.governance)   [optional]
  • OwnershipSnapshot         (iios.investment.company.ownership)    [optional]
  • Market Intelligence       [optional]
  • Risk Snapshot             [optional]

Produces:
  • OpportunitySnapshot

Does NOT:
  • Perform financial analysis, valuation, or market analysis
  • Generate Buy/Sell/Hold recommendations
  • Fetch or parse raw financial data
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.opportunity.classification_engine import ClassificationEngine
from iios.investment.company.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.company.opportunity.explanation_engine import ExplanationEngine
from iios.investment.company.opportunity.lifecycle_tracker import LifecycleTracker
from iios.investment.company.opportunity.opportunity_confidence import (
    compute_opportunity_confidence, explain_confidence,
)
from iios.investment.company.opportunity.opportunity_history import OpportunityHistory
from iios.investment.company.opportunity.opportunity_monitor import OpportunityMonitor
from iios.investment.company.opportunity.opportunity_plugin import (
    OpportunityPlugin, OpportunityPluginRegistry,
)
from iios.investment.company.opportunity.opportunity_profile import (
    OpportunityCategory, OpportunityLifecycle,
)
from iios.investment.company.opportunity.opportunity_score import compute_opportunity_score
from iios.investment.company.opportunity.opportunity_snapshot import OpportunitySnapshot
from iios.investment.company.opportunity.opportunity_statistics import (
    clamp, compute_data_completeness, confidence_to_level, score_to_priority,
    score_to_strength,
)
from iios.investment.company.opportunity.ranking_engine import RankingEngine


class CompanyOpportunityEngine:
    """
    Thread-safe Company Opportunity Intelligence Engine.

    Evaluates companies using intelligence from all upstream engines,
    maintains a live opportunity registry, and exposes rich query APIs.

    One instance should exist per IIOS deployment (singleton encouraged).
    """

    VERSION = "1.0.0"

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # Sub-engines
        self._classifier   = ClassificationEngine()
        self._explainer    = ExplanationEngine()
        self._lifecycle    = LifecycleTracker()
        self._ranking      = RankingEngine()
        self._monitor      = OpportunityMonitor()
        self._history      = OpportunityHistory()
        self._plugin_registry = OpportunityPluginRegistry()

        # Opportunity registry
        self._registry: Dict[str, CompanyOpportunity] = {}

    # ── Primary API ───────────────────────────────────────────────────────────

    def evaluate(
        self,
        ticker:              str,
        financial_snapshot:  Any,                        # FinancialSnapshot (required)
        earnings_snapshot:   Any,                        # EarningsSnapshot  (required)
        business_quality:    Any,                        # BusinessQualitySnapshot (required)
        valuation_snapshot:  Any = None,                 # Optional[ValuationSnapshot]
        growth_snapshot:     Any = None,                 # Optional[GrowthSnapshot]
        management_snapshot: Any = None,                 # Optional[ManagementSnapshot]
        ownership_snapshot:  Any = None,                 # Optional[OwnershipSnapshot]
        market_intelligence: Any = None,                 # Optional market data
        risk_snapshot:       Any = None,                 # Optional risk intelligence
        company_metadata:    Optional[Dict] = None,      # name, sector, industry, exchange
    ) -> OpportunitySnapshot:
        """
        Evaluate a company and return an OpportunitySnapshot.

        Thread-safe — may be called concurrently for different tickers.
        """
        with self._lock:
            meta = company_metadata or {}

            # ── Ensure registry entry ─────────────────────────────────────────
            opp = self._ensure_registry_entry(ticker, meta)
            opp.evaluation_count += 1

            # ── Compute composite score ───────────────────────────────────────
            breakdown = compute_opportunity_score(
                financial_snapshot=financial_snapshot,
                earnings_snapshot=earnings_snapshot,
                business_quality=business_quality,
                valuation_snapshot=valuation_snapshot,
                growth_snapshot=growth_snapshot,
                management_snapshot=management_snapshot,
                ownership_snapshot=ownership_snapshot,
                risk_snapshot=risk_snapshot,
                market_intelligence=market_intelligence,
            )
            overall_score = breakdown.final_score
            opp.record_score(overall_score)
            score_trend = opp.score_trend

            # ── Score history for confidence ──────────────────────────────────
            score_history = opp.score_history

            # ── Compute confidence ────────────────────────────────────────────
            confidence = compute_opportunity_confidence(
                financial_snapshot=financial_snapshot,
                earnings_snapshot=earnings_snapshot,
                business_quality=business_quality,
                valuation_snapshot=valuation_snapshot,
                growth_snapshot=growth_snapshot,
                management_snapshot=management_snapshot,
                ownership_snapshot=ownership_snapshot,
                score_history=score_history,
            )

            # ── Lifecycle ─────────────────────────────────────────────────────
            lifecycle = self._lifecycle.update(
                ticker=ticker,
                score=overall_score,
                confidence=confidence,
                score_trend=score_trend,
            )
            opp.lifecycle_state = lifecycle

            # ── Classification ────────────────────────────────────────────────
            comp = breakdown.components()
            bq_sc   = comp[2].score  # business_quality
            val_sc  = comp[3].score  # valuation_attractiveness
            grw_sc  = comp[4].score  # growth_quality
            mgmt_sc = comp[5].score  # management_quality
            fin_sc  = comp[0].score  # financial_strength
            ear_sc  = comp[1].score  # earnings_quality
            own_sc  = comp[6].score  # ownership_quality

            div_yield   = _extract_dividend_yield(financial_snapshot, earnings_snapshot)
            payout      = _extract_payout_ratio(financial_snapshot, earnings_snapshot)

            classification = self._classifier.classify(
                overall_score=overall_score,
                bq_score=bq_sc, val_score=val_sc, grw_score=grw_sc,
                mgmt_score=mgmt_sc, fin_score=fin_sc, ear_score=ear_sc,
                own_score=own_sc,
                earnings_snapshot=earnings_snapshot,
                business_quality=business_quality,
                valuation_snapshot=valuation_snapshot,
                growth_snapshot=growth_snapshot,
                dividend_yield=div_yield,
                payout_ratio=payout,
            )
            opp.primary_category = classification.primary

            # ── Strength, Priority ────────────────────────────────────────────
            strength = score_to_strength(overall_score)
            priority = score_to_priority(overall_score, lifecycle)
            opp.priority = priority

            # ── Thesis ───────────────────────────────────────────────────────
            upstream_alerts = self._collect_upstream_alerts(
                ownership_snapshot, management_snapshot
            )
            thesis = self._explainer.generate(
                ticker=ticker,
                category=classification.primary,
                lifecycle=lifecycle,
                strength=strength,
                overall_score=overall_score,
                bq_score=bq_sc, val_score=val_sc, grw_score=grw_sc,
                mgmt_score=mgmt_sc, fin_score=fin_sc, own_score=own_sc,
                confidence=confidence,
                alerts=upstream_alerts,
                financial_snapshot=financial_snapshot,
                earnings_snapshot=earnings_snapshot,
                business_quality=business_quality,
                valuation_snapshot=valuation_snapshot,
                growth_snapshot=growth_snapshot,
                management_snapshot=management_snapshot,
                ownership_snapshot=ownership_snapshot,
            )

            # ── Ranking ───────────────────────────────────────────────────────
            ranking_result = self._ranking.update(
                ticker=ticker,
                score=overall_score,
                sector=opp.sector,
                industry=opp.industry,
            )

            # ── Monitoring ────────────────────────────────────────────────────
            alerts = self._monitor.process(
                ticker=ticker,
                overall_score=overall_score,
                lifecycle=lifecycle,
                category=classification.primary,
                priority=priority,
                score_breakdown=breakdown,
                fin_score=fin_sc,
                own_score=own_sc,
                ownership_snapshot=ownership_snapshot,
                earnings_snapshot=earnings_snapshot,
                upstream_alerts=upstream_alerts,
            )

            # ── Plugin adjustments ────────────────────────────────────────────
            plugin_inputs = {
                "ticker": ticker, "overall_score": overall_score,
                "primary_category": classification.primary, "lifecycle": lifecycle,
                "confidence": confidence, "score_breakdown": breakdown,
                "financial_snapshot": financial_snapshot,
                "earnings_snapshot": earnings_snapshot,
                "business_quality": business_quality,
                "valuation_snapshot": valuation_snapshot,
                "growth_snapshot": growth_snapshot,
                "management_snapshot": management_snapshot,
                "ownership_snapshot": ownership_snapshot,
                "market_intelligence": market_intelligence,
                "risk_snapshot": risk_snapshot,
            }
            plugin_results = self._plugin_registry.run_all(plugin_inputs)
            score_adj = sum(
                r.get("score_adjustment", 0.0)
                for r in plugin_results
            )
            if score_adj != 0.0:
                overall_score = clamp(overall_score + score_adj)
                breakdown.final_score = round(overall_score, 2)

            for r in plugin_results:
                for msg in r.get("alerts", []):
                    from iios.investment.company.opportunity.opportunity_profile import (
                        AlertSeverity, OpportunityAlert,
                    )
                    alerts.append(OpportunityAlert(
                        message=msg,
                        severity=AlertSeverity.MEDIUM,
                        source="plugin",
                        generated_at=datetime.now(timezone.utc),
                    ))

            # ── Confidence level and data completeness ────────────────────────
            conf_level = confidence_to_level(confidence)
            avail_count = sum([
                financial_snapshot is not None, earnings_snapshot is not None,
                business_quality is not None, valuation_snapshot is not None,
                growth_snapshot is not None, management_snapshot is not None,
                ownership_snapshot is not None,
            ])
            data_completeness = compute_data_completeness(avail_count, 7)

            # ── Assemble snapshot ─────────────────────────────────────────────
            snapshot = OpportunitySnapshot(
                ticker=ticker,
                opportunity_id=opp.opportunity_id,
                company_name=opp.company_name,
                sector=opp.sector,
                industry=opp.industry,
                exchange=opp.exchange,
                generated_at=datetime.now(timezone.utc),
                discovery_time=opp.discovery_time,
                primary_category=classification.primary,
                secondary_categories=classification.secondary,
                lifecycle=lifecycle,
                priority=priority,
                score_breakdown=breakdown,
                overall_score=overall_score,
                strength=strength,
                confidence=confidence,
                confidence_level=conf_level,
                data_completeness=data_completeness,
                thesis=thesis,
                ranking=ranking_result,
                alerts=alerts,
                data_sources=self._build_data_sources(
                    financial_snapshot, earnings_snapshot, business_quality,
                    valuation_snapshot, growth_snapshot,
                    management_snapshot, ownership_snapshot,
                    market_intelligence, risk_snapshot,
                ),
                evaluation_count=opp.evaluation_count,
            )

            opp.last_snapshot = snapshot
            self._history.record(snapshot)
            return snapshot

    # ── Query APIs ────────────────────────────────────────────────────────────

    def get_snapshot(self, ticker: str) -> Optional[OpportunitySnapshot]:
        with self._lock:
            opp = self._registry.get(ticker)
            return opp.last_snapshot if opp else None

    def get_top_companies(
        self,
        n:        int = 20,
        category: Optional[str] = None,
        sector:   Optional[str] = None,
        industry: Optional[str] = None,
    ) -> List[OpportunitySnapshot]:
        """Return top-*n* opportunity snapshots, optionally filtered."""
        with self._lock:
            tickers = self._ranking.get_top(n=n * 2, sector=sector, industry=industry)
            snapshots = []
            for t in tickers:
                opp = self._registry.get(t)
                if opp and opp.last_snapshot:
                    snap = opp.last_snapshot
                    if category and snap.primary_category.value != category:
                        continue
                    snapshots.append(snap)
                if len(snapshots) >= n:
                    break
            return snapshots

    def get_opportunity_rank(self, ticker: str) -> Optional[int]:
        with self._lock:
            return self._ranking.get_global_rank(ticker)

    def get_investment_thesis(self, ticker: str) -> Optional[Any]:
        with self._lock:
            opp = self._registry.get(ticker)
            if opp and opp.last_snapshot:
                return opp.last_snapshot.thesis
            return None

    def search_opportunities(
        self,
        min_score:  float = 0.0,
        category:   Optional[str] = None,
        sector:     Optional[str] = None,
        lifecycle:  Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[OpportunitySnapshot]:
        """Return all snapshots matching the given filter criteria."""
        with self._lock:
            results = []
            for opp in self._registry.values():
                snap = opp.last_snapshot
                if snap is None:
                    continue
                if snap.overall_score < min_score:
                    continue
                if snap.confidence < min_confidence:
                    continue
                if category and snap.primary_category.value != category:
                    continue
                if sector and snap.sector != sector:
                    continue
                if lifecycle and snap.lifecycle.value != lifecycle:
                    continue
                results.append(snap)
            return sorted(results, key=lambda s: s.overall_score, reverse=True)

    def compare_companies(
        self, tickers: List[str]
    ) -> Dict[str, Optional[OpportunitySnapshot]]:
        """Return snapshots for each ticker keyed by ticker."""
        with self._lock:
            return {t: self.get_snapshot(t) for t in tickers}

    def get_sector_opportunities(
        self, sector: str, n: int = 20
    ) -> List[OpportunitySnapshot]:
        return self.get_top_companies(n=n, sector=sector)

    def get_industry_opportunities(
        self, industry: str, n: int = 20
    ) -> List[OpportunitySnapshot]:
        return self.get_top_companies(n=n, industry=industry)

    def get_watchlist(self) -> List[OpportunitySnapshot]:
        with self._lock:
            watchlisted = [
                opp.last_snapshot
                for opp in self._registry.values()
                if opp.is_watchlisted and opp.last_snapshot is not None
            ]
            return sorted(watchlisted, key=lambda s: s.overall_score, reverse=True)

    def get_history(self, ticker: str, n: int = 10) -> List[OpportunitySnapshot]:
        return self._history.get_history(ticker, n)

    def get_alerts(self, ticker: str) -> List[str]:
        """Return all current alert messages for *ticker*, including plugin alerts."""
        with self._lock:
            opp = self._registry.get(ticker)
            if opp and opp.last_snapshot:
                return [a.message for a in opp.last_snapshot.alerts]
        return self._monitor.get_alert_messages(ticker)

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._registry.keys())

    def population_size(self) -> int:
        with self._lock:
            return len(self._registry)

    def score_distribution(self) -> Dict[str, float]:
        return self._ranking.score_distribution()

    # ── Watchlist management ──────────────────────────────────────────────────

    def add_to_watchlist(
        self, ticker: str, notes: str = "", tags: Optional[List[str]] = None
    ) -> bool:
        with self._lock:
            opp = self._registry.get(ticker)
            if opp is None:
                return False
            opp.add_to_watchlist(notes=notes, tags=tags)
            return True

    def remove_from_watchlist(self, ticker: str) -> bool:
        with self._lock:
            opp = self._registry.get(ticker)
            if opp is None:
                return False
            opp.remove_from_watchlist()
            return True

    # ── Plugin management ─────────────────────────────────────────────────────

    def register_plugin(self, plugin: OpportunityPlugin) -> None:
        with self._lock:
            self._plugin_registry.register(plugin)

    # ── Utility ───────────────────────────────────────────────────────────────

    def _ensure_registry_entry(
        self, ticker: str, meta: Dict
    ) -> CompanyOpportunity:
        if ticker not in self._registry:
            opp_id = f"opp-{ticker.lower().replace('.', '-')}-{uuid.uuid4().hex[:6]}"
            self._registry[ticker] = CompanyOpportunity(
                ticker=ticker,
                opportunity_id=opp_id,
            )
        opp = self._registry[ticker]
        if meta.get("company_name") and not opp.company_name:
            opp.company_name = meta["company_name"]
        if meta.get("sector") and not opp.sector:
            opp.sector = meta["sector"]
        if meta.get("industry") and not opp.industry:
            opp.industry = meta["industry"]
        if meta.get("exchange") and not opp.exchange:
            opp.exchange = meta["exchange"]
        return opp

    @staticmethod
    def _collect_upstream_alerts(
        ownership_snapshot:  Any,
        management_snapshot: Any,
    ) -> List[str]:
        alerts: List[str] = []
        if ownership_snapshot is not None:
            own_alerts = getattr(ownership_snapshot, "alerts", None)
            if own_alerts is None:
                risk = getattr(ownership_snapshot, "ownership_risk", None)
                own_alerts = getattr(risk, "alerts", []) if risk else []
            if own_alerts:
                alerts.extend(str(a) for a in own_alerts[:3])
        if management_snapshot is not None:
            mgmt_flags = getattr(management_snapshot, "flags", [])
            if mgmt_flags:
                alerts.extend(str(f) for f in mgmt_flags[:2])
        return alerts

    @staticmethod
    def _build_data_sources(
        financial:   Any, earnings:   Any, bq: Any,
        valuation:   Any, growth:     Any, management: Any,
        ownership:   Any, market_int: Any, risk: Any,
    ) -> List[str]:
        sources = []
        if financial   is not None: sources.append("financials")
        if earnings    is not None: sources.append("earnings")
        if bq          is not None: sources.append("business_quality")
        if valuation   is not None: sources.append("valuation")
        if growth      is not None: sources.append("growth")
        if management  is not None: sources.append("management")
        if ownership   is not None: sources.append("ownership")
        if market_int  is not None: sources.append("market_intelligence")
        if risk        is not None: sources.append("risk")
        return sources

    @staticmethod
    def _extract_dividend_yield_static(
        fin: Any, ear: Any
    ) -> Optional[float]:
        return _extract_dividend_yield(fin, ear)


def _extract_dividend_yield(fin: Any, ear: Any) -> Optional[float]:
    """Try to extract dividend yield from financial ratios dict."""
    if fin is not None:
        ratios = getattr(fin, "ratios", {}) or {}
        dy = ratios.get("dividend_yield") or ratios.get("div_yield")
        if dy is not None:
            try:
                return float(dy)
            except (TypeError, ValueError):
                pass
    return None


def _extract_payout_ratio(fin: Any, ear: Any) -> Optional[float]:
    if fin is not None:
        ratios = getattr(fin, "ratios", {}) or {}
        pr = ratios.get("dividend_payout_ratio") or ratios.get("payout_ratio")
        if pr is not None:
            try:
                return float(pr)
            except (TypeError, ValueError):
                pass
    return None
