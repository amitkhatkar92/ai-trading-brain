"""opportunity_engine/knowledge_fusion — KLP-004/005 Knowledge Fusion Layer."""
from .kf_models import (
    SourceInventoryItem,
    KnowledgeFusionRecord,
    AngleResult,
    MultiAngleView,
    RelationshipCandidate,
    ContradictionRecord,
    RedundancyRecord,
    SelectionAnalysisRecord,
    KnowledgeObject,
    CANDIDATE, OBSERVED, VALIDATED, DECISION_ELIGIBLE, RETIRED,
    USED_IN_DECISION, USED_AS_CONTEXT, OBSERVED_ONLY, UNUSED, INSUFFICIENT_DATA,
    CONTRADICTION_NONE, CONTRADICTION_MINOR, CONTRADICTION_MAJOR,
    OOS_NOT_TESTED, OOS_TESTED, OOS_PASSED, OOS_FAILED,
)
from .knowledge_fusion_engine import KnowledgeFusionEngine
from .market_behavior_adapter import (
    MarketLeaderRecord,
    load_market_leader_records,
    get_sector_leader_stats,
    get_symbol_leader_stats,
)

__all__ = [
    "KnowledgeFusionEngine",
    "SourceInventoryItem", "KnowledgeFusionRecord",
    "AngleResult", "MultiAngleView",
    "RelationshipCandidate", "ContradictionRecord",
    "RedundancyRecord", "SelectionAnalysisRecord", "KnowledgeObject",
    "CANDIDATE", "OBSERVED", "VALIDATED", "DECISION_ELIGIBLE", "RETIRED",
    "USED_IN_DECISION", "USED_AS_CONTEXT", "OBSERVED_ONLY", "UNUSED",
    "INSUFFICIENT_DATA", "CONTRADICTION_NONE", "CONTRADICTION_MINOR",
    "CONTRADICTION_MAJOR", "OOS_NOT_TESTED", "OOS_TESTED", "OOS_PASSED", "OOS_FAILED",
    # KLP-005 PART 4
    "MarketLeaderRecord", "load_market_leader_records",
    "get_sector_leader_stats", "get_symbol_leader_stats",
]
