"""
iios/decisions/decision_constants.py
=====================================
Shared enumerations and constants for the Decision Engine Core.
Error-code prefix: DE-
"""
from __future__ import annotations

from enum import Enum


# ── Decision type ─────────────────────────────────────────────────────────────

class DecisionType(str, Enum):
    """The kind of action a decision represents."""
    ACCEPT   = "accept"
    REJECT   = "reject"
    DEFER    = "defer"
    ESCALATE = "escalate"
    HOLD     = "hold"
    REVISE   = "revise"
    EXECUTE  = "execute"
    CANCEL   = "cancel"
    GENERIC  = "generic"


# ── Decision status ───────────────────────────────────────────────────────────

class DecisionStatus(str, Enum):
    """Lifecycle state of a Decision."""
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"
    EXPIRED     = "expired"
    DEFERRED    = "deferred"


# ── Priority ──────────────────────────────────────────────────────────────────

class DecisionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ── Candidate status ──────────────────────────────────────────────────────────

class CandidateStatus(str, Enum):
    PENDING   = "pending"
    EVALUATED = "evaluated"
    SELECTED  = "selected"
    REJECTED  = "rejected"


# ── Workflow stages ───────────────────────────────────────────────────────────

class WorkflowStage(str, Enum):
    RECEIVE      = "receive"
    VALIDATE     = "validate"
    GENERATE     = "generate"
    EVALUATE     = "evaluate"
    POLICY_CHECK = "policy_check"
    SCORE        = "score"
    RANK         = "rank"
    SELECT       = "select"
    EXPLAIN      = "explain"
    PUBLISH      = "publish"


# ── Policy outcome ────────────────────────────────────────────────────────────

class PolicyOutcome(str, Enum):
    PASS     = "pass"
    FAIL     = "fail"
    OVERRIDE = "override"
    ABSTAIN  = "abstain"


# ── Evaluation dimension ──────────────────────────────────────────────────────

class DecisionDimension(str, Enum):
    CONFIDENCE    = "confidence"
    RISK          = "risk"
    COMPLETENESS  = "completeness"
    CONSISTENCY   = "consistency"
    TIMELINESS    = "timeliness"
    EVIDENCE      = "evidence"


# ── Numeric thresholds ────────────────────────────────────────────────────────

DECISION_ENGINE_VERSION:    str   = "1.0.0"
MAX_DECISION_RECORDS:       int   = 100_000
MAX_CANDIDATES_PER_REQUEST: int   = 50
DEFAULT_DECISION_TTL_S:     float = 3_600.0
MIN_CONFIDENCE_THRESHOLD:   float = 0.50
MIN_CANDIDATE_SCORE:        float = 0.0    # generic — no investment constraints
DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    DecisionDimension.CONFIDENCE.value:   0.30,
    DecisionDimension.RISK.value:         0.25,
    DecisionDimension.EVIDENCE.value:     0.20,
    DecisionDimension.COMPLETENESS.value: 0.10,
    DecisionDimension.CONSISTENCY.value:  0.10,
    DecisionDimension.TIMELINESS.value:   0.05,
}

# ── System identifiers ────────────────────────────────────────────────────────

DECISION_ENGINE_SYSTEM_ID: str = "iios:decision:engine"
DECISION_AUTO_SELECTOR_ID: str = "iios:decision:auto_selector"
