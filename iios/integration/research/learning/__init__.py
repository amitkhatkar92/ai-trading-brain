"""learning/__init__.py — Public API for the AI Learning & Model Training Framework."""
from iios.integration.research.learning.learning_constants import (
    JobStatus,
    LearningEngineStatus,
    ModelStatus,
    LearningType,
    ModelTask,
    DataSplitStrategy,
    FeatureType,
    DeploymentStatus,
    DeploymentStrategy,
    DriftType,
    AlertSeverity,
    ValidationStatus,
    ExperimentStatus,
    CheckpointStatus,
    LEARNING_ENGINE_VERSION,
)
from iios.integration.research.learning.learning_exceptions import (
    LearningError,
    EngineNotRunningError,
    EngineAlreadyRunningError,
    EngineInitializationError,
    JobNotFoundError,
    JobAlreadyExistsError,
    JobStateError,
    JobCapacityError,
    JobFailedError,
    DatasetError,
    DatasetNotFoundError,
    InsufficientDataError,
    DataValidationError,
    FeatureError,
    FeatureNotFoundError,
    FeaturePipelineError,
    FeatureValidationError,
    ModelError,
    ModelNotFoundError,
    ModelVersionError,
    ModelValidationError,
    TrainingError,
    CheckpointError,
    EvaluationError,
    DeploymentError,
    DeploymentConflictError,
    DeploymentNotFoundError,
    MonitoringError,
    DriftDetectedError,
    ExperimentError,
    ExperimentNotFoundError,
)
from iios.integration.research.learning.learning_engine import (
    LearningEngine,
    get_learning_engine,
    reset_learning_engine,
)
from iios.integration.research.learning.core.learning_configuration import LearningConfiguration
from iios.integration.research.learning.core.training_result        import TrainingResult
from iios.integration.research.learning.core.experiment             import Experiment
from iios.integration.research.learning.core.learning_history       import LearningHistory, LearningHistoryEntry
from iios.integration.research.learning.datasets.training_dataset   import (
    DatasetRecord,
    TrainingDataset,
    ValidationDataset,
    TestDataset,
)
from iios.integration.research.learning.features.feature_definition  import FeatureDefinition
from iios.integration.research.learning.features.feature_transformer import FeatureTransformerProtocol
from iios.integration.research.learning.features.feature_pipeline    import FeaturePipeline
from iios.integration.research.learning.models.base_model            import BaseModel
from iios.integration.research.learning.models.model_metadata        import ModelMetadata
from iios.integration.research.learning.training.training_job        import TrainingJob
from iios.integration.research.learning.evaluation.metrics_engine    import MetricsEngine
from iios.integration.research.learning.evaluation.evaluation_report import EvaluationReport
from iios.integration.research.learning.deployment.deployment_registry import DeploymentRecord
from iios.integration.research.learning.drift.drift_detector        import DriftDetector, DriftResult

__version__ = LEARNING_ENGINE_VERSION

__all__ = [
    # Engine
    "LearningEngine",
    "get_learning_engine",
    "reset_learning_engine",
    # Enums
    "JobStatus",
    "LearningEngineStatus",
    "ModelStatus",
    "LearningType",
    "ModelTask",
    "DataSplitStrategy",
    "FeatureType",
    "DeploymentStatus",
    "DeploymentStrategy",
    "DriftType",
    "AlertSeverity",
    "ValidationStatus",
    "ExperimentStatus",
    "CheckpointStatus",
    # Exceptions
    "LearningError",
    "EngineNotRunningError",
    "EngineAlreadyRunningError",
    "JobNotFoundError",
    "JobStateError",
    "DatasetNotFoundError",
    "InsufficientDataError",
    "ModelNotFoundError",
    "TrainingError",
    "EvaluationError",
    "DeploymentError",
    "DriftDetectedError",
    "ExperimentError",
    # Core entities
    "LearningConfiguration",
    "TrainingResult",
    "Experiment",
    "LearningHistory",
    # Datasets
    "DatasetRecord",
    "TrainingDataset",
    "ValidationDataset",
    "TestDataset",
    # Features
    "FeatureDefinition",
    "FeatureTransformerProtocol",
    "FeaturePipeline",
    # Models
    "BaseModel",
    "ModelMetadata",
    # Training
    "TrainingJob",
    # Evaluation
    "MetricsEngine",
    "EvaluationReport",
    # Deployment
    "DeploymentRecord",
    # Drift
    "DriftDetector",
    "DriftResult",
]
