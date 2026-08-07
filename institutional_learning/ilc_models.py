"""institutional_learning/ilc_models.py — Data models for ILC-001."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Phase 1: Universe classification ──────────────────────────────────────────

class UniverseStatus:
    INSIDE                  = "INSIDE"
    OUTSIDE_BY_DESIGN       = "OUTSIDE_BY_DESIGN"       # intentionally excluded
    OUTSIDE_UNEXPECTED      = "OUTSIDE_UNEXPECTED"       # should have been inside
    OUTSIDE_UNIVERSE_RULES  = "OUTSIDE_UNIVERSE_RULES"  # excluded by active filter rules


@dataclass
class MarketOpportunityItem:
    symbol: str
    daily_return_pct: float
    actual_direction: str          # UP | DOWN
    volume: float
    move_type: str                 # GAINER | LOSER
    universe_status: str           # UniverseStatus.*
    universe_reason: str           # explanation
    in_scanned_today: bool
    dna_coverage: int
    is_archived: bool = False      # set True for OUTSIDE_BY_DESIGN


# ── Phase 5: Learning Confidence ──────────────────────────────────────────────

class LearningConfidence:
    HIGH         = "HIGH"
    MEDIUM       = "MEDIUM"
    LOW          = "LOW"
    EXPERIMENTAL = "EXPERIMENTAL"


# ── Phase 8: Verification ─────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    learning_id: str
    window_days: int
    verification_date: str         # date when this window was checked
    measured_date: str             # actual measurement date
    metric_name: str
    baseline_value: float
    measured_value: float
    change_pct: float
    verdict: str                   # IMPROVED | NO_CHANGE | DECLINED
    promoted: bool = False
    retired: bool = False
    action_taken: str = ""


@dataclass
class LearningRecord:
    """Persistent record for tracking learning actions and their verification."""
    learning_id: str
    created_date: str
    action_type: str
    category: str                  # A–G
    symbol: str
    description: str
    target_system: str
    expected_benefit: str
    prediction_metric: str         # scan_hit_rate | win_rate | decision_confidence | dna_count
    measurement_windows: List[int] = field(default_factory=lambda: [30, 60, 90])
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    verification_results: List[VerificationResult] = field(default_factory=list)
    status: str = "PENDING"        # PENDING | MEASURING | IMPROVED | NO_CHANGE | DECLINED | RETIRED
    confidence: str = "LOW"        # LearningConfidence.*
    eig_score: float = 0.0
    roi: Optional[float] = None
    executed: bool = False
    outcome: str = ""


# ── Phase 9: ROI ──────────────────────────────────────────────────────────────

@dataclass
class ROIRecord:
    learning_id: str
    symbol: str
    category: str
    target_system: str
    implementation_cost: float     # 0–1 normalised
    observed_improvement: float    # measured delta (0–1)
    roi_score: float               # (improvement - cost) / cost
    confidence: str


# ── Phase 10: Knowledge Lifecycle ─────────────────────────────────────────────

@dataclass
class LifecycleRecord:
    item_id: str
    item_type: str                 # DNA | HYPOTHESIS | EDGE | CALIBRATION
    symbol: str
    discovery_date: str
    validation_date: Optional[str] = None
    promotion_date: Optional[str] = None
    current_status: str = "DISCOVERED"
    verification_history: List[Dict[str, Any]] = field(default_factory=list)
    improvement_history: List[Dict[str, Any]] = field(default_factory=list)
    decay_events: List[Dict[str, Any]] = field(default_factory=list)
    retirement_date: Optional[str] = None
    lifecycle_score: float = 0.0   # 0–100


# ── Phase 11: Institutional Learning Score ────────────────────────────────────

@dataclass
class ILSScore:
    learning_efficiency: float     # verified_improved / total_actions
    knowledge_efficiency: float    # active_dna / total_dna
    prediction_improvement: float  # delta in accuracy vs baseline
    research_productivity: float   # hypotheses / research_days
    knowledge_roi: float           # avg ROI across verified
    overall_score: float           # 0–100
    grade: str                     # A+ / A / B / C / D / F
    narrative: str


# ── Full ILC pipeline result ───────────────────────────────────────────────────

@dataclass
class ILCResult:
    date: str
    status: str
    n_opportunities: int           # total stocks audited (up to 40 = 20G + 20L)
    n_inside_universe: int
    n_outside_by_design: int
    n_outside_unexpected: int
    n_analyses: int                # PGA analyses run
    n_missed_winners: int
    n_missed_losers: int
    n_root_causes: int
    n_actions: int                 # learning actions planned
    n_actions_executed: int
    n_verified_today: int          # verification checks run today
    n_improved: int
    n_no_change: int
    n_declined: int
    learning_score: float          # ILS 0–100
    grade: str
    report_dir: str
    elapsed_seconds: float
    high_confidence_actions: int
    medium_confidence_actions: int
    low_confidence_actions: int
    experimental_actions: int
    top_eig_action: str            # description of top priority action
    verification_records_total: int
    roi_positive_pct: float        # % of actions with positive ROI
