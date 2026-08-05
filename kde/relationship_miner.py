"""
relationship_miner.py — Mines relationships between Discovery objects.
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .kde_models import Discovery, DiscoveryRelationship, RelationshipType


class RelationshipMiner:
    """
    Identifies semantic relationships between discoveries.

    Rules:
      CORRELATED:    discoveries share feature_names or dna_ids
      COMPLEMENTARY: one is S001 (winner) and other is S002 (loser) on same feature
      CONTRADICTORY: two discoveries about the same feature but opposing answers
      ENABLES:       a context-dependency discovery (S015) + a winner (S001) on same feature
      SUBSUMES:      a cross-year discovery (S014) contains the years of a narrower discovery
    """

    def mine(self, discoveries: List[Discovery]) -> List[DiscoveryRelationship]:
        relationships: List[DiscoveryRelationship] = []
        seen: Set[Tuple[str, str]] = set()
        counter = 0

        def _add(a: Discovery, b: Discovery, rtype: str, strength: float, desc: str) -> None:
            nonlocal counter
            pair = (min(a.discovery_id, b.discovery_id), max(a.discovery_id, b.discovery_id), rtype)
            if pair in seen:
                return
            seen.add(pair)
            counter += 1
            relationships.append(DiscoveryRelationship(
                relationship_id   = f"KDE-REL-{counter:04d}",
                discovery_a       = a.discovery_id,
                discovery_b       = b.discovery_id,
                relationship_type = rtype,
                strength          = round(strength, 4),
                description       = desc,
            ))

        for i, da in enumerate(discoveries):
            for db in discoveries[i + 1:]:
                shared_features = set(da.feature_names) & set(db.feature_names)
                shared_dna      = set(da.dna_ids)      & set(db.dna_ids)

                # COMPLEMENTARY: S001 winner + S002 loser on same feature
                if {da.scheme_id, db.scheme_id} == {"S001", "S002"} and shared_features:
                    strength = len(shared_features) / max(
                        len(set(da.feature_names) | set(db.feature_names)), 1
                    )
                    _add(da, db, RelationshipType.COMPLEMENTARY.value, strength,
                         f"Winner/Loser complementary pair on features {sorted(shared_features)}")

                # CORRELATED: share features but not S001+S002
                elif shared_features or shared_dna:
                    strength = (len(shared_features) + len(shared_dna)) / max(
                        len(set(da.feature_names) | set(db.feature_names)
                            | set(da.dna_ids) | set(db.dna_ids)), 1
                    )
                    if strength >= 0.30:
                        _add(da, db, RelationshipType.CORRELATED.value, strength,
                             f"Share features/DNA: {sorted(shared_features | shared_dna)[:3]}")

                # ENABLES: S015 context-dependency enables S001 winner
                if {da.scheme_id, db.scheme_id} == {"S015", "S001"} and shared_features:
                    s015 = da if da.scheme_id == "S015" else db
                    s001 = da if da.scheme_id == "S001" else db
                    _add(s015, s001, RelationshipType.ENABLES.value, 0.65,
                         f"Context-dependency enables winner signal on {sorted(shared_features)}")

                # SUBSUMES: S014 persistence discovery spans more years than another
                if da.scheme_id == "S014" and shared_dna:
                    years_a = set(da.years_observed)
                    years_b = set(db.years_observed)
                    if years_b and years_b.issubset(years_a) and years_a != years_b:
                        _add(da, db, RelationshipType.SUBSUMES.value, 0.70,
                             f"Cross-year persistence subsumes narrower discovery on {sorted(shared_dna)}")

        return relationships
