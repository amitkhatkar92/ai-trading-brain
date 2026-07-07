# Knowledge Graph Engine

The Knowledge Graph Engine is the semantic backbone of the Investment Intelligence Operating System (IIOS). It stores, manages, traverses, validates, and queries relationships between all knowledge objects, providing the foundation for reasoning, inference, dependency analysis, and AI intelligence.

---

## Architecture Overview

```
iios/knowledge/graph/
├── knowledge_graph.py          # Original reference graph (KnowledgeEngine compatibility)
├── graph_constants.py          # Enums: GraphNodeType, GraphEdgeType, NodeStatus …
├── graph_exceptions.py         # Exception hierarchy (18 typed exceptions)
├── graph_context.py            # Thread-local actor / operation tracking
├── graph_factory.py            # Object factory (nodes, edges, subgraphs)
├── graph_engine.py             # Traversal + analytics (BFS, DFS, Dijkstra, PageRank …)
├── graph_manager.py            # High-level façade (primary entry-point)
├── graph_registry.py           # Lazy-resolution component registry
├── models/
│   ├── graph_metadata.py       # GraphMetadata (owner, tags, timestamps)
│   ├── graph_node.py           # GraphNode dataclass
│   ├── graph_edge.py           # GraphEdge dataclass
│   ├── graph_path.py           # GraphPath + PathStep
│   ├── graph_cluster.py        # GraphCluster
│   ├── graph_subgraph.py       # GraphSubgraph
│   └── graph_statistics.py     # GraphStatistics, NodeStatistics, ImpactResult
└── storage/
    ├── graph_query.py          # Filter + pagination objects (NodeQuery, EdgeQuery …)
    ├── graph_storage.py        # Raw in-memory node/edge store
    ├── graph_cache.py          # LRU node/edge cache with TTL
    ├── graph_index.py          # Inverted indexes (type, status, keyword, tag, knowledge_id)
    └── graph_repository.py     # Unified CRUD façade (storage + cache + index)
```

---

## Quick Start

```python
from iios.knowledge.graph import get_graph_manager, GraphNodeType, GraphEdgeType

gm = get_graph_manager()

# Create nodes
nifty   = gm.create_node("NIFTY 50",         GraphNodeType.MARKET)
signal  = gm.create_node("Bullish Momentum",  GraphNodeType.SIGNAL)
strat   = gm.create_node("Trend Following",   GraphNodeType.STRATEGY)

# Create edges
gm.connect(nifty.node_id,  signal.node_id, GraphEdgeType.TRIGGERS,    weight=0.9)
gm.connect(signal.node_id, strat.node_id,  GraphEdgeType.SUPPORTS,    weight=0.8)

# Query
path   = gm.shortest_path(nifty.node_id, strat.node_id)
impact = gm.impact_analysis(nifty.node_id)
stats  = gm.statistics()

print(f"Path depth : {path.total_depth}")
print(f"Nodes affected by NIFTY change: {impact.total_affected}")
print(f"Graph: {stats.active_node_count} nodes, {stats.active_edge_count} edges")
```

---

## Knowledge Graph Guide

### Node Types (`GraphNodeType`)

| Type         | Purpose                                         |
|--------------|-------------------------------------------------|
| `KNOWLEDGE`  | A KnowledgeItem from the Knowledge Engine       |
| `STRATEGY`   | A trading strategy                              |
| `SIGNAL`     | A market signal or indicator output             |
| `AGENT`      | An AI agent in the IIOS hierarchy               |
| `MARKET`     | A market or index (e.g. NIFTY 50, BANKNIFTY)    |
| `INSTRUMENT` | A tradeable instrument (symbol)                 |
| `INDICATOR`  | A technical or fundamental indicator            |
| `RULE`       | A rule or constraint                            |
| `CONCEPT`    | An abstract concept                             |
| `ENTITY`     | A generic entity                                |
| `CLUSTER`    | A cluster of related nodes                      |
| `EVENT`      | A market or system event                        |
| `METRIC`     | A performance or risk metric                    |

### Edge Types (`GraphEdgeType`)

| Type             | Semantics                                    |
|------------------|----------------------------------------------|
| `RELATED_TO`     | Generic bidirectional association            |
| `DEPENDS_ON`     | A depends on B to function                   |
| `INFLUENCES`     | A has causal influence on B                  |
| `SUPPORTS`       | A provides evidence supporting B             |
| `CONTRADICTS`    | A contradicts or refutes B                   |
| `DERIVED_FROM`   | A was derived/calculated from B              |
| `PART_OF`        | A is a component of B                        |
| `INSTANCE_OF`    | A is an instance of concept B                |
| `CAUSES`         | A causes B to occur                          |
| `CORRELATES_WITH`| Statistical correlation                      |
| `SUPERSEDES`     | A replaces or supersedes B                   |
| `IMPLEMENTS`     | A implements rule or strategy B              |
| `TRIGGERS`       | A triggers event or signal B                 |
| `CONTAINS`       | A contains B as a sub-element                |
| `REFERENCES`     | A references B without structural dependency |
| `SIMILAR_TO`     | A is semantically similar to B               |
| `PRECEDES`       | A precedes B temporally                      |
| `FOLLOWS`        | A follows B temporally                       |
| `GENERATES`      | A generates output B                         |
| `VALIDATES`      | A validates or verifies B                    |

### Node Lifecycle

```python
node = gm.create_node("Momentum", GraphNodeType.SIGNAL)

node.deactivate()   # status → INACTIVE
node.activate()     # status → ACTIVE
node.archive()      # status → ARCHIVED  (read-only)
node.merge()        # status → MERGED    (replaced by a merged node)

gm.update_node(node)
```

### Edge Lifecycle

```python
edge = gm.connect(a.node_id, b.node_id, GraphEdgeType.SUPPORTS, weight=0.85)

edge.deactivate()
edge.expire()           # is_expired = True, is_active = False
edge.set_weight(0.5)    # clamped to [0.0, 1.0]

gm.update_edge(edge)
```

---

## Traversal Guide

All traversal methods are available directly on `GraphManager`.

### Breadth-First Search

```python
# Visit all nodes reachable from start within max_depth hops
node_ids = gm.bfs(start_id, max_depth=5)

# Filter to specific edge types
node_ids = gm.bfs(start_id, edge_types=[GraphEdgeType.DEPENDS_ON])
```

### Depth-First Search

```python
node_ids = gm.dfs(start_id, max_depth=10)
```

### Shortest Path

```python
# Unweighted (hop count)
path = gm.shortest_path(source_id, target_id)
print(path.node_ids)    # [src, ..., tgt]
print(path.total_depth) # number of hops

# Weighted (Dijkstra — cost = 1 - edge.weight, higher weight = cheaper)
path = gm.weighted_shortest_path(source_id, target_id)
print(path.total_cost)
```

### Multi-Hop

```python
# Returns nodes by hop distance
hops = gm.multi_hop(start_id, hops=3)
# {1: [id1, id2], 2: [id3], 3: [id4, id5]}
```

### Neighborhood

```python
# All nodes within radius hops in either direction
nbrs = gm.neighborhood(node_id, radius=2)
```

### Reachability

```python
if gm.reachable(source_id, target_id):
    ...
```

### Dependency Traversal

```python
# Follow DEPENDS_ON edges only
deps = gm.dependency_traversal(node_id, depth=5)
```

---

## Analytics Guide

### Cycle Detection

```python
if gm.has_cycle():
    print("Graph contains a cycle")
```

### Degree Centrality

```python
# Normalized degree centrality per node
centrality = gm.degree_centrality()
most_central = max(centrality, key=centrality.get)
```

### Connected Components

```python
# List of sets of node_ids, one set per weakly-connected component
components = gm.connected_components()
print(f"{len(components)} components found")
```

### Influence Scores (PageRank)

```python
# PageRank-like scores (damping=0.85, iterations=20)
scores = gm.influence_scores()
top_influencer = max(scores, key=scores.get)
```

### Impact Analysis

```python
impact = gm.impact_analysis(node_id)
print(f"Direct dependents    : {impact.direct_dependents}")
print(f"Transitive dependents: {impact.transitive_dependents}")
print(f"Total affected       : {impact.total_affected}")
print(f"Impact score         : {impact.impact_score:.3f}")
```

### Graph Statistics

```python
stats = gm.statistics()
print(f"Nodes      : {stats.active_node_count}")
print(f"Edges      : {stats.active_edge_count}")
print(f"Is DAG     : {stats.is_dag}")
print(f"Components : {stats.component_count}")
print(f"Density    : {stats.density:.4f}")
```

### Node Statistics

```python
ns = gm.node_statistics(node_id)
print(f"In-degree  : {ns.in_degree}")
print(f"Out-degree : {ns.out_degree}")
print(f"Total      : {ns.total_degree}")
```

---

## Subgraph Operations

```python
# Extract subgraph induced by a set of node IDs
sg = gm.extract_subgraph({n1_id, n2_id, n3_id})

# Build dependency subgraph rooted at a node
sg = gm.dependency_graph(root_id, depth=5)

# Deep clone a subgraph (new node/edge IDs)
cloned = gm.clone_subgraph(root_id, depth=3)
```

---

## Merge and Split

```python
# Merge multiple nodes into one (edges are re-routed)
merged = gm.merge_nodes([id_a, id_b, id_c], merged_label="Super-Strategy")

# Split a node into parts (no edge re-routing)
parts = gm.split_node(node_id, labels=["Part A", "Part B"])
```

---

## Bulk Operations

```python
nodes = [factory.create_node(f"n{i}", GraphNodeType.ENTITY) for i in range(100)]
gm.bulk_create_nodes(nodes)

edges = [factory.create_edge(nodes[i].node_id, nodes[i+1].node_id,
                              GraphEdgeType.DEPENDS_ON)
         for i in range(99)]
gm.bulk_create_edges(edges)
```

---

## Querying

```python
from iios.knowledge.graph import NodeQuery, NodeFilter, EdgeQuery, EdgeFilter, GraphNodeType

# Find all active SIGNAL nodes
result = gm.query_nodes(NodeQuery(filter=NodeFilter(
    node_types=[GraphNodeType.SIGNAL],
)))
for node in result.items:
    print(node.label)

# Pagination
from iios.knowledge.graph.storage.graph_query import PageRequest, GraphSortOrder
result = gm.query_nodes(NodeQuery(
    filter=NodeFilter(label_contains="nifty"),
    pagination=PageRequest(page=2, page_size=20),
))
print(f"Page {result.page} of {result.total} results")
```

---

## Context Tracking

```python
from iios.knowledge.graph import graph_operation, current_graph_actor

with graph_operation("create_strategy_nodes", actor_id="agent:strategy_lab"):
    n = gm.create_node("NIFTY Momentum", GraphNodeType.STRATEGY)
    print(f"Actor: {current_graph_actor()}")  # agent:strategy_lab
```

---

## Registry

```python
from iios.knowledge.graph import get_graph_registry

reg = get_graph_registry()
print(reg.list_registered())  # ['cache', 'context', 'engine', 'factory', 'index', 'manager', ...]

# Resolve a component by name
engine = reg.resolve("engine")

# Register a custom component
reg.register("my_analyzer", MyAnalyzer())
```

---

## Graph Validation

```python
report = gm.validate_graph()
if not report["valid"]:
    for issue in report["issues"]:
        print(f"ISSUE: {issue}")
print(f"Has cycle: {report['has_cycle']}")
```

---

## Developer Guide

### Singleton Pattern

All components follow the same singleton pattern:

```python
from iios.knowledge.graph.graph_manager import get_graph_manager, reset_graph_manager

gm = get_graph_manager()   # creates or returns existing singleton
reset_graph_manager()       # sets _manager = None (for tests)
```

### Thread Safety

- All shared-state classes use `threading.RLock()` (never `threading.Lock()`)
- `GraphContext` uses `threading.local()` — each thread has independent actor/operation state
- Singletons are protected by module-level `threading.Lock()` during construction

### Resetting in Tests

```python
def _reset_all():
    from iios.knowledge.graph.graph_manager  import reset_graph_manager
    from iios.knowledge.graph.graph_engine   import reset_graph_engine
    from iios.knowledge.graph.graph_registry import reset_graph_registry
    from iios.knowledge.graph.graph_context  import reset_graph_context
    from iios.knowledge.graph.storage.graph_repository import reset_graph_repository
    from iios.knowledge.graph.storage.graph_index      import reset_graph_index
    from iios.knowledge.graph.storage.graph_cache      import reset_graph_cache
    from iios.knowledge.graph.storage.graph_storage    import reset_graph_storage
    import iios.knowledge.graph.graph_factory as _f
    reset_graph_manager(); reset_graph_engine(); reset_graph_registry()
    reset_graph_context(); reset_graph_repository(); reset_graph_index()
    reset_graph_cache(); reset_graph_storage()
    _f._factory = None
```

### Adding a New Node Type

1. Add the value to `GraphNodeType` in `graph_constants.py`
2. Add a convenience method to `GraphFactory` (e.g. `create_indicator_node`)
3. Update this README

### Adding a New Edge Type

1. Add the value to `GraphEdgeType` in `graph_constants.py`
2. Update the edge type table in this README

### Extending the Engine

`GraphEngine` is a stateless service. Add new analytics as methods and expose them via `GraphManager`. Follow the existing pattern:

```python
# graph_engine.py
def my_algorithm(self, node_id: str) -> dict[str, float]:
    repo = self._repo
    ...

# graph_manager.py
def my_algorithm(self, node_id: str) -> dict[str, float]:
    return self._engine.my_algorithm(node_id)
```

---

## Integration with Knowledge Engine

```python
from iios.knowledge         import get_knowledge_manager
from iios.knowledge.graph   import get_graph_manager, GraphNodeType, GraphEdgeType

km = get_knowledge_manager()
gm = get_graph_manager()

# Create a KnowledgeItem and mirror it as a graph node
item  = km.create("NIFTY Trend", "ANALYSIS", content="Bullish trend detected")
gnode = gm.create_node(
    label        = item.title,
    node_type    = GraphNodeType.KNOWLEDGE,
    knowledge_id = item.id,
)

# Find the graph node for a knowledge ID
node = gm.find_node_by_knowledge_id(item.id)
```
