"""iios/investment/decision/confidence/__init__.py
Public surface of the Institutional Decision Confidence Engine.
"""
from iios.investment.decision.confidence.confidence_constants import (
    CalibrationStatus,
    ConfidenceDimension,
    ConfidenceEngineStatus,
    ConfidenceLevel,
    ConfidenceQualityGrade,
    DriftSeverity,
    EvidenceConfidenceFactor,
    ReasoningConfidenceFactor,
    TrendDirection,
    EVIDENCE_DIM_WEIGHT,
    REASONING_DIM_WEIGHT,
    SCORING_DIM_WEIGHT,
    HISTORICAL_DIM_WEIGHT,
    CALIBRATION_DIM_WEIGHT,
    HIGH_CONFIDENCE_THRESHOLD,
    MIN_CALIBRATION_SAMPLES,
)
from iios.investment.decision.confidence.decision_confidence import (
    DecisionConfidence,
    build_decision_confidence,
)
from iios.investment.decision.confidence.confidence_snapshot import (
    ConfidenceSnapshot,
    build_confidence_snapshot,
)
from iios.investment.decision.confidence.confidence_history import ConfidenceHistory
from iios.investment.decision.confidence.confidence_statistics import (
    ConfidenceStatistics,
    ConfidenceStatisticsTracker,
)
from iios.investment.decision.confidence.evidence_confidence import (
    EvidenceConfidenceEstimator,
    EvidenceConfidenceResult,
)
from iios.investment.decision.confidence.source_reliability import (
    SourceReliabilityAnalyzer,
    SourceReliabilityScore,
)
from iios.investment.decision.confidence.freshness_analysis import (
    FreshnessAnalyzer,
    FreshnessResult,
)
from iios.investment.decision.confidence.coverage_analysis import (
    CoverageAnalyzer,
    CoverageResult,
)
from iios.investment.decision.confidence.reasoning_confidence import (
    ReasoningConfidenceEstimator,
    ReasoningConfidenceResult,
)
from iios.investment.decision.confidence.reasoning_consistency import (
    ConsistencyResult,
    ReasoningConsistencyAnalyzer,
)
from iios.investment.decision.confidence.logic_strength import (
    LogicStrengthAnalyzer,
    LogicStrengthResult,
)
from iios.investment.decision.confidence.contradiction_analysis import (
    ContradictionAnalyzer,
    ContradictionResult,
)
from iios.investment.decision.confidence.historical_confidence import (
    HistoricalConfidenceAnalyzer,
    HistoricalConfidenceResult,
)
from iios.investment.decision.confidence.confidence_trends import (
    ConfidenceTrendAnalyzer,
    TrendResult,
)
from iios.investment.decision.confidence.confidence_evolution import (
    ConfidenceEvolutionTracker,
    EvolutionRecord,
    EvolutionResult,
)
from iios.investment.decision.confidence.confidence_drift import (
    ConfidenceDriftDetector,
    DriftResult,
)
from iios.investment.decision.confidence.confidence_calibrator import (
    CalibrationBucket,
    CalibrationRecord,
    ConfidenceCalibrator,
)
from iios.investment.decision.confidence.calibration_engine import (
    CalibrationEngine,
    CalibrationResult,
)
from iios.investment.decision.confidence.calibration_statistics import (
    CalibrationStats,
    CalibrationStatisticsTracker,
)
from iios.investment.decision.confidence.confidence_validator import (
    ConfidenceValidationResult,
    ConfidenceValidator,
)
from iios.investment.decision.confidence.overall_confidence import (
    OverallConfidenceEstimator,
    OverallConfidenceResult,
)
from iios.investment.decision.confidence.confidence_score import (
    ConfidenceScore,
    compute_confidence_score,
)
from iios.investment.decision.confidence.confidence_quality import (
    ConfidenceQualityEvaluator,
    ConfidenceQualityReport,
)
from iios.investment.decision.confidence.confidence_health import (
    ConfidenceHealthMonitor,
    ConfidenceHealthReport,
)
from iios.investment.decision.confidence.confidence_pipeline import (
    BaseConfidenceModule,
    ConfidenceContext,
    ConfidencePipeline,
    PipelineResult,
    ScoringSnapshotProtocol,
)
from iios.investment.decision.confidence.decision_confidence_engine import (
    DecisionConfidenceEngine,
)

__all__ = [
    # Constants
    "CalibrationStatus",
    "ConfidenceDimension",
    "ConfidenceEngineStatus",
    "ConfidenceLevel",
    "ConfidenceQualityGrade",
    "DriftSeverity",
    "EvidenceConfidenceFactor",
    "ReasoningConfidenceFactor",
    "TrendDirection",
    "EVIDENCE_DIM_WEIGHT",
    "REASONING_DIM_WEIGHT",
    "SCORING_DIM_WEIGHT",
    "HISTORICAL_DIM_WEIGHT",
    "CALIBRATION_DIM_WEIGHT",
    "HIGH_CONFIDENCE_THRESHOLD",
    "MIN_CALIBRATION_SAMPLES",
    # Core models
    "DecisionConfidence",
    "build_decision_confidence",
    "ConfidenceSnapshot",
    "build_confidence_snapshot",
    "ConfidenceHistory",
    "ConfidenceStatistics",
    "ConfidenceStatisticsTracker",
    # Evidence confidence
    "EvidenceConfidenceEstimator",
    "EvidenceConfidenceResult",
    "SourceReliabilityAnalyzer",
    "SourceReliabilityScore",
    "FreshnessAnalyzer",
    "FreshnessResult",
    "CoverageAnalyzer",
    "CoverageResult",
    # Reasoning confidence
    "ReasoningConfidenceEstimator",
    "ReasoningConfidenceResult",
    "ConsistencyResult",
    "ReasoningConsistencyAnalyzer",
    "LogicStrengthAnalyzer",
    "LogicStrengthResult",
    "ContradictionAnalyzer",
    "ContradictionResult",
    # Historical confidence
    "HistoricalConfidenceAnalyzer",
    "HistoricalConfidenceResult",
    "ConfidenceTrendAnalyzer",
    "TrendResult",
    "ConfidenceEvolutionTracker",
    "EvolutionRecord",
    "EvolutionResult",
    "ConfidenceDriftDetector",
    "DriftResult",
    # Calibration
    "CalibrationBucket",
    "CalibrationRecord",
    "ConfidenceCalibrator",
    "CalibrationEngine",
    "CalibrationResult",
    "CalibrationStats",
    "CalibrationStatisticsTracker",
    # Validation + quality
    "ConfidenceValidationResult",
    "ConfidenceValidator",
    "ConfidenceQualityEvaluator",
    "ConfidenceQualityReport",
    # Overall + score
    "OverallConfidenceEstimator",
    "OverallConfidenceResult",
    "ConfidenceScore",
    "compute_confidence_score",
    # Health
    "ConfidenceHealthMonitor",
    "ConfidenceHealthReport",
    # Pipeline
    "BaseConfidenceModule",
    "ConfidenceContext",
    "ConfidencePipeline",
    "PipelineResult",
    "ScoringSnapshotProtocol",
    # Engine
    "DecisionConfidenceEngine",
]
