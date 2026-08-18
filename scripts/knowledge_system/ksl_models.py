"""
scripts/knowledge_system/ksl_models.py
=======================================
Data models for the Knowledge System Autonomous Research Loop (KSL-001).

All models are lightweight dataclasses + enums — no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class Classification(str, Enum):
    CORRECT_SELECT    = "CORRECT_SELECT"    # Selected by C2 Top-5
    RANKING_MISS      = "RANKING_MISS"      # Not selected; would have been a ≥2% mover
    CORRECT_REJECT    = "CORRECT_REJECT"    # Strategy-rejected; outcome was bad
    FALSE_REJECT      = "FALSE_REJECT"      # Strategy-rejected; outcome was good
    DISCOVERY_SUCCESS = "DISCOVERY_SUCCESS" # In V3 pool (all shadow candidates)
    DISCOVERY_MISS    = "DISCOVERY_MISS"    # Not in V3 pool (needs full-universe data)
    UNRESOLVED        = "UNRESOLVED"        # Outcome data not yet available


class MissReason(str, Enum):
    OUTRANKED_BY_STRONGER_OPENERS = "OUTRANKED_BY_STRONGER_OPENERS"
    ADVERSE_OPEN_GAP              = "ADVERSE_OPEN_GAP"
    LOW_C2_SCORE                  = "LOW_C2_SCORE"
    STRATEGY_REJECTION            = "STRATEGY_REJECTION"
    RISK_REJECTION                = "RISK_REJECTION"
    NO_DATA                       = "NO_DATA"
    NOT_APPLICABLE                = "NOT_APPLICABLE"


class PatternType(str, Enum):
    HIGH_RANKING_MISS_RATE       = "HIGH_RANKING_MISS_RATE"
    ADVERSE_GAP_DOMINATES        = "ADVERSE_GAP_DOMINATES"
    FALSE_REJECT_RATE            = "FALSE_REJECT_RATE"
    DIRECTION_ASYMMETRY          = "DIRECTION_ASYMMETRY"
    REGIME_UNDERPERFORMANCE      = "REGIME_UNDERPERFORMANCE"
    RANK_DECAY_CONFIRMED         = "RANK_DECAY_CONFIRMED"
    STRATEGY_CONTEXT_DISAGREEMENT = "STRATEGY_CONTEXT_DISAGREEMENT"
    OUTCOME_CONCENTRATION        = "OUTCOME_CONCENTRATION"


class ResearchArea(str, Enum):
    C2_RANKING  = "C2_RANKING"
    V3_DISCOVERY = "V3_DISCOVERY"
    STRATEGY    = "STRATEGY"
    DIRECTION   = "DIRECTION"
    REGIME      = "REGIME"
    POOL        = "POOL"
    EXECUTION   = "EXECUTION"
    OTHER       = "OTHER"


class ResearchQuestionStatus(str, Enum):
    GENERATED           = "GENERATED"
    QUEUED              = "QUEUED"
    RUNNING             = "RUNNING"
    COMPLETED           = "COMPLETED"
    VALIDATED           = "VALIDATED"
    REJECTED            = "REJECTED"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    BLOCKED_DATA        = "BLOCKED_DATA"
    SUPERSEDED          = "SUPERSEDED"


class FindingVerdict(str, Enum):
    VALIDATED            = "VALIDATED"
    PARTIALLY_VALIDATED  = "PARTIALLY_VALIDATED"
    NO_INCREMENTAL_VALUE = "NO_INCREMENTAL_VALUE"
    REJECTED             = "REJECTED"
    INSUFFICIENT_SAMPLE  = "INSUFFICIENT_SAMPLE"
    BLOCKED_BY_DATA      = "BLOCKED_BY_DATA"


class KSLEventType(str, Enum):
    EVIDENCE              = "EVIDENCE"
    PATTERN               = "PATTERN"
    RESEARCH_QUESTION     = "RESEARCH_QUESTION"
    RESEARCH_PROPOSAL     = "RESEARCH_PROPOSAL"
    FINDING               = "FINDING"
    KNOWLEDGE_UPDATE      = "KNOWLEDGE_UPDATE"
    SHADOW_CANDIDATE      = "SHADOW_CANDIDATE"
    DUPLICATE_SUPPRESSED  = "DUPLICATE_SUPPRESSED"


# ─────────────────────────────────────────────────────────────────────────────
# Evidence Record
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class EvidenceRecord:
    """One classified candidate from the shadow JSONL."""
    event_id:               str
    source_run_id:          str
    trade_date:             str
    symbol:                 str
    direction:              str
    v3_score:               Optional[float]
    c2_score:               Optional[float]
    c2_rank:                Optional[int]
    selected_final_5:       bool
    strategy_status:        Optional[str]
    strategy_rejected:      bool
    knowledge_strategy_disagreement: Optional[str]
    t1_ret_pct:             Optional[float]
    t3_ret_pct:             Optional[float]   # not in shadow JSONL; None
    t5_ret_pct:             Optional[float]   # not in shadow JSONL; None
    mfe_pct:                Optional[float]
    mae_pct:                Optional[float]
    ge1:                    Optional[bool]
    ge2:                    Optional[bool]
    ge3:                    Optional[bool]
    classification:         Classification
    miss_reason:            MissReason
    regime:                 Optional[str]
    processed_at:           str

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["classification"] = self.classification.value
        d["miss_reason"] = self.miss_reason.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceRecord":
        d = d.copy()
        d["classification"] = Classification(d["classification"])
        d["miss_reason"] = MissReason(d["miss_reason"])
        return cls(**d)


# ─────────────────────────────────────────────────────────────────────────────
# Pattern Record
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PatternRecord:
    """A detected pattern with statistical evidence."""
    pattern_id:   str
    pattern_type: PatternType
    area:         ResearchArea
    direction:    str           # "UP", "DOWN", or "BOTH"
    regime:       str           # "BULL", "BEAR", "RANGE", "ALL"
    description:  str
    sample_size:  int
    effect_size:  float         # e.g., miss_rate - baseline_rate
    baseline:     float         # comparison value
    observed:     float         # observed value
    strength:     float         # composite [0,1] — determines if question is warranted
    data:         Dict[str, Any] = field(default_factory=dict)
    created_at:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["pattern_type"] = self.pattern_type.value
        d["area"] = self.area.value
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Research Question
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ResearchQuestion:
    """An automatically generated, testable research question."""
    research_question_id: str
    created_at:           str
    source_pattern_ids:   List[str]
    question:             str
    problem_area:         ResearchArea
    direction:            str
    regime_scope:         str
    baseline:             str
    candidate_change:     str
    target_metric:        str
    minimum_sample:       int
    required_data:        List[str]
    known_data_gaps:      List[str]
    leakage_risk:         str
    research_priority:    float       # 0-100
    status:               ResearchQuestionStatus
    duplicate_of:         Optional[str] = None   # hypothesis_id or rq_id if duplicate
    notes:                str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["problem_area"] = self.problem_area.value
        d["status"] = self.status.value
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Research Proposal
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ResearchProposal:
    """Full research proposal for a high-priority question."""
    proposal_id:            str
    research_question_id:   str
    created_at:             str
    title:                  str
    # Experiment design
    baseline_description:   str
    candidate_description:  str
    dataset_path:           str
    dataset_rows:           int
    train_days:             int
    val_days:               int
    oos_days:               int
    oos_start:              str
    oos_end:                str
    metrics:                List[str]
    # Safety checks required
    leakage_test_required:  bool
    look_ahead_test:        bool
    sample_sufficiency_min: int
    production_isolation:   bool
    # Expected outcome
    expected_delta:         str
    risk_of_regression:     str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Finding
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class KnowledgeFinding:
    """Ingested research result — immutable once created."""
    finding_id:             str
    research_question_id:   str
    experiment_id:          str
    verdict:                FindingVerdict
    baseline_metrics:       Dict[str, float]
    candidate_metrics:      Dict[str, float]
    delta:                  Dict[str, float]
    oos_result:             str
    leakage_result:         str
    sample_size:            int
    confidence:             float
    limitations:            str
    recommendation:         str
    created_at:             str

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["verdict"] = self.verdict.value
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Shadow Candidate (promotion entry)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class KSLShadowCandidate:
    """A validated research result eligible for shadow-period evaluation."""
    candidate_id:            str
    research_question_id:    str
    finding_id:              str
    created_at:              str
    baseline_version:        str
    candidate_version:       str
    reason:                  str
    evidence:                str
    oos_dir_acc:             float
    oos_ge2_rate:            float
    expected_improvement:    str
    risk:                    str
    required_observation_days: int
    promotion_requirements:  str
    status:                  str = "SHADOW_ELIGIBLE"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


# ─────────────────────────────────────────────────────────────────────────────
# System State
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class KSLState:
    """Persistent processing state for restart safety."""
    last_processed_byte_offset: int = 0
    last_processed_at:          str = ""
    processed_run_ids:          List[str] = field(default_factory=list)
    total_records_ingested:     int = 0
    total_patterns_detected:    int = 0
    total_questions_generated:  int = 0
    last_loop_run_at:           str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KSLState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
