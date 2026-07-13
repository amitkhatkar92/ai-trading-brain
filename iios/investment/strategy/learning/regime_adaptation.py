"""iios/investment/strategy/learning/regime_adaptation.py
RegimeAdaptation — measures how well a strategy adapts to different market regimes.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class RegimeAdaptationResult:
    """Regime suitability map and adaptability score for a strategy."""
    strategy_id:       str
    assessed_at:       datetime

    regime_suitability:   Dict[str, float]    # regime → suitability 0-100
    regimes_experienced:  List[str]
    regimes_not_seen:     List[str]           # supported but not yet observed

    best_regime:          str
    worst_regime:         str
    adaptability_score:   float               # 0-100
    regime_breadth:       float               # 0-100 (regimes covered / total supported)
    mismatch_rate:        float               # fraction of observations with mismatch

    recommended_regimes:  List[str]           # regimes to focus on
    avoid_regimes:        List[str]           # regimes to avoid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":        self.strategy_id,
            "assessed_at":        self.assessed_at.isoformat(),
            "regime_suitability": {k: round(v, 2) for k, v in self.regime_suitability.items()},
            "best_regime":        self.best_regime,
            "worst_regime":       self.worst_regime,
            "adaptability_score": round(self.adaptability_score, 2),
            "regime_breadth":     round(self.regime_breadth, 2),
            "mismatch_rate":      round(self.mismatch_rate, 4),
            "recommended_regimes": self.recommended_regimes,
            "avoid_regimes":      self.avoid_regimes,
        }


class RegimeAdaptationAnalyzer:
    """
    Analyses regime-level performance from observations.
    Produces actionable suitability maps without modifying the strategy.
    """

    _KNOWN_REGIMES = frozenset([
        "trending", "ranging", "volatile", "crisis", "recovery",
        "bullish", "bearish", "sideways", "unknown"
    ])

    def __init__(self, min_obs_per_regime: int = 2) -> None:
        self._min_obs = min_obs_per_regime

    def analyse(self, observations: List[LearningObservation]) -> Optional[RegimeAdaptationResult]:
        if len(observations) < 3:
            return None

        sid = observations[0].strategy_id

        # Build regime score map
        regime_map: Dict[str, List[float]] = {}
        for o in observations:
            regime_map.setdefault(o.current_regime, []).append(o.evaluation_score)

        # Filter to regimes with enough data
        qualified = {
            r: vs for r, vs in regime_map.items()
            if len(vs) >= self._min_obs
        }

        suitability: Dict[str, float] = {}
        for regime, scores in qualified.items():
            mean_s = statistics.mean(scores)
            # Suitability = mean score normalised to 0-100 (already 0-100 scale)
            suitability[regime] = clamp(mean_s)

        if not suitability:
            # Not enough data per regime — use all with single obs
            for r, vs in regime_map.items():
                suitability[r] = clamp(statistics.mean(vs))

        best_regime  = max(suitability, key=suitability.get)   # type: ignore[arg-type]
        worst_regime = min(suitability, key=suitability.get)   # type: ignore[arg-type]

        # Supported regimes from first observation
        first = observations[0]
        supported = set(first.supported_regimes)
        experienced = set(suitability.keys()) - {"unknown"}
        not_seen = list(supported - experienced) if supported else []

        # Regime breadth: how many of the supported regimes have been observed
        breadth = clamp(
            (len(experienced & supported) / max(len(supported), 1)) * 100.0
            if supported else 50.0
        )

        # Mismatch rate
        total = len(observations)
        mismatched = sum(1 for o in observations if o.regime_mismatch)
        mismatch_rate = mismatched / total if total else 0.0

        # Adaptability: based on breadth, best-worst gap normalised, and mismatch penalty
        best_suit  = suitability.get(best_regime, 0.0)
        worst_suit = suitability.get(worst_regime, 0.0)
        gap_penalty = clamp((best_suit - worst_suit) / 100.0 * 30.0)

        adaptability = clamp(
            0.50 * breadth
            + 0.30 * best_suit
            - gap_penalty
            - mismatch_rate * 20.0
        )

        recommended = [r for r, s in suitability.items() if s >= 65.0]
        avoid       = [r for r, s in suitability.items() if s < 40.0]

        return RegimeAdaptationResult(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            regime_suitability=suitability,
            regimes_experienced=list(experienced),
            regimes_not_seen=not_seen,
            best_regime=best_regime,
            worst_regime=worst_regime,
            adaptability_score=adaptability,
            regime_breadth=breadth,
            mismatch_rate=mismatch_rate,
            recommended_regimes=recommended,
            avoid_regimes=avoid,
        )
