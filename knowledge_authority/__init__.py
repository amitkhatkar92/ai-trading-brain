"""knowledge_authority — KDA-001 / KDA-002 / KDA-003 Knowledge Decision Authority package."""
from .kda_models import (
    AngleAnalysis,
    AngleVerdict,
    CounterfactualResult,
    DecisionAuthority,
    DecisionOutcome,
    EvidenceHierarchyLevel,
    EvidenceState,
    ExitState,
    InformationContribution,
    KDADecision,
    KDADecisionRecord,
    KDAOutcomeFeedback,
    KDARelationship,
    KnowledgeAuthorityComponents,
    StrategyContext,
)
from .knowledge_decision_authority import KnowledgeDecisionAuthority

# KDA-002 — outcome models
from .kda_outcome_models import (
    AuthorityBucketResult,
    AuthorityStatus,
    AuthorityValidationReport,
    ComparisonType,
    EvidenceTierResult,
    KDAComparisonRecord,
    KDAOutcomeRecord,
    MoveSpeed,
    OHLCVBar,
    OutcomeClass,
    OutcomeStatus,
    OverruleResult,
    SourcePerformanceRecord,
    TargetComparison,
)

# KDA-002 — engines
from .kda_ledger           import KDALedger
from .kda_outcome_engine   import KDAOutcomeEngine
from .kda_comparative      import KDAComparativeAnalyzer
from .kda_authority_report import KDAAuthorityReporter

# KDA-003 — shadow pipeline orchestration boundary
from .knowledge_decision_pipeline import (
    KnowledgeDecisionPipeline,
    get_knowledge_pipeline,
)

__all__ = [
    # KDA-001 models
    "KnowledgeDecisionAuthority",
    "KDADecisionRecord", "KDAOutcomeFeedback",
    "KDADecision", "DecisionAuthority", "EvidenceState",
    "EvidenceHierarchyLevel", "AngleVerdict", "KDARelationship",
    "ExitState", "DecisionOutcome",
    "AngleAnalysis", "InformationContribution", "CounterfactualResult",
    "StrategyContext", "KnowledgeAuthorityComponents",
    # KDA-002 models
    "OutcomeStatus", "OutcomeClass", "ComparisonType", "OverruleResult",
    "AuthorityStatus", "TargetComparison", "MoveSpeed",
    "OHLCVBar", "KDAOutcomeRecord", "KDAComparisonRecord",
    "SourcePerformanceRecord", "AuthorityBucketResult",
    "EvidenceTierResult", "AuthorityValidationReport",
    # KDA-002 engines
    "KDALedger", "KDAOutcomeEngine", "KDAComparativeAnalyzer", "KDAAuthorityReporter",
]
