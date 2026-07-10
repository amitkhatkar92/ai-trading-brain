"""iios/integration/news/alternative/alternative_source.py

Metadata for an alternative data source registration.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import AlternativeDataType


@dataclass
class AlternativeSource:
    source_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id: str               = ""
    name:        str               = ""
    description: str               = ""
    alt_type:    AlternativeDataType = AlternativeDataType.CUSTOM
    url:         str               = ""
    is_free:     bool              = False
    update_freq: str               = ""    # "daily", "hourly", "realtime"
    tags:        list[str]         = field(default_factory=list)
    registered_at: float           = field(default_factory=time.time)
    metadata:    dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id":  self.source_id,
            "name":       self.name,
            "alt_type":   self.alt_type.value,
            "is_free":    self.is_free,
            "update_freq": self.update_freq,
        }
