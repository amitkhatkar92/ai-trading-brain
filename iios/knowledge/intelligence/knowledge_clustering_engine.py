"""
knowledge_clustering_engine.py — iios.knowledge.intelligence
------------------------------------------------------------
Groups knowledge artifacts into clusters using embedding similarity.

Stub strategy: deterministic hash-bucketing (no ML library required).
A ClusteringAdapter Protocol allows injection of scikit-learn, faiss, etc.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import ClusteringAlgorithm, DEFAULT_MAX_CLUSTERS
from .embedding_registry import EmbeddingRegistry

_log = get_logger(__name__)


@runtime_checkable
class ClusteringAdapter(Protocol):
    """Protocol for pluggable clustering algorithm backends."""
    def cluster(
        self,
        artifact_ids: List[str],
        vectors:      List[List[float]],
        n_clusters:   int,
    ) -> Dict[int, List[str]]: ...   # cluster_id → [artifact_ids]


class KnowledgeClusteringEngine:
    """
    Clusters knowledge artifacts by embedding proximity.

    Stub mode: modular hash bucketing (fast, deterministic).
    Adapter mode: delegates to an injected ClusteringAdapter.
    """

    def __init__(
        self,
        registry:    EmbeddingRegistry,
        algorithm:   ClusteringAlgorithm = ClusteringAlgorithm.KMEANS,
        n_clusters:  int                 = 5,
        adapter:     Optional[ClusteringAdapter] = None,
    ) -> None:
        self._registry   = registry
        self._algorithm  = algorithm
        self._n_clusters = min(n_clusters, DEFAULT_MAX_CLUSTERS)
        self._adapter    = adapter

    def cluster(
        self,
        n_clusters: int = 0,
    ) -> Dict[int, List[str]]:
        """
        Cluster all indexed artifacts.

        Returns: {cluster_id: [artifact_ids]}. Never raises.
        """
        k = n_clusters or self._n_clusters
        all_ids = self._registry.all_artifact_ids()
        if not all_ids:
            return {}
        try:
            if self._adapter:
                vectors = [
                    list(self._registry.get(aid).vector)
                    for aid in all_ids
                    if self._registry.get(aid)
                ]
                return self._adapter.cluster(all_ids, vectors, k)
            return self._stub_cluster(all_ids, k)
        except Exception as exc:
            _log.warning(f"Clustering failed: {exc!r}")
            return {0: all_ids}

    def _stub_cluster(
        self,
        artifact_ids: List[str],
        n_clusters:   int,
    ) -> Dict[int, List[str]]:
        """Deterministic modular hash bucketing."""
        result: Dict[int, List[str]] = {i: [] for i in range(n_clusters)}
        for aid in artifact_ids:
            bucket = hash(aid) % n_clusters
            result[bucket].append(aid)
        return result

    def set_adapter(self, adapter: ClusteringAdapter) -> None:
        self._adapter = adapter
        _log.info("ClusteringAdapter registered")
