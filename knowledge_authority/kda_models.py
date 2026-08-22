"""
knowledge_authority/kda_models.py
===================================
KDA-001 — Knowledge Decision Authority data models.

All models are pure dataclasses with no external dependencies and no broker calls.
no_lookahead = True is a hard invariant on every decision record.

Safety contract:
  broker_calls = 0, orders = 0, PAPER_TRADING unchanged
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Evidence states
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceState(str, Enum):
    INSUFFICIENT      = "INSUFFICIENT"
    DEVELOPING        = "DEVELOPING"
    USEFUL            = "USEFUL"
    VALIDATED         = "VALIDATED"
    DECISION_ELIGIBLE = "DECISION_ELIGIBLE"


# ─────────────────────────────────────────────────────────────────────────────
# Decision types
# ─────────────────────────────────────────────────────────────────────────────

class KDADecision(str, Enum):
    KNOWLEDGE_BUY  = "KNOWLEDGE_BUY"
    KNOWLEDGE_SELL = "KNOWLEDGE_SELL"
    KNOWLEDGE_HOLD = "KNOWLEDGE_HOLD"
    KNOWLEDGE_WAIT = "KNOWLEDGE_WAIT"
    KNOWLEDGE_EXIT = "KNOWLEDGE_EXIT"


# ─────────────────────────────────────────────────────────────────────────────
# Decision authority
# ─────────────────────────────────────────────────────────────────────────────

class DecisionAuthority(str, Enum):
    KNOWLEDGE        = "KNOWLEDGE"
    STRATEGY_CONTEXT = "STRATEGY_CONTEXT"
    RISK             = "RISK"
    NONE             = "NONE"


# ─────────────────────────────────────────────────────────────────────────────
# Angle verdict (per-angle evaluation)
# ─────────────────────────────────────────────────────────────────────────────

class AngleVerdict(str, Enum):
    SUPPORT      = "SUPPORT"
    NEUTRAL      = "NEUTRAL"
    CONTRADICT   = "CONTRADICT"
    INSUFFICIENT = "INSUFFICIENT"


# ─────────────────────────────────────────────────────────────────────────────
# KDA ↔ StrategyLab relationship
# ─────────────────────────────────────────────────────────────────────────────

class KDARelationship(str, Enum):
    KNOWLEDGE_AGREES           = "KNOWLEDGE_AGREES"
    KNOWLEDGE_DISAGREES        = "KNOWLEDGE_DISAGREES"
    KNOWLEDGE_OVERRULES_STRATEGY = "KNOWLEDGE_OVERRULES_STRATEGY"
    STRATEGY_OVERRULES_KNOWLEDGE = "STRATEGY_OVERRULES_KNOWLEDGE"
    KNOWLEDGE_INSUFFICIENT     = "KNOWLEDGE_INSUFFICIENT"
    KNOWLEDGE_CONFLICTED       = "KNOWLEDGE_CONFLICTED"


# ─────────────────────────────────────────────────────────────────────────────
# Exit states
# ─────────────────────────────────────────────────────────────────────────────

class ExitState(str, Enum):
    TARGET_REACHED         = "TARGET_REACHED"
    STOP_REACHED           = "STOP_REACHED"
    THESIS_INVALIDATED     = "THESIS_INVALIDATED"
    TIME_DECAY             = "TIME_DECAY"
    BEHAVIOUR_CHANGED      = "BEHAVIOUR_CHANGED"
    KNOWLEDGE_CONTRADICTION = "KNOWLEDGE_CONTRADICTION"
    RISK_OVERRIDE          = "RISK_OVERRIDE"


# ─────────────────────────────────────────────────────────────────────────────
# Decision outcome (for learning loop)
# ─────────────────────────────────────────────────────────────────────────────

class DecisionOutcome(str, Enum):
    CORRECT_KNOWLEDGE_DECISION = "CORRECT_KNOWLEDGE_DECISION"
    FALSE_POSITIVE             = "FALSE_POSITIVE"
    MISSED_OPPORTUNITY         = "MISSED_OPPORTUNITY"
    CORRECT_WAIT               = "CORRECT_WAIT"
    CORRECT_EXIT               = "CORRECT_EXIT"
    INCORRECT_EXIT             = "INCORRECT_EXIT"


# ─────────────────────────────────────────────────────────────────────────────
# Evidence hierarchy levels (most → least specific)
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceHierarchyLevel(str, Enum):
    SYMBOL_DIR_REGIME_CTX = "SYMBOL_DIR_REGIME_CTX"
    SYMBOL_DIR            = "SYMBOL_DIR"
    SECTOR_DIR_REGIME     = "SECTOR_DIR_REGIME"
    REGIME_DIR            = "REGIME_DIR"
    SECTOR_DIR            = "SECTOR_DIR"
    BROAD_DIR             = "BROAD_DIR"
    ATR_FALLBACK          = "ATR_FALLBACK"


# ─────────────────────────────────────────────────────────────────────────────
# Angle analysis record (per-angle SUPPORT/NEUTRAL/CONTRADICT/INSUFFICIENT)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AngleAnalysis:
    angle_name:   str
    verdict:      AngleVerdict
    confidence:   float        # 0–1
    sample_count: int
    summary:      str
    metrics:      Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "angle_name": self.angle_name,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
            "summary": self.summary,
            "metrics": self.metrics,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Information contribution (source-level attribution)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InformationContribution:
    """Records which source and angle changed the decision, and by how much."""
    source:       str
    angle:        str
    contribution: float  # signed; positive = pro-decision, negative = anti-decision
    direction:    str    # SUPPORT / CONTRADICT / NEUTRAL
    value:        float  # absolute contribution magnitude

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Counterfactual result (with / without a source)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CounterfactualResult:
    source_removed:    str
    decision_with:     str    # decision when source IS included
    decision_without:  str    # decision when source is removed
    authority_with:    float
    authority_without: float
    delta:             float  # authority_with - authority_without

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# StrategyLab context (informational only — not decision authority)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StrategyContext:
    status:            str            # PASS / REJECT / DISABLED / UNKNOWN
    strategy_name:     Optional[str]
    disagreement:      Optional[str]
    informational_only: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge authority component scores (decomposable)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KnowledgeAuthorityComponents:
    """
    Formula: authority = evidence_strength × relevance × stability
                        × oos_quality × source_independence × contradiction_factor

    Each component is [0, 1]. composite_authority = product of all six.
    """
    evidence_strength:     float
    relevance:             float
    stability:             float
    oos_quality:           float
    source_independence:   float
    contradiction_factor:  float
    composite_authority:   float

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Full KDA decision record (immutable output)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KDADecisionRecord:
    """
    Immutable, complete Knowledge Decision Authority output for one opportunity.

    Safety invariants:
      broker_calls == 0
      orders == 0
      no_lookahead == True
      mode == "SHADOW_DECISION"  (until explicit promotion)
    """
    decision_id:               str
    timestamp:                 str
    symbol:                    str
    direction:                 str   # BUY / SELL / SHORT

    authority:                 DecisionAuthority
    decision:                  KDADecision

    knowledge_score:           float   # 0–10 scanner confidence at observation
    knowledge_authority:       float   # 0–1 composite authority score

    evidence_state:            EvidenceState
    evidence_level:            EvidenceHierarchyLevel
    evidence_count:            int
    effective_sample_size:     float
    evidence_confidence:       float

    expected_move_p25:         Optional[float]
    expected_move_p50:         Optional[float]
    expected_move_p75:         Optional[float]

    target:                    Optional[float]
    stop_loss:                 Optional[float]

    expected_days_p25:         Optional[float]
    expected_days_p50:         Optional[float]
    expected_days_p75:         Optional[float]

    target_source:             str   # EMPIRICAL / ATR_FALLBACK / NONE
    stop_source:               str   # EMPIRICAL / ATR_FALLBACK / NONE
    horizon_source:            str   # EMPIRICAL / UNKNOWN

    supporting_angles:         List[str]
    contradicting_angles:      List[str]

    source_count:              int
    source_agreement:          float   # 0–1
    contradiction_status:      str

    oos_status:                str

    strategy_context:          Optional[StrategyContext]
    kda_strategy_relationship: str   # KDARelationship value

    risk_constraints:          Dict[str, Any]

    fallback_used:             bool

    authority_components:      KnowledgeAuthorityComponents
    angle_analyses:            Dict[str, AngleAnalysis]
    information_contributions: List[InformationContribution]
    counterfactual_results:    List[CounterfactualResult]

    exit_conditions:           List[str]   # ExitState values that would trigger

    mode:                      str = "SHADOW_DECISION"
    no_lookahead:              bool = True
    broker_calls:              int = 0
    orders:                    int = 0

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["authority"]      = self.authority.value
        d["decision"]       = self.decision.value
        d["evidence_state"] = self.evidence_state.value
        d["evidence_level"] = self.evidence_level.value
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Outcome feedback record (for learning loop)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KDAOutcomeFeedback:
    """
    Links a KDADecisionRecord to its market outcome.
    Populated by the LearningEngine at EOD / after sufficient time.
    """
    decision_id:       str
    symbol:            str
    direction:         str
    decision:          str
    authority:         str
    actual_return_1d:  Optional[float]
    actual_return_5d:  Optional[float]
    target_hit:        Optional[bool]
    stop_hit:          Optional[bool]
    outcome_class:     Optional[str]   # DecisionOutcome value
    recorded_at:       str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
