"""iios/investment/company/integration/conflict_detector.py
Detects conflicts between pairs of engine scores / signals.
"""
from __future__ import annotations

from typing import Any, List, Optional

from iios.investment.company.integration.company_state import (
    ConflictSeverity, ConflictStatus, ConflictType,
    DIVERGENCE_CRIT_THRESHOLD, DIVERGENCE_WARN_THRESHOLD,
)
from iios.investment.company.integration.company_statistics import safe_float


# ── ConflictRecord ────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
import uuid
from datetime import datetime, timezone
from typing import Dict


@dataclass
class ConflictRecord:
    """A detected conflict between two intelligence dimensions."""
    conflict_id:    str = field(default_factory=lambda: f"cfl-{uuid.uuid4().hex[:8]}")
    ticker:         str = ""
    conflict_type:  ConflictType = ConflictType.SCORE_DIVERGENCE
    engine_a:       str = ""
    engine_b:       str = ""
    assertion_a:    str = ""     # Human-readable description from engine_a
    assertion_b:    str = ""     # Human-readable description from engine_b
    severity:       ConflictSeverity = ConflictSeverity.MEDIUM
    status:         ConflictStatus = ConflictStatus.DETECTED
    resolution:     Optional[str] = None
    detected_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_critical(self) -> bool:
        return self.severity == ConflictSeverity.CRITICAL

    @property
    def is_resolved(self) -> bool:
        return self.status == ConflictStatus.RESOLVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id":   self.conflict_id,
            "ticker":        self.ticker,
            "conflict_type": self.conflict_type.value,
            "engine_a":      self.engine_a,
            "engine_b":      self.engine_b,
            "assertion_a":   self.assertion_a,
            "assertion_b":   self.assertion_b,
            "severity":      self.severity.value,
            "status":        self.status.value,
            "resolution":    self.resolution,
            "detected_at":   self.detected_at.isoformat(),
        }


# ── Detection helpers ─────────────────────────────────────────────────────────

def _score_conflict(
    ticker: str,
    engine_a: str, engine_b: str,
    score_a: Optional[float], score_b: Optional[float],
) -> Optional[ConflictRecord]:
    """Detect a score-divergence conflict between two engine scores."""
    if score_a is None or score_b is None:
        return None
    a, b = safe_float(score_a), safe_float(score_b)
    gap = abs(a - b)

    if gap >= DIVERGENCE_CRIT_THRESHOLD:
        severity = ConflictSeverity.CRITICAL
    elif gap >= DIVERGENCE_WARN_THRESHOLD:
        severity = ConflictSeverity.MEDIUM
    else:
        return None

    return ConflictRecord(
        ticker=ticker,
        conflict_type=ConflictType.SCORE_DIVERGENCE,
        engine_a=engine_a,
        engine_b=engine_b,
        assertion_a=f"{engine_a} score = {a:.0f}",
        assertion_b=f"{engine_b} score = {b:.0f}",
        severity=severity,
    )


def _signal_conflict(
    ticker: str,
    engine_a: str, engine_b: str,
    signal_a: str, signal_b: str,
    description: str,
    severity: ConflictSeverity = ConflictSeverity.MEDIUM,
) -> ConflictRecord:
    return ConflictRecord(
        ticker=ticker,
        conflict_type=ConflictType.SIGNAL_CONFLICT,
        engine_a=engine_a,
        engine_b=engine_b,
        assertion_a=signal_a,
        assertion_b=signal_b,
        severity=severity,
    )


# ── Public detection interface ────────────────────────────────────────────────

def detect_conflicts(ticker: str, intel: Any) -> List[ConflictRecord]:
    """
    Detect conflicts in the aggregated intelligence for *ticker*.

    Checks score divergences and fundamental signal contradictions.
    Accepts any object with score attributes (uses getattr safely).
    """
    conflicts: List[ConflictRecord] = []

    fin  = _sf(getattr(intel, "financial_score", None))
    earn = _sf(getattr(intel, "earnings_score", None))
    bq   = _sf(getattr(intel, "business_quality_score", None))
    val  = _sf(getattr(intel, "valuation_score", None))
    grw  = _sf(getattr(intel, "growth_score", None))
    mgmt = _sf(getattr(intel, "management_score", None))
    own  = _sf(getattr(intel, "ownership_score", None))
    opp  = _sf(getattr(intel, "opportunity_score", None))

    # ── Score divergence checks ───────────────────────────────────────────────
    for ea, sa, eb, sb in [
        ("financials", fin,  "earnings",         earn),
        ("financials", fin,  "business_quality",  bq),
        ("earnings",   earn, "business_quality",  bq),
        ("growth",     grw,  "earnings",          earn),
        ("management", mgmt, "ownership",         own),
        ("opportunity", opp, "financials",        fin),
    ]:
        c = _score_conflict(ticker, ea, eb, sa, sb)
        if c:
            conflicts.append(c)

    # ── Signal conflicts ──────────────────────────────────────────────────────
    is_profitable = getattr(intel, "is_profitable", None)
    is_growing    = getattr(intel, "is_growing", None)

    # Growing company with no profitability and very poor earnings
    if is_growing is True and is_profitable is False and earn is not None and earn < 30:
        conflicts.append(_signal_conflict(
            ticker, "growth", "earnings",
            "company is reported as growing",
            "earnings score critically low with no profitability",
            "Growing but deeply unprofitable (earnings score < 30)",
            ConflictSeverity.HIGH,
        ))

    # High opportunity score but both financials and earnings poor
    if (opp is not None and opp >= 70
            and fin is not None and fin < 30
            and earn is not None and earn < 30):
        conflicts.append(_signal_conflict(
            ticker, "opportunity", "financials",
            f"opportunity score = {opp:.0f} (high)",
            f"financial score = {fin:.0f}, earnings score = {earn:.0f} (both poor)",
            "High opportunity despite critically weak financial fundamentals",
            ConflictSeverity.CRITICAL,
        ))

    # High promoter pledge with high management quality
    pledge = getattr(intel, "promoter_pledge_pct", None)
    if pledge is not None and safe_float(pledge) >= 50 and mgmt is not None and mgmt >= 70:
        conflicts.append(_signal_conflict(
            ticker, "management", "ownership",
            f"management score = {mgmt:.0f} (high)",
            f"promoter pledge = {safe_float(pledge):.0f}% (critical)",
            "High management score with critically high promoter pledge",
            ConflictSeverity.HIGH,
        ))

    return conflicts


def _sf(v: Optional[Any]) -> Optional[float]:
    if v is None:
        return None
    return safe_float(v)
