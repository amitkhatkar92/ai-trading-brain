"""
iios/observation/quality/quality_manager.py
============================================
QualityManager — policy enforcement layer on top of QualityEngine.

Responsibilities
----------------
- Score every observation via the QualityEngine
- Route based on quality tier:
    EXCELLENT / GOOD  → fast-track (proceed immediately)
    FAIR              → flag for monitoring; proceed
    POOR              → quarantine or reject based on policy
- Reject observations below an absolute minimum OQI
- Write quality tier and OQI back to the observation metadata
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation    import Observation
from ..observation_constants import ObservationQuality
from .quality_engine         import QualityEngine, get_quality_engine
from .quality_score          import QualityScore
from ..validators.validation_constants  import MIN_QUALITY_THRESHOLD
from ..validators.validation_exceptions import QualityThresholdError

__all__ = [
    "QualityDecision",
    "QualityPolicy",
    "QualityManager",
    "get_quality_manager",
    "reset_quality_manager",
]

_LOG  = logging.getLogger("iios.observation.quality.manager")
_lock = threading.Lock()
_manager: Optional["QualityManager"] = None


# ── Policy ────────────────────────────────────────────────────────────────────

@dataclass
class QualityPolicy:
    """Configurable quality routing policy."""
    min_oqi:            float = MIN_QUALITY_THRESHOLD  # hard reject below this
    quarantine_below:   float = 0.50                   # quarantine below this
    flag_below:         float = 0.60                   # flag for monitoring below this
    fast_track_above:   float = 0.80                   # skip normal queue above this
    reject_on_low:      bool  = False                  # True → reject instead of quarantine

    def action_for(self, oqi: float) -> str:
        if oqi < self.min_oqi:
            return "reject"
        if oqi < self.quarantine_below:
            return "quarantine" if not self.reject_on_low else "reject"
        if oqi < self.flag_below:
            return "flag"
        if oqi >= self.fast_track_above:
            return "fast_track"
        return "proceed"


# ── Decision ──────────────────────────────────────────────────────────────────

@dataclass
class QualityDecision:
    """Outcome of the quality manager's assessment of one observation."""
    obs_id:     str
    oqi:        float
    tier:       ObservationQuality
    action:     str                   # "approve"/"reject"/"quarantine"/"flag"/"fast_track"
    reason:     str                   = ""
    score:      Optional[QualityScore] = None
    decided_at: float                 = field(default_factory=time.time)

    @property
    def approved(self) -> bool:
        return self.action in ("proceed", "fast_track", "flag")

    @property
    def rejected(self) -> bool:
        return self.action == "reject"

    @property
    def quarantined(self) -> bool:
        return self.action == "quarantine"

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":     self.obs_id,
            "oqi":        round(self.oqi, 4),
            "tier":       self.tier.value,
            "action":     self.action,
            "reason":     self.reason,
            "decided_at": self.decided_at,
        }


# ── Manager ───────────────────────────────────────────────────────────────────

class QualityManager:
    """Applies quality policy to observations.

    Parameters
    ----------
    engine:
        :class:`QualityEngine` to use.  Defaults to global singleton.
    policy:
        :class:`QualityPolicy` governing routing decisions.
    raise_on_reject:
        If True, raises :class:`QualityThresholdError` for rejected obs.
    """

    def __init__(
        self,
        engine:          Optional[QualityEngine] = None,
        policy:          Optional[QualityPolicy] = None,
        raise_on_reject: bool                    = False,
    ) -> None:
        self._engine         = engine or get_quality_engine()
        self._policy         = policy or QualityPolicy()
        self._raise          = raise_on_reject
        self._lock           = threading.RLock()
        self._total          = 0
        self._by_action:     dict[str, int] = {}

    def assess(self, obs: Observation) -> QualityDecision:
        """Score *obs* and return a routing :class:`QualityDecision`."""
        qs     = self._engine.score(obs)
        action = self._policy.action_for(qs.oqi)
        reason = self._reason(action, qs)

        decision = QualityDecision(
            obs_id = obs.id,
            oqi    = qs.oqi,
            tier   = qs.tier,
            action = action,
            reason = reason,
            score  = qs,
        )

        self._tally(action)

        _LOG.log(
            logging.DEBUG if decision.approved else logging.INFO,
            "Quality decision: %s | oqi=%.3f [%s] | action=%s",
            obs.uid[:8] + "…", qs.oqi, qs.tier.value, action,
        )

        if decision.rejected and self._raise:
            raise QualityThresholdError(
                f"Observation {obs.uid[:8]} rejected: OQI={qs.oqi:.3f} < {self._policy.min_oqi:.3f}",
                oqi       = qs.oqi,
                threshold = self._policy.min_oqi,
            )
        return decision

    def assess_batch(self, observations: list[Observation]) -> list[QualityDecision]:
        return [self.assess(obs) for obs in observations]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":      self._total,
                "by_action":  dict(self._by_action),
                "policy":     {
                    "min_oqi":          self._policy.min_oqi,
                    "quarantine_below": self._policy.quarantine_below,
                    "flag_below":       self._policy.flag_below,
                    "fast_track_above": self._policy.fast_track_above,
                },
            }

    def _reason(self, action: str, qs: QualityScore) -> str:
        reasons = {
            "reject":      f"OQI={qs.oqi:.3f} below minimum {self._policy.min_oqi:.3f}",
            "quarantine":  f"OQI={qs.oqi:.3f} below quarantine threshold {self._policy.quarantine_below:.3f}",
            "flag":        f"OQI={qs.oqi:.3f} below flag threshold {self._policy.flag_below:.3f}; monitoring",
            "fast_track":  f"OQI={qs.oqi:.3f} — excellent quality; fast-tracked",
            "proceed":     f"OQI={qs.oqi:.3f} within acceptable range",
        }
        return reasons.get(action, f"OQI={qs.oqi:.3f}")

    def _tally(self, action: str) -> None:
        with self._lock:
            self._total += 1
            self._by_action[action] = self._by_action.get(action, 0) + 1


# ── Singletons ────────────────────────────────────────────────────────────────

def get_quality_manager() -> QualityManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = QualityManager()
    return _manager


def reset_quality_manager() -> None:
    global _manager
    with _lock:
        _manager = None
