"""
learning_evaluation_exceptions.py -- iios.ai.learning_evaluation.exceptions
=============================================================================
A7 exception hierarchy.  All exceptions extend :class:`AIException` from A1.

Error code range: AI-1200 – AI-1299

Hierarchy
---------
AIException (A1)
└── AILearningEvaluationException      AI-1200  base
    ├── AIEvaluationSessionNotFoundError         AI-1201
    ├── AIEvaluationSessionAlreadyExistsError    AI-1202
    ├── AIEvaluationSessionClosedError           AI-1203
    ├── AIEvaluationRequestNotFoundError         AI-1204
    ├── AIEvaluationValidationError              AI-1205
    ├── AIBenchmarkException                     AI-1210  base benchmark
    │   ├── AIBenchmarkNotFoundError             AI-1211
    │   ├── AIBenchmarkSuiteNotFoundError        AI-1212
    │   ├── AIBenchmarkAlreadyRunningError       AI-1213
    │   └── AIBenchmarkScenarioError             AI-1214
    ├── AILearningException                      AI-1220  base learning
    │   ├── AILearningRecordNotFoundError        AI-1221
    │   ├── AIFeedbackException                  AI-1222
    │   └── AIImprovementException               AI-1223
    ├── AIQualityException                       AI-1230  base quality
    │   ├── AIQualityRuleViolationError          AI-1231
    │   ├── AIQualityAssessmentError             AI-1232
    │   └── AIValidationException                AI-1233
    ├── AIMetricsException                       AI-1240  base metrics
    │   └── AIMetricsCalculationError            AI-1241
    └── AILearningEvaluationPolicyException      AI-1250  base policy
        └── AILearningEvaluationPolicyViolationError  AI-1251

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class AILearningEvaluationException(AIException):
    """Base exception for A7 Learning & Evaluation Platform (AI-1200)."""

    def __init__(self, message: str = "Learning evaluation error", code: str = "AI-1200") -> None:
        super().__init__(message, code=code)


# ---------------------------------------------------------------------------
# Evaluation errors  AI-1201–AI-1205
# ---------------------------------------------------------------------------

class AIEvaluationSessionNotFoundError(AILearningEvaluationException):
    """Evaluation session not found (AI-1201)."""
    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Evaluation session not found: {session_id!r}" if session_id else "Evaluation session not found",
            code="AI-1201",
        )


class AIEvaluationSessionAlreadyExistsError(AILearningEvaluationException):
    """Evaluation session already exists (AI-1202)."""
    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Evaluation session already exists: {session_id!r}" if session_id else "Evaluation session already exists",
            code="AI-1202",
        )


class AIEvaluationSessionClosedError(AILearningEvaluationException):
    """Operation on closed evaluation session (AI-1203)."""
    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Evaluation session is closed: {session_id!r}" if session_id else "Evaluation session is closed",
            code="AI-1203",
        )


class AIEvaluationRequestNotFoundError(AILearningEvaluationException):
    """Evaluation request not found (AI-1204)."""
    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            f"Evaluation request not found: {request_id!r}" if request_id else "Evaluation request not found",
            code="AI-1204",
        )


class AIEvaluationValidationError(AILearningEvaluationException):
    """Evaluation request failed validation (AI-1205)."""
    def __init__(self, message: str = "Evaluation validation failed") -> None:
        super().__init__(message, code="AI-1205")


# ---------------------------------------------------------------------------
# Benchmark errors  AI-1210–AI-1214
# ---------------------------------------------------------------------------

class AIBenchmarkException(AILearningEvaluationException):
    """Base benchmark exception (AI-1210)."""
    def __init__(self, message: str = "Benchmark error", code: str = "AI-1210") -> None:
        super().__init__(message, code=code)


class AIBenchmarkNotFoundError(AIBenchmarkException):
    """Benchmark not found (AI-1211)."""
    def __init__(self, benchmark_id: str = "") -> None:
        super().__init__(
            f"Benchmark not found: {benchmark_id!r}" if benchmark_id else "Benchmark not found",
            code="AI-1211",
        )


class AIBenchmarkSuiteNotFoundError(AIBenchmarkException):
    """Benchmark suite not found (AI-1212)."""
    def __init__(self, suite_id: str = "") -> None:
        super().__init__(
            f"Benchmark suite not found: {suite_id!r}" if suite_id else "Benchmark suite not found",
            code="AI-1212",
        )


class AIBenchmarkAlreadyRunningError(AIBenchmarkException):
    """Benchmark is already running (AI-1213)."""
    def __init__(self, benchmark_id: str = "") -> None:
        super().__init__(
            f"Benchmark already running: {benchmark_id!r}" if benchmark_id else "Benchmark already running",
            code="AI-1213",
        )


class AIBenchmarkScenarioError(AIBenchmarkException):
    """Benchmark scenario execution error (AI-1214)."""
    def __init__(self, message: str = "Benchmark scenario error") -> None:
        super().__init__(message, code="AI-1214")


# ---------------------------------------------------------------------------
# Learning errors  AI-1220–AI-1223
# ---------------------------------------------------------------------------

class AILearningException(AILearningEvaluationException):
    """Base learning exception (AI-1220)."""
    def __init__(self, message: str = "Learning error", code: str = "AI-1220") -> None:
        super().__init__(message, code=code)


class AILearningRecordNotFoundError(AILearningException):
    """Learning record not found (AI-1221)."""
    def __init__(self, record_id: str = "") -> None:
        super().__init__(
            f"Learning record not found: {record_id!r}" if record_id else "Learning record not found",
            code="AI-1221",
        )


class AIFeedbackException(AILearningException):
    """Feedback processing error (AI-1222)."""
    def __init__(self, message: str = "Feedback error") -> None:
        super().__init__(message, code="AI-1222")


class AIImprovementException(AILearningException):
    """Improvement recommendation error (AI-1223)."""
    def __init__(self, message: str = "Improvement error") -> None:
        super().__init__(message, code="AI-1223")


# ---------------------------------------------------------------------------
# Quality errors  AI-1230–AI-1233
# ---------------------------------------------------------------------------

class AIQualityException(AILearningEvaluationException):
    """Base quality exception (AI-1230)."""
    def __init__(self, message: str = "Quality error", code: str = "AI-1230") -> None:
        super().__init__(message, code=code)


class AIQualityRuleViolationError(AIQualityException):
    """Output violated a quality rule (AI-1231)."""
    def __init__(self, rule_name: str = "") -> None:
        super().__init__(
            f"Quality rule violated: {rule_name!r}" if rule_name else "Quality rule violated",
            code="AI-1231",
        )


class AIQualityAssessmentError(AIQualityException):
    """Quality assessment could not be completed (AI-1232)."""
    def __init__(self, message: str = "Quality assessment error") -> None:
        super().__init__(message, code="AI-1232")


class AIValidationException(AIQualityException):
    """Validation pipeline error (AI-1233)."""
    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(message, code="AI-1233")


# ---------------------------------------------------------------------------
# Metrics errors  AI-1240–AI-1241
# ---------------------------------------------------------------------------

class AIMetricsException(AILearningEvaluationException):
    """Base metrics exception (AI-1240)."""
    def __init__(self, message: str = "Metrics error", code: str = "AI-1240") -> None:
        super().__init__(message, code=code)


class AIMetricsCalculationError(AIMetricsException):
    """Metric calculation failed (AI-1241)."""
    def __init__(self, metric_name: str = "") -> None:
        super().__init__(
            f"Metrics calculation failed for: {metric_name!r}" if metric_name else "Metrics calculation failed",
            code="AI-1241",
        )


# ---------------------------------------------------------------------------
# Policy errors  AI-1250–AI-1251
# ---------------------------------------------------------------------------

class AILearningEvaluationPolicyException(AILearningEvaluationException):
    """Base policy exception (AI-1250)."""
    def __init__(self, message: str = "Policy error", code: str = "AI-1250") -> None:
        super().__init__(message, code=code)


class AILearningEvaluationPolicyViolationError(AILearningEvaluationPolicyException):
    """Policy violation (AI-1251)."""
    def __init__(self, message: str = "Policy violation") -> None:
        super().__init__(message, code="AI-1251")
