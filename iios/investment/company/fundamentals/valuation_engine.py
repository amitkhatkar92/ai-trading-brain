"""iios/investment/company/fundamentals/valuation_engine.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import ValuationStatus


@dataclass
class ValuationAnalysis:
    pe:              float | None   = None
    pb:              float | None   = None
    ev_ebitda:       float | None   = None
    price_to_sales:  float | None   = None
    status:          ValuationStatus = ValuationStatus.UNKNOWN
    valuation_score: float          = 50.0   # 0–100; higher = cheaper
    metadata:        dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pe":              self.pe,
            "pb":              self.pb,
            "ev_ebitda":       self.ev_ebitda,
            "price_to_sales":  self.price_to_sales,
            "status":          self.status.value,
            "valuation_score": self.valuation_score,
            "metadata":        self.metadata,
        }


class ValuationEngine:
    """
    Classifies company valuation from multiples.

    Expected keys in data (all optional):
      price, market_cap, pe, pb, ev, ebitda, revenue
    """

    # PE thresholds: deeply_under | under | fair | over | deeply_over
    _PE_BANDS  = [10.0,  15.0, 25.0, 40.0]
    _PB_BANDS  = [1.0,   2.0,  4.0,  8.0]
    _EV_BANDS  = [6.0,   10.0, 18.0, 30.0]
    _PS_BANDS  = [0.5,   1.5,  4.0,  10.0]

    def analyze(self, data: dict[str, Any]) -> ValuationAnalysis:
        if not data:
            return ValuationAnalysis()

        pe = self._safe(data, "pe")
        pb = self._safe(data, "pb")

        # Compute EV/EBITDA if not provided directly
        ev_ebitda = self._safe(data, "ev_ebitda")
        if ev_ebitda is None:
            ev     = self._safe(data, "ev")
            ebitda = self._safe(data, "ebitda")
            if ev is not None and ebitda and ebitda > 0:
                ev_ebitda = ev / ebitda

        # Compute P/S if not provided
        ps = self._safe(data, "price_to_sales")
        if ps is None:
            mcap    = self._safe(data, "market_cap")
            revenue = self._safe(data, "revenue")
            if mcap is not None and revenue and revenue > 0:
                ps = mcap / revenue

        # Assign band scores for each available metric
        scores: list[float] = []
        if pe is not None and pe > 0:
            scores.append(self._band_score(pe, self._PE_BANDS))
        if pb is not None and pb > 0:
            scores.append(self._band_score(pb, self._PB_BANDS))
        if ev_ebitda is not None and ev_ebitda > 0:
            scores.append(self._band_score(ev_ebitda, self._EV_BANDS))
        if ps is not None and ps > 0:
            scores.append(self._band_score(ps, self._PS_BANDS))

        if not scores:
            return ValuationAnalysis(pe=pe, pb=pb, ev_ebitda=ev_ebitda, price_to_sales=ps)

        avg_score = sum(scores) / len(scores)
        status    = self._classify_status(avg_score)

        return ValuationAnalysis(
            pe              = pe,
            pb              = pb,
            ev_ebitda       = ev_ebitda,
            price_to_sales  = ps,
            status          = status,
            valuation_score = round(avg_score, 2),
            metadata        = {"metrics_used": len(scores)},
        )

    @staticmethod
    def _safe(data: dict, key: str) -> float | None:
        v = data.get(key)
        if v is None:
            return None
        try:
            f = float(v)
            return f if f > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _band_score(value: float, bands: list[float]) -> float:
        """
        Maps a multiple to a cheapness score 0–100.
        Lower multiple = higher score (cheaper).
        """
        if value < bands[0]:
            return 100.0
        elif value < bands[1]:
            return 75.0
        elif value < bands[2]:
            return 50.0
        elif value < bands[3]:
            return 25.0
        else:
            return 5.0

    @staticmethod
    def _classify_status(score: float) -> ValuationStatus:
        if score >= 85:
            return ValuationStatus.DEEPLY_UNDERVALUED
        elif score >= 65:
            return ValuationStatus.UNDERVALUED
        elif score >= 40:
            return ValuationStatus.FAIR_VALUE
        elif score >= 20:
            return ValuationStatus.OVERVALUED
        else:
            return ValuationStatus.DEEPLY_OVERVALUED
