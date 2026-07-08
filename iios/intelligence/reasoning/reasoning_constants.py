"""
iios/intelligence/reasoning/reasoning_constants.py
===================================================
Shared constants and enumerations for the Reasoning & Debate Engine.
"""
from __future__ import annotations

from enum import Enum, IntEnum


class ReasoningType(str, Enum):
    """Types of reasoning the engine can perform."""
    DEDUCTIVE      = "deductive"       # General → specific
    INDUCTIVE      = "inductive"       # Specific → general
    ABDUCTIVE      = "abductive"       # Best-explanation inference
    ANALOGICAL     = "analogical"      # Pattern / similarity matching
    CAUSAL         = "causal"          # Cause → effect chains
    COUNTERFACTUAL = "counterfactual"  # What-if analysis
    PROBABILISTIC  = "probabilistic"   # Bayesian / probabilistic
    DIALECTICAL    = "dialectical"     # Through debate / contradiction
    HEURISTIC      = "heuristic"       # Rule-based shortcut
    GENERIC        = "generic"         # Unspecified


class ReasoningStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"


class EvidenceType(str, Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE  = "qualitative"
    STATISTICAL  = "statistical"
    HISTORICAL   = "historical"
    EXPERT       = "expert"
    MARKET       = "market"
    FUNDAMENTAL  = "fundamental"
    TECHNICAL    = "technical"
    SENTIMENT    = "sentiment"
    MACRO        = "macro"
    GENERIC      = "generic"


class EvidenceStrength(IntEnum):
    """Numeric ordering: higher value = stronger evidence."""
    WEAK        = 1
    MODERATE    = 2
    STRONG      = 3
    VERY_STRONG = 4
    CONCLUSIVE  = 5


class EvidenceStatus(str, Enum):
    UNVALIDATED = "unvalidated"
    VALID       = "valid"
    INVALID     = "invalid"
    CONFLICTING = "conflicting"
    SUPERSEDED  = "superseded"


class EvidenceRelation(str, Enum):
    SUPPORTS     = "supports"
    CONTRADICTS  = "contradicts"
    CORROBORATES = "corroborates"
    REFINES      = "refines"
    SUPERSEDES   = "supersedes"


class DebateRole(str, Enum):
    PROPONENT         = "proponent"
    OPPONENT          = "opponent"
    MODERATOR         = "moderator"
    OBSERVER          = "observer"
    CONSENSUS_BUILDER = "consensus_builder"


class DebateStatus(str, Enum):
    PENDING           = "pending"
    ACTIVE            = "active"
    PAUSED            = "paused"
    CONSENSUS_REACHED = "consensus_reached"
    DEADLOCKED        = "deadlocked"
    COMPLETED         = "completed"
    FAILED            = "failed"


class ArgumentType(str, Enum):
    SUPPORTING       = "supporting"
    OPPOSING         = "opposing"
    NEUTRAL          = "neutral"
    CLARIFYING       = "clarifying"
    REBUTTAL         = "rebuttal"
    COUNTER_REBUTTAL = "counter_rebuttal"


class ConfidenceLevel(str, Enum):
    VERY_LOW  = "very_low"    # < 0.20
    LOW       = "low"         # 0.20–0.40
    MODERATE  = "moderate"    # 0.40–0.60
    HIGH      = "high"        # 0.60–0.80
    VERY_HIGH = "very_high"   # 0.80–0.95
    CERTAIN   = "certain"     # > 0.95


class ExplanationType(str, Enum):
    SUMMARY          = "summary"
    DETAILED         = "detailed"
    PROOF_CHAIN      = "proof_chain"
    TRACE            = "trace"
    HUMAN_READABLE   = "human_readable"
    MACHINE_READABLE = "machine_readable"


class TraceStepType(str, Enum):
    INPUT      = "input"
    EVIDENCE   = "evidence"
    INFERENCE  = "inference"
    ARGUMENT   = "argument"
    DEBATE     = "debate"
    CONSENSUS  = "consensus"
    CONFIDENCE = "confidence"
    OUTPUT     = "output"


# ── Version ────────────────────────────────────────────────────────────────────

REASONING_ENGINE_VERSION = "1.0.0"

# ── Hard limits ────────────────────────────────────────────────────────────────

MAX_DEBATE_ROUNDS        = 10
MAX_EVIDENCE_ITEMS       = 1_000
MAX_REASONING_DEPTH      = 20
MAX_REASONING_SESSIONS   = 500
MAX_ARGUMENTS_PER_ROUND  = 50
MAX_PROOF_CHAIN_STEPS    = 100
MAX_TRACE_STEPS          = 500

# ── Timeouts (seconds) ─────────────────────────────────────────────────────────

DEFAULT_SESSION_TIMEOUT_S   = 300.0
DEFAULT_DEBATE_TIMEOUT_S    = 120.0
DEFAULT_ROUND_TIMEOUT_S     =  30.0
DEFAULT_REASONING_TIMEOUT_S =  60.0

# ── Confidence thresholds ──────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD_VERY_LOW  = 0.0
CONFIDENCE_THRESHOLD_LOW       = 0.20
CONFIDENCE_THRESHOLD_MODERATE  = 0.40
CONFIDENCE_THRESHOLD_HIGH      = 0.60
CONFIDENCE_THRESHOLD_VERY_HIGH = 0.80
CONFIDENCE_THRESHOLD_CERTAIN   = 0.95

# ── Default weights for confidence model ──────────────────────────────────────

CONFIDENCE_WEIGHT_EVIDENCE    = 0.30
CONFIDENCE_WEIGHT_SOURCE      = 0.15
CONFIDENCE_WEIGHT_REASONING   = 0.25
CONFIDENCE_WEIGHT_CONSENSUS   = 0.20
CONFIDENCE_WEIGHT_HISTORICAL  = 0.10

# ── System identifiers ─────────────────────────────────────────────────────────

SYSTEM_REASONER_ID  = "iios:reasoner:system"
DEBATE_CHANNEL_NAME = "iios:debate:broadcast"
