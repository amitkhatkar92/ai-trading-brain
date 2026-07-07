"""
iios/knowledge/graph/graph_factory.py
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from .graph_constants import (
    GraphNodeType, GraphEdgeType, NodeStatus,
    DEFAULT_EDGE_WEIGHT, DEFAULT_EDGE_CONFIDENCE,
    GRAPH_NAMESPACE, SYSTEM_GRAPH_ACTOR,
)
from .models.graph_metadata import GraphMetadata
from .models.graph_node     import GraphNode
from .models.graph_edge     import GraphEdge
from .models.graph_subgraph import GraphSubgraph

__all__ = ["GraphFactory", "get_graph_factory"]

_factory: Optional["GraphFactory"] = None


class GraphFactory:
    """Creates correctly-typed GraphNode, GraphEdge, and GraphSubgraph objects.

    Usage::

        factory = get_graph_factory()
        node    = factory.create_node("NIFTY 50", GraphNodeType.MARKET)
        edge    = factory.create_edge(
            node.node_id, other.node_id, GraphEdgeType.CORRELATES_WITH, weight=0.8
        )
    """

    def __init__(
        self,
        default_actor: str = SYSTEM_GRAPH_ACTOR,
        namespace:     str = GRAPH_NAMESPACE,
    ) -> None:
        self._actor     = default_actor
        self._namespace = namespace

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _new_node_id(self) -> str:
        return f"{self._namespace}/{uuid.uuid4()}"

    def _new_edge_id(self) -> str:
        return f"{self._namespace}/edge/{uuid.uuid4()}"

    def _metadata(
        self,
        actor:       Optional[str]       = None,
        description: str                 = "",
        tags:        Optional[list[str]] = None,
    ) -> GraphMetadata:
        a = actor or self._actor
        return GraphMetadata(
            owner_id    = a,
            created_by  = a,
            updated_by  = a,
            description = description,
            tags        = list(tags or []),
        )

    # ── Node factory ──────────────────────────────────────────────────────────

    def create_node(
        self,
        label:        str,
        node_type:    GraphNodeType           = GraphNodeType.ENTITY,
        properties:   Optional[dict[str,Any]] = None,
        weight:       float                   = 1.0,
        confidence:   float                   = 1.0,
        knowledge_id: Optional[str]           = None,
        tags:         Optional[list[str]]     = None,
        description:  str                     = "",
        actor:        Optional[str]           = None,
    ) -> GraphNode:
        return GraphNode(
            node_id      = self._new_node_id(),
            node_type    = node_type,
            label        = label,
            status       = NodeStatus.ACTIVE,
            properties   = dict(properties or {}),
            metadata     = self._metadata(actor, description, tags),
            weight       = weight,
            confidence   = confidence,
            knowledge_id = knowledge_id,
        )

    def create_knowledge_node(
        self, knowledge_id: str, label: str,
        node_type: GraphNodeType = GraphNodeType.KNOWLEDGE,
        **kwargs: Any,
    ) -> GraphNode:
        return self.create_node(
            label=label, node_type=node_type, knowledge_id=knowledge_id, **kwargs,
        )

    def create_strategy_node(self, strategy_name: str, **kwargs: Any) -> GraphNode:
        return self.create_node(label=strategy_name, node_type=GraphNodeType.STRATEGY, **kwargs)

    def create_signal_node(self, signal_name: str, **kwargs: Any) -> GraphNode:
        return self.create_node(label=signal_name, node_type=GraphNodeType.SIGNAL, **kwargs)

    def create_market_node(self, market_name: str, **kwargs: Any) -> GraphNode:
        return self.create_node(label=market_name, node_type=GraphNodeType.MARKET, **kwargs)

    def create_instrument_node(self, symbol: str, **kwargs: Any) -> GraphNode:
        return self.create_node(label=symbol, node_type=GraphNodeType.INSTRUMENT, **kwargs)

    # ── Edge factory ──────────────────────────────────────────────────────────

    def create_edge(
        self,
        source_id:  str,
        target_id:  str,
        edge_type:  GraphEdgeType          = GraphEdgeType.RELATED_TO,
        weight:     float                  = DEFAULT_EDGE_WEIGHT,
        confidence: float                  = DEFAULT_EDGE_CONFIDENCE,
        properties: Optional[dict[str,Any]] = None,
        is_directed: bool                  = True,
        expires_at: Optional[float]        = None,
        actor:      Optional[str]          = None,
    ) -> GraphEdge:
        return GraphEdge(
            edge_id     = self._new_edge_id(),
            source_id   = source_id,
            target_id   = target_id,
            edge_type   = edge_type,
            weight      = weight,
            confidence  = confidence,
            properties  = dict(properties or {}),
            metadata    = self._metadata(actor),
            is_directed = is_directed,
            expires_at  = expires_at,
        )

    # ── Subgraph factory ──────────────────────────────────────────────────────

    def create_subgraph(
        self,
        nodes:   list[GraphNode],
        edges:   list[GraphEdge],
        label:   str             = "subgraph",
        root_id: Optional[str]  = None,
    ) -> GraphSubgraph:
        sg = GraphSubgraph.new(label=label, root_id=root_id)
        for n in nodes:
            sg.add_node(n)
        for e in edges:
            sg.add_edge(e)
        return sg


def get_graph_factory(actor: str = SYSTEM_GRAPH_ACTOR) -> GraphFactory:
    global _factory
    if _factory is None:
        _factory = GraphFactory(default_actor=actor)
    return _factory
