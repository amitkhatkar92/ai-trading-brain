"""models/model_statistics.py — Aggregated statistics for the model registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelStatistics:
    """Summary stats across all registered models."""
    total_models:      int
    by_status:         dict[str, int]
    by_task:           dict[str, int]
    by_learning_type:  dict[str, int]
    by_framework:      dict[str, int]
    champion_count:    int

    @classmethod
    def compute(cls, metadata_list: list) -> "ModelStatistics":
        by_status:        dict[str, int] = {}
        by_task:          dict[str, int] = {}
        by_learning_type: dict[str, int] = {}
        by_framework:     dict[str, int] = {}
        champion_count = 0

        for m in metadata_list:
            s = m.status.value
            t = m.model_task.value
            lt = m.learning_type.value
            fw = m.framework

            by_status[s]         = by_status.get(s, 0) + 1
            by_task[t]           = by_task.get(t, 0) + 1
            by_learning_type[lt] = by_learning_type.get(lt, 0) + 1
            by_framework[fw]     = by_framework.get(fw, 0) + 1

            from iios.integration.research.learning.learning_constants import ModelStatus
            if m.status == ModelStatus.DEPLOYED:
                champion_count += 1

        return cls(
            total_models     = len(metadata_list),
            by_status        = by_status,
            by_task          = by_task,
            by_learning_type = by_learning_type,
            by_framework     = by_framework,
            champion_count   = champion_count,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_models":     self.total_models,
            "by_status":        self.by_status,
            "by_task":          self.by_task,
            "by_learning_type": self.by_learning_type,
            "by_framework":     self.by_framework,
            "champion_count":   self.champion_count,
        }
