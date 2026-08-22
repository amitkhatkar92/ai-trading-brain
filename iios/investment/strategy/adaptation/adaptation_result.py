"""iios/investment/strategy/adaptation/adaptation_result.py
Result model returned by all adaptation components.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import AdaptationType


@dataclass
class AdaptationResult:
    """
    Records what changed when a strategy was adapted.

    ``applied`` is False by default; the manager sets it to True
    after committing the adapted params to the profile.
    """

    result_id:         str            = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:       str            = ""
    adaptation_type:   AdaptationType = AdaptationType.CUSTOM
    original_params:   dict[str, Any] = field(default_factory=dict)
    adapted_params:    dict[str, Any] = field(default_factory=dict)
    changes:           dict[str, Any] = field(default_factory=dict)   # {param: {"old": v, "new": v}}
    reason:            str            = ""
    recommendation:    str            = ""
    confidence:        float          = 0.5     # 0–1
    applied:           bool           = False
    metadata:          dict[str, Any] = field(default_factory=dict)
    created_at:        float          = field(default_factory=time.time)

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)

    @property
    def n_changes(self) -> int:
        return len(self.changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "strategy_id":     self.strategy_id,
            "adaptation_type": self.adaptation_type.value,
            "original_params": self.original_params,
            "adapted_params":  self.adapted_params,
            "changes":         self.changes,
            "reason":          self.reason,
            "recommendation":  self.recommendation,
            "confidence":      self.confidence,
            "applied":         self.applied,
            "has_changes":     self.has_changes,
            "n_changes":       self.n_changes,
            "metadata":        self.metadata,
            "created_at":      self.created_at,
        }
