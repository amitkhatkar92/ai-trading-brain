"""iios/investment/strategy/learning/learning_policy.py
LearningPolicy — configuration for the Learning Engine.
Controls all thresholds, windows, and behaviour flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class LearningPolicy:
    """
    Immutable policy defining how the learning engine operates.
    Inject into StrategyLearningEngine at construction time.
    """
    policy_name: str = "default"

    # ── baseline ───────────────────────────────────────────────────────────────
    baseline_window: int = 10          # observations needed to establish baseline
    min_observations_for_patterns: int = 5
    min_observations_for_drift: int = 15

    # ── drift detection ────────────────────────────────────────────────────────
    drift_threshold_mild:     float = 0.05   # 5% degradation from baseline
    drift_threshold_moderate: float = 0.15   # 15%
    drift_threshold_severe:   float = 0.25   # 25%
    drift_threshold_critical: float = 0.40   # 40%
    drift_window: int = 10                   # recent observations for drift

    # ── pattern detection ──────────────────────────────────────────────────────
    success_threshold:  float = 70.0          # eval score > this = success
    failure_threshold:  float = 45.0          # eval score < this = failure
    pattern_confidence_min: float = 0.60      # min pattern confidence
    pattern_min_support: int = 3              # min observations per pattern

    # ── recommendations ────────────────────────────────────────────────────────
    recommendation_cooldown_obs: int = 5      # min observations between same-type recs
    max_active_recommendations: int = 10

    # ── maturity ───────────────────────────────────────────────────────────────
    nascent_threshold:    int = 10
    developing_threshold: int = 50
    established_threshold: int = 200
    mature_threshold:     int = 1000

    # ── scoring ────────────────────────────────────────────────────────────────
    ewma_alpha: float = 0.20        # EWMA decay for smoothed metrics
    regime_coverage_weight: float = 0.25
    consistency_weight: float = 0.35
    improvement_weight: float = 0.25
    knowledge_weight: float = 0.15

    # ── history ────────────────────────────────────────────────────────────────
    max_snapshots_per_strategy: int = 2_000
    max_recommendations_stored: int = 500

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":               self.policy_name,
            "baseline_window":           self.baseline_window,
            "drift_threshold_mild":      self.drift_threshold_mild,
            "drift_threshold_moderate":  self.drift_threshold_moderate,
            "drift_threshold_severe":    self.drift_threshold_severe,
            "drift_threshold_critical":  self.drift_threshold_critical,
            "success_threshold":         self.success_threshold,
            "failure_threshold":         self.failure_threshold,
            "maturity_thresholds": {
                "nascent":     self.nascent_threshold,
                "developing":  self.developing_threshold,
                "established": self.established_threshold,
                "mature":      self.mature_threshold,
            },
        }


DEFAULT_POLICY = LearningPolicy(policy_name="default")

CONSERVATIVE_POLICY = LearningPolicy(
    policy_name="conservative",
    baseline_window=20,
    drift_threshold_mild=0.03,
    drift_threshold_moderate=0.10,
    drift_threshold_severe=0.20,
    drift_threshold_critical=0.30,
    success_threshold=75.0,
    failure_threshold=50.0,
)

AGGRESSIVE_POLICY = LearningPolicy(
    policy_name="aggressive",
    baseline_window=5,
    drift_threshold_mild=0.10,
    drift_threshold_moderate=0.20,
    drift_threshold_severe=0.35,
    drift_threshold_critical=0.50,
    success_threshold=60.0,
    failure_threshold=35.0,
)

INSTITUTIONAL_POLICY = LearningPolicy(
    policy_name="institutional",
    baseline_window=30,
    min_observations_for_patterns=10,
    min_observations_for_drift=20,
    drift_threshold_mild=0.05,
    drift_threshold_moderate=0.12,
    drift_threshold_severe=0.22,
    drift_threshold_critical=0.35,
    success_threshold=72.0,
    failure_threshold=48.0,
    recommendation_cooldown_obs=10,
    max_active_recommendations=5,
    ewma_alpha=0.15,
)
