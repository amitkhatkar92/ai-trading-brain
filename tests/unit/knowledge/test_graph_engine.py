"""
tests/unit/knowledge/test_graph_engine.py
==========================================
Comprehensive tests for the IIOS Knowledge Graph Engine.

Run::

    .venv\\Scripts\\python -m pytest tests/unit/knowledge/test_graph_engine.py -v --tb=short
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_all() -> None:
    from iios.knowledge.graph.graph_manager  import reset_graph_manager
    from iios.knowledge.graph.graph_engine   import reset_graph_engine
    from iios.knowledge.graph.graph_registry import reset_graph_registry
    from iios.knowledge.graph.graph_context  import reset_graph_context
    from iios.knowledge.graph.storage.graph_repository import reset_graph_repository
    from iios.knowledge.graph.storage.graph_index      import reset_graph_index
    from iios.knowledge.graph.storage.graph_cache      import reset_graph_cache
    from iios.knowledge.graph.storage.graph_storage    import reset_graph_storage
    import iios.knowledge.graph.graph_factory as _f

    reset_graph_manager()
    reset_graph_engine()
    reset_graph_registry()
    reset_graph_context()
    reset_graph_repository()
    reset_graph_index()
    reset_graph_cache()
    reset_graph_storage()
    _f._factory = None


def _gm():
    from iios.knowledge.graph.graph_manager import get_graph_manager
    return get_graph_manager()


def _factory():
    from iios.knowledge.graph.graph_factory import get_graph_factory
    return get_graph_factory()


def _make_node(label: str = "Test Node", **kwargs):
    from iios.knowledge.graph.graph_constants import GraphNodeType
    return _factory().create_node(label=label, node_type=GraphNodeType.ENTITY, **kwargs)


def _make_edge(src: str, tgt: str, **kwargs):
    from iios.knowledge.graph.graph_constants import GraphEdgeType
    return _factory().create_edge(source_id=src, target_id=tgt,
                                   edge_type=GraphEdgeType.RELATED_TO, **kwargs)


def _add_chain(gm, n: int):
    """Add n nodes in a linear chain and return their IDs in order."""
    from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
    nodes = [gm.create_node(f"Node{i}", GraphNodeType.ENTITY) for i in range(n)]
    for i in range(n - 1):
        gm.connect(nodes[i].node_id, nodes[i + 1].node_id, GraphEdgeType.DEPENDS_ON)
    return [nd.node_id for nd in nodes]


# ===========================================================================
# 1. GraphMetadata
# ===========================================================================

class TestGraphMetadata:
    def setup_method(self): _reset_all()

    def test_defaults(self):
        from iios.knowledge.graph.models.graph_metadata import GraphMetadata
        from iios.knowledge.graph.graph_constants import SYSTEM_GRAPH_ACTOR
        m = GraphMetadata()
        assert m.owner_id == SYSTEM_GRAPH_ACTOR

    def test_add_tag(self):
        from iios.knowledge.graph.models.graph_metadata import GraphMetadata
        m = GraphMetadata()
        m.add_tag("equity")
        assert m.has_tag("equity")

    def test_touch_updates_timestamp(self):
        import time
        from iios.knowledge.graph.models.graph_metadata import GraphMetadata
        m = GraphMetadata()
        before = m.updated_at
        time.sleep(0.001)
        m.touch()
        assert m.updated_at >= before

    def test_roundtrip(self):
        from iios.knowledge.graph.models.graph_metadata import GraphMetadata
        m = GraphMetadata(description="test", tags=["a"])
        m2 = GraphMetadata.from_dict(m.to_dict())
        assert m2.description == "test"
        assert m2.tags == ["a"]


# ===========================================================================
# 2. GraphNode
# ===========================================================================

class TestGraphNode:
    def setup_method(self): _reset_all()

    def test_new(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType
        n = GraphNode.new("NIFTY 50", GraphNodeType.MARKET)
        assert "iios.graph" in n.node_id
        assert n.label == "NIFTY 50"

    def test_is_active_default(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType
        n = GraphNode.new("test", GraphNodeType.ENTITY)
        assert n.is_active

    def test_deactivate(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType, NodeStatus
        n = GraphNode.new("test", GraphNodeType.ENTITY)
        n.deactivate()
        assert n.status == NodeStatus.INACTIVE
        assert not n.is_active

    def test_archive(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType, NodeStatus
        n = GraphNode.new("test", GraphNodeType.ENTITY)
        n.archive()
        assert n.status == NodeStatus.ARCHIVED

    def test_merge(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType, NodeStatus
        n = GraphNode.new("test", GraphNodeType.ENTITY)
        n.merge()
        assert n.status == NodeStatus.MERGED

    def test_to_dict_roundtrip(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType
        n = GraphNode.new("roundtrip", GraphNodeType.KNOWLEDGE)
        d = n.to_dict()
        n2 = GraphNode.from_dict(d)
        assert n2.node_id == n.node_id
        assert n2.label == n.label

    def test_set_get_property(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType
        n = GraphNode.new("props", GraphNodeType.ENTITY)
        n.set_property("sector", "banking")
        assert n.get_property("sector") == "banking"
        assert n.get_property("missing", "default") == "default"


# ===========================================================================
# 3. GraphEdge
# ===========================================================================

class TestGraphEdge:
    def setup_method(self): _reset_all()

    def test_new(self):
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        e = GraphEdge.new("src", "tgt", GraphEdgeType.DEPENDS_ON)
        assert "edge" in e.edge_id
        assert e.is_active

    def test_is_active_respects_deleted(self):
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        e = GraphEdge.new("s", "t", GraphEdgeType.SUPPORTS)
        e.is_deleted = True
        assert not e.is_active

    def test_expire(self):
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        e = GraphEdge.new("s", "t", GraphEdgeType.TRIGGERS)
        e.expire()
        assert e.is_expired
        assert not e.is_active

    def test_set_weight_clamped(self):
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        e = GraphEdge.new("s", "t", GraphEdgeType.RELATED_TO)
        e.set_weight(5.0)
        assert e.weight == 1.0
        e.set_weight(-1.0)
        assert e.weight == 0.0

    def test_to_dict_roundtrip(self):
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        e = GraphEdge.new("s", "t", GraphEdgeType.CAUSES)
        e2 = GraphEdge.from_dict(e.to_dict())
        assert e2.edge_id == e.edge_id
        assert e2.edge_type == e.edge_type

    def test_deactivate(self):
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphEdgeType, EdgeStatus
        e = GraphEdge.new("s", "t", GraphEdgeType.RELATED_TO)
        e.deactivate()
        assert e.status == EdgeStatus.INACTIVE


# ===========================================================================
# 4. GraphPath
# ===========================================================================

class TestGraphPath:
    def setup_method(self): _reset_all()

    def test_node_ids(self):
        from iios.knowledge.graph.models.graph_path import GraphPath, PathStep
        p = GraphPath(
            source_id="a", target_id="c",
            steps=[PathStep("a", depth=0), PathStep("b", depth=1), PathStep("c", depth=2)],
        )
        assert p.node_ids == ["a", "b", "c"]

    def test_total_depth(self):
        from iios.knowledge.graph.models.graph_path import GraphPath, PathStep
        p = GraphPath(
            source_id="a", target_id="b",
            steps=[PathStep("a"), PathStep("b")],
        )
        assert p.total_depth == 1

    def test_is_valid(self):
        from iios.knowledge.graph.models.graph_path import GraphPath, PathStep
        p = GraphPath(
            source_id="a", target_id="c",
            steps=[PathStep("a"), PathStep("b"), PathStep("c")],
        )
        assert p.is_valid

    def test_to_dict(self):
        from iios.knowledge.graph.models.graph_path import GraphPath, PathStep
        p = GraphPath(
            source_id="x", target_id="y",
            steps=[PathStep("x"), PathStep("y")],
            total_cost=1.0, algorithm="bfs",
        )
        d = p.to_dict()
        assert d["algorithm"] == "bfs"
        assert d["total_depth"] == 1


# ===========================================================================
# 5. GraphCluster
# ===========================================================================

class TestGraphCluster:
    def setup_method(self): _reset_all()

    def test_new(self):
        from iios.knowledge.graph.models.graph_cluster import GraphCluster
        c = GraphCluster.new("test-cluster", {"a", "b", "c"})
        assert c.size == 3

    def test_add_remove_node(self):
        from iios.knowledge.graph.models.graph_cluster import GraphCluster
        c = GraphCluster.new("c")
        c.add_node("x")
        assert c.contains("x")
        c.remove_node("x")
        assert not c.contains("x")

    def test_merge_clusters(self):
        from iios.knowledge.graph.models.graph_cluster import GraphCluster
        c1 = GraphCluster.new("a", {"1", "2"})
        c2 = GraphCluster.new("b", {"3", "4"})
        merged = c1.merge_with(c2)
        assert merged.size == 4

    def test_roundtrip(self):
        from iios.knowledge.graph.models.graph_cluster import GraphCluster
        c = GraphCluster.new("cluster", {"n1", "n2"})
        c2 = GraphCluster.from_dict(c.to_dict())
        assert c2.size == 2


# ===========================================================================
# 6. GraphSubgraph
# ===========================================================================

class TestGraphSubgraph:
    def setup_method(self): _reset_all()

    def test_new_empty(self):
        from iios.knowledge.graph.models.graph_subgraph import GraphSubgraph
        sg = GraphSubgraph.new("test-sg")
        assert sg.node_count == 0
        assert sg.edge_count == 0

    def test_add_node(self):
        from iios.knowledge.graph.models.graph_subgraph import GraphSubgraph
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType
        sg = GraphSubgraph.new("sg")
        n = GraphNode.new("n1", GraphNodeType.ENTITY)
        sg.add_node(n)
        assert sg.node_count == 1
        assert sg.get_node(n.node_id) is not None

    def test_add_edge_and_query(self):
        from iios.knowledge.graph.models.graph_subgraph import GraphSubgraph
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.models.graph_edge import GraphEdge
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        sg = GraphSubgraph.new("sg")
        n1 = GraphNode.new("a", GraphNodeType.ENTITY)
        n2 = GraphNode.new("b", GraphNodeType.ENTITY)
        sg.add_node(n1); sg.add_node(n2)
        e  = GraphEdge.new(n1.node_id, n2.node_id, GraphEdgeType.RELATED_TO)
        sg.add_edge(e)
        assert sg.edge_count == 1
        assert len(sg.get_edges_from(n1.node_id)) == 1

    def test_to_dict_has_keys(self):
        from iios.knowledge.graph.models.graph_subgraph import GraphSubgraph
        sg = GraphSubgraph.new("sg-dict")
        d  = sg.to_dict()
        assert "nodes" in d and "edges" in d


# ===========================================================================
# 7. GraphStatistics
# ===========================================================================

class TestGraphStatistics:
    def setup_method(self): _reset_all()

    def test_to_dict(self):
        from iios.knowledge.graph.models.graph_statistics import GraphStatistics
        s = GraphStatistics(node_count=5, edge_count=3)
        d = s.to_dict()
        assert d["node_count"] == 5

    def test_impact_result(self):
        from iios.knowledge.graph.models.graph_statistics import ImpactResult
        r = ImpactResult(node_id="x", direct_dependents=["a", "b"], transitive_dependents=["a", "b", "c"])
        assert r.total_affected == 3

    def test_node_statistics_total_degree(self):
        from iios.knowledge.graph.models.graph_statistics import NodeStatistics
        ns = NodeStatistics(node_id="x", in_degree=3, out_degree=4)
        assert ns.total_degree == 7


# ===========================================================================
# 8. GraphStorage — Nodes
# ===========================================================================

class TestGraphStorageNodes:
    def setup_method(self): _reset_all()

    def _store(self):
        from iios.knowledge.graph.storage.graph_storage import get_graph_storage
        return get_graph_storage()

    def test_put_and_get(self):
        s = self._store()
        n = _make_node("n1")
        s.put_node(n)
        got = s.get_node(n.node_id)
        assert got.node_id == n.node_id

    def test_get_missing_raises(self):
        from iios.knowledge.graph.graph_exceptions import GraphNodeNotFoundError
        s = self._store()
        with pytest.raises(GraphNodeNotFoundError):
            s.get_node("iios.graph/nonexistent")

    def test_node_exists(self):
        s = self._store()
        n = _make_node()
        assert not s.node_exists(n.node_id)
        s.put_node(n)
        assert s.node_exists(n.node_id)

    def test_soft_delete(self):
        s = self._store()
        n = _make_node()
        s.put_node(n)
        s.delete_node(n.node_id, hard=False)
        got = s.get_node(n.node_id)  # still present
        assert got.is_deleted

    def test_hard_delete(self):
        from iios.knowledge.graph.graph_exceptions import GraphNodeNotFoundError
        s = self._store()
        n = _make_node()
        s.put_node(n)
        s.delete_node(n.node_id, hard=True)
        with pytest.raises(GraphNodeNotFoundError):
            s.get_node(n.node_id)

    def test_all_nodes_excludes_deleted(self):
        s = self._store()
        n = _make_node()
        s.put_node(n)
        s.delete_node(n.node_id)
        live = s.all_nodes(include_deleted=False)
        assert all(not nd.is_deleted for nd in live)

    def test_node_count(self):
        s = self._store()
        for i in range(3):
            s.put_node(_make_node(f"n{i}"))
        assert s.node_count() == 3

    def test_clear(self):
        s = self._store()
        s.put_node(_make_node())
        s.clear()
        assert s.node_count() == 0


# ===========================================================================
# 9. GraphStorage — Edges
# ===========================================================================

class TestGraphStorageEdges:
    def setup_method(self): _reset_all()

    def _store(self):
        from iios.knowledge.graph.storage.graph_storage import get_graph_storage
        return get_graph_storage()

    def test_put_and_get_edge(self):
        s = self._store()
        n1 = _make_node("a"); n2 = _make_node("b")
        s.put_node(n1); s.put_node(n2)
        e = _make_edge(n1.node_id, n2.node_id)
        s.put_edge(e)
        got = s.get_edge(e.edge_id)
        assert got.edge_id == e.edge_id

    def test_edges_from(self):
        s = self._store()
        n1 = _make_node("src"); n2 = _make_node("tgt")
        s.put_node(n1); s.put_node(n2)
        e = _make_edge(n1.node_id, n2.node_id)
        s.put_edge(e)
        edges = s.get_edges_from(n1.node_id)
        assert any(ex.edge_id == e.edge_id for ex in edges)

    def test_edges_to(self):
        s = self._store()
        n1 = _make_node("src"); n2 = _make_node("tgt")
        s.put_node(n1); s.put_node(n2)
        e = _make_edge(n1.node_id, n2.node_id)
        s.put_edge(e)
        edges = s.get_edges_to(n2.node_id)
        assert any(ex.edge_id == e.edge_id for ex in edges)

    def test_hard_delete_edge(self):
        from iios.knowledge.graph.graph_exceptions import GraphEdgeNotFoundError
        s = self._store()
        n1 = _make_node("a"); n2 = _make_node("b")
        s.put_node(n1); s.put_node(n2)
        e = _make_edge(n1.node_id, n2.node_id)
        s.put_edge(e)
        s.delete_edge(e.edge_id, hard=True)
        with pytest.raises(GraphEdgeNotFoundError):
            s.get_edge(e.edge_id)

    def test_edge_count(self):
        s = self._store()
        n1 = _make_node("a"); n2 = _make_node("b")
        s.put_node(n1); s.put_node(n2)
        s.put_edge(_make_edge(n1.node_id, n2.node_id))
        s.put_edge(_make_edge(n2.node_id, n1.node_id))
        assert s.edge_count() == 2


# ===========================================================================
# 10. GraphIndex
# ===========================================================================

class TestGraphIndex:
    def setup_method(self): _reset_all()

    def _index(self):
        from iios.knowledge.graph.storage.graph_index import get_graph_index
        return get_graph_index()

    def test_index_by_type(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        idx = self._index()
        n = _make_node()
        idx.index_node(n)
        ids = idx.nodes_by_type(n.node_type)
        assert n.node_id in ids

    def test_index_by_keyword(self):
        from iios.knowledge.graph.models.graph_node import GraphNode
        from iios.knowledge.graph.graph_constants import GraphNodeType
        idx = self._index()
        n = GraphNode.new("NIFTY 50 index", GraphNodeType.MARKET)
        idx.index_node(n)
        ids = idx.nodes_by_keyword("nifty")
        assert n.node_id in ids

    def test_index_by_tag(self):
        idx = self._index()
        n = _make_node()
        n.metadata.add_tag("equity")
        idx.index_node(n)
        ids = idx.nodes_by_tag("equity")
        assert n.node_id in ids

    def test_deindex_node(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        idx = self._index()
        n = _make_node()
        idx.index_node(n)
        idx.deindex_node(n.node_id)
        assert n.node_id not in idx.nodes_by_type(n.node_type)

    def test_index_edge_by_type(self):
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        idx = self._index()
        e = _make_edge("src", "tgt")
        idx.index_edge(e)
        ids = idx.edges_by_type(e.edge_type)
        assert e.edge_id in ids

    def test_knowledge_id_lookup(self):
        idx = self._index()
        n = _make_node()
        n.knowledge_id = "iios.knowledge/test-id"
        idx.index_node(n)
        result = idx.node_by_knowledge_id("iios.knowledge/test-id")
        assert result == n.node_id


# ===========================================================================
# 11. GraphRepository — Nodes
# ===========================================================================

class TestGraphRepositoryNodes:
    def setup_method(self): _reset_all()

    def _repo(self):
        from iios.knowledge.graph.storage.graph_repository import get_graph_repository
        return get_graph_repository()

    def test_add_and_get(self):
        repo = self._repo()
        n = _make_node("repo-node")
        repo.add_node(n)
        got = repo.get_node(n.node_id)
        assert got.node_id == n.node_id

    def test_duplicate_raises(self):
        from iios.knowledge.graph.graph_exceptions import GraphNodeAlreadyExistsError
        repo = self._repo()
        n = _make_node()
        repo.add_node(n)
        with pytest.raises(GraphNodeAlreadyExistsError):
            repo.add_node(n)

    def test_update_node(self):
        repo = self._repo()
        n = _make_node("original")
        repo.add_node(n)
        n.label = "updated"
        repo.update_node(n)
        assert repo.get_node(n.node_id).label == "updated"

    def test_delete_soft(self):
        from iios.knowledge.graph.graph_exceptions import GraphNodeNotFoundError
        repo = self._repo()
        n = _make_node()
        repo.add_node(n)
        repo.delete_node(n.node_id)
        with pytest.raises(GraphNodeNotFoundError):
            repo.get_node(n.node_id)

    def test_delete_hard(self):
        from iios.knowledge.graph.graph_exceptions import GraphNodeNotFoundError
        repo = self._repo()
        n = _make_node()
        repo.add_node(n)
        repo.delete_node(n.node_id, hard=True)
        with pytest.raises(GraphNodeNotFoundError):
            repo.get_node(n.node_id)

    def test_upsert(self):
        repo = self._repo()
        n = _make_node("upsert")
        repo.upsert_node(n)
        n.label = "upserted"
        repo.upsert_node(n)
        assert repo.get_node(n.node_id).label == "upserted"

    def test_bulk_add_nodes(self):
        repo = self._repo()
        nodes = [_make_node(f"bulk-{i}") for i in range(5)]
        added = repo.bulk_add_nodes(nodes)
        assert added == 5

    def test_query_nodes_by_type(self):
        from iios.knowledge.graph.storage.graph_query import NodeQuery, NodeFilter
        from iios.knowledge.graph.graph_constants import GraphNodeType
        repo = self._repo()
        from iios.knowledge.graph.models.graph_node import GraphNode
        n = GraphNode.new("signal-node", GraphNodeType.SIGNAL)
        repo.add_node(n)
        result = repo.query_nodes(NodeQuery(filter=NodeFilter(node_types=[GraphNodeType.SIGNAL])))
        assert any(nd.node_id == n.node_id for nd in result.items)


# ===========================================================================
# 12. GraphRepository — Edges
# ===========================================================================

class TestGraphRepositoryEdges:
    def setup_method(self): _reset_all()

    def _repo(self):
        from iios.knowledge.graph.storage.graph_repository import get_graph_repository
        return get_graph_repository()

    def _pair(self, repo):
        n1 = _make_node("src"); n2 = _make_node("tgt")
        repo.add_node(n1); repo.add_node(n2)
        return n1, n2

    def test_add_and_get_edge(self):
        repo = self._repo()
        n1, n2 = self._pair(repo)
        e = _make_edge(n1.node_id, n2.node_id)
        repo.add_edge(e)
        got = repo.get_edge(e.edge_id)
        assert got.edge_id == e.edge_id

    def test_missing_endpoint_raises(self):
        from iios.knowledge.graph.graph_exceptions import GraphNodeNotFoundError
        repo = self._repo()
        n1, _ = self._pair(repo)
        e = _make_edge(n1.node_id, "iios.graph/ghost")
        with pytest.raises(GraphNodeNotFoundError):
            repo.add_edge(e)

    def test_delete_edge(self):
        from iios.knowledge.graph.graph_exceptions import GraphEdgeNotFoundError
        repo = self._repo()
        n1, n2 = self._pair(repo)
        e = _make_edge(n1.node_id, n2.node_id)
        repo.add_edge(e)
        repo.delete_edge(e.edge_id, hard=True)
        with pytest.raises(GraphEdgeNotFoundError):
            repo.get_edge(e.edge_id)

    def test_edges_from_and_to(self):
        repo = self._repo()
        n1, n2 = self._pair(repo)
        e = _make_edge(n1.node_id, n2.node_id)
        repo.add_edge(e)
        assert any(x.edge_id == e.edge_id for x in repo.get_edges_from(n1.node_id))
        assert any(x.edge_id == e.edge_id for x in repo.get_edges_to(n2.node_id))

    def test_bulk_add_edges(self):
        repo = self._repo()
        n1, n2 = self._pair(repo)
        edges = [_make_edge(n1.node_id, n2.node_id) for _ in range(3)]
        added = repo.bulk_add_edges(edges)
        assert added == 3


# ===========================================================================
# 13. GraphEngine — BFS / DFS / Shortest Path
# ===========================================================================

class TestGraphEngineTraversal:
    def setup_method(self): _reset_all()

    def _engine(self):
        from iios.knowledge.graph.graph_engine import get_graph_engine
        return get_graph_engine()

    def test_bfs_chain(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        engine = self._engine()
        result = engine.bfs(ids[0])
        assert result[0] == ids[0]
        assert ids[-1] in result

    def test_bfs_max_depth(self):
        gm = _gm()
        ids = _add_chain(gm, 5)
        engine = self._engine()
        result = engine.bfs(ids[0], max_depth=2)
        assert ids[4] not in result  # depth 4 is beyond max_depth=2

    def test_dfs_visits_all(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        engine = self._engine()
        result = engine.dfs(ids[0])
        assert set(ids) == set(result)

    def test_dfs_max_depth(self):
        gm = _gm()
        ids = _add_chain(gm, 5)
        engine = self._engine()
        result = engine.dfs(ids[0], max_depth=1)
        assert ids[2] not in result

    def test_shortest_path_found(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        engine = self._engine()
        path = engine.shortest_path(ids[0], ids[2])
        assert path is not None
        assert path.is_valid
        assert path.total_depth == 2

    def test_shortest_path_same_node(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType
        n = gm.create_node("single", GraphNodeType.ENTITY)
        engine = self._engine()
        path = engine.shortest_path(n.node_id, n.node_id)
        assert path is not None
        assert path.total_depth == 0

    def test_shortest_path_no_path(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType
        a = gm.create_node("isolated-a", GraphNodeType.ENTITY)
        b = gm.create_node("isolated-b", GraphNodeType.ENTITY)
        engine = self._engine()
        path = engine.shortest_path(a.node_id, b.node_id)
        assert path is None

    def test_weighted_shortest_path(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        engine = self._engine()
        path = engine.weighted_shortest_path(ids[0], ids[2])
        assert path is not None
        assert path.algorithm == "dijkstra"


# ===========================================================================
# 14. GraphEngine — Traversal (multi-hop, cycle, dependency)
# ===========================================================================

class TestGraphEngineAdvanced:
    def setup_method(self): _reset_all()

    def _engine(self):
        from iios.knowledge.graph.graph_engine import get_graph_engine
        return get_graph_engine()

    def test_multi_hop(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        engine = self._engine()
        hops = engine.multi_hop(ids[0], hops=3)
        assert ids[1] in hops.get(1, [])
        assert ids[2] in hops.get(2, [])
        assert ids[3] in hops.get(3, [])

    def test_neighborhood(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        engine = self._engine()
        nbrs = engine.neighborhood(ids[1], radius=1)
        assert ids[0] in nbrs
        assert ids[2] in nbrs

    def test_no_cycle_in_dag(self):
        gm = _gm()
        _add_chain(gm, 4)
        engine = self._engine()
        assert not engine.has_cycle()

    def test_cycle_detected(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        c = gm.create_node("c", GraphNodeType.ENTITY)
        gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        gm.connect(b.node_id, c.node_id, GraphEdgeType.RELATED_TO)
        gm.connect(c.node_id, a.node_id, GraphEdgeType.RELATED_TO)
        engine = self._engine()
        assert engine.has_cycle()

    def test_reachable(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        engine = self._engine()
        assert engine.reachable(ids[0], ids[2])

    def test_not_reachable(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType
        a = gm.create_node("iso-a", GraphNodeType.ENTITY)
        b = gm.create_node("iso-b", GraphNodeType.ENTITY)
        engine = self._engine()
        assert not engine.reachable(a.node_id, b.node_id)


# ===========================================================================
# 15. GraphEngine — Analytics
# ===========================================================================

class TestGraphEngineAnalytics:
    def setup_method(self): _reset_all()

    def _engine(self):
        from iios.knowledge.graph.graph_engine import get_graph_engine
        return get_graph_engine()

    def test_degree_centrality_star(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        hub  = gm.create_node("hub", GraphNodeType.ENTITY)
        spokes = [gm.create_node(f"spoke{i}", GraphNodeType.ENTITY) for i in range(4)]
        for s in spokes:
            gm.connect(hub.node_id, s.node_id, GraphEdgeType.RELATED_TO)
        engine = self._engine()
        centrality = engine.degree_centrality()
        assert centrality[hub.node_id] > centrality[spokes[0].node_id]

    def test_connected_components_two(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        c = gm.create_node("c", GraphNodeType.ENTITY)  # isolated
        engine = self._engine()
        components = engine.connected_components()
        assert len(components) == 2

    def test_impact_analysis_downstream(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        engine = self._engine()
        impact = engine.impact_analysis(ids[0])
        assert ids[3] in impact.transitive_dependents
        assert impact.max_depth == 3

    def test_influence_scores_sum(self):
        gm = _gm()
        _add_chain(gm, 3)
        engine = self._engine()
        scores = engine.influence_scores()
        assert len(scores) == 3
        assert all(v >= 0.0 for v in scores.values())

    def test_node_statistics_degrees(self):
        gm = _gm()
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        c = gm.create_node("c", GraphNodeType.ENTITY)
        gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        gm.connect(c.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        engine = self._engine()
        ns = engine.node_statistics(b.node_id)
        assert ns.in_degree == 2
        assert ns.out_degree == 0

    def test_compute_statistics(self):
        gm = _gm()
        _add_chain(gm, 3)
        engine = self._engine()
        stats = engine.compute_statistics()
        assert stats.active_node_count == 3
        assert stats.active_edge_count == 2
        assert stats.is_dag

    def test_dependency_graph(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        engine = self._engine()
        sg = engine.dependency_graph(ids[0], depth=5)
        assert sg.node_count == 3

    def test_extract_subgraph(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        engine = self._engine()
        sg = engine.extract_subgraph({ids[0], ids[1]})
        assert sg.node_count == 2


# ===========================================================================
# 16. GraphManager — Nodes and Edges
# ===========================================================================

class TestGraphManagerNodes:
    def setup_method(self): _reset_all()

    def test_create_and_get(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        n = gm.create_node("BANKNIFTY", GraphNodeType.MARKET)
        got = gm.get_node(n.node_id)
        assert got.label == "BANKNIFTY"

    def test_node_exists(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        n = gm.create_node("x", GraphNodeType.ENTITY)
        assert gm.node_exists(n.node_id)

    def test_update_node(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        n = gm.create_node("original", GraphNodeType.ENTITY)
        n.label = "modified"
        gm.update_node(n)
        assert gm.get_node(n.node_id).label == "modified"

    def test_delete_node(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        from iios.knowledge.graph.graph_exceptions import GraphNodeNotFoundError
        gm = _gm()
        n = gm.create_node("del-me", GraphNodeType.ENTITY)
        gm.delete_node(n.node_id)
        with pytest.raises(GraphNodeNotFoundError):
            gm.get_node(n.node_id)

    def test_find_by_type(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        gm.create_node("sig1", GraphNodeType.SIGNAL)
        gm.create_node("sig2", GraphNodeType.SIGNAL)
        result = gm.find_nodes_by_type(GraphNodeType.SIGNAL)
        assert len(result) == 2

    def test_node_count(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        before = gm.node_count()
        gm.create_node("n", GraphNodeType.ENTITY)
        assert gm.node_count() == before + 1

    def test_bulk_create(self):
        gm = _gm()
        nodes = [_make_node(f"bulk-{i}") for i in range(5)]
        added = gm.bulk_create_nodes(nodes)
        assert added == 5

    def test_query_by_label_keyword(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        from iios.knowledge.graph.storage.graph_query import NodeQuery, NodeFilter
        gm = _gm()
        gm.create_node("NIFTY trend analysis", GraphNodeType.CONCEPT)
        result = gm.query_nodes(NodeQuery(filter=NodeFilter(label_contains="nifty")))
        assert len(result.items) >= 1


class TestGraphManagerEdges:
    def setup_method(self): _reset_all()

    def test_connect_and_get_edge(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        gm = _gm()
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        e = gm.connect(a.node_id, b.node_id, GraphEdgeType.SUPPORTS, weight=0.8)
        got = gm.get_edge(e.edge_id)
        assert got.weight == 0.8

    def test_disconnect(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        gm = _gm()
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        removed = gm.disconnect(a.node_id, b.node_id)
        assert removed == 1

    def test_delete_edge(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        from iios.knowledge.graph.graph_exceptions import GraphEdgeNotFoundError
        gm = _gm()
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        e = gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        gm.delete_edge(e.edge_id, hard=True)
        with pytest.raises(GraphEdgeNotFoundError):
            gm.get_edge(e.edge_id)

    def test_edge_count(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        gm = _gm()
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        assert gm.edge_count() >= 1

    def test_bulk_create_edges(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        nodes = [gm.create_node(f"n{i}", GraphNodeType.ENTITY) for i in range(4)]
        edges = [_make_edge(nodes[0].node_id, nodes[i].node_id) for i in range(1, 4)]
        added = gm.bulk_create_edges(edges)
        assert added == 3


# ===========================================================================
# 17. GraphManager — Advanced Operations
# ===========================================================================

class TestGraphManagerOperations:
    def setup_method(self): _reset_all()

    def test_merge_nodes(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, NodeStatus
        gm = _gm()
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        merged = gm.merge_nodes([a.node_id, b.node_id], "merged-ab")
        assert merged.label == "merged-ab"
        # originals should be MERGED
        assert gm.get_node(a.node_id).status == NodeStatus.MERGED

    def test_split_node(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        n = gm.create_node("original", GraphNodeType.CONCEPT)
        parts = gm.split_node(n.node_id, ["part-a", "part-b"])
        assert len(parts) == 2

    def test_clone_subgraph(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        sg = gm.clone_subgraph(ids[0], depth=5)
        assert sg.node_count == 3

    def test_extract_subgraph(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        sg = gm.extract_subgraph(ids[:2])
        assert sg.node_count == 2

    def test_validate_graph(self):
        gm = _gm()
        _add_chain(gm, 3)
        report = gm.validate_graph()
        assert report["valid"] is True
        assert report["node_count"] >= 3

    def test_status(self):
        gm = _gm()
        _add_chain(gm, 2)
        s = gm.status()
        assert s["status"] == "running"
        assert s["node_count"] >= 2


# ===========================================================================
# 18. GraphManager — Traversal + Analytics
# ===========================================================================

class TestGraphManagerAnalytics:
    def setup_method(self): _reset_all()

    def test_bfs_traversal(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        result = gm.bfs(ids[0])
        assert set(ids) == set(result)

    def test_shortest_path(self):
        gm = _gm()
        ids = _add_chain(gm, 3)
        path = gm.shortest_path(ids[0], ids[2])
        assert path is not None
        assert path.total_depth == 2

    def test_impact_analysis(self):
        gm = _gm()
        ids = _add_chain(gm, 4)
        impact = gm.impact_analysis(ids[0])
        assert len(impact.transitive_dependents) == 3

    def test_connected_components(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        gm = _gm()
        ids = _add_chain(gm, 2)
        gm.create_node("isolated", GraphNodeType.ENTITY)
        comps = gm.connected_components()
        assert len(comps) == 2

    def test_statistics(self):
        gm = _gm()
        _add_chain(gm, 4)
        stats = gm.statistics()
        assert stats.active_node_count == 4
        assert stats.is_dag is True

    def test_has_cycle_false(self):
        gm = _gm()
        _add_chain(gm, 3)
        assert not gm.has_cycle()

    def test_neighborhood_includes_both_directions(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        gm = _gm()
        a = gm.create_node("a", GraphNodeType.ENTITY)
        b = gm.create_node("b", GraphNodeType.ENTITY)
        c = gm.create_node("c", GraphNodeType.ENTITY)
        gm.connect(a.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        gm.connect(c.node_id, b.node_id, GraphEdgeType.RELATED_TO)
        nbrs = gm.neighborhood(b.node_id, radius=1)
        assert a.node_id in nbrs
        assert c.node_id in nbrs


# ===========================================================================
# 19. GraphFactory
# ===========================================================================

class TestGraphFactory:
    def setup_method(self): _reset_all()

    def test_create_node_all_types(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        f = _factory()
        for ntype in [
            GraphNodeType.KNOWLEDGE, GraphNodeType.STRATEGY,
            GraphNodeType.SIGNAL, GraphNodeType.MARKET,
        ]:
            n = f.create_node(label="test", node_type=ntype)
            assert n.node_type == ntype

    def test_create_edge(self):
        from iios.knowledge.graph.graph_constants import GraphEdgeType
        f = _factory()
        e = f.create_edge("src", "tgt", GraphEdgeType.CAUSES, weight=0.7)
        assert e.weight == 0.7
        assert e.edge_type == GraphEdgeType.CAUSES

    def test_create_knowledge_node(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType
        f = _factory()
        n = f.create_knowledge_node("iios.knowledge/abc", "Fact about NIFTY")
        assert n.knowledge_id == "iios.knowledge/abc"
        assert n.node_type == GraphNodeType.KNOWLEDGE

    def test_create_subgraph(self):
        from iios.knowledge.graph.graph_constants import GraphNodeType, GraphEdgeType
        f = _factory()
        n1 = f.create_node("n1", GraphNodeType.ENTITY)
        n2 = f.create_node("n2", GraphNodeType.ENTITY)
        e  = f.create_edge(n1.node_id, n2.node_id, GraphEdgeType.RELATED_TO)
        sg = f.create_subgraph([n1, n2], [e], label="test-sg")
        assert sg.node_count == 2
        assert sg.edge_count == 1


# ===========================================================================
# 20. GraphContext
# ===========================================================================

class TestGraphContext:
    def setup_method(self): _reset_all()

    def test_default_actor(self):
        from iios.knowledge.graph.graph_context import current_graph_actor
        from iios.knowledge.graph.graph_constants import SYSTEM_GRAPH_ACTOR
        assert current_graph_actor() == SYSTEM_GRAPH_ACTOR

    def test_context_sets_actor(self):
        from iios.knowledge.graph.graph_context import get_graph_context, current_graph_actor
        ctx = get_graph_context()
        with ctx.operation("write", actor_id="user:alice"):
            assert current_graph_actor() == "user:alice"

    def test_operation_id_set(self):
        from iios.knowledge.graph.graph_context import (
            get_graph_context, current_graph_operation_id,
        )
        ctx = get_graph_context()
        with ctx.operation("op") as op_id:
            assert op_id == current_graph_operation_id()
            assert len(op_id) > 0

    def test_graph_operation_shortcut(self):
        from iios.knowledge.graph.graph_context import graph_operation, current_graph_actor
        with graph_operation("test", actor_id="user:bob"):
            assert current_graph_actor() == "user:bob"


# ===========================================================================
# 21. GraphRegistry
# ===========================================================================

class TestGraphRegistry:
    def setup_method(self): _reset_all()

    def test_has_defaults(self):
        from iios.knowledge.graph.graph_registry import get_graph_registry
        reg = get_graph_registry()
        for name in ["storage", "cache", "index", "repository", "engine", "manager"]:
            assert reg.has(name), f"Missing: {name}"

    def test_resolve_manager(self):
        from iios.knowledge.graph.graph_registry import get_graph_registry
        from iios.knowledge.graph.graph_manager import GraphManager
        reg = get_graph_registry()
        mgr = reg.resolve("manager")
        assert isinstance(mgr, GraphManager)

    def test_register_and_resolve_custom(self):
        from iios.knowledge.graph.graph_registry import get_graph_registry
        reg = get_graph_registry()
        reg.register("custom_component", {"key": "value"})
        val = reg.resolve("custom_component")
        assert val == {"key": "value"}

    def test_list_registered(self):
        from iios.knowledge.graph.graph_registry import get_graph_registry
        reg = get_graph_registry()
        names = reg.list_registered()
        assert "manager" in names
        assert "engine"  in names
