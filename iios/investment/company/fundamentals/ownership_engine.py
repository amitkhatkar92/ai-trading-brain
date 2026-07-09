"""iios/investment/company/fundamentals/ownership_engine.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import (
    HIGH_PLEDGE_THRESHOLD,
    HIGH_PROMOTER_THRESHOLD,
    LOW_INSTITUTIONAL_THRESHOLD,
    OwnershipConcentration,
)


@dataclass
class OwnershipAnalysis:
    promoter_holding:      float                = 0.0
    institutional_holding: float                = 0.0
    retail_holding:        float                = 0.0
    promoter_pledge_pct:   float                = 0.0
    promoter_change_qoq:   float                = 0.0
    concentration:         OwnershipConcentration = OwnershipConcentration.UNKNOWN
    ownership_score:       float                = 50.0   # 0–100
    metadata:              dict[str, Any]        = field(default_factory=dict)

    @property
    def high_pledge(self) -> bool:
        return self.promoter_pledge_pct > HIGH_PLEDGE_THRESHOLD * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "promoter_holding":      self.promoter_holding,
            "institutional_holding": self.institutional_holding,
            "retail_holding":        self.retail_holding,
            "promoter_pledge_pct":   self.promoter_pledge_pct,
            "promoter_change_qoq":   self.promoter_change_qoq,
            "high_pledge":           self.high_pledge,
            "concentration":         self.concentration.value,
            "ownership_score":       self.ownership_score,
            "metadata":              self.metadata,
        }


class OwnershipEngine:
    """
    Analyses promoter and institutional ownership patterns.

    Expected keys (all optional, values in %, e.g. 55.2 = 55.2%):
      promoter_holding, institutional_holding, retail_holding,
      promoter_pledge, promoter_change_qoq
    """

    def analyze(self, data: dict[str, Any]) -> OwnershipAnalysis:
        if not data:
            return OwnershipAnalysis()

        promoter  = float(data.get("promoter_holding", 0) or 0)
        inst      = float(data.get("institutional_holding", 0) or 0)
        retail    = float(data.get("retail_holding", 0) or 0)
        pledge    = float(data.get("promoter_pledge", 0) or 0)
        change    = float(data.get("promoter_change_qoq", 0) or 0)

        # Convert to fractions for threshold comparison
        p_frac = promoter / 100.0
        i_frac = inst     / 100.0
        pledge_frac = pledge / 100.0

        concentration = self._classify_concentration(p_frac)
        score         = self._score(p_frac, i_frac, pledge_frac, change)

        return OwnershipAnalysis(
            promoter_holding      = round(promoter, 2),
            institutional_holding = round(inst, 2),
            retail_holding        = round(retail, 2),
            promoter_pledge_pct   = round(pledge, 2),
            promoter_change_qoq   = round(change, 2),
            concentration         = concentration,
            ownership_score       = round(score, 2),
            metadata              = {"n_items": len(data)},
        )

    @staticmethod
    def _classify_concentration(p_frac: float) -> OwnershipConcentration:
        if p_frac >= HIGH_PROMOTER_THRESHOLD:
            return OwnershipConcentration.CONCENTRATED
        elif p_frac >= 0.25:
            return OwnershipConcentration.MODERATE
        else:
            return OwnershipConcentration.DISTRIBUTED

    @staticmethod
    def _score(
        p_frac:     float,
        i_frac:     float,
        pledge_frac: float,
        change:     float,
    ) -> float:
        # Promoter holding component (40%): 50–75% ideal
        if 0.50 <= p_frac <= 0.75:
            p_score = 100.0
        elif 0.35 <= p_frac < 0.50:
            p_score = 75.0
        elif p_frac > 0.75:
            p_score = 60.0   # very high can be lock-in risk
        elif p_frac >= 0.20:
            p_score = 50.0
        else:
            p_score = 20.0

        # Institutional holding component (25%): higher = better governance
        if i_frac >= 0.30:
            i_score = 100.0
        elif i_frac >= 0.15:
            i_score = 70.0
        elif i_frac >= LOW_INSTITUTIONAL_THRESHOLD:
            i_score = 40.0
        else:
            i_score = 10.0

        # Pledge component (25%): lower = better
        if pledge_frac <= 0.02:
            pledge_score = 100.0
        elif pledge_frac <= HIGH_PLEDGE_THRESHOLD:
            pledge_score = 50.0
        else:
            pledge_score = 0.0

        # Change component (10%): positive = promoter buying = bullish
        if change > 0:
            chg_score = 80.0
        elif change >= -0.01:
            chg_score = 50.0
        else:
            chg_score = 20.0

        return (
            p_score      * 0.40
            + i_score    * 0.25
            + pledge_score * 0.25
            + chg_score  * 0.10
        )
