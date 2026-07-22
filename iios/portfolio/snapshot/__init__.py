"""
__init__.py — iios.portfolio.snapshot
======================================
Public API for the Portfolio Snapshot subsystem.

PortfolioSnapshot is the ONLY published representation of the Portfolio
Intelligence subsystem.  Every downstream subsystem MUST consume
PortfolioSnapshot instead of internal Portfolio objects.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from .constants import (
    SNAPSHOT_SYSTEM_ID,
    VERSION,
    ACTOR_BUILDER,
    ACTOR_STORE,
    ACTOR_ENGINE,
    DEFAULT_MAX_STORE,
    DEFAULT_MAX_CACHE,
    DEFAULT_MAX_HISTORY_PER_PF,
    SnapshotStatus,
    PortfolioHealth,
    SnapshotEventType,
    SnapshotValidationCode,
    VALID_SNAPSHOT_TRANSITIONS,
    PUBLISHED_STATUSES,
    TERMINAL_STATUSES,
)
from .exceptions import (
    PortfolioSnapshotError,
    SnapshotBuildError,
    SnapshotNotFoundError,
    SnapshotValidationError,
    SnapshotDuplicateError,
    SnapshotStoreError,
    SnapshotCacheError,
    SnapshotVersionError,
    SnapshotCapacityError,
    SnapshotPublicationError,
)
from .portfolio_snapshot_metadata import (
    SnapshotAuditMetadata,
    PortfolioSnapshotMetadata,
)
from .portfolio_snapshot import PortfolioSnapshot
from .portfolio_snapshot_events import (
    SnapshotEvent,
    make_snapshot_created,
    make_snapshot_validated,
    make_snapshot_published,
    make_snapshot_archived,
    make_snapshot_retrieved,
    make_snapshot_cached,
)
from .portfolio_snapshot_validation import (
    SnapshotValidationCheckResult,
    SnapshotValidationResult,
    PortfolioSnapshotValidator,
)
from .portfolio_snapshot_statistics import PortfolioSnapshotStatistics
from .portfolio_snapshot_cache import PortfolioSnapshotCache
from .portfolio_snapshot_history import PortfolioSnapshotHistory
from .portfolio_snapshot_store import PortfolioSnapshotStore
from .portfolio_snapshot_registry import PortfolioSnapshotRegistry
from .portfolio_snapshot_builder import PortfolioSnapshotBuilder
from .portfolio_snapshot_factory import PortfolioSnapshotFactory
from .portfolio_snapshot_bundle import PortfolioSnapshotBundle

__all__ = [
    # constants
    "SNAPSHOT_SYSTEM_ID",
    "VERSION",
    "ACTOR_BUILDER",
    "ACTOR_STORE",
    "ACTOR_ENGINE",
    "DEFAULT_MAX_STORE",
    "DEFAULT_MAX_CACHE",
    "DEFAULT_MAX_HISTORY_PER_PF",
    "SnapshotStatus",
    "PortfolioHealth",
    "SnapshotEventType",
    "SnapshotValidationCode",
    "VALID_SNAPSHOT_TRANSITIONS",
    "PUBLISHED_STATUSES",
    "TERMINAL_STATUSES",
    # exceptions
    "PortfolioSnapshotError",
    "SnapshotBuildError",
    "SnapshotNotFoundError",
    "SnapshotValidationError",
    "SnapshotDuplicateError",
    "SnapshotStoreError",
    "SnapshotCacheError",
    "SnapshotVersionError",
    "SnapshotCapacityError",
    "SnapshotPublicationError",
    # metadata
    "SnapshotAuditMetadata",
    "PortfolioSnapshotMetadata",
    # core
    "PortfolioSnapshot",
    # events
    "SnapshotEvent",
    "make_snapshot_created",
    "make_snapshot_validated",
    "make_snapshot_published",
    "make_snapshot_archived",
    "make_snapshot_retrieved",
    "make_snapshot_cached",
    # validation
    "SnapshotValidationCheckResult",
    "SnapshotValidationResult",
    "PortfolioSnapshotValidator",
    # infrastructure
    "PortfolioSnapshotStatistics",
    "PortfolioSnapshotCache",
    "PortfolioSnapshotHistory",
    "PortfolioSnapshotStore",
    "PortfolioSnapshotRegistry",
    # build
    "PortfolioSnapshotBuilder",
    "PortfolioSnapshotFactory",
    # bundle
    "PortfolioSnapshotBundle",
]
