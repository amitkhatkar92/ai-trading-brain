"""
KDE-001 — Knowledge Discovery Engine.

Transforms historical and live market knowledge into institutional discoveries.

Public API:
    KDEEngine            — top-level orchestrator
    KDEConfig            — configuration
    BaseDiscoveryScheme  — base class for custom schemes
    DiscoveryContext     — read-only input context for schemes
    ALL_SCHEMES          — list of 15 built-in scheme classes

All data models:
    Discovery, DiscoveryEvidence, DiscoveryCandidate, DiscoveryScore
    DiscoveryRelationship, DiscoveryCluster, DiscoveryStatistics
    KDERunResult, KDEStatus
    DiscoveryStatus, SDRecommendation, PotentialValue,
    RelationshipType, EvidenceType

Quick start:
    from kde import KDEEngine
    engine = KDEEngine()
    result = engine.run(hkap_packages, dna_records, edge_records)
"""
from .kde_engine          import KDEEngine
from .kde_config          import KDEConfig
from .scheme_base         import BaseDiscoveryScheme, DiscoveryContext
from .discovery_scorer    import DiscoveryScorer
from .relationship_miner  import RelationshipMiner
from .cluster_builder     import ClusterBuilder
from .report_generator    import KDEReportGenerator
from .kde_models          import (
    # enums
    DiscoveryStatus, SDRecommendation, PotentialValue,
    RelationshipType, EvidenceType,
    # models
    DiscoveryScore, DiscoveryEvidence, DiscoveryCandidate,
    Discovery, DiscoveryRelationship, DiscoveryCluster,
    DiscoveryStatistics, KDERunResult, KDEStatus,
    # constants
    DISCOVERY_WEIGHTS,
    # errors
    KDEError,
)
from .schemes import ALL_SCHEMES

__all__ = [
    # core
    "KDEEngine", "KDEConfig",
    "BaseDiscoveryScheme", "DiscoveryContext",
    "DiscoveryScorer", "RelationshipMiner", "ClusterBuilder", "KDEReportGenerator",
    # enums
    "DiscoveryStatus", "SDRecommendation", "PotentialValue",
    "RelationshipType", "EvidenceType",
    # models
    "DiscoveryScore", "DiscoveryEvidence", "DiscoveryCandidate",
    "Discovery", "DiscoveryRelationship", "DiscoveryCluster",
    "DiscoveryStatistics", "KDERunResult", "KDEStatus",
    "DISCOVERY_WEIGHTS",
    # errors
    "KDEError",
    # schemes
    "ALL_SCHEMES",
]
