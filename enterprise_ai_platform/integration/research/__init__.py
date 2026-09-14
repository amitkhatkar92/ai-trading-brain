"""enterprise_ai_platform/integration/research/__init__.py

Public API for the Quantitative Research Framework.
"""
# Singleton entry-points
from enterprise_ai_platform.integration.research.research_engine import (
    ResearchEngine,
    get_research_engine,
    reset_research_engine,
)

# Constants
from enterprise_ai_platform.integration.research.research_constants import (
    ExperimentPriority,
    ExperimentStatus,
    ResearchDatasetStatus,
    ResearchEngineStatus,
    ResearchEventType,
    ResearchProjectStatus,
    ResearchSessionStatus,
    WorkflowStatus,
    RESEARCH_ENGINE_VERSION,
    RESEARCH_ERROR_PREFIX,
)

# Exceptions
from enterprise_ai_platform.integration.research.research_exceptions import (
    ResearchError,
    ResearchEngineNotRunningError,
    ResearchEngineAlreadyRunningError,
    ResearchProjectNotFoundError,
    ResearchExperimentNotFoundError,
    ResearchDatasetNotFoundError,
    ExperimentStateError,
    ExperimentAlreadyRunningError,
    ExperimentNotRunningError,
    WorkflowError,
)

# Core models
from enterprise_ai_platform.integration.research.core import (
    ResearchProject,
    ResearchExperiment,
    ResearchDataset,
    ResearchSession,
    ResearchResult,
    ResearchStatistics,
    ResearchHistory,
    ResearchHistoryEntry,
    ResearchMetadata,
)

# Sub-components
from enterprise_ai_platform.integration.research.experiments import ExperimentLifecycle, ExperimentRunner
from enterprise_ai_platform.integration.research.workflow    import ResearchWorkflow, WorkflowStep

__all__ = [
    "ResearchEngine",
    "get_research_engine",
    "reset_research_engine",
    "ResearchProject",
    "ResearchExperiment",
    "ResearchDataset",
    "ResearchSession",
    "ResearchResult",
    "ResearchStatistics",
    "ExperimentLifecycle",
    "ExperimentRunner",
    "ResearchWorkflow",
    "WorkflowStep",
]
