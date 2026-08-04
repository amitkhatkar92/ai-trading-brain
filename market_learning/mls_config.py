"""
mls_config.py — Market Learning System configuration.

All MLS algorithm thresholds are owned by this module.
No threshold is hardcoded anywhere else in the market_learning package.
Changes to these values must follow the change control process in
MLS_GOVERNANCE.md §4.1.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass


@dataclass
class MLSConfig:
    """
    Single source of truth for all MLS configurable parameters.

    Every threshold that governs observation, DNA discovery, or validation
    lives here.  Statistical gates G-ML-01 through G-ML-07 (MLS_GOVERNANCE.md)
    correspond directly to the fields in this class.
    """

    # ── Temporal contract ──────────────────────────────────────────────────
    feature_deadline_hour:   int   = 9    # 09:15 IST = market open
    feature_deadline_minute: int   = 15
    feature_deadline_second: int   = 0    # boundary is inclusive: 09:15:00 passes

    # ── Universe ───────────────────────────────────────────────────────────
    min_universe_size: int = 10           # abort capture if fewer symbols extracted

    # ── Statistical gates ─────────────────────────────────────────────────
    min_group_size:            int   = 30    # G-ML-01: minimum n per winner/loser group
    min_effect_size:           float = 0.50  # G-ML-02: minimum |Cohen's d|
    max_p_value:               float = 0.05  # G-ML-03: max adjusted p-value
    min_consistency_pct_weekly:    float = 60.0  # G-ML-04: % of days in 5-day window
    min_consistency_pct_monthly:   float = 60.0  # G-ML-04: % of days in 20-day window
    min_consistency_pct_quarterly: float = 50.0  # G-ML-04: % of days in 60-day window
    min_regime_count:          int   = 2    # G-ML-05: regimes where characteristic holds
    min_sector_count:          int   = 3    # G-ML-06: sectors where characteristic holds
    min_oos_consistency_pct:   float = 0.50  # G-ML-07: OOS walk-forward pass rate
    max_contradiction_ratio:   float = 0.20  # max fraction of contradicting studies

    # ── Confidence formula weights (must sum to 1.0) ───────────────────────
    confidence_consistency_weight:  float = 0.50
    confidence_effect_size_weight:  float = 0.30
    confidence_significance_weight: float = 0.20

    # ── DNA lifecycle ──────────────────────────────────────────────────────
    new_char_lookback_days: int = 5    # days absent before re-flagging as "new"
    retirement_days:        int = 20   # consecutive absent days before RETIRED

    # ── Aggregation windows ────────────────────────────────────────────────
    weekly_window_days:    int = 5
    monthly_window_days:   int = 20
    quarterly_window_days: int = 60

    # ── Storage ────────────────────────────────────────────────────────────
    snapshot_retention_days: int = 90

    # ── Phase 2: PopulationClassifier ─────────────────────────────────────
    # Performance — exclusive percentile fractions (from each end)
    perf_top1_frac:  float = 0.01  # fraction assigned to TOP_1PCT
    perf_top5_frac:  float = 0.05  # fraction assigned to TOP_5PCT (exclusive)
    perf_top10_frac: float = 0.10  # fraction assigned to TOP_10PCT (exclusive)
    perf_bot10_frac: float = 0.10  # fraction assigned to BOTTOM_10PCT (exclusive)
    perf_bot5_frac:  float = 0.05  # fraction assigned to BOTTOM_5PCT (exclusive)
    perf_bot1_frac:  float = 0.01  # fraction assigned to BOTTOM_1PCT

    # Sector relative (feature: sector_strength, range 0-1)
    sector_winner_threshold: float = 0.65
    sector_loser_threshold:  float = 0.35

    # Liquidity (feature: liquidity_score, range 0-1)
    liquidity_high_threshold: float = 0.70
    liquidity_low_threshold:  float = 0.30

    # Volatility (feature: hist_vol_5d, range ~0.05-0.30)
    vol_high_threshold: float = 0.20
    vol_low_threshold:  float = 0.10

    # Market cap proxy (feature: liquidity_score as proxy, range 0-1)
    mktcap_large_threshold: float = 0.70
    mktcap_small_threshold: float = 0.35

    # Volume expansion (feature: volume_ratio_raw, range ~0.8-3.0)
    vol_expansion_ratio:   float = 1.50   # >= this -> EXPANDING
    vol_contraction_ratio: float = 0.90   # <= this -> CONTRACTING

    # Relative strength (feature: rsi, range 5-95)
    rs_strong_rsi: float = 65.0
    rs_weak_rsi:   float = 35.0

    # Regime alignment (feature: mom_5d for bull/bear, iv_rank for volatile)
    regime_mom_threshold: float = 0.0   # mom_5d > this -> aligned in BULL regime

    # ── Phase 3: DNADiscoveryEngine ───────────────────────────────────────────
    # Discovery gates
    dna_min_group_size:      int   = 2     # min members in winner/loser group to run analysis
    dna_min_effect_size:     float = 0.30  # min |Cohen's d| to report a characteristic
    dna_min_spearman:        float = 0.15  # min |Spearman r| for monotonic evidence
    dna_interaction_amplify: float = 0.30  # joint effect / best_individual - 1 >= this
    dna_bootstrap_samples:   int   = 200   # bootstrap CI resamples

    # Performance populations used as winner / loser groups
    dna_winner_labels: tuple = ("TOP_5PCT", "TOP_10PCT")
    dna_loser_labels:  tuple = ("BOTTOM_5PCT", "BOTTOM_10PCT")

    # ── Phase 4: DNAConsensusEngine ───────────────────────────────────────────
    # Lifecycle gates
    consensus_institutional_min_count: int   = 10    # evidence_count >= → INSTITUTIONAL
    consensus_institutional_min_score: float = 0.60  # consensus_score >= → INSTITUTIONAL
    consensus_retirement_absent_days:  int   = 30    # absent calendar days → RETIRED
    # Drift
    consensus_drift_threshold:         float = 0.30  # drift magnitude >= → significant
    consensus_drift_window:            int   = 7     # rolling window (days) for drift
    # Confidence trend
    consensus_trend_window:            int   = 7     # OLS window for slope
    consensus_trend_declining_slope:   float = 0.05  # |slope| > this → significant
    # Stability gates
    consensus_stability_min_rep_freq:  float = 0.50
    consensus_stability_min_temporal:  float = 0.50
    consensus_stability_min_regime:    float = 0.40
    # Consensus score weights — must sum to 1.0
    consensus_w_replication:  float = 0.25
    consensus_w_temporal:     float = 0.20
    consensus_w_regime:       float = 0.20
    consensus_w_sector:       float = 0.15
    consensus_w_confidence:   float = 0.10
    consensus_w_persistence:  float = 0.10

    # ── Phase 5: PMCIEngine ────────────────────────────────────────────────────
    # Positive component weights — must sum to 1.0
    pmci_w_winner:    float = 0.35   # winner DNA alignment
    pmci_w_evidence:  float = 0.20   # evidence strength (avg consensus_score)
    pmci_w_regime:    float = 0.15   # cross-regime stability
    pmci_w_sector:    float = 0.10   # cross-sector stability
    pmci_w_trend:     float = 0.07   # confidence evolution (improving fraction)
    pmci_w_freshness: float = 0.06   # DNA freshness (recency decay)
    pmci_w_coverage:  float = 0.05   # knowledge coverage fraction
    pmci_w_neutral:   float = 0.02   # neutral DNA alignment
    # Loser penalty — applied as a discount on positive score (not in sum-to-1)
    pmci_w_loser:     float = 0.25
    # Freshness decay window
    pmci_freshness_days:              int   = 30
    # Feature alignment midpoint (assumes [0,1]-normalised features)
    pmci_feature_midpoint:            float = 0.50
    # Similarity classification thresholds
    pmci_high_similarity_threshold:   float = 0.70
    pmci_low_similarity_threshold:    float = 0.30

    # ── Phase 5A: MCIEngine ───────────────────────────────────────────────────
    # Context dimension weights — must sum to 1.0
    mcie_w_regime:          float = 0.20   # regime clarity / strength
    mcie_w_volatility:      float = 0.15   # VIX-based volatility environment
    mcie_w_liquidity:       float = 0.15   # institutional flow + breadth
    mcie_w_participation:   float = 0.12   # market-breadth participation
    mcie_w_sector:          float = 0.12   # sector rotation quality
    mcie_w_institutional:   float = 0.10   # FII/DII institutional activity
    mcie_w_global:          float = 0.10   # global sentiment alignment
    mcie_w_risk:            float = 0.06   # PCR + VIX combined risk
    # VIX scoring thresholds
    mcie_vix_low:           float = 15.0   # VIX ≤ this → score 0.90
    mcie_vix_medium:        float = 20.0   # VIX ≤ this → score 0.70
    mcie_vix_high:          float = 30.0   # VIX ≤ this → score 0.40
    mcie_vix_extreme:       float = 40.0   # VIX ≤ this → score 0.20
    # PCR balanced zone (both ends inclusive)
    mcie_pcr_balanced_lo:   float = 0.80
    mcie_pcr_balanced_hi:   float = 1.20
    # Component drift detection threshold
    mcie_drift_threshold:   float = 0.10   # |delta| ≥ this → component is drifting
    # Context score classification
    mcie_high_context_threshold: float = 0.65
    mcie_low_context_threshold:  float = 0.35
    # In-memory history buffer size
    mcie_max_history_size: int = 100

    # ── Phase 5A.1: CDSEngine ─────────────────────────────────────────────────
    # CDS dimension weights — must sum to 1.0
    cds_w_regime:         float = 0.20
    cds_w_sector:         float = 0.15
    cds_w_volatility:     float = 0.15
    cds_w_breadth:        float = 0.12
    cds_w_liquidity:      float = 0.10
    cds_w_institutional:  float = 0.10
    cds_w_global:         float = 0.08
    cds_w_freshness:      float = 0.05
    cds_w_stability:      float = 0.03
    cds_w_historical:     float = 0.02
    # Relevance thresholds
    cds_highly_relevant:  float = 0.75
    cds_relevant:         float = 0.55
    cds_neutral:          float = 0.40
    cds_weak:             float = 0.25
    cds_irrelevant:       float = 0.10
    # Freshness decay window (days)
    cds_freshness_days:   int   = 30
    # In-memory context history size
    cds_max_history_size: int   = 200
    # Top-N historical analogues returned per query
    cds_top_analogues:    int   = 5
    # Context stability change thresholds — based on (1 - stability)
    cds_stable_threshold:            float = 0.05
    cds_changing_threshold:          float = 0.15
    cds_rapidly_changing_threshold:  float = 0.25
    cds_unstable_threshold:          float = 0.35

    # ── Phase 5B: CAPMCIEngine ────────────────────────────────────────────────
    # Context adjustment weights (max contribution per dimension = ±weight)
    ca_pmci_w_regime:       float = 0.15   # regime match max adjustment
    ca_pmci_w_volatility:   float = 0.10   # volatility match max adjustment
    ca_pmci_w_sector:       float = 0.10   # sector match max adjustment
    ca_pmci_w_stability:    float = 0.07   # context stability max adjustment
    ca_pmci_w_freshness:    float = 0.05   # DNA freshness max adjustment
    # Adjustment bounds
    ca_pmci_max_single_adj: float = 0.15   # per-adjustment clamp ceiling
    ca_pmci_max_total_adj:  float = 0.30   # total adjustment clamp ceiling
    # Classification thresholds
    ca_pmci_high_threshold: float = 0.70   # CA-PMCI ≥ this → high similarity
    ca_pmci_low_threshold:  float = 0.30   # CA-PMCI ≤ this → low similarity

    # ── R-013: IDRRepository ──────────────────────────────────────────────────
    idr_schema_version:          int   = 1      # current DB schema version
    idr_max_evidence_per_dna:    int   = 500    # soft cap on evidence records per DNA
    idr_max_history_per_dna:     int   = 1000   # soft cap on history points per DNA
    idr_max_context_per_dna:     int   = 200    # soft cap on context snapshots per DNA
    idr_backup_on_schema_change: bool  = True   # auto-backup before schema migration
    idr_wal_mode:                bool  = True   # enable WAL journal mode
    idr_min_confidence_active:   float = 0.0    # min confidence to include in list_active
    idr_default_operator:        str   = "system"

    # ── R-001: PlatformIntelligenceGateway ────────────────────────────────────
    pig_high_threshold:   float = 0.70   # CA-PMCI >= this -> HIGH quality signal
    pig_medium_threshold: float = 0.45   # CA-PMCI >= this -> MEDIUM quality signal
    pig_low_threshold:    float = 0.30   # CA-PMCI <= this -> LOW quality signal

    # ── R-001 Phase 2: PIG integration influence policy ──────────────────────
    pig_vote_weight:               float = 0.08   # DecisionEngine weight for InstitutionalDNAAI
    pig_min_ca_pmci_for_vote:      float = 0.30   # min CA-PMCI to cast a vote; below → silent
    pig_max_conviction_boost:      float = 1.0    # max additive boost to TradeSignal.confidence
    pig_min_ca_pmci_for_boost:     float = 0.30   # min CA-PMCI to apply opportunity boost
    pig_opportunity_boost_enabled: bool  = True   # enable Opportunity Engine enrichment
    pig_decision_vote_enabled:     bool  = True   # enable Decision Engine vote injection
    pig_telemetry_enabled:         bool  = True   # emit [PIGTelemetry] log lines

    def config_hash(self) -> str:
        """SHA-256[:16] of canonical JSON config — used in audit trail."""
        raw = json.dumps(dataclasses.asdict(self), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
