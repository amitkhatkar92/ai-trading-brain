"""iios/investment/decision/committee/committee_constants.py
All enumerations, constants, and thresholds for the Committee Engine.
"""
from __future__ import annotations

from enum import Enum


# ── Committee position (what the committee decides about this decision package) ───────────
class CommitteePosition(str, Enum):
    PROCEED_TO_RECOMMENDATION = "proceed_to_recommendation"   # send to recommendation engine
    DEFER_PENDING_EVIDENCE    = "defer_pending_evidence"       # more evidence needed
    INSUFFICIENT_EVIDENCE     = "insufficient_evidence"        # not enough to deliberate
    BLOCKED                   = "blocked"                      # risk/compliance barrier

    @property
    def is_terminal(self) -> bool:
        """True when no further deliberation will change this outcome."""
        return self in {
            CommitteePosition.PROCEED_TO_RECOMMENDATION,
            CommitteePosition.BLOCKED,
        }

    @property
    def severity(self) -> int:
        return {
            "proceed_to_recommendation": 0,
            "defer_pending_evidence":     1,
            "insufficient_evidence":      2,
            "blocked":                    3,
        }[self.value]


# ── Consensus level ──────────────────────────────────────────────────────────
class ConsensusLevel(str, Enum):
    UNANIMOUS    = "unanimous"     # > 95 % support weight
    STRONG       = "strong"        # > 80 %
    MAJORITY     = "majority"      # > 60 %
    SLIM_MAJORITY= "slim_majority" # > 50 %
    NO_CONSENSUS = "no_consensus"  # ≤ 50 %

    @classmethod
    def from_fraction(cls, fraction: float) -> "ConsensusLevel":
        if fraction > 0.95: return cls.UNANIMOUS
        if fraction > 0.80: return cls.STRONG
        if fraction > 0.60: return cls.MAJORITY
        if fraction > 0.50: return cls.SLIM_MAJORITY
        return cls.NO_CONSENSUS

    @property
    def supports_proceed(self) -> bool:
        return self in {
            ConsensusLevel.UNANIMOUS,
            ConsensusLevel.STRONG,
            ConsensusLevel.MAJORITY,
            ConsensusLevel.SLIM_MAJORITY,
        }


# ── Vote types ────────────────────────────────────────────────────────────────
class VoteType(str, Enum):
    SUPPORT = "support"
    OPPOSE  = "oppose"
    ABSTAIN = "abstain"


# ── Session state ─────────────────────────────────────────────────────────────
class SessionState(str, Enum):
    INITIALIZING    = "initializing"
    CONVENED        = "convened"
    REVIEWING       = "reviewing"
    DELIBERATING    = "deliberating"
    VOTING          = "voting"
    CONCLUDED       = "concluded"
    FAILED          = "failed"

    @property
    def is_active(self) -> bool:
        return self in {
            SessionState.CONVENED,
            SessionState.REVIEWING,
            SessionState.DELIBERATING,
            SessionState.VOTING,
        }

    @property
    def is_terminal(self) -> bool:
        return self in {SessionState.CONCLUDED, SessionState.FAILED}


# ── Specialist types ──────────────────────────────────────────────────────────
class SpecialistType(str, Enum):
    MARKET_INTELLIGENCE  = "market_intelligence"
    COMPANY_INTELLIGENCE = "company_intelligence"
    STRATEGY_INTELLIGENCE= "strategy_intelligence"
    RISK_INTELLIGENCE    = "risk_intelligence"
    PORTFOLIO_INTELLIGENCE="portfolio_intelligence"
    MACRO_INTELLIGENCE   = "macro_intelligence"
    QUANTITATIVE_ANALYST = "quantitative_analyst"
    FUNDAMENTAL_ANALYST  = "fundamental_analyst"
    TECHNICAL_ANALYST    = "technical_analyst"
    SENTIMENT_ANALYST    = "sentiment_analyst"
    COMPLIANCE           = "compliance"
    RESEARCH             = "research"
    CUSTOM               = "custom"


# ── Round type ────────────────────────────────────────────────────────────────
class RoundType(str, Enum):
    OPENING_REVIEW       = "opening_review"
    EVIDENCE_REVIEW      = "evidence_review"
    CHALLENGE            = "challenge"
    DELIBERATION         = "deliberation"
    FINAL_VOTE           = "final_vote"


# ── Challenge type ────────────────────────────────────────────────────────────
class ChallengeType(str, Enum):
    INSUFFICIENT_EVIDENCE  = "insufficient_evidence"
    LOW_CONFIDENCE         = "low_confidence"
    HIGH_RISK              = "high_risk"
    STALE_EVIDENCE         = "stale_evidence"
    INCONSISTENT_REASONING = "inconsistent_reasoning"
    COMPLIANCE_CONCERN     = "compliance_concern"
    EVIDENCE_QUALITY       = "evidence_quality"
    MISSING_DOMAIN         = "missing_domain"


# ── Committee quality grade ───────────────────────────────────────────────────
class CommitteeGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> "CommitteeGrade":
        if score >= 85: return cls.A
        if score >= 70: return cls.B
        if score >= 55: return cls.C
        if score >= 40: return cls.D
        return cls.F


# ── Committee engine status ───────────────────────────────────────────────────
class CommitteeStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {CommitteeStatus.READY, CommitteeStatus.RUNNING}


# ── Numeric thresholds ────────────────────────────────────────────────────────
MIN_MEMBERS_FOR_QUORUM           = 5
MIN_EVIDENCE_ITEMS_FOR_DELIBERATION = 3
DOMAIN_SUPPORT_THRESHOLD         = 55.0   # domain score ≥ this → SUPPORT
DOMAIN_OPPOSE_THRESHOLD          = 35.0   # domain score < this → OPPOSE
CONFIDENCE_MIN_FOR_SUPPORT       = 45.0   # overall confidence floor
RISK_MAX_FOR_SUPPORT             = 70.0   # overall risk ceiling
CHALLENGE_SEVERITY_THRESHOLD     = 60.0   # challenges above this are "serious"
COMMITTEE_HISTORY_WINDOW         = 200    # max sessions kept in history
DEFAULT_CHAIR_WEIGHT             = 1.50
DEFAULT_MEMBER_WEIGHT            = 1.00
