"""
opportunity_engine/hbe_models.py
==================================
Data models for the Historical Behaviour Engine (KLP-003).

All models are pure dataclasses — no external dependencies, no broker calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Outcome status constants (mirrors klp_outcome_engine)
# ─────────────────────────────────────────────────────────────────────────────

TARGET_HIT        = "TARGET_HIT"
STOP_HIT          = "STOP_HIT"
OUTCOME_AMBIGUOUS = "OUTCOME_AMBIGUOUS"
OUTCOME_EXPIRED   = "OUTCOME_EXPIRED"
OUTCOME_PENDING   = "OUTCOME_PENDING"
OUTCOME_NO_DATA   = "OUTCOME_NO_DATA"

COMPLETED_OUTCOMES = {TARGET_HIT, STOP_HIT, OUTCOME_AMBIGUOUS, OUTCOME_EXPIRED}

# ─────────────────────────────────────────────────────────────────────────────
# Evidence tiers
# ─────────────────────────────────────────────────────────────────────────────

TIER_THRESHOLDS = [0, 10, 20, 50, 100, 250, 500]
TIER_LABELS = {
    0: "TIER_0_NONE",
    1: "TIER_1_WEAK",
    2: "TIER_2_DEVELOPING",
    3: "TIER_3_USEFUL",
    4: "TIER_4_STRONG_DEVELOPING",
    5: "TIER_5_STRONG",
    6: "TIER_6_HIGH_VOLUME",
}


def evidence_tier(n: int) -> int:
    """Map raw observation count to evidence tier (0–6)."""
    for tier, threshold in enumerate(TIER_THRESHOLDS):
        if n < threshold:
            return tier - 1 if tier > 0 else 0
    return 6


# ─────────────────────────────────────────────────────────────────────────────
# Parsed outcome record (joined observation + outcome)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OutcomeRecord:
    """
    A single completed KLP observation+outcome pair, fully parsed.

    Created from KNOWLEDGE_OBSERVATION + its matching OUTCOME_UPDATE.
    Only COMPLETED outcomes are loaded (TARGET_HIT, STOP_HIT, OUTCOME_EXPIRED,
    OUTCOME_AMBIGUOUS). PENDING and NO_DATA records are excluded.

    no_lookahead is always True — entry = reference_entry frozen at scan time.
    """
    obs_id:          str
    trading_date:    str        # "YYYY-MM-DD"
    symbol:          str
    direction:       str        # "BUY" / "SELL" / "SHORT"
    regime:          str        # "BULL" / "BEAR" / "RANGE" / "VOLATILE" / ""
    sector:          str        # derived from symbol lookup
    reference_entry: float
    knowledge_target: float
    knowledge_stop:   float
    atr:             float
    atr_pct:         float      # atr / entry * 100
    scanner_confidence: float   # 0–10
    candidate_score: float      # 0–1 composite
    knowledge_score: float      # KNOWLEDGE_RESEARCH_SCORE_v1 0–1
    knowledge_rr:    float      # reward / risk
    # outcomes
    first_event:      str       # TARGET_HIT / STOP_HIT / EXPIRED / AMBIGUOUS
    first_event_day:  Optional[str]
    target_hit:       bool
    stop_hit:         bool
    t1_ret_pct:       Optional[float]
    t3_ret_pct:       Optional[float]
    t5_ret_pct:       Optional[float]
    mfe_pct:          Optional[float]   # max favourable excursion % (sign: + = good)
    mae_pct:          Optional[float]   # max adverse excursion % (sign: - = bad for long)
    days_to_event:    Optional[int]     # trading days from trading_date to first_event_day
    no_lookahead:     bool = True
    source_type:      str  = "LIVE"        # LIVE | PAPER | HISTORICAL
    validation_partition: str = ""          # TRAIN | VALIDATION | OOS | RECENT_OOS | ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # ── Convenience ─────────────────────────────────────────────────────────

    @property
    def is_long(self) -> bool:
        return self.direction.upper() in ("BUY", "LONG")

    @property
    def favourable_ret(self) -> Optional[float]:
        """MFE adjusted for direction (positive = good)."""
        if self.mfe_pct is None:
            return None
        return self.mfe_pct if self.is_long else -self.mfe_pct

    @property
    def adverse_ret(self) -> Optional[float]:
        """MAE adjusted for direction (positive magnitude = bad)."""
        if self.mae_pct is None:
            return None
        return -self.mae_pct if self.is_long else self.mae_pct

    @property
    def directional_t1(self) -> Optional[float]:
        """T+1 return signed for direction (positive = favourable)."""
        if self.t1_ret_pct is None:
            return None
        return self.t1_ret_pct if self.is_long else -self.t1_ret_pct

    @property
    def directional_t3(self) -> Optional[float]:
        if self.t3_ret_pct is None:
            return None
        return self.t3_ret_pct if self.is_long else -self.t3_ret_pct

    @property
    def directional_t5(self) -> Optional[float]:
        if self.t5_ret_pct is None:
            return None
        return self.t5_ret_pct if self.is_long else -self.t5_ret_pct


# ─────────────────────────────────────────────────────────────────────────────
# Behaviour metrics (computed from a bundle of OutcomeRecords)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BehaviourMetrics:
    """
    Empirical behaviour statistics computed from a filtered set of OutcomeRecords.
    All probabilities are [0, 1].  None = insufficient data for that metric.
    """
    # ── Evidence provenance ─────────────────────────────────────────────────
    observation_count:    int
    relevant_sample_size: int           # count after context filter
    effective_sample_size: float        # recency-weighted count
    oldest_observation:   Optional[str] # "YYYY-MM-DD"
    newest_observation:   Optional[str] # "YYYY-MM-DD"
    evidence_tier:        int           # 0–6
    evidence_tier_label:  str
    evidence_level:       int           # 1–7 (hierarchical fallback level used)
    evidence_source:      str           # "SYMBOL_DIRECTION_REGIME", "SECTOR_REGIME", etc.
    fallback_level:       int           # deepest fallback level tried
    confidence:           float         # 0–1 composite confidence

    # ── Probability estimates ────────────────────────────────────────────────
    positive_move_probability:  Optional[float]  # P(directional_t5 > 0)
    target_hit_probability:     Optional[float]  # P(TARGET_HIT as first event)
    stop_first_probability:     Optional[float]  # P(STOP_HIT as first event)
    expired_probability:        Optional[float]  # P(OUTCOME_EXPIRED)

    # ── Favourable move distribution (MFE, signed for direction) ─────────────
    favourable_move_p25: Optional[float]
    favourable_move_p50: Optional[float]
    favourable_move_p75: Optional[float]

    # ── Adverse move distribution (MAE magnitude) ────────────────────────────
    adverse_move_p25: Optional[float]
    adverse_move_p50: Optional[float]
    adverse_move_p75: Optional[float]

    # ── Time to first event (trading days) ───────────────────────────────────
    time_to_target_p25: Optional[float]
    time_to_target_p50: Optional[float]
    time_to_target_p75: Optional[float]
    time_to_stop_p25:   Optional[float]
    time_to_stop_p50:   Optional[float]
    time_to_stop_p75:   Optional[float]

    # ── Expected move distribution (signed, using MFE) ───────────────────────
    expected_move_p25: Optional[float]
    expected_move_p50: Optional[float]
    expected_move_p75: Optional[float]

    # ── T+N horizon distributions ────────────────────────────────────────────
    t1_ret_p25: Optional[float]
    t1_ret_p50: Optional[float]
    t1_ret_p75: Optional[float]
    t3_ret_p25: Optional[float]
    t3_ret_p50: Optional[float]
    t3_ret_p75: Optional[float]
    t5_ret_p25: Optional[float]
    t5_ret_p50: Optional[float]
    t5_ret_p75: Optional[float]

    # ── Threshold probabilities ───────────────────────────────────────────────
    prob_move_1pct_by_t1: Optional[float]
    prob_move_1pct_by_t3: Optional[float]
    prob_move_1pct_by_t5: Optional[float]
    prob_move_2pct_by_t1: Optional[float]
    prob_move_2pct_by_t3: Optional[float]
    prob_move_2pct_by_t5: Optional[float]
    prob_move_3pct_by_t5: Optional[float]
    prob_move_5pct_by_t5: Optional[float]

    # ── Holding horizon (trading days to first event, any direction) ──────────
    expected_days_p25: Optional[float]
    expected_days_p50: Optional[float]
    expected_days_p75: Optional[float]

    # ── Historical target/stop offsets ───────────────────────────────────────
    # These are % offsets from entry (not price levels — those are per-signal)
    knowledge_target_offset_p50: Optional[float]   # median empirical target move %
    knowledge_stop_offset_p50:   Optional[float]   # median empirical stop distance %
    target_source:   str   # "EMPIRICAL" | "ATR_FALLBACK"
    stop_source:     str   # "EMPIRICAL" | "ATR_FALLBACK"
    target_confidence: str  # "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT"
    stop_confidence:   str

    # ── Stability ─────────────────────────────────────────────────────────────
    stability_status: str          # stable | developing | unstable | insufficient_data
    recent_hit_rate:  Optional[float]
    historical_hit_rate: Optional[float]

    # ── Source provenance (informational only — does not affect ESS or conviction) ──
    bootstrap_record_count:              int = 0   # source_type == "HISTORICAL"
    live_record_count:                   int = 0   # source_type == "LIVE" or "PAPER"
    historical_replay_record_count:      int = 0   # source_type == "HISTORICAL_REPLAY" (all partitions)
    historical_replay_train_count:       int = 0   # DTA-033: TRAIN partition
    historical_replay_validation_count:  int = 0   # DTA-033: VALIDATION partition
    historical_replay_oos_count:         int = 0   # DTA-033: OOS partition (excluded from evidence computation)
    research_record_count:               int = 0   # DTA-033: bootstrap + replay (all non-live)
    live_authority_record_count:         int = 0   # DTA-033: LIVE source_type only

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Score V2 preview components
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KnowledgeScoreV2Preview:
    """
    KLP-003: Knowledge Research Score V2 preview.

    READ-ONLY — does NOT affect production pipeline.
    Weights:
        40% current scanner features (V1 component — unchanged)
        30% empirical target probability (NEW)
        20% empirical move magnitude  (NEW)
        10% regime × sector alignment (NEW — from data, not hard-coded table)

    Falls back to V1 if empirical data is insufficient.
    """
    score_v2:              float   # 0–1
    score_v1:              float   # original V1 for comparison
    v2_delta:              float   # v2 - v1

    # V1 component (40% of V2)
    w_scanner:             float = 0.40
    scanner_component:     float = 0.0

    # Empirical target probability component (30% of V2)
    w_empirical_target:    float = 0.30
    empirical_target_component: float = 0.0
    target_hit_probability: Optional[float] = None

    # Empirical move magnitude component (20% of V2)
    w_empirical_move:      float = 0.20
    empirical_move_component: float = 0.0
    expected_move_p50:     Optional[float] = None

    # Regime/sector historical alignment component (10% of V2)
    w_historical_alignment: float = 0.10
    historical_alignment_component: float = 0.0

    # Evidence quality
    evidence_level:        int = 7          # 7 = ATR fallback
    evidence_tier:         int = 0
    evidence_confidence:   float = 0.0
    using_fallback:        bool = True      # True if V2 = V1 due to no data

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Behaviour profile (top-level HBE output)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BehaviourProfile:
    """
    Complete Historical Behaviour Engine output for one query.

    Produced by HistoricalBehaviourEngine.get_behaviour_profile().
    Always contains valid metrics (Level 7 ATR fallback if no data).
    no_lookahead is always True — no future data used in any calculation.
    """
    # ── Query ─────────────────────────────────────────────────────────────────
    query_symbol:    str
    query_direction: str
    query_regime:    Optional[str]
    query_sector:    str

    # ── Primary metrics ───────────────────────────────────────────────────────
    metrics: BehaviourMetrics

    # ── V2 score preview ──────────────────────────────────────────────────────
    score_v2_preview: KnowledgeScoreV2Preview

    # ── ATR fallback values (always populated) ────────────────────────────────
    atr_scanner_target_pct: Optional[float]    # scanner target_pct = (target/entry-1)*100
    atr_scanner_stop_pct:   Optional[float]    # scanner stop_pct = (1-stop/entry)*100

    # ── Computed knowledge target/stop FOR THIS SIGNAL ───────────────────────
    knowledge_target:  Optional[float]  # empirical offset applied to signal entry; None = use scanner
    knowledge_stop:    Optional[float]  # empirical offset applied to signal entry; None = use scanner
    target_source:     str              # "EMPIRICAL_L1" … "ATR_FALLBACK"
    stop_source:       str

    # ── Metadata ─────────────────────────────────────────────────────────────
    calculation_ts:      str    # ISO8601 UTC
    calculation_version: str    # "HBE_v1"
    no_lookahead:        bool   = True
    broker_calls:        int    = 0
    orders:              int    = 0

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d
