"""
knowledge_authority/kda_outcome_models.py
==========================================
KDA-002 — data models for outcome evaluation, comparative analysis,
source performance, and authority validation.

Safety contract:
  broker_calls = 0, orders = 0, no_lookahead = True, PAPER_TRADING unchanged
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# KDA-002 enums
# ─────────────────────────────────────────────────────────────────────────────

class OutcomeStatus(str, Enum):
    OUTCOME_PENDING  = "OUTCOME_PENDING"
    OUTCOME_NO_DATA  = "OUTCOME_NO_DATA"
    OUTCOME_INVALID  = "OUTCOME_INVALID"
    OUTCOME_COMPLETE = "OUTCOME_COMPLETE"


class OutcomeClass(str, Enum):
    """Per-spec section 5: granular decision classification."""
    CORRECT_BUY        = "CORRECT_BUY"
    INCORRECT_BUY      = "INCORRECT_BUY"
    CORRECT_SELL       = "CORRECT_SELL"
    INCORRECT_SELL     = "INCORRECT_SELL"
    CORRECT_WAIT       = "CORRECT_WAIT"
    INCORRECT_WAIT     = "INCORRECT_WAIT"
    CORRECT_HOLD       = "CORRECT_HOLD"
    INCORRECT_HOLD     = "INCORRECT_HOLD"
    CORRECT_EXIT       = "CORRECT_EXIT"
    INCORRECT_EXIT     = "INCORRECT_EXIT"
    MISSED_OPPORTUNITY = "MISSED_OPPORTUNITY"
    UNRESOLVED         = "UNRESOLVED"


class ComparisonType(str, Enum):
    """KDA vs StrategyLab alignment classification."""
    KDA_ONLY               = "KDA_ONLY"
    STRATEGY_ONLY          = "STRATEGY_ONLY"
    BOTH_AGREE             = "BOTH_AGREE"
    BOTH_REJECT            = "BOTH_REJECT"
    KDA_OVERRULES_STRATEGY = "KDA_OVERRULES_STRATEGY"
    STRATEGY_OVERRULES_KDA = "STRATEGY_OVERRULES_KDA"


class OverruleResult(str, Enum):
    KNOWLEDGE_SUCCESSFUL_OVERRULE = "KNOWLEDGE_SUCCESSFUL_OVERRULE"
    KNOWLEDGE_FALSE_OVERRULE      = "KNOWLEDGE_FALSE_OVERRULE"
    FALSE_KNOWLEDGE_REJECTION     = "FALSE_KNOWLEDGE_REJECTION"
    FALSE_KNOWLEDGE_SELECTION     = "FALSE_KNOWLEDGE_SELECTION"


class AuthorityStatus(str, Enum):
    NOT_VALIDATED    = "NOT_VALIDATED"
    PROMISING        = "PROMISING"
    USEFUL           = "USEFUL"
    VALIDATED        = "VALIDATED"
    STRONG_VALIDATED = "STRONG_VALIDATED"


class TargetComparison(str, Enum):
    TOO_AGGRESSIVE    = "TOO_AGGRESSIVE"
    REASONABLE        = "REASONABLE"
    TOO_CONSERVATIVE  = "TOO_CONSERVATIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MoveSpeed(str, Enum):
    FAST_MOVE   = "FAST_MOVE"
    NORMAL_MOVE = "NORMAL_MOVE"
    SLOW_MOVE   = "SLOW_MOVE"
    UNRESOLVED  = "UNRESOLVED"


# ─────────────────────────────────────────────────────────────────────────────
# Simple price bar (OHLCV) for outcome evaluation input
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OHLCVBar:
    """Single daily OHLCV bar. date is ISO 'YYYY-MM-DD'."""
    date:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Outcome record — full evaluation of one completed KDA decision
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KDAOutcomeRecord:
    """
    Complete outcome evaluation for one KDA decision.
    Created by KDAOutcomeEngine after sufficient bars are available.
    """
    outcome_id:            str
    decision_id:           str
    observation_id:        Optional[str]
    trading_date:          str
    symbol:                str
    direction:             str
    decision:              str       # KDADecision value
    authority:             str       # DecisionAuthority value
    knowledge_authority:   float
    entry_price:           float

    target:                Optional[float]
    stop_loss:             Optional[float]
    expected_move_p25:     Optional[float]
    expected_move_p50:     Optional[float]
    expected_move_p75:     Optional[float]
    expected_days_p25:     Optional[float]
    expected_days_p50:     Optional[float]
    expected_days_p75:     Optional[float]
    target_source:         str
    stop_source:           str
    horizon_source:        str

    # Returns (%)
    return_t1:             Optional[float]
    return_t3:             Optional[float]
    return_t5:             Optional[float]
    return_t10:            Optional[float]
    return_t20:            Optional[float]

    # Path-dependent metrics (%)
    mfe:                   Optional[float]   # Max Favorable Excursion
    mae:                   Optional[float]   # Max Adverse Excursion

    # Events
    target_hit:            Optional[bool]
    stop_hit:              Optional[bool]
    time_to_target:        Optional[int]     # bar index (1-based)
    time_to_stop:          Optional[int]
    first_event:           Optional[str]     # "TARGET_HIT" / "STOP_HIT" / None
    event_day:             Optional[int]

    # Horizon
    horizon_error:         Optional[float]   # |actual - p50| in days
    horizon_accuracy:      Optional[float]   # 0–1
    move_speed:            Optional[str]     # MoveSpeed value

    # Target comparison
    target_accuracy:       Optional[float]   # actual_move / knowledge_target
    target_comparison:     Optional[str]     # TargetComparison value

    # Correctness
    direction_correct:     Optional[bool]
    decision_correct:      Optional[bool]

    # Classification
    outcome_class:         Optional[str]     # OutcomeClass value

    # Evidence carried through for tier/authority analysis
    evidence_state:        str
    evidence_level:        str

    # Status
    status:                str              # OutcomeStatus value
    bars_available:        int
    evaluation_horizon:    int             # max bars we tried to evaluate

    # Strategy context for comparison
    strategy_status:       Optional[str]   # PASS / REJECT / UNKNOWN
    scanner_confidence:    Optional[float]

    # Safety
    no_lookahead:          bool = True
    broker_calls:          int  = 0
    orders:                int  = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Comparison record — KDA vs StrategyLab vs Scanner-only
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KDAComparisonRecord:
    comparison_id:      str
    decision_id:        str
    symbol:             str
    trading_date:       str

    kda_decision:       str            # KDADecision value
    strategy_decision:  Optional[str]  # PASS / REJECT
    scanner_signal:     Optional[str]  # BUY / SELL / HOLD (scanner-only baseline)

    comparison_type:    str            # ComparisonType value
    overrule_result:    Optional[str]  # OverruleResult value (when KDA overrules)

    # Outcome reference
    outcome_class:      Optional[str]
    return_t5:          Optional[float]
    direction_correct:  Optional[bool]
    target_hit:         Optional[bool]
    stop_hit:           Optional[bool]

    # Per-path correctness
    kda_correct:        Optional[bool]
    strategy_correct:   Optional[bool]
    scanner_correct:    Optional[bool]

    no_lookahead:       bool = True
    broker_calls:       int  = 0
    orders:             int  = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Source-level performance (from angle contributions + outcomes)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SourcePerformanceRecord:
    source:                  str
    sample_count:            int
    support_count:           int
    contradiction_count:     int
    decision_change_count:   int
    correct_change_count:    int
    incorrect_change_count:  int
    incremental_value:       float   # correct_changes / decision_changes (0–1) or 0
    oos_value:               float   # proportion of OOS-tested decisions using this source

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Per-authority-bucket statistics
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuthorityBucketResult:
    bucket:             str            # e.g. "0.00-0.20"
    bucket_min:         float
    bucket_max:         float
    n:                  int
    direction_accuracy: Optional[float]
    target_hit_rate:    Optional[float]
    stop_hit_rate:      Optional[float]
    avg_mfe:            Optional[float]
    avg_mae:            Optional[float]
    median_return:      Optional[float]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Per-evidence-tier statistics
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvidenceTierResult:
    tier:               str            # INSUFFICIENT / DEVELOPING / USEFUL / VALIDATED / DECISION_ELIGIBLE
    n:                  int
    direction_accuracy: Optional[float]
    target_hit_rate:    Optional[float]
    stop_hit_rate:      Optional[float]
    median_return:      Optional[float]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Authority validation report
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuthorityValidationReport:
    """
    Top-level KDA authority validation. Diagnostic only — does NOT enable
    live execution. authority_status is informational.
    """
    generated_at:        str
    authority_status:    str            # AuthorityStatus value
    why_not_promoted:    List[str]

    total_decisions:     int
    complete_outcomes:   int
    pending_outcomes:    int
    no_data_outcomes:    int

    direction_accuracy:  Optional[float]
    target_hit_rate:     Optional[float]
    stop_hit_rate:       Optional[float]
    avg_return_t5:       Optional[float]
    median_return_t5:    Optional[float]
    avg_mfe:             Optional[float]
    avg_mae:             Optional[float]

    authority_buckets:   List[AuthorityBucketResult]
    evidence_tiers:      List[EvidenceTierResult]

    calibration:         Dict[str, Any]  # confidence bucket → actual success rate

    horizon_validation:  Dict[str, Any]  # p25/p50/p75 accuracy metrics
    target_validation:   Dict[str, Any]  # TOO_AGGRESSIVE / REASONABLE / TOO_CONSERVATIVE
    source_performance:  List[Dict[str, Any]]

    # Safety invariants
    no_lookahead:        bool = True
    broker_calls:        int  = 0
    orders:              int  = 0
    modifications:       int  = 0
    cancellations:       int  = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
