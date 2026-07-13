"""iios/investment/company/profile/ownership_tree.py
Hierarchical ownership structure — parent, entity, subsidiaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from iios.investment.company.profile.models import RelatedEntity, RelationshipType, Subsidiary


@dataclass
class OwnershipNode:
    ticker:            Optional[str]
    name:              str
    ownership_pct:     float    # % held by parent node
    relationship_type: RelationshipType
    children:          List["OwnershipNode"] = field(default_factory=list)

    def add_child(self, node: "OwnershipNode") -> None:
        self.children.append(node)

    def to_dict(self, depth: int = 0) -> dict:
        return {
            "ticker":            self.ticker,
            "name":              self.name,
            "ownership_pct":     round(self.ownership_pct, 2),
            "relationship_type": self.relationship_type.value,
            "depth":             depth,
            "children":          [c.to_dict(depth + 1) for c in self.children],
        }


class OwnershipTree:
    """Full ownership hierarchy for one company."""

    def __init__(
        self,
        entity_ticker: str,
        entity_name:   str,
    ) -> None:
        self._root = OwnershipNode(
            ticker=entity_ticker,
            name=entity_name,
            ownership_pct=100.0,
            relationship_type=RelationshipType.SUBSIDIARY,
        )

    def set_parent(
        self,
        parent_ticker:  Optional[str],
        parent_name:    str,
        ownership_pct:  float,
    ) -> None:
        """Attach a parent node above the root."""
        parent_node = OwnershipNode(
            ticker=parent_ticker,
            name=parent_name,
            ownership_pct=100.0,
            relationship_type=RelationshipType.SUBSIDIARY,
        )
        parent_node.add_child(self._root)
        self._root = parent_node

    def add_subsidiary(self, subsidiary: Subsidiary) -> None:
        node = OwnershipNode(
            ticker=subsidiary.ticker,
            name=subsidiary.name,
            ownership_pct=subsidiary.ownership_pct,
            relationship_type=subsidiary.relationship_type,
        )
        self._root.add_child(node)

    def add_related(self, entity: RelatedEntity) -> None:
        node = OwnershipNode(
            ticker=entity.ticker,
            name=entity.name,
            ownership_pct=entity.ownership_pct or 0.0,
            relationship_type=entity.relationship_type,
        )
        self._root.add_child(node)

    def root(self) -> OwnershipNode:
        return self._root

    def all_nodes(self) -> List[OwnershipNode]:
        """Flatten tree into list (BFS)."""
        result = []
        queue  = [self._root]
        while queue:
            node = queue.pop(0)
            result.append(node)
            queue.extend(node.children)
        return result

    def total_entities(self) -> int:
        return len(self.all_nodes())

    def subsidiary_count(self) -> int:
        return sum(
            1 for n in self.all_nodes()
            if n.relationship_type is RelationshipType.SUBSIDIARY
            and n is not self._root
        )

    def to_dict(self) -> dict:
        return self._root.to_dict()

    def depth(self) -> int:
        """Max depth of ownership hierarchy."""
        def _depth(node: OwnershipNode) -> int:
            if not node.children:
                return 0
            return 1 + max(_depth(c) for c in node.children)
        return _depth(self._root)
