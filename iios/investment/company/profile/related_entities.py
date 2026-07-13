"""iios/investment/company/profile/related_entities.py
Associates, joint ventures, and cross-holdings management.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.profile.models import RelatedEntity, RelationshipType


class RelatedEntityStore:
    """Manages all non-subsidiary related entities for one company."""

    def __init__(self) -> None:
        self._entities: List[RelatedEntity] = []

    def add(self, entity: RelatedEntity) -> None:
        if not any(e.entity_id == entity.entity_id for e in self._entities):
            self._entities.append(entity)

    def remove(self, entity_id: str) -> bool:
        before = len(self._entities)
        self._entities = [e for e in self._entities if e.entity_id != entity_id]
        return len(self._entities) < before

    def all(self) -> List[RelatedEntity]:
        return list(self._entities)

    def by_type(self, rel_type: RelationshipType) -> List[RelatedEntity]:
        return [e for e in self._entities if e.relationship_type is rel_type]

    def associates(self) -> List[RelatedEntity]:
        return self.by_type(RelationshipType.ASSOCIATE)

    def joint_ventures(self) -> List[RelatedEntity]:
        return self.by_type(RelationshipType.JOINT_VENTURE)

    def cross_holdings(self) -> List[RelatedEntity]:
        return self.by_type(RelationshipType.CROSS_HOLDING)

    def minority_stakes(self) -> List[RelatedEntity]:
        return self.by_type(RelationshipType.MINORITY_STAKE)

    def by_country(self) -> Dict[str, List[RelatedEntity]]:
        result: Dict[str, List[RelatedEntity]] = {}
        for e in self._entities:
            country = e.country or "UNKNOWN"
            result.setdefault(country, []).append(e)
        return result

    def find_by_ticker(self, ticker: str) -> Optional[RelatedEntity]:
        for e in self._entities:
            if e.ticker and e.ticker.upper() == ticker.upper():
                return e
        return None

    def __len__(self) -> int:
        return len(self._entities)
