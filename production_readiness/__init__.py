"""production_readiness — PRR-001 Final Production Readiness package."""
from .prr_config import *
from .prr_models import (
    EdgeGateResult,
    ShortDNASignal,
    ShortDNAAudit,
    FreshnessResult,
    SignalFreshnessReport,
    UniverseSymbol,
    UniverseCoverageReport,
    PipelineStageResult,
    DailyPipelineResult,
    KnowledgeItem,
    KnowledgeValidityReport,
    MissClassification,
    MissedOpportunityReport,
    LearningImpactSummary,
    CertificationCheck,
    ProductionCertificate,
)
from .ph1_edge_gate import (
    is_edge_allowed,
    filter_edges,
    get_edge_gate_summary,
    patch_knowledge_provider,
)
from .ph2_short_dna import (
    evaluate_short_dna,
    get_short_dna_confidence_boost,
    run_short_dna_audit,
)
from .ph3_signal_freshness import (
    compute_freshness,
    is_signal_expired,
    build_freshness_report,
)
from .ph4_universe import (
    load_raw_universe,
    get_eligible_symbols,
    get_eligible_symbol_list,
    build_dynamic_watchlist_rows,
    build_universe_coverage_report,
)
from .ph5_daily_pipeline import run_daily_pipeline
from .ph6_knowledge_validity import build_knowledge_validity_report
from .ph7_missed_opps import (
    classify_single_miss,
    classify_all_misses,
    build_missed_opportunity_report,
)
from .ph8_learning_impact import get_learning_impact_summary
from .ph9_certification import build_certificate
from .prr_reporter import write_all_reports
from .prr_runner import run_prr

__all__ = [
    # Models
    "EdgeGateResult", "ShortDNASignal", "ShortDNAAudit",
    "FreshnessResult", "SignalFreshnessReport",
    "UniverseSymbol", "UniverseCoverageReport",
    "PipelineStageResult", "DailyPipelineResult",
    "KnowledgeItem", "KnowledgeValidityReport",
    "MissClassification", "MissedOpportunityReport",
    "LearningImpactSummary",
    "CertificationCheck", "ProductionCertificate",
    # Phase functions
    "is_edge_allowed", "filter_edges", "get_edge_gate_summary", "patch_knowledge_provider",
    "evaluate_short_dna", "get_short_dna_confidence_boost", "run_short_dna_audit",
    "compute_freshness", "is_signal_expired", "build_freshness_report",
    "load_raw_universe", "get_eligible_symbols", "get_eligible_symbol_list",
    "build_dynamic_watchlist_rows", "build_universe_coverage_report",
    "run_daily_pipeline",
    "build_knowledge_validity_report",
    "classify_single_miss", "classify_all_misses", "build_missed_opportunity_report",
    "get_learning_impact_summary",
    "build_certificate",
    "write_all_reports",
    "run_prr",
]
