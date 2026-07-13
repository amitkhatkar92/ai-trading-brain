"""iios/investment/company/ownership/control_risk.py
Control structure risk analysis.
"""
from __future__ import annotations

from typing import Any, Optional

from iios.investment.company.ownership.ownership_statistics import clamp, pct_to_100


def score_control_risk(
    promoter_pct:         Optional[float],
    is_family_controlled: bool = False,
    ceo_chairman_same:    bool = False,
    govt_holding_pct:     Optional[float] = None,
) -> float:
    """
    Control risk score (0-100; higher = more risky from minority perspective).
    """
    risk = 25.0   # moderate base

    if promoter_pct is not None:
        pp = pct_to_100(promoter_pct) or 0.0
        if pp >= 75:
            risk += 25.0   # single entity controls company
        elif pp >= 60:
            risk += 15.0
        elif pp <= 15:
            risk += 10.0   # diffuse ownership → proxy contests possible

    if is_family_controlled:
        risk += 15.0

    if ceo_chairman_same:
        risk += 10.0

    if govt_holding_pct is not None:
        gp = pct_to_100(govt_holding_pct) or 0.0
        if gp >= 50:
            risk += 15.0   # government control → political risk

    return clamp(risk)


def score_minority_protection(
    board_independence_ratio: Optional[float],
    audit_committee_independent: Optional[bool],
    institutional_pct: Optional[float],
) -> float:
    """
    Score minority shareholder protection quality (0-100; higher = better protected).
    """
    score = 40.0

    if board_independence_ratio is not None:
        r = pct_to_100(board_independence_ratio) or 0.0
        if r >= 60:
            score += 30.0
        elif r >= 40:
            score += 20.0
        elif r >= 25:
            score += 10.0

    if audit_committee_independent is True:
        score += 15.0

    if institutional_pct is not None:
        ip = pct_to_100(institutional_pct) or 0.0
        if ip >= 25:
            score += 15.0   # institutional watchdogs provide oversight
        elif ip >= 10:
            score += 8.0

    return clamp(score)


def score_hostile_takeover_exposure(
    promoter_pct:      Optional[float],
    free_float_pct:    Optional[float],
    institutional_pct: Optional[float],
) -> float:
    """
    Risk of hostile takeover (0-100; higher = more exposed).
    Low promoter + high free float + low institutional = vulnerable.
    """
    risk = 20.0

    if promoter_pct is not None:
        pp = pct_to_100(promoter_pct) or 0.0
        if pp < 20:
            risk += 35.0
        elif pp < 35:
            risk += 20.0
        elif pp >= 51:
            risk -= 15.0   # majority control → hostile takeover nearly impossible

    if free_float_pct is not None:
        ff = pct_to_100(free_float_pct) or 0.0
        if ff >= 60:
            risk += 15.0
        elif ff <= 20:
            risk -= 10.0

    if institutional_pct is not None:
        ip = pct_to_100(institutional_pct) or 0.0
        # Institutions are swing votes in takeover scenarios
        if ip >= 40:
            risk += 5.0   # large institutional block = swing vote risk
        elif ip <= 5:
            risk += 5.0   # very low institutional = weaker oversight

    return clamp(risk)
