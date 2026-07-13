"""iios/investment/company/opportunity/alert_engine.py
Generates structured alerts based on opportunity conditions and changes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from iios.investment.company.opportunity.change_detector import ChangeRecord
from iios.investment.company.opportunity.opportunity_profile import (
    AlertSeverity, OpportunityAlert, OpportunityCategory, OpportunityLifecycle,
)


def generate_opportunity_alerts(
    ticker:            str,
    overall_score:     float,
    lifecycle:         OpportunityLifecycle,
    category:          OpportunityCategory,
    fin_score:         float,
    own_score:         float,
    changes:           Optional[List[ChangeRecord]] = None,
    upstream_alerts:   Optional[List[str]] = None,
    previous_score:    Optional[float] = None,
    previous_lifecycle: Optional[OpportunityLifecycle] = None,
    ownership_snapshot: Any = None,
    earnings_snapshot:  Any = None,
) -> List[OpportunityAlert]:
    """
    Generate a list of OpportunityAlerts for the current evaluation.
    """
    now = datetime.now(timezone.utc)
    alerts: List[OpportunityAlert] = []

    # ── Score-based thresholds ────────────────────────────────────────────────
    if overall_score < 35:
        alerts.append(OpportunityAlert(
            message=f"{ticker}: Overall opportunity score has fallen to {overall_score:.0f} — below active threshold",
            severity=AlertSeverity.HIGH,
            source="score",
            generated_at=now,
        ))

    # ── Score deterioration ───────────────────────────────────────────────────
    if previous_score is not None:
        delta = overall_score - previous_score
        if delta <= -10:
            alerts.append(OpportunityAlert(
                message=(
                    f"{ticker}: Significant score decline of {abs(delta):.1f} points "
                    f"({previous_score:.0f} → {overall_score:.0f})"
                ),
                severity=AlertSeverity.HIGH if delta <= -15 else AlertSeverity.MEDIUM,
                source="score",
                generated_at=now,
            ))

    # ── Lifecycle transitions ─────────────────────────────────────────────────
    if previous_lifecycle and lifecycle != previous_lifecycle:
        if lifecycle in (OpportunityLifecycle.WEAKENING, OpportunityLifecycle.EXPIRED):
            alerts.append(OpportunityAlert(
                message=(
                    f"{ticker}: Lifecycle transitioned to {lifecycle.value} "
                    f"(was {previous_lifecycle.value})"
                ),
                severity=AlertSeverity.HIGH,
                source="lifecycle",
                generated_at=now,
            ))
        elif lifecycle == OpportunityLifecycle.HIGH_CONVICTION:
            alerts.append(OpportunityAlert(
                message=f"{ticker}: Reached HIGH CONVICTION lifecycle — elevated signal quality",
                severity=AlertSeverity.INFO,
                source="lifecycle",
                generated_at=now,
            ))
        elif lifecycle == OpportunityLifecycle.CONFIRMED:
            alerts.append(OpportunityAlert(
                message=f"{ticker}: Opportunity CONFIRMED — sustained high-conviction evaluation",
                severity=AlertSeverity.INFO,
                source="lifecycle",
                generated_at=now,
            ))

    # ── Financial distress ────────────────────────────────────────────────────
    if fin_score < 30:
        alerts.append(OpportunityAlert(
            message=f"{ticker}: Financial health score critically low ({fin_score:.0f}/100)",
            severity=AlertSeverity.CRITICAL,
            source="financial",
            generated_at=now,
        ))

    # ── Ownership risk ────────────────────────────────────────────────────────
    if ownership_snapshot is not None:
        pledge = getattr(ownership_snapshot, "promoter_pledge_pct", None)
        if pledge is not None and float(pledge) >= 50:
            alerts.append(OpportunityAlert(
                message=f"{ticker}: Promoter pledge {pledge:.0f}% — significant ownership risk",
                severity=AlertSeverity.HIGH,
                source="ownership",
                generated_at=now,
            ))

    # ── Earnings risk ─────────────────────────────────────────────────────────
    if earnings_snapshot is not None:
        is_profitable = getattr(earnings_snapshot, "is_profitable", True)
        if not is_profitable:
            alerts.append(OpportunityAlert(
                message=f"{ticker}: Company is currently unprofitable — monitor earnings recovery",
                severity=AlertSeverity.MEDIUM,
                source="earnings",
                generated_at=now,
            ))

    # ── Component-level changes ───────────────────────────────────────────────
    if changes:
        adverse = [c for c in changes if c.is_adverse and c.magnitude >= 10]
        for chg in adverse[:2]:
            alerts.append(OpportunityAlert(
                message=(
                    f"{ticker}: {chg.dimension} deteriorated significantly "
                    f"({chg.from_value} → {chg.to_value}, Δ{chg.magnitude:.1f})"
                ),
                severity=AlertSeverity.MEDIUM,
                source="change_detector",
                generated_at=now,
            ))

    # ── Propagate upstream alerts ─────────────────────────────────────────────
    if upstream_alerts:
        for msg in upstream_alerts[:3]:
            alerts.append(OpportunityAlert(
                message=msg,
                severity=AlertSeverity.MEDIUM,
                source="upstream",
                generated_at=now,
            ))

    return alerts
