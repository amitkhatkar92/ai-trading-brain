"""iios/integration/news/alternative/alternative_dataset.py

Represents a collection of alternative data records.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.news.news_constants import AlternativeDataType


@dataclass
class AlternativeEvent:
    """One record inside an alternative dataset."""

    event_id:    str               = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:  str               = ""
    timestamp:   float             = 0.0
    received_at: float             = field(default_factory=time.time)
    symbol:      str               = ""    # associated ticker or "" if market-wide
    value:       float             = 0.0
    value_str:   str               = ""    # string value if not numeric
    unit:        str               = ""    # "USD", "count", "kg", …
    source_url:  str               = ""
    metadata:    dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "dataset_id": self.dataset_id,
            "timestamp":  self.timestamp,
            "symbol":     self.symbol,
            "value":      self.value,
            "unit":       self.unit,
        }


@dataclass
class AlternativeDataset:
    """
    A named alternative data collection from one source.

    Examples:
    - SatelliteCarCountDataset (SATELLITE_DATA)
    - RedditWallStreetBetsDataset (SOCIAL_MEDIA)
    - SECInsiderFilingsDataset (CORPORATE_FILING)
    """

    dataset_id:   str                 = field(default_factory=lambda: str(uuid.uuid4()))
    name:         str                 = ""
    description:  str                 = ""
    alt_type:     AlternativeDataType = AlternativeDataType.CUSTOM
    provider_id:  str                 = ""
    schema:       dict[str, str]      = field(default_factory=dict)    # field → dtype
    records:      list[AlternativeEvent] = field(default_factory=list)
    period_start: float               = 0.0
    period_end:   float               = 0.0
    record_count: int                 = 0
    created_at:   float               = field(default_factory=time.time)
    updated_at:   float               = field(default_factory=time.time)
    metadata:     dict[str, Any]      = field(default_factory=dict)

    def add_record(self, evt: AlternativeEvent) -> None:
        evt.dataset_id = self.dataset_id
        self.records.append(evt)
        self.record_count = len(self.records)
        self.updated_at = time.time()
        if evt.timestamp < self.period_start or self.period_start == 0.0:
            self.period_start = evt.timestamp
        if evt.timestamp > self.period_end:
            self.period_end = evt.timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id":   self.dataset_id,
            "name":         self.name,
            "alt_type":     self.alt_type.value,
            "provider_id":  self.provider_id,
            "record_count": self.record_count,
            "period_start": self.period_start,
            "period_end":   self.period_end,
            "created_at":   self.created_at,
        }
