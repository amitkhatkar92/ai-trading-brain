"""
iios/observation/quality/quality_assessment.py
===============================================
Dimension assessors for the Observation Quality Engine.

Each assessor computes a raw score in [0.0, 1.0] for one quality dimension.

Assessors
---------
CompletenessAssessor  — required fields and metadata coverage
AccuracyAssessor      — value plausibility
ConsistencyAssessor   — internal cross-field coherence
TimelinessAssessor    — event-to-ingestion latency
ReliabilityAssessor   — source historical reliability (configurable trust map)
SourceTrustAssessor   — static trust rating per ObservationSource
FreshnessAssessor     — remaining TTL fraction
IntegrityAssessor     — checksum verification
"""
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from ..observation_constants import ObservationSource, ObservationType
from ..models.observation    import Observation
from .quality_score          import DEFAULT_WEIGHTS, DimensionScore

__all__ = [
    "DimensionAssessor",
    "CompletenessAssessor",
    "AccuracyAssessor",
    "ConsistencyAssessor",
    "TimelinessAssessor",
    "ReliabilityAssessor",
    "SourceTrustAssessor",
    "FreshnessAssessor",
    "IntegrityAssessor",
]

_LOG = logging.getLogger("iios.observation.quality.assessment")

# ── Static source trust table ─────────────────────────────────────────────────
# Values reflect relative reliability of each source on [0, 1].
_SOURCE_TRUST: dict[ObservationSource, float] = {
    ObservationSource.DHAN_FEED:      0.90,
    ObservationSource.YFINANCE:       0.80,
    ObservationSource.NSE_FEED:       0.95,
    ObservationSource.BSE_FEED:       0.95,
    ObservationSource.ZERODHA:        0.90,
    ObservationSource.BLOOMBERG:      0.98,
    ObservationSource.REUTERS:        0.95,
    ObservationSource.INTERNAL_AGENT: 0.85,
    ObservationSource.MANUAL_ENTRY:   0.60,
    ObservationSource.BACKTEST:       0.70,
    ObservationSource.SIMULATION:     0.65,
    ObservationSource.TELEGRAM:       0.50,
    ObservationSource.WEBHOOK:        0.70,
    ObservationSource.API_CALL:       0.75,
    ObservationSource.FILE_IMPORT:    0.65,
    ObservationSource.SCHEDULER:      0.85,
    ObservationSource.SYSTEM:         0.90,
    ObservationSource.UNKNOWN:        0.30,
}


# ── Abstract base ─────────────────────────────────────────────────────────────

class DimensionAssessor(ABC):
    """Base class for quality dimension scorers."""

    dimension: str

    def assess(self, obs: Observation) -> DimensionScore:
        try:
            score, reason = self._score(obs)
        except Exception as exc:
            _LOG.debug("Assessor %s failed for %s: %s", self.dimension, obs.uid[:8], exc)
            score, reason = 0.0, f"error: {exc}"
        weight = DEFAULT_WEIGHTS.get(self.dimension, 0.10)
        return DimensionScore(
            name   = self.dimension,
            score  = max(0.0, min(1.0, score)),
            weight = weight,
            reason = reason,
        )

    @abstractmethod
    def _score(self, obs: Observation) -> tuple[float, str]:
        """Return ``(score_in_0_1, reason_str)``."""


# ── Completeness ──────────────────────────────────────────────────────────────

class CompletenessAssessor(DimensionAssessor):
    """Score based on how many expected fields are present."""
    dimension = "completeness"

    def _score(self, obs: Observation) -> tuple[float, str]:
        checks = {
            "content_present":    obs.content is not None,
            "title_present":      bool(obs.title and obs.title.strip()),
            "type_known":         obs.obs_type != ObservationType.UNKNOWN,
            "source_known":       obs.source_info.source != ObservationSource.UNKNOWN,
            "schema_version":     bool(obs.schema_version),
            "confidence_set":     obs.metadata.confidence > 0.0,
            "tags_present":       len(obs.metadata.tags) > 0,
            "instrument_present": bool(obs.source_info.instrument),
        }
        score = sum(checks.values()) / len(checks)
        missing = [k for k, v in checks.items() if not v]
        reason = "all fields present" if not missing else f"missing: {', '.join(missing)}"
        return score, reason


# ── Accuracy ──────────────────────────────────────────────────────────────────

class AccuracyAssessor(DimensionAssessor):
    """Score based on value plausibility and range checks."""
    dimension = "accuracy"

    def _score(self, obs: Observation) -> tuple[float, str]:
        issues: list[str] = []
        checks = 0
        passed = 0

        # confidence in [0, 1]
        checks += 1
        if 0.0 <= obs.metadata.confidence <= 1.0:
            passed += 1
        else:
            issues.append("confidence_out_of_range")

        # created_at is a plausible unix timestamp (2020–2100)
        checks += 1
        if 1_577_836_800.0 < obs.created_at < 4_102_444_800.0:
            passed += 1
        else:
            issues.append("created_at_implausible")

        # content is not empty
        checks += 1
        if obs.content is not None and obs.content != {} and obs.content != "":
            passed += 1
        else:
            issues.append("content_empty")

        # For market data: check price fields if available
        if obs.obs_type == ObservationType.MARKET_DATA and isinstance(obs.content, dict):
            for price_key in ("close", "price", "ltp", "last_price"):
                if price_key in obs.content:
                    checks += 1
                    val = obs.content[price_key]
                    if isinstance(val, (int, float)) and val > 0:
                        passed += 1
                    else:
                        issues.append(f"{price_key}_invalid")
                    break

        score  = passed / max(1, checks)
        reason = "all checks passed" if not issues else f"issues: {', '.join(issues)}"
        return score, reason


# ── Consistency ───────────────────────────────────────────────────────────────

class ConsistencyAssessor(DimensionAssessor):
    """Score based on internal cross-field coherence."""
    dimension = "consistency"

    def _score(self, obs: Observation) -> tuple[float, str]:
        issues: list[str] = []

        # checksum should match content
        if obs.checksum and obs.content is not None:
            raw      = str(obs.content).encode("utf-8", errors="replace")
            computed = hashlib.md5(raw, usedforsecurity=False).hexdigest()
            if computed != obs.checksum:
                issues.append("checksum_mismatch")

        # created_at ≤ updated_at
        if obs.updated_at < obs.created_at - 1.0:
            issues.append("updated_before_created")

        # version should be ≥ 1
        if obs.version < 1:
            issues.append("invalid_version")

        # not expired and status not terminal conflict
        if obs.metadata.is_expired and obs.is_active:
            issues.append("expired_but_active")

        score  = 1.0 - len(issues) * 0.25
        reason = "consistent" if not issues else f"inconsistencies: {', '.join(issues)}"
        return max(0.0, score), reason


# ── Timeliness ────────────────────────────────────────────────────────────────

class TimelinessAssessor(DimensionAssessor):
    """Score based on latency from event time to ingestion.

    Uses ``source_info.source_timestamp`` if available, otherwise
    ``metadata.observed_at``, otherwise ``created_at`` (perfect score).
    """
    dimension = "timeliness"

    # Acceptable latency budgets per observation type (seconds)
    _LATENCY_BUDGET: dict[ObservationType, float] = {
        ObservationType.MARKET_DATA:      5.0,
        ObservationType.TRADE_EVENT:      2.0,
        ObservationType.ORDER_EVENT:      2.0,
        ObservationType.SYSTEM_EVENT:    10.0,
        ObservationType.NEWS:            300.0,
        ObservationType.ECONOMIC:       3600.0,
        ObservationType.CORPORATE_ACTION: 86400.0,
    }

    def _score(self, obs: Observation) -> tuple[float, str]:
        event_ts = (
            obs.source_info.source_timestamp
            or obs.metadata.observed_at
        )
        if event_ts is None:
            return 1.0, "no event timestamp — assuming timely"

        latency = obs.created_at - event_ts
        if latency < 0:
            latency = 0.0  # clock skew; treat as timely

        budget = self._LATENCY_BUDGET.get(obs.obs_type, 60.0)
        if budget <= 0:
            return 1.0, "no latency budget defined"

        ratio  = latency / budget
        score  = max(0.0, 1.0 - ratio)
        reason = f"latency={latency:.1f}s vs budget={budget:.1f}s"
        return score, reason


# ── Reliability ───────────────────────────────────────────────────────────────

class ReliabilityAssessor(DimensionAssessor):
    """Configurable per-source reliability score.

    Defaults to :data:`_SOURCE_TRUST`.  Callers can override by passing
    a custom trust map.
    """
    dimension = "reliability"

    def __init__(self, trust_map: dict[ObservationSource, float] | None = None) -> None:
        self._trust = trust_map or _SOURCE_TRUST

    def _score(self, obs: Observation) -> tuple[float, str]:
        src   = obs.source_info.source
        score = self._trust.get(src, 0.50)
        return score, f"source={src.value} → reliability={score:.2f}"


# ── Source trust ──────────────────────────────────────────────────────────────

class SourceTrustAssessor(DimensionAssessor):
    """Static trust rating per source (uses same trust table as Reliability)."""
    dimension = "source_trust"

    def __init__(self, trust_map: dict[ObservationSource, float] | None = None) -> None:
        self._trust = trust_map or _SOURCE_TRUST

    def _score(self, obs: Observation) -> tuple[float, str]:
        src   = obs.source_info.source
        score = self._trust.get(src, 0.50)
        return score, f"trust[{src.value}]={score:.2f}"


# ── Freshness ─────────────────────────────────────────────────────────────────

class FreshnessAssessor(DimensionAssessor):
    """Score based on remaining TTL fraction."""
    dimension = "freshness"

    def _score(self, obs: Observation) -> tuple[float, str]:
        if obs.metadata.is_expired:
            return 0.0, "observation has expired"

        expires_at = obs.metadata.expires_at
        if expires_at is None:
            return 1.0, "no expiry — treating as perpetually fresh"

        total_life = expires_at - obs.metadata.created_at
        if total_life <= 0:
            return 0.0, "zero-duration TTL"

        remaining = expires_at - time.time()
        score     = max(0.0, min(1.0, remaining / total_life))
        return score, f"remaining={remaining:.0f}s / ttl={total_life:.0f}s"


# ── Integrity ─────────────────────────────────────────────────────────────────

class IntegrityAssessor(DimensionAssessor):
    """Score based on checksum verification."""
    dimension = "integrity"

    def _score(self, obs: Observation) -> tuple[float, str]:
        if not obs.checksum:
            return 0.5, "no checksum stored — integrity cannot be verified"
        if obs.content is None:
            return 0.5, "no content — checksum check skipped"

        raw      = str(obs.content).encode("utf-8", errors="replace")
        computed = hashlib.md5(raw, usedforsecurity=False).hexdigest()
        if computed == obs.checksum:
            return 1.0, "checksum verified"
        return 0.0, f"checksum MISMATCH: stored={obs.checksum[:8]}… computed={computed[:8]}…"
