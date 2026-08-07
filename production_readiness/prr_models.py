"""production_readiness/prr_models.py — Data models for all PRR-001 phases."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Phase 1: Edge gate ────────────────────────────────────────────────────────

@dataclass
class EdgeGateResult:
    total_edges: int
    active_edges: int
    candidate_edges: int
    decaying_blocked: int
    retired_blocked: int
    pct_blocked: float
    blocked_edge_ids: List[str]
    audit_timestamp: str = ""


# ── Phase 2: SHORT DNA ────────────────────────────────────────────────────────

@dataclass
class ShortDNASignal:
    symbol: str
    direction: str = "SHORT"
    dna_confidence: float = 0.0
    matching_conditions: List[str] = field(default_factory=list)
    loser_pattern_id: str = ""
    regime_compatible: bool = True
    governance_approved: bool = False
    rejection_reason: str = ""


@dataclass
class ShortDNAAudit:
    date: str
    total_loser_dna: int
    conditions_evaluated: int
    short_signals_generated: int
    short_signals_approved: int
    regime: str
    confidence_gate: float
    top_signals: List[ShortDNASignal] = field(default_factory=list)


# ── Phase 3: Signal freshness ──────────────────────────────────────────────────

@dataclass
class FreshnessResult:
    symbol: str
    signal_ts: str
    age_trading_days: float
    freshness_score: float        # 1.0 = brand new, 0.0 = expired
    freshness_status: str         # FRESH | WEAKENING | EXPIRED
    is_expired: bool
    reason: str


@dataclass
class SignalFreshnessReport:
    date: str
    signals_checked: int
    fresh: int
    weakening: int
    expired: int
    blocked_for_execution: int
    oldest_blocked_days: float
    details: List[FreshnessResult] = field(default_factory=list)


# ── Phase 4: Universe ─────────────────────────────────────────────────────────

@dataclass
class UniverseSymbol:
    symbol: str
    yahoo_ticker: str
    sector: str
    index: str
    adv_crore: float = 0.0
    data_quality_days: int = 0
    is_eligible: bool = True
    exclusion_reason: str = ""


@dataclass
class UniverseCoverageReport:
    date: str
    total_nifty500: int
    eligible: int
    excluded: int
    coverage_pct: float
    unexpected_exclusions: List[str]
    exclusion_breakdown: Dict[str, int]
    symbols: List[UniverseSymbol] = field(default_factory=list)


# ── Phase 5: Daily pipeline ────────────────────────────────────────────────────

@dataclass
class PipelineStageResult:
    stage: str
    success: bool
    elapsed_seconds: float
    output: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class DailyPipelineResult:
    date: str
    total_elapsed_seconds: float
    stages_completed: int
    stages_failed: int
    pga: Optional[PipelineStageResult] = None
    ilc: Optional[PipelineStageResult] = None
    gva: Optional[PipelineStageResult] = None
    sd_review: Optional[PipelineStageResult] = None
    verification: Optional[PipelineStageResult] = None
    reports: Optional[PipelineStageResult] = None


# ── Phase 6: Knowledge validity ────────────────────────────────────────────────

@dataclass
class KnowledgeItem:
    item_id: str
    item_type: str              # DNA | EDGE | HYPOTHESIS | NODE
    created_date: str
    last_verified: str
    days_since_verified: int
    validity_status: str        # VALID | STALE | EXPIRED
    expiry_date: str
    blocks_trading: bool
    detail: str = ""


@dataclass
class KnowledgeValidityReport:
    date: str
    total_items: int
    valid_items: int
    stale_items: int
    expired_items: int
    trading_blocked_items: int
    by_type: Dict[str, Dict[str, int]] = field(default_factory=dict)
    items: List[KnowledgeItem] = field(default_factory=list)


# ── Phase 7: Missed opportunity classification ─────────────────────────────────

@dataclass
class MissClassification:
    symbol: str
    move_pct: float
    direction: str
    classification: str
    triggers_learning: bool
    evidence: List[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class MissedOpportunityReport:
    date: str
    total_misses: int
    correctly_ignored: int
    universe_limitation: int
    knowledge_limitation: int
    research_limitation: int
    threshold_limitation: int
    risk_limitation: int
    portfolio_limitation: int
    external_event: int
    triggers_learning: int      # sum of Knowledge + Research + Threshold
    classifications: List[MissClassification] = field(default_factory=list)


# ── Phase 8: Learning impact ───────────────────────────────────────────────────

@dataclass
class LearningImpactSummary:
    date: str
    total_actions: int
    pending_verification: int
    under_verification: int
    improved: int
    no_change: int
    declined: int
    retired: int
    avg_improvement_pct: float
    roi_positive_pct: float
    top_improved: List[str] = field(default_factory=list)
    top_declined: List[str] = field(default_factory=list)


# ── Phase 9: Production certification ─────────────────────────────────────────

@dataclass
class CertificationCheck:
    check_name: str
    passed: bool
    detail: str
    severity: str = "CRITICAL"    # CRITICAL | WARNING | INFO


@dataclass
class ProductionCertificate:
    date: str
    verdict: str                  # PRODUCTION_READY | PRODUCTION_READY_WITH_OBSERVATIONS | NOT_READY
    certifying_agents: List[str]
    checks: List[CertificationCheck]
    critical_failures: int
    warnings: int
    ils_score: float
    gva_score: float
    edge_gate_pct_blocked: float
    short_dna_operational: bool
    signal_expiry_active: bool
    auto_universe_active: bool
    daily_ilc_active: bool
    knowledge_validity_active: bool
    learning_verification_active: bool
    narrative: str = ""
