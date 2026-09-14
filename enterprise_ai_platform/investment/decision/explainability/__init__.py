"""enterprise_ai_platform/investment/decision/explainability/__init__.py
Public surface of the Decision Explainability Engine.
"""
from enterprise_ai_platform.investment.decision.explainability.audit_view import AuditView, build_audit_view
from enterprise_ai_platform.investment.decision.explainability.analyst_view import AnalystView, build_analyst_view
from enterprise_ai_platform.investment.decision.explainability.counterfactual_engine import (
    CounterfactualEngine,
    CounterfactualReport,
)
from enterprise_ai_platform.investment.decision.explainability.decision_explanation import (
    DecisionExplanation,
    ExplanationFactor,
)
from enterprise_ai_platform.investment.decision.explainability.decision_explainability_engine import (
    DecisionExplainabilityEngine,
)
from enterprise_ai_platform.investment.decision.explainability.decision_narrative import (
    DecisionNarrative,
    EnglishNarrativeTemplate,
    NarrativeReport,
    NarrativeTemplate,
)
from enterprise_ai_platform.investment.decision.explainability.decision_sensitivity import (
    DecisionSensitivityAnalyzer,
    SensitivityReport,
)
from enterprise_ai_platform.investment.decision.explainability.decision_trace import (
    DecisionTrace,
    EvidenceTraceNode,
    ReasoningTraceNode,
)
from enterprise_ai_platform.investment.decision.explainability.developer_view import (
    DeveloperView,
    build_developer_view,
)
from enterprise_ai_platform.investment.decision.explainability.evidence_mapper import EvidenceMapper
from enterprise_ai_platform.investment.decision.explainability.executive_view import (
    ExecutiveView,
    build_executive_view,
)
from enterprise_ai_platform.investment.decision.explainability.explainability_constants import (
    CAUTION_CONFIDENCE_MIN,
    EXPLANATION_HISTORY_WINDOW,
    FULL_TRACEABILITY_ITEM_MIN,
    MIN_FACTORS_FOR_FULL_TRANSPARENCY,
    MIN_STEPS_FOR_FULL_TRACEABILITY,
    PROCEED_CONFIDENCE_MIN,
    PROCEED_RISK_MAX,
    SENSITIVITY_PERTURBATION_STEP,
    CounterfactualType,
    DecisionOutcome,
    ExplainabilityGrade,
    ExplainabilityStatus,
    ExplanationFormat,
    ExplanationLevel,
    FactorSource,
    TraceabilityLevel,
)
from enterprise_ai_platform.investment.decision.explainability.explainability_health import (
    ExplainabilityHealthMonitor,
    ExplainabilityHealthReport,
)
from enterprise_ai_platform.investment.decision.explainability.explainability_quality import (
    ExplainabilityQualityEvaluator,
)
from enterprise_ai_platform.investment.decision.explainability.explanation_formatter import ExplanationFormatter
from enterprise_ai_platform.investment.decision.explainability.explanation_generator import (
    ExplainabilityInput,
    ExplanationGenerator,
)
from enterprise_ai_platform.investment.decision.explainability.explanation_history import ExplanationHistory
from enterprise_ai_platform.investment.decision.explainability.explanation_snapshot import (
    ExplanationSnapshot,
    build_explanation_snapshot,
)
from enterprise_ai_platform.investment.decision.explainability.explanation_statistics import (
    ExplanationStatistics,
    ExplanationStatisticsTracker,
)
from enterprise_ai_platform.investment.decision.explainability.reasoning_mapper import ReasoningMapper
from enterprise_ai_platform.investment.decision.explainability.summary_builder import (
    SummaryBuilder,
    derive_outcome,
)
from enterprise_ai_platform.investment.decision.explainability.threshold_analysis import (
    ThresholdAnalyzer,
    ThresholdReport,
    ThresholdResult,
)
from enterprise_ai_platform.investment.decision.explainability.traceability_engine import TraceabilityEngine
from enterprise_ai_platform.investment.decision.explainability.traceability_score import TraceabilityScorer
from enterprise_ai_platform.investment.decision.explainability.transparency_score import TransparencyScorer
from enterprise_ai_platform.investment.decision.explainability.what_if_analysis import (
    WhatIfAnalyzer,
    WhatIfReport,
    WhatIfScenario,
)

__all__ = [
    # Engine
    "DecisionExplainabilityEngine",
    # Input wrapper
    "ExplainabilityInput",
    # Snapshots
    "ExplanationSnapshot", "build_explanation_snapshot",
    "DecisionExplanation", "ExplanationFactor",
    # Narrative
    "DecisionNarrative", "NarrativeReport", "NarrativeTemplate", "EnglishNarrativeTemplate",
    # Generator
    "ExplanationGenerator",
    # Traceability
    "TraceabilityEngine",
    "DecisionTrace", "EvidenceTraceNode", "ReasoningTraceNode",
    "EvidenceMapper", "ReasoningMapper",
    # Views
    "ExecutiveView", "build_executive_view",
    "AnalystView", "build_analyst_view",
    "DeveloperView", "build_developer_view",
    "AuditView", "build_audit_view",
    # Counterfactual
    "CounterfactualEngine", "CounterfactualReport",
    "WhatIfAnalyzer", "WhatIfReport", "WhatIfScenario",
    "DecisionSensitivityAnalyzer", "SensitivityReport",
    "ThresholdAnalyzer", "ThresholdReport", "ThresholdResult",
    # Quality
    "TransparencyScorer",
    "TraceabilityScorer",
    "ExplainabilityQualityEvaluator",
    # Health / stats / history
    "ExplainabilityHealthMonitor", "ExplainabilityHealthReport",
    "ExplanationStatistics", "ExplanationStatisticsTracker",
    "ExplanationHistory",
    # Formatting
    "ExplanationFormatter",
    # Summary
    "SummaryBuilder", "derive_outcome",
    # Constants / enums
    "DecisionOutcome", "ExplanationLevel", "ExplanationFormat",
    "TraceabilityLevel", "ExplainabilityGrade", "ExplainabilityStatus",
    "FactorSource", "CounterfactualType",
    "PROCEED_CONFIDENCE_MIN", "PROCEED_RISK_MAX", "CAUTION_CONFIDENCE_MIN",
    "EXPLANATION_HISTORY_WINDOW", "SENSITIVITY_PERTURBATION_STEP",
]
