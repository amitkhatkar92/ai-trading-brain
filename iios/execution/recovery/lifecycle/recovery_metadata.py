"""iios/execution/recovery/lifecycle/recovery_metadata.py
==================================================
RecoveryMetadata — immutable supplementary metadata attached to a
recovery session after creation.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class RecoveryMetadata:
    """
    Supplementary immutable metadata for a recovery session.

    Fields
    ------
    metadata_id:          Unique ID for this metadata record.
    recovery_session_id:  Parent recovery session.
    attempt_count:        Number of recovery attempts so far.
    max_attempts:         Maximum allowed attempts before failure.
    backoff_seconds:      Delay between retry attempts.
    detection_threshold:  Threshold value that triggered detection.
    assessment_data:      Key-value findings from the ASSESSING phase.
    verification_data:    Key-value findings from the VERIFYING phase.
    created_at:           Wall-time of creation.
    updated_at:           Wall-time of last update.
    framework_version:    Platform version.
    """

    metadata_id:          str
    recovery_session_id:  str

    attempt_count:        int                = 0
    max_attempts:         int                = 3
    backoff_seconds:      float              = 30.0
    detection_threshold:  Optional[float]    = None
    assessment_data:      Dict[str, Any]     = field(default_factory=dict, compare=False)
    verification_data:    Dict[str, Any]     = field(default_factory=dict, compare=False)
    created_at:           float              = field(default_factory=time.time, compare=False)
    updated_at:           float              = field(default_factory=time.time, compare=False)
    framework_version:    str                = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def attempts_remaining(self) -> int:
        return max(0, self.max_attempts - self.attempt_count)

    @property
    def is_exhausted(self) -> bool:
        return self.attempt_count >= self.max_attempts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_id":         self.metadata_id,
            "recovery_session_id": self.recovery_session_id,
            "attempt_count":       self.attempt_count,
            "max_attempts":        self.max_attempts,
            "backoff_seconds":     self.backoff_seconds,
            "detection_threshold": self.detection_threshold,
            "assessment_data":     dict(self.assessment_data),
            "verification_data":   dict(self.verification_data),
            "created_at":          self.created_at,
            "updated_at":          self.updated_at,
            "framework_version":   self.framework_version,
        }


def make_recovery_metadata(
    recovery_session_id: str,
    *,
    attempt_count:       int            = 0,
    max_attempts:        int            = 3,
    backoff_seconds:     float          = 30.0,
    detection_threshold: Optional[float]= None,
    assessment_data:     Optional[Dict[str, Any]] = None,
    verification_data:   Optional[Dict[str, Any]] = None,
    metadata_id:         Optional[str]  = None,
) -> RecoveryMetadata:
    """Factory function for RecoveryMetadata."""
    return RecoveryMetadata(
        metadata_id          = metadata_id or str(uuid.uuid4()),
        recovery_session_id  = recovery_session_id,
        attempt_count        = attempt_count,
        max_attempts         = max_attempts,
        backoff_seconds      = backoff_seconds,
        detection_threshold  = detection_threshold,
        assessment_data      = dict(assessment_data) if assessment_data else {},
        verification_data    = dict(verification_data) if verification_data else {},
    )
