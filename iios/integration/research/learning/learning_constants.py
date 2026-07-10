"""learning_constants.py — Enumerations and scalar constants for the AI Learning & Model Training Framework."""
from __future__ import annotations

from enum import Enum


# ── Job / engine status ───────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    PAUSED    = "paused"


class LearningEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Model lifecycle ───────────────────────────────────────────────────────────

class ModelStatus(str, Enum):
    DRAFT       = "draft"
    TRAINING    = "training"
    TRAINED     = "trained"
    VALIDATED   = "validated"
    DEPLOYED    = "deployed"
    ARCHIVED    = "archived"
    DEPRECATED  = "deprecated"


# ── Learning paradigm ─────────────────────────────────────────────────────────

class LearningType(str, Enum):
    SUPERVISED       = "supervised"
    UNSUPERVISED     = "unsupervised"
    SEMI_SUPERVISED  = "semi_supervised"
    REINFORCEMENT    = "reinforcement"
    HYBRID           = "hybrid"
    SELF_SUPERVISED  = "self_supervised"


class ModelTask(str, Enum):
    CLASSIFICATION     = "classification"
    REGRESSION         = "regression"
    RANKING            = "ranking"
    FORECASTING        = "forecasting"
    CLUSTERING         = "clustering"
    ANOMALY_DETECTION  = "anomaly_detection"
    REINFORCEMENT      = "reinforcement"
    ENSEMBLE           = "ensemble"
    CUSTOM             = "custom"


# ── Dataset / feature enumerations ────────────────────────────────────────────

class DataSplitStrategy(str, Enum):
    RANDOM         = "random"
    TIME_SERIES    = "time_series"
    WALK_FORWARD   = "walk_forward"
    STRATIFIED     = "stratified"
    GROUP_K_FOLD   = "group_k_fold"


class FeatureType(str, Enum):
    NUMERIC      = "numeric"
    CATEGORICAL  = "categorical"
    BOOLEAN      = "boolean"
    TEMPORAL     = "temporal"
    TEXT         = "text"
    EMBEDDING    = "embedding"
    CUSTOM       = "custom"


# ── Deployment enumerations ───────────────────────────────────────────────────

class DeploymentStatus(str, Enum):
    INACTIVE    = "inactive"
    SHADOW      = "shadow"
    CHAMPION    = "champion"
    CHALLENGER  = "challenger"
    RETIRED     = "retired"


class DeploymentStrategy(str, Enum):
    DIRECT              = "direct"
    SHADOW              = "shadow"
    CHAMPION_CHALLENGER = "champion_challenger"
    CANARY              = "canary"
    BLUE_GREEN          = "blue_green"


# ── Monitoring / drift enumerations ──────────────────────────────────────────

class DriftType(str, Enum):
    DATA_DRIFT        = "data_drift"
    CONCEPT_DRIFT     = "concept_drift"
    PERFORMANCE_DRIFT = "performance_drift"
    PREDICTION_DRIFT  = "prediction_drift"


class AlertSeverity(str, Enum):
    INFO      = "info"
    WARNING   = "warning"
    CRITICAL  = "critical"
    EMERGENCY = "emergency"


# ── Evaluation / experiment enumerations ─────────────────────────────────────

class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"


class ExperimentStatus(str, Enum):
    ACTIVE    = "active"
    COMPLETED = "completed"
    FAILED    = "failed"
    ARCHIVED  = "archived"


class CheckpointStatus(str, Enum):
    CREATED = "created"
    VALID   = "valid"
    CORRUPT = "corrupt"
    DELETED = "deleted"


# ── Scalar constants ──────────────────────────────────────────────────────────

LEARNING_ENGINE_VERSION      = "1.0.0"
ML_ERROR_PREFIX              = "ML"

DEFAULT_TRAIN_SPLIT          = 0.70
DEFAULT_VAL_SPLIT            = 0.15
DEFAULT_TEST_SPLIT           = 0.15
DEFAULT_MAX_JOBS             = 10_000
DEFAULT_MAX_MODELS           = 50_000
DEFAULT_MAX_DATASETS         = 10_000
DEFAULT_MAX_EXPERIMENTS      = 10_000
DEFAULT_MAX_DEPLOYMENTS      = 10_000
DEFAULT_MAX_CHECKPOINTS      = 100    # per job
DEFAULT_EARLY_STOP_PATIENCE  = 10
DEFAULT_MAX_EPOCHS           = 1_000
DEFAULT_BATCH_SIZE           = 32
DEFAULT_LEARNING_RATE        = 1e-3
DEFAULT_RANDOM_SEED          = 42
DEFAULT_HISTORY_MAX_ENTRIES  = 100_000
PSI_DRIFT_THRESHOLD          = 0.20   # PSI > 0.20 = significant drift
MEAN_SHIFT_THRESHOLD         = 2.0    # standard deviations
DEFAULT_CV_FOLDS             = 5
MIN_DATASET_SIZE             = 10     # minimum records for any split
