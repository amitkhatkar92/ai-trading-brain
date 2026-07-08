"""
iios/decisions/models/decision_metadata.py
==========================================
DecisionMetadata — contextual provenance for a Decision.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DecisionMetadata:
    """
    Provenance information attached to a Decision.

    Attributes
    ----------
    context_id        : Unique metadata record identifier.
    source_id         : Engine/module that initiated the decision.
    intelligence_ids  : IDs of intelligence products consumed.
    reasoning_ids     : IDs of reasoning artefacts used.
    agent_ids         : IDs of agents that participated.
    quality_record_ids: Governance quality record references.
    constraints       : Active constraints at decision time.
    labels            : Free-form labels for filtering.
    version           : Schema version.
    created_at        : Unix timestamp.
    """

    context_id:         str              = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:          str              = ""
    intelligence_ids:   list[str]        = field(default_factory=list)
    reasoning_ids:      list[str]        = field(default_factory=list)
    agent_ids:          list[str]        = field(default_factory=list)
    quality_record_ids: list[str]        = field(default_factory=list)
    constraints:        dict[str, Any]   = field(default_factory=dict)
    labels:             list[str]        = field(default_factory=list)
    version:            str              = "1.0"
    created_at:         float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":         self.context_id,
            "source_id":          self.source_id,
            "intelligence_ids":   list(self.intelligence_ids),
            "reasoning_ids":      list(self.reasoning_ids),
            "agent_ids":          list(self.agent_ids),
            "quality_record_ids": list(self.quality_record_ids),
            "constraints":        dict(self.constraints),
            "labels":             list(self.labels),
            "version":            self.version,
            "created_at":         self.created_at,
        }
