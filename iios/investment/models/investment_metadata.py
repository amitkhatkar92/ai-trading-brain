"""iios/investment/models/investment_metadata.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class InvestmentMetadata:
    """Enrichment / tagging metadata for an investment result."""

    metadata_id: str        = field(default_factory=lambda: str(uuid.uuid4()))
    result_id:   str        = ""
    source:      str        = ""
    tags:        list[str]  = field(default_factory=list)
    attributes:  dict       = field(default_factory=dict)
    created_at:  float      = field(default_factory=time.time)

    def get(self, key: str, default=None):
        return self.attributes.get(key, default)

    def to_dict(self) -> dict:
        return {
            "metadata_id": self.metadata_id,
            "result_id":   self.result_id,
            "source":      self.source,
            "tags":        self.tags,
            "attributes":  self.attributes,
            "created_at":  self.created_at,
        }
