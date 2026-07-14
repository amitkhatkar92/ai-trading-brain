"""iios/investment/decision/core/decision_constants.py
All enumerations, state machine, and threshold constants for the Decision Framework.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DecisionStatus(str, Enum):
    """Lifecycle states of a decision — drives the state machine."""
    CREATED             = "created"
    COLLECTING_EVIDENCE = "collecting_evidence"
    UNDER_REVIEW        = "under_review"
    SCORED              = "scored"
    RISK_REVIEWED       = "risk_reviewed"
    APPROVED            = "approved"
    REJECTED            = "rejected"
    PUBLISHED           = "published"
    ARCHIVED            = "archived"
    EXPIRED             = "expired"
    FAILED              = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {DecisionStatus.ARCHIVED, DecisionStatus.EXPIRED}

    @property
    def is_active(self) -> bool:
        return self in {
            DecisionStatus.CREATED,
            DecisionStatus.COLLECTING_EVIDENCE,
            DecisionStatus.UNDER_REVIEW,
            DecisionStatus.SCORED,
            DecisionStatus.RISK_REVIEWED,
        }

    @property
    def is_final(self) -> bool:
        return self in {
            DecisionStatus.APPROVED,
            DecisionStatus.REJECTED,
            DecisionStatus.PUBLISHED,
            DecisionStatus.FAILED,
        }


class DecisionType(str, Enum):
    INVESTMENT           = "investment"
    PORTFOLIO_ADJUSTMENT = "portfolio_adjustment"
    RISK_ACTION          = "risk_action"
    RESEARCH             = "research"
    SYSTEM               = "system"


class RecommendationType(str, Enum):
    BUY               = "buy"
    STRONG_BUY        = "strong_buy"
    ACCUMULATE        = "accumulate"
    HOLD              = "hold"
    REDUCE            = "reduce"
    SELL              = "sell"
    STRONG_SELL       = "strong_sell"
    AVOID             = "avoid"
    WATCHLIST         = "watchlist"
    RESEARCH_REQUIRED = "research_required"

    @property
    def is_bullish(self) -> bool:
        return self in {
            RecommendationType.BUY,
            RecommendationType.STRONG_BUY,
            RecommendationType.ACCUMULATE,
        }

    @property
    def is_bearish(self) -> bool:
        return self in {
            RecommendationType.SELL,
            RecommendationType.STRONG_SELL,
            RecommendationType.REDUCE,
        }

    @property
    def is_neutral(self) -> bool:
        return self in {RecommendationType.HOLD, RecommendationType.WATCHLIST}

    @property
    def direction_score(self) -> int:
        """−2 (strong sell) … +2 (strong buy)."""
        _map = {
            "strong_buy": 2, "buy": 2, "accumulate": 1,
            "hold": 0, "watchlist": 0, "research_required": 0,
            "reduce": -1, "sell": -2, "strong_sell": -2, "avoid": -2,
        }
        return _map.get(self.value, 0)


class ActionType(str, Enum):
    BUY_ORDER            = "buy_order"
    SELL_ORDER           = "sell_order"
    REDUCE_POSITION      = "reduce_position"
    INCREASE_POSITION    = "increase_position"
    REBALANCE            = "rebalance"
    HEDGE                = "hedge"
    EXIT                 = "exit"
    RESEARCH             = "research"
    MONITOR              = "monitor"
    ALERT                = "alert"
    PORTFOLIO_ADJUSTMENT = "portfolio_adjustment"
    RISK_ACTION          = "risk_action"


class DecisionEventType(str, Enum):
    CREATED           = "decision_created"
    EVIDENCE_READY    = "evidence_ready"
    EVIDENCE_FAILED   = "evidence_failed"
    VALIDATED         = "validated"
    VALIDATION_FAILED = "validation_failed"
    PREPARED          = "prepared"
    EVALUATED         = "evaluated"
    SCORED            = "scored"
    RISK_REVIEWED     = "risk_reviewed"
    RISK_REJECTED     = "risk_rejected"
    APPROVED          = "approved"
    REJECTED          = "rejected"
    PUBLISHED         = "published"
    ARCHIVED          = "archived"
    EXPIRED           = "expired"
    OVERRIDE          = "override"
    REVIEW_REQUESTED  = "review_requested"
    STATE_CHANGED     = "state_changed"
    FRAMEWORK_STARTED = "framework_started"
    FRAMEWORK_STOPPED = "framework_stopped"


class DecisionPriority(str, Enum):
    LOW      = "low"
    NORMAL   = "normal"
    HIGH     = "high"
    URGENT   = "urgent"
    CRITICAL = "critical"

    @property
    def sort_key(self) -> int:
        return {"low": 0, "normal": 1, "high": 2, "urgent": 3, "critical": 4}[self.value]


class ApprovalStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDE = "override"
    EXPIRED  = "expired"

    @property
    def is_positive(self) -> bool:
        return self in {ApprovalStatus.APPROVED, ApprovalStatus.OVERRIDE}


class RiskReviewStatus(str, Enum):
    PENDING     = "pending"
    APPROVED    = "approved"
    REJECTED    = "rejected"
    CONDITIONAL = "conditional"

    @property
    def allows_approval(self) -> bool:
        return self in {RiskReviewStatus.APPROVED, RiskReviewStatus.CONDITIONAL}


class ConfidenceLevel(str, Enum):
    VERY_LOW  = "very_low"
    LOW       = "low"
    MEDIUM    = "medium"
    HIGH      = "high"
    VERY_HIGH = "very_high"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 85:
            return cls.VERY_HIGH
        if score >= 70:
            return cls.HIGH
        if score >= 50:
            return cls.MEDIUM
        if score >= 30:
            return cls.LOW
        return cls.VERY_LOW


class EnvironmentProfile(str, Enum):
    DEVELOPMENT = "development"
    PAPER       = "paper"
    LIVE        = "live"
    BACKTEST    = "backtest"

    @property
    def requires_approval(self) -> bool:
        return self in {EnvironmentProfile.PAPER, EnvironmentProfile.LIVE}

    @property
    def is_production(self) -> bool:
        return self == EnvironmentProfile.LIVE


class DecisionFrameworkStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    BUSY         = "busy"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {
            DecisionFrameworkStatus.READY,
            DecisionFrameworkStatus.BUSY,
        }


# ---------------------------------------------------------------------------
# State machine — valid transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: Dict[DecisionStatus, Set[DecisionStatus]] = {
    DecisionStatus.CREATED: {
        DecisionStatus.COLLECTING_EVIDENCE,
        DecisionStatus.FAILED,
    },
    DecisionStatus.COLLECTING_EVIDENCE: {
        DecisionStatus.UNDER_REVIEW,
        DecisionStatus.FAILED,
    },
    DecisionStatus.UNDER_REVIEW: {
        DecisionStatus.SCORED,
        DecisionStatus.FAILED,
    },
    DecisionStatus.SCORED: {
        DecisionStatus.RISK_REVIEWED,
        DecisionStatus.FAILED,
    },
    DecisionStatus.RISK_REVIEWED: {
        DecisionStatus.APPROVED,
        DecisionStatus.REJECTED,
        DecisionStatus.FAILED,
    },
    DecisionStatus.APPROVED: {
        DecisionStatus.PUBLISHED,
        DecisionStatus.FAILED,
    },
    DecisionStatus.REJECTED: {
        DecisionStatus.ARCHIVED,
    },
    DecisionStatus.PUBLISHED: {
        DecisionStatus.ARCHIVED,
        DecisionStatus.EXPIRED,
    },
    DecisionStatus.FAILED: {
        DecisionStatus.ARCHIVED,
    },
    DecisionStatus.EXPIRED: {
        DecisionStatus.ARCHIVED,
    },
    DecisionStatus.ARCHIVED: set(),   # terminal
}

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

DEFAULT_APPROVAL_THRESHOLD    = 65.0    # minimum decision score (0–100)
DEFAULT_CONFIDENCE_THRESHOLD  = 50.0    # minimum confidence (0–100)
DEFAULT_RISK_THRESHOLD        = 70.0    # max acceptable risk score (0–100)
DEFAULT_EVIDENCE_TIMEOUT_SECS = 300.0   # 5 minutes
MAX_DECISION_AGE_SECS         = 86_400  # 24 hours
