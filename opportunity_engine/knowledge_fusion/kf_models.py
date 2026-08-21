"""
opportunity_engine/knowledge_fusion/kf_models.py
==================================================
KLP-004 — Knowledge Fusion Layer data models.

All models are pure dataclasses with no external dependencies and no broker calls.
no_lookahead = True is a hard invariant on every record.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Promotion status constants (Knowledge Object lifecycle)
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATE         = "CANDIDATE"          # derived from data, not yet validated
OBSERVED          = "OBSERVED"           # consistent pattern in recent data
VALIDATED         = "VALIDATED"          # confirmed in out-of-sample test
DECISION_ELIGIBLE = "DECISION_ELIGIBLE"  # ready for consideration (NOT YET APPLIED)
RETIRED           = "RETIRED"            # superseded or invalidated

# ─────────────────────────────────────────────────────────────────────────────
# Usage status constants (source/feature usage)
# ─────────────────────────────────────────────────────────────────────────────

USED_IN_DECISION  = "USED_IN_DECISION"
USED_AS_CONTEXT   = "USED_AS_CONTEXT"
OBSERVED_ONLY     = "OBSERVED_ONLY"
UNUSED            = "UNUSED"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

# ─────────────────────────────────────────────────────────────────────────────
# Contradiction constants
# ─────────────────────────────────────────────────────────────────────────────

CONTRADICTION_NONE       = "NONE"
CONTRADICTION_MINOR      = "MINOR"
CONTRADICTION_MAJOR      = "MAJOR"
CONTRADICTION_UNRESOLVED = "UNRESOLVED"

# ─────────────────────────────────────────────────────────────────────────────
# Out-of-sample constants
# ─────────────────────────────────────────────────────────────────────────────

OOS_NOT_TESTED = "NOT_TESTED"
OOS_TESTED     = "TESTED"
OOS_PASSED     = "PASSED"
OOS_FAILED     = "FAILED"

# ─────────────────────────────────────────────────────────────────────────────
# Selection analysis classification constants
# ─────────────────────────────────────────────────────────────────────────────

TRUE_POSITIVE  = "TRUE_POSITIVE"   # selected + moved favourably
FALSE_POSITIVE = "FALSE_POSITIVE"  # selected + moved adversely
TRUE_NEGATIVE  = "TRUE_NEGATIVE"   # rejected + moved adversely (correct rejection)
FALSE_NEGATIVE = "FALSE_NEGATIVE"  # rejected + moved favourably (missed opportunity)
OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Source inventory item
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SourceInventoryItem:
    """Describes one information source and its current state."""
    source:                      str   # unique source identifier
    field:                       str   # primary field / description
    availability:                str   # AVAILABLE | PARTIAL | ABSENT
    historical_depth:            str   # e.g. "2026-08-20 to 2026-08-21"
    record_count:                int
    update_frequency:            str   # REALTIME | DAILY | WEEKLY | STATIC
    is_outcome_linked:           bool  # does source contain trade outcomes?
    currently_used_in_decisions: bool  # is this source used in live decisions?
    usage_status:                str   # USED_IN_DECISION | USED_AS_CONTEXT | etc.

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Normalized fusion record (joins all available sources per observation)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KnowledgeFusionRecord:
    """
    Normalized record joining all available sources for one signal or observation.

    Fields that are unavailable for a given record are None.
    missing_fields lists every field that could not be populated.
    no_lookahead = True always: only information available at observation_time.
    """
    fusion_id:          str
    trading_date:       str     # "YYYY-MM-DD"
    symbol:             str
    direction:          str     # BUY / SELL / SHORT
    sector:             str

    # ── Scanner angle ─────────────────────────────────────────────────────────
    scanner_confidence:  Optional[float] = None  # 0–10
    candidate_score:     Optional[float] = None  # 0–1
    knowledge_score:     Optional[float] = None  # 0–1 (V1)
    atr_pct:             Optional[float] = None  # ATR as % of price
    knowledge_rr:        Optional[float] = None  # RR ratio

    # ── Market angle ─────────────────────────────────────────────────────────
    regime:              Optional[str]   = None  # BULL / BEAR / RANGE / VOLATILE
    vix:                 Optional[float] = None
    pcr:                 Optional[float] = None
    breadth:             Optional[float] = None  # 0–1

    # ── Regime probability angle ──────────────────────────────────────────────
    trend_prob:          Optional[float] = None
    bear_prob:           Optional[float] = None
    range_prob:          Optional[float] = None
    volatile_prob:       Optional[float] = None
    regime_confidence:   Optional[float] = None  # max_prob − runner_up

    # ── Multi-agent debate angle ──────────────────────────────────────────────
    technical_score:     Optional[float] = None  # 0–10
    risk_score:          Optional[float] = None
    macro_score:         Optional[float] = None
    sentiment_score:     Optional[float] = None
    regime_agent_score:  Optional[float] = None
    final_decision:      Optional[str]   = None  # APPROVED / REJECTED
    decision_confidence: Optional[float] = None  # weighted average 0–10
    rejection_reason:    Optional[str]   = None

    # ── Outcome angle ─────────────────────────────────────────────────────────
    outcome_available:   bool            = False
    move_1d_pct:         Optional[float] = None
    move_3d_pct:         Optional[float] = None
    move_5d_pct:         Optional[float] = None
    max_favorable_move:  Optional[float] = None
    max_adverse_move:    Optional[float] = None
    target_hit:          Optional[bool]  = None
    stop_hit:            Optional[bool]  = None
    rejection_outcome:   Optional[str]   = None  # CORRECT_REJECTION | FALSE_REJECTION

    # ── Provenance ────────────────────────────────────────────────────────────
    missing_fields:      List[str]       = field(default_factory=list)
    source_ids:          List[str]       = field(default_factory=list)
    no_lookahead:        bool            = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_long(self) -> bool:
        return self.direction.upper() in ("BUY", "LONG")

    @property
    def directional_move_5d(self) -> Optional[float]:
        """T+5 move signed for direction: positive = favourable."""
        if self.move_5d_pct is None:
            return None
        return self.move_5d_pct if self.is_long else -self.move_5d_pct


# ─────────────────────────────────────────────────────────────────────────────
# Angle result (one analytical view)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AngleResult:
    """Result of one analytical angle for a given record or query."""
    angle_name:     str             # e.g. "STOCK", "MARKET", "SECTOR"
    sample_count:   int
    metrics:        Dict[str, Any]
    evidence_level: int             # 1 (best) → 7 (fallback)
    confidence:     float           # 0–1
    summary:        str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Multi-angle view (all 10 angles for one record)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MultiAngleView:
    """Complete multi-angle analysis for one fusion record."""
    fusion_id:              str
    symbol:                 str
    direction:              str
    trading_date:           str
    angles:                 Dict[str, AngleResult]  # angle_name → AngleResult
    overall_signal:         str     # AGREE | DISAGREE | MIXED | INSUFFICIENT
    contradiction_detected: bool
    no_lookahead:           bool = True

    def get_angle(self, name: str) -> Optional[AngleResult]:
        return self.angles.get(name)

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Relationship candidate (discovered feature combination)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RelationshipCandidate:
    """
    A discovered feature combination and its empirical outcome statistics.

    Sample counts must come from observed data only.
    Do NOT promote to VALIDATED without out-of-sample confirmation.
    """
    rel_id:               str
    features:             List[str]          # feature names in combination
    conditions:           Dict[str, Any]     # specific values or bands
    sample_count:         int
    ess:                  float              # effective sample size
    positive_rate:        Optional[float]    # P(directional move > 0)
    target_hit_rate:      Optional[float]
    stop_hit_rate:        Optional[float]
    median_move:          Optional[float]    # median move_5d_pct (directional)
    p25_move:             Optional[float]
    p75_move:             Optional[float]
    median_time_to_move:  Optional[float]    # trading days
    stability:            str               # stable | developing | unstable | insufficient_data
    recency_weight:       float             # ESS-weighted recency 0–1
    decision_usefulness:  float             # 0–1 diagnostic score
    out_of_sample_status: str
    promotion_status:     str              = CANDIDATE
    created_at:           str              = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Contradiction record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ContradictionRecord:
    """Detected contradiction between two or more information sources."""
    contradiction_id:     str
    fusion_id:            str             # associated fusion record
    sources:              List[str]       # e.g. ["SCANNER", "HISTORICAL_BEHAVIOUR"]
    contradiction_type:   str             # DIRECTION | STRENGTH | REGIME | MAGNITUDE
    details:              Dict[str, Any]  # source-specific values
    strength:             float           # 0–1
    historical_resolution: Optional[str] # which source was more often correct
    outcome:              Optional[str]   # actual outcome where available

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Redundancy record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RedundancyRecord:
    """Detected redundant / near-duplicate information across sources."""
    redundancy_id:  str
    sources:        List[str]
    field_names:    List[str]
    correlation:    Optional[float]  # Pearson if computable
    recommendation: str              # DEDUPLICATE | USE_PRIMARY | AVERAGE

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Selection analysis record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SelectionAnalysisRecord:
    """
    Analysis of a selection decision against its outcome.

    Classification:
      TRUE_POSITIVE  — selected AND moved favourably
      FALSE_POSITIVE — selected BUT moved adversely
      TRUE_NEGATIVE  — rejected AND moved adversely (correct rejection)
      FALSE_NEGATIVE — rejected BUT moved favourably (missed opportunity)
      OUTCOME_UNKNOWN — outcome not yet available
    """
    analysis_id:       str
    trading_date:      str
    symbol:            str
    direction:         str
    selected:          bool
    outcome_available: bool
    move_5d_pct:       Optional[float]
    directional_move:  Optional[float]  # signed for direction
    classification:    str
    rejection_reason:  Optional[str]
    no_lookahead:      bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge object
# ─────────────────────────────────────────────────────────────────────────────

_PROMOTION_ORDER = [CANDIDATE, OBSERVED, VALIDATED, DECISION_ELIGIBLE]


@dataclass
class KnowledgeObject:
    """
    A structured knowledge unit with formal promotion lifecycle.

    Never skip directly to DECISION_ELIGIBLE from CANDIDATE.
    Each transition requires meeting specific evidence thresholds.

    Promotion thresholds:
      CANDIDATE → OBSERVED:         sample >= 10, confidence >= 0.30
      OBSERVED → VALIDATED:         sample >= 20, stability="stable", confidence >= 0.50
      VALIDATED → DECISION_ELIGIBLE: OOS_PASSED, contradiction in (NONE, MINOR)
    """
    knowledge_id:               str
    knowledge_type:             str     # PATTERN | RELATIONSHIP | BEHAVIOUR | CONTEXT
    statement:                  str
    scope:                      str     # SYMBOL | SECTOR | REGIME | BROAD
    conditions:                 Dict[str, Any]
    supporting_sources:         List[str]
    supporting_observation_ids: List[str]
    sample_count:               int
    ess:                        float
    evidence_level:             int     # 1–7
    stability:                  str     # stable | developing | unstable | insufficient_data
    recency:                    float   # 0–1
    confidence:                 float   # 0–1
    contradiction_status:       str
    out_of_sample_status:       str
    decision_usefulness:        float   # 0–1 diagnostic
    created_at:                 str
    updated_at:                 str
    promotion_status:           str = CANDIDATE

    def can_promote(self) -> bool:
        """Return True if this object meets criteria for the next promotion level."""
        if self.promotion_status == CANDIDATE:
            return self.sample_count >= 10 and self.confidence >= 0.30
        if self.promotion_status == OBSERVED:
            return (self.sample_count >= 20
                    and self.stability == "stable"
                    and self.confidence >= 0.50)
        if self.promotion_status == VALIDATED:
            return (self.out_of_sample_status == OOS_PASSED
                    and self.contradiction_status in (CONTRADICTION_NONE, CONTRADICTION_MINOR))
        return False  # DECISION_ELIGIBLE cannot self-promote

    def promote(self) -> bool:
        """Advance promotion_status by one level. Returns True if promoted."""
        if not self.can_promote():
            return False
        idx = _PROMOTION_ORDER.index(self.promotion_status)
        if idx < len(_PROMOTION_ORDER) - 1:
            self.promotion_status = _PROMOTION_ORDER[idx + 1]
            self.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def retire(self) -> None:
        self.promotion_status = RETIRED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge value score (diagnostic, not for execution)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KnowledgeValueScore:
    """
    Diagnostic score for a discovered relationship or knowledge object.

    Components:
      evidence_strength (0–1):   based on sample count and ESS
      stability (0–1):           consistent behaviour over time
      recency (0–1):             weighted toward recent observations
      sample_quality (0–1):      proportion of completed outcomes
      cross_validation (0–1):    agreement across multiple sources
      out_of_sample (0–1):       OOS performance (0 if not tested)
      decision_relevance (0–1):  does this affect the decision we care about?
      incremental_value (0–1):   adds information beyond existing sources?

    All components documented.
    Thresholds are NOT hard-coded as gates — they are reference points.
    """
    knowledge_id:         str
    evidence_strength:    float
    stability_score:      float
    recency_score:        float
    sample_quality:       float
    cross_validation:     float
    out_of_sample:        float
    decision_relevance:   float
    incremental_value:    float
    composite_score:      float   # weighted composite

    # Weights (documented, not hidden)
    W_EVIDENCE:    float = 0.20
    W_STABILITY:   float = 0.20
    W_RECENCY:     float = 0.15
    W_QUALITY:     float = 0.10
    W_CROSS_VAL:   float = 0.10
    W_OOS:         float = 0.10
    W_RELEVANCE:   float = 0.10
    W_INCREMENTAL: float = 0.05

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
