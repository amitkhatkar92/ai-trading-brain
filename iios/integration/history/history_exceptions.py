"""iios/integration/history/history_exceptions.py

Exception hierarchy for the Historical Data & Replay Framework.
Error-code prefix: HD
"""
from __future__ import annotations


class HistoryDataError(Exception):
    """Root exception for all historical data framework errors."""
    code: str = "HD-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.code}: {self})"


# ── Engine errors  HD-001 – HD-009 ────────────────────────────────────────────

class HistoryEngineNotRunningError(HistoryDataError):
    code = "HD-001"

class HistoryEngineAlreadyRunningError(HistoryDataError):
    code = "HD-002"

class HistoryEngineInitializationError(HistoryDataError):
    code = "HD-003"


# ── Storage errors  HD-010 – HD-019 ───────────────────────────────────────────

class StorageError(HistoryDataError):
    code = "HD-010"

class StorageNotFoundError(HistoryDataError):
    code = "HD-011"

class StorageCapacityError(HistoryDataError):
    code = "HD-012"

class StorageCorruptionError(HistoryDataError):
    code = "HD-013"

class StorageIOError(HistoryDataError):
    code = "HD-014"


# ── Dataset errors  HD-020 – HD-029 ───────────────────────────────────────────

class DatasetNotFoundError(HistoryDataError):
    code = "HD-020"

class DatasetAlreadyExistsError(HistoryDataError):
    code = "HD-021"

class DatasetValidationError(HistoryDataError):
    code = "HD-022"

class DatasetCapacityError(HistoryDataError):
    code = "HD-023"

class DatasetLockedError(HistoryDataError):
    code = "HD-024"

class PartitionNotFoundError(HistoryDataError):
    code = "HD-025"

class ChecksumMismatchError(HistoryDataError):
    code = "HD-026"


# ── Replay errors  HD-030 – HD-039 ────────────────────────────────────────────

class ReplayError(HistoryDataError):
    code = "HD-030"

class ReplaySessionNotFoundError(HistoryDataError):
    code = "HD-031"

class ReplayAlreadyActiveError(HistoryDataError):
    code = "HD-032"

class ReplayNotActiveError(HistoryDataError):
    code = "HD-033"

class ReplaySpeedError(HistoryDataError):
    code = "HD-034"

class ReplayTimeRangeError(HistoryDataError):
    code = "HD-035"


# ── Timeline errors  HD-040 – HD-049 ──────────────────────────────────────────

class TimelineError(HistoryDataError):
    code = "HD-040"

class TimelineNotActiveError(HistoryDataError):
    code = "HD-041"

class TimelineSeekError(HistoryDataError):
    code = "HD-042"

class TimelineOverflowError(HistoryDataError):
    code = "HD-043"


# ── Query errors  HD-050 – HD-059 ─────────────────────────────────────────────

class QueryError(HistoryDataError):
    code = "HD-050"

class QueryTimeoutError(HistoryDataError):
    code = "HD-051"

class QueryValidationError(HistoryDataError):
    code = "HD-052"

class QueryResultTooLargeError(HistoryDataError):
    code = "HD-053"


# ── Simulation errors  HD-060 – HD-069 ────────────────────────────────────────

class SimulationError(HistoryDataError):
    code = "HD-060"

class SimulationNotActiveError(HistoryDataError):
    code = "HD-061"

class ScenarioNotFoundError(HistoryDataError):
    code = "HD-062"

class SimulationClockError(HistoryDataError):
    code = "HD-063"


# ── Index errors  HD-070 – HD-079 ─────────────────────────────────────────────

class IndexError(HistoryDataError):
    code = "HD-070"

class IndexNotFoundError(HistoryDataError):
    code = "HD-071"

class IndexCorruptionError(HistoryDataError):
    code = "HD-072"


# ── Registry errors  HD-080 – HD-089 ──────────────────────────────────────────

class HistoryRegistryError(HistoryDataError):
    code = "HD-080"

class HistoryRegistryFullError(HistoryDataError):
    code = "HD-081"
