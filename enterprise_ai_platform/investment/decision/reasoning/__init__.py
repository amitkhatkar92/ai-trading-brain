"""enterprise_ai_platform/investment/decision/reasoning/__init__.py
Public surface of the Decision Reasoning Engine.
"""
from enterprise_ai_platform.investment.decision.reasoning.reasoning_constants import (
    ReasoningStepType,
    SignalDirection,
    HypothesisType,
    HypothesisStatus,
    ArgumentType,
    ArgumentStrengthLevel,
    RelationshipType,
    LogicValidationStatus,
    ReasoningStatus,
    ReasoningEngineStatus,
    ReasoningQualityDimension,
    BULLISH_SIGNAL_THRESHOLD,
    BEARISH_SIGNAL_THRESHOLD,
    DEFAULT_REASONING_TIMEOUT_SECS,
)
from enterprise_ai_platform.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step
from enterprise_ai_platform.investment.decision.reasoning.reasoning_chain import ReasoningChain, build_chain
from enterprise_ai_platform.investment.decision.reasoning.evidence_interpreter import (
    EvidenceInterpreter, InterpretedSignal,
)
from enterprise_ai_platform.investment.decision.reasoning.context_analyzer import ContextAnalyzer, ContextProfile
from enterprise_ai_platform.investment.decision.reasoning.signal_interpreter import SignalInterpreter
from enterprise_ai_platform.investment.decision.reasoning.relationship_mapper import (
    RelationshipMapper, Relationship, RelationshipMap,
)
from enterprise_ai_platform.investment.decision.reasoning.hypothesis_engine import HypothesisEngine, Hypothesis
from enterprise_ai_platform.investment.decision.reasoning.hypothesis_registry import HypothesisRegistry
from enterprise_ai_platform.investment.decision.reasoning.hypothesis_validator import (
    HypothesisValidator, HypothesisValidationResult,
)
from enterprise_ai_platform.investment.decision.reasoning.hypothesis_history import HypothesisHistory
from enterprise_ai_platform.investment.decision.reasoning.supporting_arguments import (
    Argument, SupportingArguments,
)
from enterprise_ai_platform.investment.decision.reasoning.opposing_arguments import OpposingArguments
from enterprise_ai_platform.investment.decision.reasoning.argument_strength import (
    ArgumentStrength, ArgumentStrengthSummary,
)
from enterprise_ai_platform.investment.decision.reasoning.argument_engine import ArgumentEngine, ArgumentReport
from enterprise_ai_platform.investment.decision.reasoning.reasoning_trace import ReasoningTrace, TraceEntry
from enterprise_ai_platform.investment.decision.reasoning.decision_logic import DecisionLogic
from enterprise_ai_platform.investment.decision.reasoning.logic_validator import (
    LogicValidator, LogicValidationResult,
)
from enterprise_ai_platform.investment.decision.reasoning.reasoning_score import (
    ReasoningQualityScore, compute_reasoning_score,
)
from enterprise_ai_platform.investment.decision.reasoning.reasoning_confidence import (
    ReasoningConfidence, ReasoningConfidenceScore,
)
from enterprise_ai_platform.investment.decision.reasoning.reasoning_quality import ReasoningQuality
from enterprise_ai_platform.investment.decision.reasoning.reasoning_health import ReasoningHealth, HealthReport
from enterprise_ai_platform.investment.decision.reasoning.reasoning_pipeline import (
    BaseReasoningModule, ReasoningContext, ReasoningPipeline, PipelineResult,
)
from enterprise_ai_platform.investment.decision.reasoning.reasoning_snapshot import (
    ReasoningSnapshot, build_reasoning_snapshot,
)
from enterprise_ai_platform.investment.decision.reasoning.reasoning_history import ReasoningHistory
from enterprise_ai_platform.investment.decision.reasoning.reasoning_statistics import (
    ReasoningStatistics, ReasoningStatisticsTracker,
)
from enterprise_ai_platform.investment.decision.reasoning.decision_reasoning_engine import DecisionReasoningEngine

__all__ = [
    # constants
    "ReasoningStepType", "SignalDirection", "HypothesisType", "HypothesisStatus",
    "ArgumentType", "ArgumentStrengthLevel", "RelationshipType",
    "LogicValidationStatus", "ReasoningStatus", "ReasoningEngineStatus",
    "ReasoningQualityDimension",
    "BULLISH_SIGNAL_THRESHOLD", "BEARISH_SIGNAL_THRESHOLD",
    "DEFAULT_REASONING_TIMEOUT_SECS",
    # models
    "ReasoningStep", "make_step", "ReasoningChain", "build_chain",
    "InterpretedSignal", "ContextProfile",
    "Relationship", "RelationshipMap",
    "Hypothesis", "HypothesisValidationResult",
    "Argument", "ArgumentStrengthSummary", "ArgumentReport",
    "TraceEntry",
    "LogicValidationResult",
    "ReasoningQualityScore", "compute_reasoning_score",
    "ReasoningConfidenceScore",
    "HealthReport",
    "ReasoningContext", "PipelineResult",
    "ReasoningSnapshot", "build_reasoning_snapshot",
    "ReasoningStatistics",
    # engines
    "EvidenceInterpreter", "ContextAnalyzer", "SignalInterpreter", "RelationshipMapper",
    "HypothesisEngine", "HypothesisRegistry", "HypothesisValidator", "HypothesisHistory",
    "SupportingArguments", "OpposingArguments", "ArgumentStrength", "ArgumentEngine",
    "ReasoningTrace", "DecisionLogic", "LogicValidator",
    "ReasoningQuality", "ReasoningConfidence", "ReasoningHealth",
    "BaseReasoningModule", "ReasoningPipeline",
    "ReasoningHistory", "ReasoningStatisticsTracker",
    "DecisionReasoningEngine",
]
