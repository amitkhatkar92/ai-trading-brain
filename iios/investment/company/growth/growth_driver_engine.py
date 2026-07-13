"""iios/investment/company/growth/growth_driver_engine.py
Orchestrates driver scoring and catalyst detection into GrowthDriverProfile.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.growth.growth_profile import GrowthDriverProfile
from iios.investment.company.growth.driver_analysis import analyse_drivers
from iios.investment.company.growth.growth_catalysts import detect_catalysts
from iios.investment.company.growth.driver_registry import DriverRegistry
from iios.investment.company.growth.growth_statistics import clamp


class GrowthDriverEngine:
    """
    Compute GrowthDriverProfile from upstream snapshot data.
    Supports plugin registration for custom driver models.
    """

    def __init__(self, registry: Optional[DriverRegistry] = None) -> None:
        self._registry = registry or DriverRegistry()

    def compute(
        self,
        avg_net_margin:      Optional[float] = None,
        current_net_margin:  Optional[float] = None,
        revenue_cagr:        Optional[float] = None,
        eps_cagr:            Optional[float] = None,
        moat_score:          Optional[float] = None,
        moat_types:          Optional[List[str]] = None,
        gross_margin_exp:    Optional[float] = None,   # bps
        avg_gross_margin:    Optional[float] = None,
        operational_quality: Optional[float] = None,
        resilience_score:    Optional[float] = None,
        avg_roic:            Optional[float] = None,
        revenue_trend:       str = "",
        earnings_trend:      str = "",
        margin_expanding:    Optional[bool] = None,
        is_cyclical:         Optional[bool] = None,
        history_depth:       int = 0,
    ) -> GrowthDriverProfile:
        explanation: List[str] = []

        # ── Core driver analysis ─────────────────────────────────────────────────
        inputs: Dict[str, Any] = {
            "avg_net_margin":      avg_net_margin,
            "current_net_margin":  current_net_margin,
            "revenue_cagr":        revenue_cagr,
            "eps_cagr":            eps_cagr,
            "moat_score":          moat_score,
            "moat_types":          moat_types or [],
            "gross_margin_exp_bps": gross_margin_exp,
            "avg_gross_margin":    avg_gross_margin,
            "operational_quality": operational_quality,
            "history_depth":       history_depth,
        }

        core = analyse_drivers(**{k: v for k, v in inputs.items() if k != "moat_types"},
                               moat_types=moat_types or [])

        # ── Plugin contributions ─────────────────────────────────────────────────
        plugin_results = self._registry.run_all(inputs)
        plugin_drivers: List[str] = []
        for res in plugin_results:
            plugin_drivers.extend(res.get("detected_drivers", []))
            if "explanation" in res:
                explanation.extend(res["explanation"])

        # ── Merge drivers ────────────────────────────────────────────────────────
        all_drivers = list(dict.fromkeys(core["detected_drivers"] + plugin_drivers))

        # ── Catalysts ───────────────────────────────────────────────────────────
        catalysts = detect_catalysts(
            moat_score=moat_score,
            moat_types=moat_types,
            revenue_trend=revenue_trend,
            earnings_trend=earnings_trend,
            margin_expanding=margin_expanding,
            resilience_score=resilience_score,
            is_cyclical=is_cyclical,
            avg_roic=avg_roic,
        )
        for c in catalysts:
            if c not in all_drivers:
                all_drivers.append(c)

        # ── Explanation ─────────────────────────────────────────────────────────
        if all_drivers:
            explanation.append(f"Growth drivers detected: {', '.join(all_drivers)}")
        else:
            explanation.append("No dominant growth drivers identified from available data")

        return GrowthDriverProfile(
            detected_drivers=all_drivers,
            primary_driver=core["primary_driver"],
            operational_leverage_score=core["operational_leverage_score"],
            pricing_power_score=core["pricing_power_score"],
            market_expansion_score=core["market_expansion_score"],
            innovation_score=core["innovation_score"],
            driver_confidence=core["driver_confidence"],
            explanation=explanation,
        )
