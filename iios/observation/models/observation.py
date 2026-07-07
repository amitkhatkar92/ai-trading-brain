"""
iios/observation/models/observation.py
=======================================
Core Observation dataclass.

An Observation is a raw external input that has entered the IIOS system
but not yet been promoted to Knowledge.  It carries:

- A unique identity (ObservationId)
- The raw payload (``content``)
- Provenance (ObservationSourceInfo)
- Rich metadata (ObservationMetadata)
- Contextual snapshot (ObservationContext)
- Lifecycle status

Every external input **must** pass through the Observation Engine
before it can influence knowledge, decisions, or trades.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    DEFAULT_CONFIDENCE,
    OBSERVATION_NAMESPACE,
    OBSERVATION_SCHEMA_VERSION,
    SYSTEM_OBSERVER,
    ObservationDomain,
    ObservationPriority,
    ObservationSource,
    ObservationStatus,
    ObservationType,
)
from .observation_context_model import ObservationContext
from .observation_identifier    import ObservationId, generate_obs_id
from .observation_metadata      import ObservationMetadata
from .observation_source        import ObservationSourceInfo

from ..observation_exceptions import ObservationLifecycleError as _LifecycleErr

__all__ = ["Observation"]


# ── Allowed lifecycle transitions ─────────────────────────────────────────────

_TRANSITIONS: dict[ObservationStatus, frozenset[ObservationStatus]] = {
    ObservationStatus.CREATED:     frozenset({ObservationStatus.COLLECTED,  ObservationStatus.REJECTED, ObservationStatus.DELETED}),
    ObservationStatus.COLLECTED:   frozenset({ObservationStatus.VALIDATING, ObservationStatus.REJECTED, ObservationStatus.DELETED}),
    ObservationStatus.VALIDATING:  frozenset({ObservationStatus.VALIDATED,  ObservationStatus.REJECTED}),
    ObservationStatus.VALIDATED:   frozenset({ObservationStatus.CLASSIFYING,ObservationStatus.ACCEPTED, ObservationStatus.REJECTED}),
    ObservationStatus.CLASSIFYING: frozenset({ObservationStatus.CLASSIFIED, ObservationStatus.REJECTED}),
    ObservationStatus.CLASSIFIED:  frozenset({ObservationStatus.ENRICHING,  ObservationStatus.ACCEPTED, ObservationStatus.REJECTED}),
    ObservationStatus.ENRICHING:   frozenset({ObservationStatus.ENRICHED,   ObservationStatus.ACCEPTED, ObservationStatus.REJECTED}),
    ObservationStatus.ENRICHED:    frozenset({ObservationStatus.ACCEPTED,   ObservationStatus.REJECTED}),
    ObservationStatus.ACCEPTED:    frozenset({ObservationStatus.ARCHIVED,   ObservationStatus.EXPIRED,  ObservationStatus.DELETED}),
    ObservationStatus.REJECTED:    frozenset({ObservationStatus.DELETED}),
    ObservationStatus.ARCHIVED:    frozenset({ObservationStatus.DELETED}),
    ObservationStatus.EXPIRED:     frozenset({ObservationStatus.DELETED,    ObservationStatus.ARCHIVED}),
    ObservationStatus.DELETED:     frozenset(),
}


def _compute_checksum(content: Any) -> str:
    raw = str(content).encode("utf-8", errors="replace")
    return hashlib.md5(raw, usedforsecurity=False).hexdigest()  # noqa: S324


@dataclass
class Observation:
    """Core unit of raw information entering IIOS.

    All external inputs are wrapped as an ``Observation`` before any
    downstream processing.  The ``content`` field is the raw payload
    (dict, str, number, or JSON-serialisable object).

    Usage::

        obs = Observation(
            obs_type = ObservationType.MARKET_DATA,
            title    = "NIFTY 50 close",
            content  = {"symbol": "^NSEI", "close": 24350.0},
        )
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    obs_id:     ObservationId         = field(default_factory=generate_obs_id)

    # ── Type & status ─────────────────────────────────────────────────────────
    obs_type:   ObservationType       = ObservationType.UNKNOWN
    status:     ObservationStatus     = ObservationStatus.CREATED

    # ── Core payload ──────────────────────────────────────────────────────────
    title:      str                   = ""
    content:    Any                   = None   # Raw payload — JSON-serialisable

    # ── Provenance ────────────────────────────────────────────────────────────
    source_info:ObservationSourceInfo = field(default_factory=ObservationSourceInfo)

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata:   ObservationMetadata   = field(default_factory=ObservationMetadata)

    # ── Context ───────────────────────────────────────────────────────────────
    context:    ObservationContext    = field(default_factory=ObservationContext)

    # ── Versioning ────────────────────────────────────────────────────────────
    version:    int                   = 1       # monotonic update counter
    checksum:   str                   = ""      # hash of content

    # ── Classification output ─────────────────────────────────────────────────
    classification:   str             = ""      # assigned class label
    classification_confidence: float  = 0.0
    classification_method: str        = ""

    # ── Validation output ─────────────────────────────────────────────────────
    validation_passed: bool            = False
    validation_notes:  list[str]       = field(default_factory=list)

    # ── Relationships ─────────────────────────────────────────────────────────
    related_obs_ids: list[str]         = field(default_factory=list)
    derived_knowledge_ids: list[str]   = field(default_factory=list)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at:  float                 = field(default_factory=time.time)
    updated_at:  float                 = field(default_factory=time.time)
    accepted_at: Optional[float]       = None
    rejected_at: Optional[float]       = None

    # ── Rejection ─────────────────────────────────────────────────────────────
    rejection_reason: str              = ""

    # ── Soft-delete ───────────────────────────────────────────────────────────
    is_deleted:  bool                  = False

    schema_version: str                = OBSERVATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.checksum and self.content is not None:
            self.checksum = _compute_checksum(self.content)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def id(self) -> str:
        """String form of the observation ID."""
        return self.obs_id.full

    @property
    def uid(self) -> str:
        return self.obs_id.uid

    @property
    def is_active(self) -> bool:
        """True while the observation is still flowing through the pipeline (not terminal, not deleted)."""
        return not self.is_terminal and not self.is_deleted

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            ObservationStatus.ACCEPTED,
            ObservationStatus.REJECTED,
            ObservationStatus.ARCHIVED,
            ObservationStatus.EXPIRED,
            ObservationStatus.DELETED,
        )

    @property
    def is_expired(self) -> bool:
        return self.metadata.is_expired or self.status == ObservationStatus.EXPIRED

    @property
    def priority(self) -> ObservationPriority:
        return self.metadata.priority

    @property
    def confidence(self) -> float:
        return self.metadata.confidence

    @property
    def domain(self) -> ObservationDomain:
        return self.metadata.domain

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def transition(self, new_status: ObservationStatus, actor: str = SYSTEM_OBSERVER) -> None:
        """Apply a validated lifecycle transition."""
        allowed = _TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise _LifecycleErr(
                f"Illegal transition {self.status.value!r} → {new_status.value!r} "
                f"for observation {self.uid[:8]}",
                code="OBS-030",
            )
        self.status     = new_status
        self.updated_at = time.time()
        self.version   += 1
        self.metadata.updated_by = actor

        if new_status == ObservationStatus.ACCEPTED:
            self.accepted_at = self.updated_at
            self.validation_passed = True
        elif new_status == ObservationStatus.REJECTED:
            self.rejected_at = self.updated_at
        elif new_status == ObservationStatus.DELETED:
            self.is_deleted = True

    def can_transition_to(self, new_status: ObservationStatus) -> bool:
        return new_status in _TRANSITIONS.get(self.status, frozenset())

    def mark_collected(self, actor: str = SYSTEM_OBSERVER) -> None:
        self.transition(ObservationStatus.COLLECTED, actor)

    def mark_validated(self, actor: str = SYSTEM_OBSERVER) -> None:
        if self.status == ObservationStatus.VALIDATING:
            self.transition(ObservationStatus.VALIDATED, actor)
        elif self.status == ObservationStatus.COLLECTED:
            self.transition(ObservationStatus.VALIDATING, actor)
            self.transition(ObservationStatus.VALIDATED, actor)

    def mark_classified(self, label: str, confidence: float, method: str = "", actor: str = SYSTEM_OBSERVER) -> None:
        if self.status == ObservationStatus.CLASSIFYING:
            self.transition(ObservationStatus.CLASSIFIED, actor)
        elif self.status == ObservationStatus.VALIDATED:
            self.transition(ObservationStatus.CLASSIFYING, actor)
            self.transition(ObservationStatus.CLASSIFIED, actor)
        self.classification = label
        self.classification_confidence = confidence
        self.classification_method = method

    def mark_enriched(self, actor: str = SYSTEM_OBSERVER) -> None:
        if self.status == ObservationStatus.ENRICHING:
            self.transition(ObservationStatus.ENRICHED, actor)
        elif self.status == ObservationStatus.CLASSIFIED:
            self.transition(ObservationStatus.ENRICHING, actor)
            self.transition(ObservationStatus.ENRICHED, actor)

    def accept(self, actor: str = SYSTEM_OBSERVER) -> None:
        """Mark observation as accepted into IIOS."""
        self.transition(ObservationStatus.ACCEPTED, actor)

    def reject(self, reason: str, actor: str = SYSTEM_OBSERVER) -> None:
        """Reject the observation with an explicit reason."""
        self.rejection_reason = reason
        self.transition(ObservationStatus.REJECTED, actor)

    def archive(self, actor: str = SYSTEM_OBSERVER) -> None:
        self.transition(ObservationStatus.ARCHIVED, actor)

    def expire(self, actor: str = SYSTEM_OBSERVER) -> None:
        self.transition(ObservationStatus.EXPIRED, actor)

    def soft_delete(self, actor: str = SYSTEM_OBSERVER) -> None:
        self.transition(ObservationStatus.DELETED, actor)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":                      self.obs_id.full,
            "obs_type":                    self.obs_type.value,
            "status":                      self.status.value,
            "title":                       self.title,
            "content":                     self.content,
            "source_info":                 self.source_info.to_dict(),
            "metadata":                    self.metadata.to_dict(),
            "context":                     self.context.to_dict(),
            "version":                     self.version,
            "checksum":                    self.checksum,
            "classification":              self.classification,
            "classification_confidence":   self.classification_confidence,
            "classification_method":       self.classification_method,
            "validation_passed":           self.validation_passed,
            "validation_notes":            list(self.validation_notes),
            "related_obs_ids":             list(self.related_obs_ids),
            "derived_knowledge_ids":       list(self.derived_knowledge_ids),
            "created_at":                  self.created_at,
            "updated_at":                  self.updated_at,
            "accepted_at":                 self.accepted_at,
            "rejected_at":                 self.rejected_at,
            "rejection_reason":            self.rejection_reason,
            "is_deleted":                  self.is_deleted,
            "schema_version":              self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Observation":
        from .observation_identifier import ObservationId
        obs = cls(
            obs_id                    = ObservationId.parse(d["obs_id"]),
            obs_type                  = ObservationType(d.get("obs_type", ObservationType.UNKNOWN.value)),
            status                    = ObservationStatus(d.get("status", ObservationStatus.CREATED.value)),
            title                     = d.get("title",     ""),
            content                   = d.get("content"),
            source_info               = ObservationSourceInfo.from_dict(d.get("source_info", {})),
            metadata                  = ObservationMetadata.from_dict(d.get("metadata", {})),
            context                   = ObservationContext.from_dict(d.get("context", {})),
            version                   = d.get("version",   1),
            checksum                  = d.get("checksum",  ""),
            classification            = d.get("classification",           ""),
            classification_confidence = d.get("classification_confidence", 0.0),
            classification_method     = d.get("classification_method",    ""),
            validation_passed         = d.get("validation_passed",        False),
            validation_notes          = list(d.get("validation_notes",    [])),
            related_obs_ids           = list(d.get("related_obs_ids",     [])),
            derived_knowledge_ids     = list(d.get("derived_knowledge_ids", [])),
            created_at                = d.get("created_at",  time.time()),
            updated_at                = d.get("updated_at",  time.time()),
            accepted_at               = d.get("accepted_at"),
            rejected_at               = d.get("rejected_at"),
            rejection_reason          = d.get("rejection_reason", ""),
            is_deleted                = d.get("is_deleted",       False),
            schema_version            = d.get("schema_version",   OBSERVATION_SCHEMA_VERSION),
        )
        return obs
