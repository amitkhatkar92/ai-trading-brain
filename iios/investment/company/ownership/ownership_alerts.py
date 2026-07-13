"""iios/investment/company/ownership/ownership_alerts.py
Ownership alert generation.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.ownership.ownership_statistics import pct_to_100


def generate_ownership_alerts(
    promoter_pledge_pct:    Optional[float] = None,
    promoter_change_3m:     Optional[float] = None,
    promoter_change_1y:     Optional[float] = None,
    control_risk_score:     float = 0.0,
    concentration_risk_score: float = 0.0,
    dilution_risk_score:    float = 0.0,
    pledge_risk_score:      float = 0.0,
    free_float_pct:         Optional[float] = None,
    esop_outstanding_pct:   Optional[float] = None,
    insider_activity_label: Optional[str] = None,
    institutional_pct:      Optional[float] = None,
    promoter_pct:           Optional[float] = None,
) -> List[str]:
    """
    Generate informational ownership alert messages.
    These are data-driven observations, NOT recommendations.
    """
    alerts: List[str] = []

    # Pledge risk
    if promoter_pledge_pct is not None:
        pp = pct_to_100(promoter_pledge_pct) or 0.0
        if pp >= 50:
            alerts.append(
                f"CRITICAL: {pp:.0f}% of promoter holding is pledged — "
                "forced selling risk is elevated."
            )
        elif pp >= 25:
            alerts.append(
                f"ALERT: {pp:.0f}% promoter pledge detected — "
                "monitor for margin call events."
            )

    # Promoter selling trend
    if promoter_change_1y is not None and promoter_change_1y <= -5.0:
        alerts.append(
            f"ALERT: Promoter holding declined {abs(promoter_change_1y):.1f}pp "
            "over the past year."
        )
    if promoter_change_3m is not None and promoter_change_3m <= -3.0:
        alerts.append(
            f"ALERT: Rapid promoter selling — {abs(promoter_change_3m):.1f}pp decline "
            "in 3 months."
        )

    # Free float liquidity
    if free_float_pct is not None:
        ff = pct_to_100(free_float_pct) or 0.0
        if ff < 10:
            alerts.append(
                f"ALERT: Very low free float ({ff:.0f}%) — "
                "liquidity risk is high."
            )

    # ESOP dilution
    if esop_outstanding_pct is not None:
        ep = pct_to_100(esop_outstanding_pct) or 0.0
        if ep >= 8:
            alerts.append(
                f"ALERT: ESOP overhang ({ep:.1f}% outstanding) — "
                "material dilution risk for shareholders."
            )

    # Control concentration
    if control_risk_score >= 75:
        alerts.append(
            "ALERT: High control concentration risk — "
            "minority shareholder protection may be limited."
        )

    # Insider distributing
    if insider_activity_label == "liquidating":
        alerts.append(
            "ALERT: Insiders are liquidating positions — "
            "significant net selling by management detected."
        )

    # Very low institutional participation
    if institutional_pct is not None:
        ip = pct_to_100(institutional_pct) or 0.0
        if ip < 5:
            alerts.append(
                f"INFO: Institutional participation is very low ({ip:.0f}%) — "
                "limited institutional oversight."
            )

    # Aggregate risk thresholds
    if concentration_risk_score >= 80:
        alerts.append(
            "ALERT: Ownership concentration risk is critical — "
            "market liquidity may be structurally constrained."
        )

    if pledge_risk_score >= 80:
        alerts.append(
            "CRITICAL: Promoter pledge risk is critical — "
            "evaluate exposure before position sizing."
        )

    return alerts
