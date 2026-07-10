"""iios/integration/history/__init__.py

Public API for the Historical Data & Replay Framework.
"""
# Singleton entry-points
from iios.integration.history.historical_data_engine import (
    HistoricalDataEngine,
    get_historical_data_engine,
    reset_historical_data_engine,
)

# Constants (key ones)
from iios.integration.history.history_constants import (
    HistoricalDataType,
    DataFormat,
    CompressionType,
    PartitionStrategy,
    DatasetStatus,
    StorageStatus,
    ReplayMode,
    ReplayStatus,
    ReplayType,
    TimelineDirection,
    TimelineStatus,
    SimulationMode,
    SimulationStatus,
    QueryOperator,
    SortOrder,
    HistoryEngineStatus,
    HISTORY_ENGINE_VERSION,
    HISTORY_ERROR_PREFIX,
)

# Exceptions (key ones)
from iios.integration.history.history_exceptions import (
    HistoryDataError,
    HistoryEngineNotRunningError,
    HistoryEngineAlreadyRunningError,
    HistoryEngineInitializationError,
    StorageError,
    DatasetNotFoundError,
    DatasetAlreadyExistsError,
    DatasetValidationError,
    ReplayError,
    ReplaySessionNotFoundError,
    QueryError,
    QueryTimeoutError,
    QueryValidationError,
    SimulationError,
    SimulationNotActiveError,
    ScenarioNotFoundError,
)

# Core models
from iios.integration.history.core import (
    HistoricalRecord,
    HistoricalDataset,
    HistoricalSnapshot,
    HistoricalPartition,
    HistoricalIndex,
)

# Query
from iios.integration.history.query import (
    HistoricalFilter,
    FieldFilter,
    QueryEngine,
)

# Replay
from iios.integration.history.replay import ReplayEngine

# Simulation
from iios.integration.history.simulation import (
    Scenario,
    ScenarioLoader,
    SimulationController,
)

__all__ = [
    # Entry-points
    "HistoricalDataEngine",
    "get_historical_data_engine",
    "reset_historical_data_engine",
    # Core models
    "HistoricalRecord",
    "HistoricalDataset",
    "HistoricalSnapshot",
    "HistoricalPartition",
    "HistoricalIndex",
    # Query
    "HistoricalFilter",
    "FieldFilter",
    "QueryEngine",
    # Replay
    "ReplayEngine",
    # Simulation
    "Scenario",
    "ScenarioLoader",
    "SimulationController",
]
