"""iios/investment/strategy/learning/learning_profile.py
StrategyLearningProfile — mutable runtime learning state per strategy.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    ewma, linear_trend, clamp
)


@dataclass
class StrategyLearningProfile:
    """
    Accumulated learning state for a strategy.
    Updated incrementally as new observations arrive.
    """
    strategy_id:   str
    strategy_name: str

    # ── lifecycle ────────────────────────────────────────────────────────────
    created_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated:  Optional[datetime] = None
    learning_version: int = 0
    observation_count: int = 0

    # ── baseline (established from first N observations) ─────────────────────
    baseline_established:     bool    = False
    baseline_score:           float   = 0.0
    baseline_sharpe:          float   = 0.0
    baseline_win_rate:        float   = 0.0
    baseline_max_drawdown:    float   = 0.0
    baseline_risk_score:      float   = 0.0
    baseline_established_at:  Optional[datetime] = None
    baseline_regime:          str     = "unknown"

    # ── rolling score history (in-memory for trend calc; capped at 200) ──────
    _score_history:   List[float] = field(default_factory=list)
    _risk_history:    List[float] = field(default_factory=list)
    _regime_history:  List[str]   = field(default_factory=list)

    # ── derived trends ────────────────────────────────────────────────────────
    score_trend:      float = 0.0    # positive = improving
    risk_trend:       float = 0.0    # positive = risk increasing (worse)
    smoothed_score:   float = 0.0    # EWMA of evaluation_score

    # ── regime intelligence ───────────────────────────────────────────────────
    regime_scores:   Dict[str, List[float]] = field(default_factory=dict)

    # ── maturity ──────────────────────────────────────────────────────────────
    maturity_level: str = "nascent"   # nascent/developing/established/mature/veteran

    # ── knowledge flags ───────────────────────────────────────────────────────
    has_success_patterns:  bool = False
    has_failure_patterns:  bool = False
    degradation_level:     str  = "none"

    _HISTORY_CAP = 200

    def record(self, obs: LearningObservation, baseline_window: int = 10) -> None:
        """Incorporate a new observation into the profile."""
        self.observation_count += 1
        self.last_updated  = obs.observed_at
        self.learning_version += 1

        # Append to rolling histories
        self._score_history.append(obs.evaluation_score)
        self._risk_history.append(obs.risk_score)
        self._regime_history.append(obs.current_regime)

        # Trim to cap
        if len(self._score_history) > self._HISTORY_CAP:
            self._score_history = self._score_history[-self._HISTORY_CAP:]
            self._risk_history  = self._risk_history[-self._HISTORY_CAP:]
            self._regime_history = self._regime_history[-self._HISTORY_CAP:]

        # Regime score accumulation
        regime = obs.current_regime
        self.regime_scores.setdefault(regime, []).append(obs.evaluation_score)

        # Establish baseline
        if not self.baseline_established and self.observation_count >= baseline_window:
            self._establish_baseline(baseline_window)

        # Recompute trends
        if len(self._score_history) >= 2:
            self.score_trend  = linear_trend(self._score_history[-20:])
            self.risk_trend   = linear_trend(self._risk_history[-20:])
            self.smoothed_score = ewma(self._score_history[-20:], alpha=0.20)

        # Maturity level
        self.maturity_level = self._compute_maturity()

    def _establish_baseline(self, window: int) -> None:
        obs_slice = self._score_history[:window]
        risk_slice = self._risk_history[:window]
        self.baseline_score       = statistics.mean(obs_slice)
        self.baseline_risk_score  = statistics.mean(risk_slice)
        self.baseline_established = True
        self.baseline_established_at = datetime.now(timezone.utc)

    def _compute_maturity(self) -> str:
        n = self.observation_count
        if n < 10:   return "nascent"
        if n < 50:   return "developing"
        if n < 200:  return "established"
        if n < 1000: return "mature"
        return "veteran"

    @property
    def best_regime(self) -> str:
        if not self.regime_scores:
            return "unknown"
        return max(
            self.regime_scores,
            key=lambda r: statistics.mean(self.regime_scores[r]),
        )

    @property
    def worst_regime(self) -> str:
        if not self.regime_scores:
            return "unknown"
        return min(
            self.regime_scores,
            key=lambda r: statistics.mean(self.regime_scores[r]),
        )

    @property
    def recent_scores(self) -> List[float]:
        return list(self._score_history[-20:])

    @property
    def recent_risk_scores(self) -> List[float]:
        return list(self._risk_history[-20:])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "strategy_name":       self.strategy_name,
            "observation_count":   self.observation_count,
            "maturity_level":      self.maturity_level,
            "baseline_established": self.baseline_established,
            "baseline_score":      round(self.baseline_score, 2),
            "smoothed_score":      round(self.smoothed_score, 2),
            "score_trend":         round(self.score_trend, 4),
            "risk_trend":          round(self.risk_trend, 4),
            "best_regime":         self.best_regime,
            "worst_regime":        self.worst_regime,
            "degradation_level":   self.degradation_level,
            "learning_version":    self.learning_version,
            "last_updated":        self.last_updated.isoformat() if self.last_updated else None,
        }
