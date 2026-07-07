"""
iios/observation/quality/__init__.py
=====================================
Public surface of the Observation Quality Engine.
"""
from __future__ import annotations

# ── Legacy simple assessor (kept for backward compat) ─────────────────────────
from .observation_quality import (
    QualityDimension,
    ObservationQualityScore,
    ObservationQualityAssessor,
    get_quality_assessor,
    reset_quality_assessor,
)

# ── Extended quality score model ──────────────────────────────────────────────
from .quality_score import (
    DimensionScore, QualityScore, quality_tier, DEFAULT_WEIGHTS,
)

# ── Dimension assessors ───────────────────────────────────────────────────────
from .quality_assessment import (
    DimensionAssessor,
    CompletenessAssessor, AccuracyAssessor, ConsistencyAssessor,
    TimelinessAssessor,   ReliabilityAssessor, SourceTrustAssessor,
    FreshnessAssessor,    IntegrityAssessor,
)

# ── Aggregate metrics ─────────────────────────────────────────────────────────
from .quality_metrics import (
    MetricWindow, QualityMetrics, get_quality_metrics, reset_quality_metrics,
)

# ── Engine ────────────────────────────────────────────────────────────────────
from .quality_engine import (
    QualityEngine, get_quality_engine, reset_quality_engine,
)

# ── Manager (policy) ──────────────────────────────────────────────────────────
from .quality_manager import (
    QualityPolicy, QualityDecision, QualityManager,
    get_quality_manager, reset_quality_manager,
)

# ── Reporting ─────────────────────────────────────────────────────────────────
from .quality_report import (
    QualityReportSection, QualityReportDocument, QualityReporter,
    get_quality_reporter, reset_quality_reporter,
)
