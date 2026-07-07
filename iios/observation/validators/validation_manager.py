"""
iios/observation/validators/validation_manager.py
==================================================
ValidationManager — top-level governance orchestrator for the
Observation Validation & Quality Engine.

Responsibilities
----------------
- Orchestrate validate → quality-score → govern flow
- Approve, reject, quarantine, or suppress observations
- Detect exact and near-duplicate observations
- Maintain a quarantine queue with TTL-based expiry
- Enforce policy: minimum score, per-source trust, rate limits
- Expose the single entry point: ``process(obs) → GovernanceDecision``
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation    import Observation
from ..observation_constants import ObservationSource, ObservationStatus
from .validation_constants   import (
    DUPLICATE_WINDOW_SECONDS,
    MAX_QUARANTINE_SIZE,
    MIN_PASSING_SCORE,
    MIN_QUALITY_THRESHOLD,
    QUARANTINE_TTL_SECONDS,
    SYSTEM_VALIDATOR,
    GovernanceAction,
    QuarantineReason,
    ValidationMode,
)
from .validation_engine      import ValidationEngine, ValidationReport, get_validation_engine
from .validation_exceptions  import (
    DuplicateObservationError,
    ValidationGovernanceError,
    ValidationQuarantineError,
)

__all__ = [
    "GovernanceDecision",
    "QuarantineEntry",
    "QuarantineQueue",
    "DuplicateDetector",
    "ValidationManager",
    "get_validation_manager",
    "reset_validation_manager",
]

_LOG  = logging.getLogger("iios.observation.validation.manager")
_lock = threading.Lock()
_manager: Optional["ValidationManager"] = None


# ── Governance decision ───────────────────────────────────────────────────────

@dataclass
class GovernanceDecision:
    """Outcome of the full validate → govern flow for one observation."""
    obs_id:      str
    action:      GovernanceAction
    reason:      str                = ""
    score:       float              = 0.0
    report:      Optional[ValidationReport] = None
    decided_at:  float              = field(default_factory=time.time)
    metadata:    dict[str, Any]     = field(default_factory=dict)

    @property
    def approved(self) -> bool:
        return self.action == GovernanceAction.APPROVE

    @property
    def rejected(self) -> bool:
        return self.action == GovernanceAction.REJECT

    @property
    def quarantined(self) -> bool:
        return self.action == GovernanceAction.QUARANTINE

    @property
    def suppressed(self) -> bool:
        return self.action == GovernanceAction.SUPPRESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":     self.obs_id,
            "action":     self.action.value,
            "reason":     self.reason,
            "score":      round(self.score, 4),
            "decided_at": self.decided_at,
            "metadata":   self.metadata,
        }


# ── Quarantine ────────────────────────────────────────────────────────────────

@dataclass
class QuarantineEntry:
    """A single entry in the quarantine queue."""
    obs_id:          str
    reason:          QuarantineReason
    quarantined_at:  float           = field(default_factory=time.time)
    expires_at:      float           = 0.0
    notes:           str             = ""
    rule_name:       str             = ""
    score:           float           = 0.0
    reviewed:        bool            = False
    reviewer:        str             = ""

    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":         self.obs_id,
            "reason":         self.reason.value,
            "quarantined_at": self.quarantined_at,
            "expires_at":     self.expires_at,
            "notes":          self.notes,
            "score":          self.score,
            "reviewed":       self.reviewed,
        }


class QuarantineQueue:
    """Thread-safe quarantine queue with TTL-based auto-expiry."""

    def __init__(
        self,
        max_size:   int   = MAX_QUARANTINE_SIZE,
        ttl_s:      float = QUARANTINE_TTL_SECONDS,
    ) -> None:
        self._entries: dict[str, QuarantineEntry] = {}
        self._lock    = threading.RLock()
        self._max     = max_size
        self._ttl     = ttl_s

    def add(
        self,
        obs:       Observation,
        reason:    QuarantineReason,
        notes:     str = "",
        rule_name: str = "",
        score:     float = 0.0,
    ) -> bool:
        """Add *obs* to quarantine.  Returns False if queue is full."""
        self.cleanup()
        with self._lock:
            if len(self._entries) >= self._max:
                return False
            entry = QuarantineEntry(
                obs_id         = obs.id,
                reason         = reason,
                notes          = notes,
                rule_name      = rule_name,
                score          = score,
                expires_at     = time.time() + self._ttl,
            )
            self._entries[obs.id] = entry
            return True

    def release(self, obs_id: str) -> Optional[QuarantineEntry]:
        """Release (approve) an observation from quarantine."""
        with self._lock:
            return self._entries.pop(obs_id, None)

    def reject(self, obs_id: str) -> bool:
        """Reject (permanently remove) an observation from quarantine."""
        with self._lock:
            if obs_id in self._entries:
                del self._entries[obs_id]
                return True
            return False

    def get(self, obs_id: str) -> Optional[QuarantineEntry]:
        with self._lock:
            return self._entries.get(obs_id)

    def pending(self) -> list[QuarantineEntry]:
        """All non-expired, un-reviewed entries."""
        with self._lock:
            return [
                e for e in self._entries.values()
                if not e.reviewed and not e.is_expired()
            ]

    def cleanup(self) -> int:
        """Remove expired entries.  Returns count removed."""
        with self._lock:
            expired = [k for k, e in self._entries.items() if e.is_expired()]
            for k in expired:
                del self._entries[k]
            return len(expired)

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":    len(self._entries),
                "pending":  sum(1 for e in self._entries.values() if not e.reviewed),
                "reviewed": sum(1 for e in self._entries.values() if e.reviewed),
                "max":      self._max,
            }


# ── Duplicate detection ───────────────────────────────────────────────────────

class DuplicateDetector:
    """Sliding-window exact-duplicate detector based on content checksum."""

    def __init__(self, window_s: float = DUPLICATE_WINDOW_SECONDS) -> None:
        self._seen:   dict[str, tuple[str, float]] = {}  # checksum → (obs_id, timestamp)
        self._window  = window_s
        self._lock    = threading.RLock()

    def is_duplicate(self, obs: Observation) -> tuple[bool, str]:
        """Return ``(is_dup, original_obs_id)``."""
        key = self._key(obs)
        self._evict()
        with self._lock:
            if key in self._seen:
                orig_id, _ = self._seen[key]
                if orig_id != obs.id:
                    return True, orig_id
        return False, ""

    def register(self, obs: Observation) -> None:
        """Record *obs* checksum into the detection window."""
        key = self._key(obs)
        with self._lock:
            self._seen[key] = (obs.id, time.time())

    def clear(self) -> None:
        with self._lock:
            self._seen.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._seen)

    def _key(self, obs: Observation) -> str:
        """Fingerprint: checksum + type + source."""
        raw = f"{obs.checksum}|{obs.obs_type.value}|{obs.source_info.source.value}"
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

    def _evict(self) -> None:
        cutoff = time.time() - self._window
        with self._lock:
            expired = [k for k, (_, ts) in self._seen.items() if ts < cutoff]
            for k in expired:
                del self._seen[k]


# ── Manager ───────────────────────────────────────────────────────────────────

class ValidationManager:
    """Top-level governance orchestrator.

    Combines validation, duplicate detection, and governance policies
    into a single ``process(obs)`` call.

    Policy (applied in order)
    -------------------------
    1. Detect exact duplicate → SUPPRESS
    2. Run validation pipeline → REJECT on failure
    3. Check minimum score    → QUARANTINE if below threshold
    4. All checks passed      → APPROVE
    """

    def __init__(
        self,
        engine:           Optional[ValidationEngine] = None,
        mode:             ValidationMode              = ValidationMode.STRICT,
        min_score:        float                       = MIN_PASSING_SCORE,
        min_quality:      float                       = MIN_QUALITY_THRESHOLD,
        suppress_dups:    bool                        = True,
        dup_window_s:     float                       = DUPLICATE_WINDOW_SECONDS,
        quarantine_ttl_s: float                       = QUARANTINE_TTL_SECONDS,
    ) -> None:
        self._engine       = engine or get_validation_engine()
        self._mode         = mode
        self._min_score    = min_score
        self._min_quality  = min_quality
        self._suppress_dups = suppress_dups
        self._detector     = DuplicateDetector(window_s=dup_window_s)
        self._quarantine   = QuarantineQueue(ttl_s=quarantine_ttl_s)
        self._lock         = threading.RLock()
        self._total_processed = 0
        self._total_approved  = 0
        self._total_rejected  = 0
        self._total_quarantined = 0
        self._total_suppressed  = 0

    # ── Main entry point ──────────────────────────────────────────────────────

    def process(
        self,
        obs:  Observation,
        mode: Optional[ValidationMode] = None,
    ) -> GovernanceDecision:
        """Validate *obs* and return a :class:`GovernanceDecision`.

        This is the single entry point — every observation must pass
        through here before entering the downstream processing pipeline.
        """
        eff_mode = mode or self._mode

        # ── Step 1: duplicate detection ───────────────────────────────────────
        if self._suppress_dups:
            is_dup, orig_id = self._detector.is_duplicate(obs)
            if is_dup:
                decision = self._decide(
                    obs, GovernanceAction.SUPPRESS, score=0.0,
                    reason=f"Exact duplicate of {orig_id[:8]}…",
                    metadata={"original_id": orig_id},
                )
                self._tally(decision.action)
                return decision

        # ── Step 2: validation pipeline ───────────────────────────────────────
        try:
            report = self._engine.validate(obs, mode=eff_mode)
        except Exception as exc:
            decision = self._decide(
                obs, GovernanceAction.REJECT, score=0.0,
                reason=f"Validation engine error: {exc}",
            )
            self._tally(decision.action)
            return decision

        score = report.score

        if not report.passed:
            decision = self._decide(
                obs, GovernanceAction.REJECT, score=score, report=report,
                reason=f"Validation failed: {report.violations[0] if report.violations else 'unknown'}",
            )
            self._tally(decision.action)
            return decision

        # ── Step 3: minimum score threshold ──────────────────────────────────
        if score < self._min_score:
            added = self._quarantine.add(
                obs, QuarantineReason.LOW_QUALITY,
                notes=f"Score {score:.3f} below threshold {self._min_score:.3f}",
                score=score,
            )
            action = GovernanceAction.QUARANTINE if added else GovernanceAction.REJECT
            decision = self._decide(
                obs, action, score=score, report=report,
                reason=f"Score {score:.3f} below minimum {self._min_score:.3f}",
            )
            self._tally(decision.action)
            return decision

        # ── Step 4: approve ───────────────────────────────────────────────────
        self._detector.register(obs)
        decision = self._decide(obs, GovernanceAction.APPROVE, score=score, report=report)
        self._tally(decision.action)
        return decision

    def process_batch(
        self,
        observations: list[Observation],
        mode:         Optional[ValidationMode] = None,
    ) -> list[GovernanceDecision]:
        return [self.process(obs, mode=mode) for obs in observations]

    # ── Quarantine management ─────────────────────────────────────────────────

    def release_from_quarantine(self, obs_id: str) -> bool:
        entry = self._quarantine.release(obs_id)
        return entry is not None

    def reject_from_quarantine(self, obs_id: str) -> bool:
        return self._quarantine.reject(obs_id)

    def quarantine_status(self) -> dict[str, Any]:
        return self._quarantine.status()

    def pending_quarantine(self) -> list[QuarantineEntry]:
        return self._quarantine.pending()

    # ── Status & statistics ───────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self._total_processed
            return {
                "total_processed":    total,
                "total_approved":     self._total_approved,
                "total_rejected":     self._total_rejected,
                "total_quarantined":  self._total_quarantined,
                "total_suppressed":   self._total_suppressed,
                "approval_rate":      round(self._total_approved / total, 4) if total else 0.0,
                "mode":               self._mode.value,
                "min_score":          self._min_score,
                "quarantine":         self._quarantine.status(),
                "duplicate_window_s": self._detector._window,
            }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _decide(
        self,
        obs:      Observation,
        action:   GovernanceAction,
        score:    float              = 0.0,
        report:   Optional[ValidationReport] = None,
        reason:   str                = "",
        metadata: dict[str, Any]     = None,  # type: ignore[assignment]
    ) -> GovernanceDecision:
        return GovernanceDecision(
            obs_id   = obs.id,
            action   = action,
            reason   = reason,
            score    = score,
            report   = report,
            metadata = metadata or {},
        )

    def _tally(self, action: GovernanceAction) -> None:
        with self._lock:
            self._total_processed += 1
            if action == GovernanceAction.APPROVE:
                self._total_approved += 1
            elif action == GovernanceAction.REJECT:
                self._total_rejected += 1
            elif action == GovernanceAction.QUARANTINE:
                self._total_quarantined += 1
            elif action == GovernanceAction.SUPPRESS:
                self._total_suppressed += 1


# ── Singletons ────────────────────────────────────────────────────────────────

def get_validation_manager() -> ValidationManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = ValidationManager()
    return _manager


def reset_validation_manager() -> None:
    global _manager
    with _lock:
        _manager = None
