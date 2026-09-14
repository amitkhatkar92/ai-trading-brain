"""learning_exceptions.py — Exception hierarchy for the AI Learning & Model Training Framework."""
from __future__ import annotations


class LearningError(Exception):
    """Root exception for the Learning Framework. Code ML-000."""
    code = "ML-000"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self})"


# ── Engine lifecycle ──────────────────────────────────────────────────────────

class EngineNotRunningError(LearningError):
    """Engine must be started before use. Code ML-001."""
    code = "ML-001"


class EngineAlreadyRunningError(LearningError):
    """Engine is already running. Code ML-002."""
    code = "ML-002"


class EngineInitializationError(LearningError):
    """Engine failed to initialize. Code ML-003."""
    code = "ML-003"


# ── Training jobs ─────────────────────────────────────────────────────────────

class JobNotFoundError(LearningError):
    """Training job not found. Code ML-010."""
    code = "ML-010"


class JobAlreadyExistsError(LearningError):
    """A job with this ID already exists. Code ML-011."""
    code = "ML-011"


class JobStateError(LearningError):
    """Invalid job state transition. Code ML-012."""
    code = "ML-012"


class JobCapacityError(LearningError):
    """Maximum job registry capacity reached. Code ML-013."""
    code = "ML-013"


class JobFailedError(LearningError):
    """Training job failed during execution. Code ML-014."""
    code = "ML-014"


# ── Datasets ──────────────────────────────────────────────────────────────────

class DatasetError(LearningError):
    """Generic dataset error. Code ML-020."""
    code = "ML-020"


class DatasetNotFoundError(LearningError):
    """Dataset not found. Code ML-021."""
    code = "ML-021"


class DatasetVersionError(LearningError):
    """Dataset version error. Code ML-022."""
    code = "ML-022"


class InsufficientDataError(LearningError):
    """Not enough records in the dataset. Code ML-023."""
    code = "ML-023"


class DataValidationError(LearningError):
    """Dataset failed validation. Code ML-024."""
    code = "ML-024"


# ── Features ──────────────────────────────────────────────────────────────────

class FeatureError(LearningError):
    """Generic feature error. Code ML-030."""
    code = "ML-030"


class FeatureNotFoundError(LearningError):
    """Feature not found in registry. Code ML-031."""
    code = "ML-031"


class FeaturePipelineError(LearningError):
    """Feature pipeline execution error. Code ML-032."""
    code = "ML-032"


class FeatureValidationError(LearningError):
    """Feature validation failed. Code ML-033."""
    code = "ML-033"


# ── Models ────────────────────────────────────────────────────────────────────

class ModelError(LearningError):
    """Generic model error. Code ML-040."""
    code = "ML-040"


class ModelNotFoundError(LearningError):
    """Model not found in registry. Code ML-041."""
    code = "ML-041"


class ModelVersionError(LearningError):
    """Model version error. Code ML-042."""
    code = "ML-042"


class ModelValidationError(LearningError):
    """Model failed validation. Code ML-043."""
    code = "ML-043"


# ── Training ──────────────────────────────────────────────────────────────────

class TrainingError(LearningError):
    """Training execution error. Code ML-050."""
    code = "ML-050"


class CheckpointError(LearningError):
    """Checkpoint error. Code ML-051."""
    code = "ML-051"


# ── Evaluation ────────────────────────────────────────────────────────────────

class EvaluationError(LearningError):
    """Evaluation error. Code ML-060."""
    code = "ML-060"


class MetricsError(LearningError):
    """Metrics computation error. Code ML-061."""
    code = "ML-061"


# ── Deployment ────────────────────────────────────────────────────────────────

class DeploymentError(LearningError):
    """Deployment error. Code ML-070."""
    code = "ML-070"


class DeploymentConflictError(LearningError):
    """A conflicting deployment already exists. Code ML-071."""
    code = "ML-071"


class DeploymentNotFoundError(LearningError):
    """Deployment not found. Code ML-072."""
    code = "ML-072"


# ── Monitoring & drift ────────────────────────────────────────────────────────

class MonitoringError(LearningError):
    """Monitoring error. Code ML-080."""
    code = "ML-080"


class DriftDetectedError(LearningError):
    """Significant drift was detected above threshold. Code ML-081."""
    code = "ML-081"


# ── Experiments ───────────────────────────────────────────────────────────────

class ExperimentError(LearningError):
    """Experiment tracking error. Code ML-090."""
    code = "ML-090"


class ExperimentNotFoundError(LearningError):
    """Experiment not found. Code ML-091."""
    code = "ML-091"
