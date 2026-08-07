"""
institutional_learning — ILC-001 Institutional Learning Cycle.

The FINAL scientific learning layer of IIOS.
Recovers every remaining gap identified in PGA, GVA, KVA, DTA, SVP.
ILC is an orchestration and verification layer — it reuses all existing modules.

Public API
----------
    from institutional_learning import run_ilc, ILCConfig

    result = run_ilc()                          # uses today's date
    result = run_ilc(report_date="2026-04-02")  # back-test a specific day
    result = run_ilc(dry_run=True)              # simulate without persisting
"""
from .ilc_runner import run_ilc
from .ilc_config import (
    ILC_DIR,
    LEARNING_REGISTRY,
    LIFECYCLE_DB_PATH,
    VERIFICATION_WINDOWS,
    ILC_TOP_N,
    EIG_WEIGHTS,
    TARGET_COST,
    SCORE_WEIGHTS,
)
from .ilc_models import (
    UniverseStatus,
    MarketOpportunityItem,
    LearningConfidence,
    VerificationResult,
    LearningRecord,
    ROIRecord,
    LifecycleRecord,
    ILSScore,
    ILCResult,
)
from .ilc_verification import (
    register_learning_actions,
    run_verification_pass,
    get_all_records,
)
from .ilc_score import compute_ils_score
from .ilc_roi import compute_all_roi
from .ilc_lifecycle import update_lifecycle
from .ilc_confidence import score_confidence, score_all_actions
from .ilc_priority import compute_eig, prioritize_actions
from .ilc_market_audit import audit_market_opportunities

__all__ = [
    "run_ilc",
    # Config
    "ILC_DIR", "LEARNING_REGISTRY", "LIFECYCLE_DB_PATH",
    "VERIFICATION_WINDOWS", "ILC_TOP_N", "EIG_WEIGHTS", "TARGET_COST", "SCORE_WEIGHTS",
    # Models
    "UniverseStatus", "MarketOpportunityItem", "LearningConfidence",
    "VerificationResult", "LearningRecord", "ROIRecord", "LifecycleRecord",
    "ILSScore", "ILCResult",
    # Core functions
    "register_learning_actions", "run_verification_pass", "get_all_records",
    "compute_ils_score", "compute_all_roi", "update_lifecycle",
    "score_confidence", "score_all_actions",
    "compute_eig", "prioritize_actions",
    "audit_market_opportunities",
]
