"""
market_metadata.py — iios.market.lifecycle
============================================
Immutable supplementary metadata for a market session.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class MarketMetadata:
    """
    Immutable supplementary metadata attached to a market session.

    Fields
    ------
    analysis_id :       Market analysis correlation identifier.
    source :            System or component that initiated the session.
    exchange :          Exchange or venue identifier.
    instrument_id :     Primary instrument identifier.
    tags :              Free-form key/value tags for filtering.
    notes :             Optional human-readable notes.
    framework_version : Framework version string.
    """
    analysis_id:       str            = ""
    source:            str            = ""
    exchange:          str            = ""
    instrument_id:     str            = ""
    tags:              Dict[str, str] = field(default_factory=dict)
    notes:             str            = ""
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        *,
        analysis_id:   str                      = "",
        source:        str                      = "",
        exchange:      str                      = "",
        instrument_id: str                      = "",
        tags:          Optional[Dict[str, str]] = None,
        notes:         str                      = "",
    ) -> "MarketMetadata":
        return cls(
            analysis_id   = analysis_id,
            source        = source,
            exchange      = exchange,
            instrument_id = instrument_id,
            tags          = dict(tags or {}),
            notes         = notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id":       self.analysis_id,
            "source":            self.source,
            "exchange":          self.exchange,
            "instrument_id":     self.instrument_id,
            "tags":              dict(self.tags),
            "notes":             self.notes,
            "framework_version": self.framework_version,
        }
