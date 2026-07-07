"""
iios/observation/models/observation_context_model.py
=====================================================
Contextual snapshot attached to an observation at ingestion time.

Captures the market/session context that surrounds the observation —
useful for downstream classification and enrichment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import OBSERVATION_SCHEMA_VERSION, SYSTEM_OBSERVER

__all__ = ["ObservationContext"]


@dataclass
class ObservationContext:
    """Contextual metadata captured at observation ingestion time."""

    # Who submitted
    actor:          str              = SYSTEM_OBSERVER
    operation_id:   Optional[str]   = None

    # Session context
    session_id:     str              = ""
    pipeline_id:    str              = ""
    batch_id:       str              = ""

    # Market context at time of observation
    market_session: str              = ""   # e.g. "pre_market", "market_hours", "post_market"
    market_regime:  str              = ""   # e.g. "bull", "bear", "sideways"
    vix_level:      Optional[float]  = None
    nifty_close:    Optional[float]  = None
    trading_day:    bool             = True

    # Causality chain
    parent_obs_id:  Optional[str]    = None   # observation that triggered this
    root_obs_id:    Optional[str]    = None   # root of the causality chain

    # Enrichment state
    enrichment_rounds: int           = 0
    validation_rounds: int           = 0

    # Custom context attributes
    attributes:     dict[str, Any]   = field(default_factory=dict)

    # When this context was captured
    captured_at:    float            = field(default_factory=time.time)
    schema_version: str              = OBSERVATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor":            self.actor,
            "operation_id":     self.operation_id,
            "session_id":       self.session_id,
            "pipeline_id":      self.pipeline_id,
            "batch_id":         self.batch_id,
            "market_session":   self.market_session,
            "market_regime":    self.market_regime,
            "vix_level":        self.vix_level,
            "nifty_close":      self.nifty_close,
            "trading_day":      self.trading_day,
            "parent_obs_id":    self.parent_obs_id,
            "root_obs_id":      self.root_obs_id,
            "enrichment_rounds": self.enrichment_rounds,
            "validation_rounds": self.validation_rounds,
            "attributes":       dict(self.attributes),
            "captured_at":      self.captured_at,
            "schema_version":   self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ObservationContext":
        return cls(
            actor             = d.get("actor",            SYSTEM_OBSERVER),
            operation_id      = d.get("operation_id"),
            session_id        = d.get("session_id",       ""),
            pipeline_id       = d.get("pipeline_id",      ""),
            batch_id          = d.get("batch_id",         ""),
            market_session    = d.get("market_session",   ""),
            market_regime     = d.get("market_regime",    ""),
            vix_level         = d.get("vix_level"),
            nifty_close       = d.get("nifty_close"),
            trading_day       = d.get("trading_day",      True),
            parent_obs_id     = d.get("parent_obs_id"),
            root_obs_id       = d.get("root_obs_id"),
            enrichment_rounds = d.get("enrichment_rounds", 0),
            validation_rounds = d.get("validation_rounds", 0),
            attributes        = dict(d.get("attributes",  {})),
            captured_at       = d.get("captured_at",      time.time()),
            schema_version    = d.get("schema_version",   OBSERVATION_SCHEMA_VERSION),
        )
