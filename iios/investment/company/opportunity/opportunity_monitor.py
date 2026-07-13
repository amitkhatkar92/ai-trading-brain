"""iios/investment/company/opportunity/opportunity_monitor.py
OpportunityMonitor — orchestrates monitoring: change detection, alerts, priority.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.company.opportunity.alert_engine import generate_opportunity_alerts
from iios.investment.company.opportunity.change_detector import (
    ChangeRecord, detect_category_change, detect_changes,
    detect_lifecycle_change, score_dict_from_breakdown,
)
from iios.investment.company.opportunity.opportunity_profile import (
    OpportunityAlert, OpportunityCategory, OpportunityLifecycle, OpportunityPriority,
)
from iios.investment.company.opportunity.priority_monitor import PriorityMonitor


class OpportunityMonitor:
    """
    Orchestrates the full monitoring pipeline for every opportunity evaluation.

    Responsibilities:
    - Detect score and component changes between evaluations
    - Detect lifecycle and category transitions
    - Generate structured alerts
    - Track and report priority changes
    - Maintain per-ticker previous-state for delta computation
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._priority_monitor = PriorityMonitor()
        self._prev_scores:    Dict[str, Dict[str, float]] = {}
        self._prev_lifecycle: Dict[str, OpportunityLifecycle] = {}
        self._prev_category:  Dict[str, OpportunityCategory] = {}
        self._prev_overall:   Dict[str, float] = {}
        self._accumulated_alerts: Dict[str, List[OpportunityAlert]] = {}

    def process(
        self,
        ticker:            str,
        overall_score:     float,
        lifecycle:         OpportunityLifecycle,
        category:          OpportunityCategory,
        priority:          OpportunityPriority,
        score_breakdown:   Any,
        fin_score:         float,
        own_score:         float,
        ownership_snapshot: Any = None,
        earnings_snapshot:  Any = None,
        upstream_alerts:    Optional[List[str]] = None,
    ) -> List[OpportunityAlert]:
        """
        Run the full monitoring pipeline for a single ticker evaluation.
        Returns a list of OpportunityAlert objects for this cycle.
        """
        with self._lock:
            prev_scores    = self._prev_scores.get(ticker)
            prev_lifecycle = self._prev_lifecycle.get(ticker)
            prev_category  = self._prev_category.get(ticker)
            prev_overall   = self._prev_overall.get(ticker)

            # ── Change detection ──────────────────────────────────────────────
            cur_scores = score_dict_from_breakdown(score_breakdown)
            changes: List[ChangeRecord] = detect_changes(cur_scores, prev_scores)

            lc_change = detect_lifecycle_change(
                lifecycle.value,
                prev_lifecycle.value if prev_lifecycle else None,
            )
            if lc_change:
                changes.append(lc_change)

            cat_change = detect_category_change(
                category.value,
                prev_category.value if prev_category else None,
            )
            if cat_change:
                changes.append(cat_change)

            # ── Alert generation ──────────────────────────────────────────────
            new_alerts = generate_opportunity_alerts(
                ticker=ticker,
                overall_score=overall_score,
                lifecycle=lifecycle,
                category=category,
                fin_score=fin_score,
                own_score=own_score,
                changes=changes,
                upstream_alerts=upstream_alerts,
                previous_score=prev_overall,
                previous_lifecycle=prev_lifecycle,
                ownership_snapshot=ownership_snapshot,
                earnings_snapshot=earnings_snapshot,
            )

            # ── Priority monitoring ───────────────────────────────────────────
            priority_alert = self._priority_monitor.update(ticker, priority)
            if priority_alert:
                new_alerts.append(priority_alert)

            # ── Update previous state ─────────────────────────────────────────
            self._prev_scores[ticker]    = cur_scores
            self._prev_lifecycle[ticker] = lifecycle
            self._prev_category[ticker]  = category
            self._prev_overall[ticker]   = overall_score

            # ── Accumulate alerts (bounded) ───────────────────────────────────
            if ticker not in self._accumulated_alerts:
                self._accumulated_alerts[ticker] = []
            self._accumulated_alerts[ticker].extend(new_alerts)
            # Keep last 100 alerts per ticker
            if len(self._accumulated_alerts[ticker]) > 100:
                self._accumulated_alerts[ticker] = self._accumulated_alerts[ticker][-100:]

            return new_alerts

    def get_alerts(self, ticker: str, n: int = 20) -> List[OpportunityAlert]:
        with self._lock:
            return list(self._accumulated_alerts.get(ticker, []))[-n:][::-1]

    def get_alert_messages(self, ticker: str, n: int = 20) -> List[str]:
        return [a.message for a in self.get_alerts(ticker, n)]

    def critical_tickers(self) -> List[str]:
        return self._priority_monitor.critical_tickers()

    def high_priority_tickers(self) -> List[str]:
        return self._priority_monitor.high_tickers()
