"""deployment/deployment_policy.py — Rules governing how models are promoted."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import DeploymentStrategy


@dataclass
class DeploymentPolicy:
    """
    Governs promotion rules for a deployment slot.

    ``min_metric_thresholds`` maps metric names to minimum acceptable values.
    A model may not be promoted unless all thresholds are satisfied.
    """

    policy_id:               str
    strategy:                DeploymentStrategy
    min_metric_thresholds:   dict[str, float]    # metric → minimum value
    promotion_metric:        str                  # metric used to decide champion
    higher_is_better:        bool
    shadow_traffic_fraction: float               # for SHADOW strategy 0..1
    canary_initial_fraction: float               # for CANARY strategy 0..1
    auto_promote:            bool
    rollback_on_error_rate:  float               # auto-rollback if error_rate > this
    notes:                   str

    @classmethod
    def default(cls) -> "DeploymentPolicy":
        return cls(
            policy_id               = "default",
            strategy                = DeploymentStrategy.DIRECT,
            min_metric_thresholds   = {},
            promotion_metric        = "val_loss",
            higher_is_better        = False,
            shadow_traffic_fraction = 0.1,
            canary_initial_fraction = 0.1,
            auto_promote            = False,
            rollback_on_error_rate  = 0.05,
            notes                   = "",
        )

    def check_promotion_eligible(self, metrics: dict[str, float]) -> tuple[bool, list[str]]:
        """Return (eligible, reasons) based on threshold checks."""
        failures: list[str] = []
        for metric, threshold in self.min_metric_thresholds.items():
            val = metrics.get(metric)
            if val is None:
                failures.append(f"Metric '{metric}' missing from evaluation")
            elif val < threshold:
                failures.append(f"Metric '{metric}' = {val:.4f} < threshold {threshold:.4f}")
        return (len(failures) == 0, failures)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":               self.policy_id,
            "strategy":                self.strategy.value,
            "min_metric_thresholds":   self.min_metric_thresholds,
            "promotion_metric":        self.promotion_metric,
            "higher_is_better":        self.higher_is_better,
            "shadow_traffic_fraction": self.shadow_traffic_fraction,
            "canary_initial_fraction": self.canary_initial_fraction,
            "auto_promote":            self.auto_promote,
            "rollback_on_error_rate":  self.rollback_on_error_rate,
        }
