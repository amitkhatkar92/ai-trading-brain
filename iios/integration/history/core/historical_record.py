"""iios/integration/history/core/historical_record.py

Atomic unit of historical data — one timestamped observation.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.history.history_constants import (
    CompressionType,
    DataFormat,
    HistoricalDataType,
)


@dataclass
class HistoricalRecord:
    """
    One atomic historical data point.

    A record may represent a market tick, a news article reference, a macro
    data point, an AI observation, a decision, an execution fill, etc.
    The ``data`` dict carries the payload; its schema is defined by the parent
    dataset.
    """

    record_id:    str                = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id:   str                = ""
    partition_id: str                = ""
    data_type:    HistoricalDataType = HistoricalDataType.CUSTOM
    symbol:       str                = ""        # primary subject (ticker, country, …)
    timestamp:    float              = 0.0       # event time (POSIX seconds, UTC)
    received_at:  float              = field(default_factory=time.time)
    sequence:     int                = 0         # monotonic sequence within dataset
    data:         dict[str, Any]     = field(default_factory=dict)
    format:       DataFormat         = DataFormat.RAW
    compression:  CompressionType   = CompressionType.NONE
    checksum:     str                = ""        # SHA-256 of serialised ``data``
    version:      int                = 1
    tags:         list[str]          = field(default_factory=list)
    metadata:     dict[str, Any]     = field(default_factory=dict)

    # ── Post-init ────────────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        if not self.checksum and self.data:
            self.checksum = self._compute_checksum()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_checksum(self) -> str:
        raw = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]

    def verify_checksum(self) -> bool:
        """Return True if stored checksum matches current data."""
        if not self.checksum:
            return True    # no checksum → always valid
        return self.checksum == self._compute_checksum()

    def age_sec(self) -> float:
        return time.time() - self.received_at

    def is_valid(self) -> bool:
        return bool(self.dataset_id) and self.timestamp > 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":   self.record_id,
            "dataset_id":  self.dataset_id,
            "data_type":   self.data_type.value,
            "symbol":      self.symbol,
            "timestamp":   self.timestamp,
            "sequence":    self.sequence,
            "checksum":    self.checksum,
            "version":     self.version,
            "data":        self.data,
        }
