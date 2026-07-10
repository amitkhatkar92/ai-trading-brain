"""iios/integration/news/alternative/alternative_statistics.py

Aggregated stats for an alternative dataset.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import AlternativeDataType


@dataclass
class AlternativeStatistics:
    stat_id:      str               = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:   str               = ""
    alt_type:     AlternativeDataType = AlternativeDataType.CUSTOM
    period_start: float             = 0.0
    period_end:   float             = 0.0
    total_records: int              = 0
    unique_symbols: int             = 0
    avg_value:    float             = 0.0
    min_value:    float             = 0.0
    max_value:    float             = 0.0
    computed_at:  float             = field(default_factory=time.time)
    metadata:     dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":       self.stat_id,
            "dataset_id":    self.dataset_id,
            "alt_type":      self.alt_type.value,
            "total_records": self.total_records,
            "avg_value":     round(self.avg_value, 4),
        }
