"""iios/investment/company/earnings/earnings_momentum.py
Short-term earnings momentum — latest period vs recent trailing average.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport, MomentumLabel
from iios.investment.company.earnings.earnings_snapshot import EarningsMomentumProfile
from iios.investment.company.earnings.earnings_statistics import _clean


_STRONG_POS = 0.15   # +15% above trailing avg = strong positive
_POS        = 0.05   # +5%
_NEG        = -0.05
_STRONG_NEG = -0.15


def _momentum_score(ratio: Optional[float]) -> float:
    """Convert (current-avg)/avg ratio to 0–100 score."""
    if ratio is None:
        return 50.0
    clamped = max(-1.0, min(1.0, ratio))
    return 50.0 + 50.0 * clamped


def _label(ratio: Optional[float]) -> MomentumLabel:
    if ratio is None:
        return MomentumLabel.INSUFFICIENT
    if ratio >= _STRONG_POS:
        return MomentumLabel.STRONG_POSITIVE
    if ratio >= _POS:
        return MomentumLabel.POSITIVE
    if ratio <= _STRONG_NEG:
        return MomentumLabel.STRONG_NEGATIVE
    if ratio <= _NEG:
        return MomentumLabel.NEGATIVE
    return MomentumLabel.NEUTRAL


class EarningsMomentumAnalyzer:
    """Computes earnings momentum from trailing history."""

    def analyze(
        self,
        history: List[EarningsReport],
        trailing: int = 4,
    ) -> EarningsMomentumProfile:
        p = EarningsMomentumProfile()
        if not history or len(history) < 2:
            return p

        p.periods_used = len(history)

        # Use all-but-last for trailing average; last for current
        current   = history[-1]
        prior     = history[-min(trailing + 1, len(history)):-1]

        def _momentum(field: str) -> Optional[float]:
            curr_val = getattr(current, field, None)
            if callable(curr_val):
                curr_val = curr_val()
            trail_vals = _clean([
                getattr(r, field, None) if not callable(getattr(r, field, None))
                else getattr(r, field, None)()
                for r in prior
            ])
            if curr_val is None or not trail_vals:
                return None
            avg = sum(trail_vals) / len(trail_vals)
            if avg == 0:
                return None
            return (curr_val - avg) / abs(avg)

        eps_mom     = _momentum("diluted_eps") if current.diluted_eps is not None else None
        if eps_mom is None:
            eps_mom = _momentum("basic_eps")

        margin_mom  = _momentum("net_margin")
        revenue_mom = _momentum("revenue")

        p.eps_momentum     = eps_mom
        p.margin_momentum  = margin_mom
        p.revenue_momentum = revenue_mom

        # Composite momentum score
        scores = []
        for val in [eps_mom, margin_mom, revenue_mom]:
            scores.append(_momentum_score(val))
        if scores:
            p.score = sum(scores) / len(scores)

        # Label based on EPS momentum (primary signal)
        p.label = _label(eps_mom if eps_mom is not None else margin_mom)

        return p
