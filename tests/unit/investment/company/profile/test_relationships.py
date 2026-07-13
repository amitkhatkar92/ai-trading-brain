"""tests/unit/investment/company/profile/test_relationships.py"""
from __future__ import annotations

import pytest

from iios.investment.company.profile.models import RelatedEntity, RelationshipType, Subsidiary
from iios.investment.company.profile.ownership_tree import OwnershipNode, OwnershipTree
from iios.investment.company.profile.parent_company import ParentRelationship
from iios.investment.company.profile.related_entities import RelatedEntityStore
from iios.investment.company.profile.subsidiaries import SubsidiaryStore


class TestSubsidiaryStore:
    def test_add_and_retrieve(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("Jio", 85.0, "IN", RelationshipType.SUBSIDIARY))
        assert len(store) == 1

    def test_replaces_same_name(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("Jio", 85.0, "IN"))
        store.add(Subsidiary("Jio", 90.0, "IN"))
        assert len(store) == 1
        assert store.all()[0].ownership_pct == pytest.approx(90.0)

    def test_remove(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("Jio", 85.0, "IN"))
        assert store.remove("Jio") is True
        assert len(store) == 0

    def test_wholly_owned(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("A", 100.0, "IN"))
        store.add(Subsidiary("B",  75.0, "IN"))
        assert len(store.wholly_owned()) == 1

    def test_majority_owned(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("A", 100.0, "IN"))
        store.add(Subsidiary("B",  75.0, "IN"))
        store.add(Subsidiary("C",  30.0, "IN"))
        assert len(store.majority_owned()) == 1

    def test_by_country(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("A", 100.0, "IN"))
        store.add(Subsidiary("B",  80.0, "US"))
        by_country = store.by_country()
        assert "IN" in by_country
        assert "US" in by_country

    def test_listed(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("A", 100.0, "IN", RelationshipType.SUBSIDIARY, "ATICO"))
        store.add(Subsidiary("B",  80.0, "IN", RelationshipType.SUBSIDIARY, None))
        assert len(store.listed()) == 1

    def test_find_by_ticker(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("A", 100.0, "IN", RelationshipType.SUBSIDIARY, "ATICO"))
        assert store.find_by_ticker("ATICO") is not None
        assert store.find_by_ticker("UNKNOWN") is None

    def test_countries(self):
        store = SubsidiaryStore()
        store.add(Subsidiary("A", 100.0, "IN"))
        store.add(Subsidiary("B", 100.0, "US"))
        assert set(store.countries()) == {"IN", "US"}


class TestRelatedEntityStore:
    def test_add_and_retrieve(self):
        store = RelatedEntityStore()
        ent   = RelatedEntity.new("Network18", RelationshipType.ASSOCIATE)
        store.add(ent)
        assert len(store) == 1

    def test_no_duplicate_entity_id(self):
        store = RelatedEntityStore()
        ent   = RelatedEntity.new("X", RelationshipType.ASSOCIATE)
        store.add(ent)
        store.add(ent)
        assert len(store) == 1

    def test_remove(self):
        store = RelatedEntityStore()
        ent   = RelatedEntity.new("X", RelationshipType.ASSOCIATE)
        store.add(ent)
        assert store.remove(ent.entity_id) is True
        assert len(store) == 0

    def test_by_type(self):
        store = RelatedEntityStore()
        store.add(RelatedEntity.new("JV1", RelationshipType.JOINT_VENTURE))
        store.add(RelatedEntity.new("JV2", RelationshipType.JOINT_VENTURE))
        store.add(RelatedEntity.new("AS1", RelationshipType.ASSOCIATE))
        assert len(store.joint_ventures()) == 2
        assert len(store.associates()) == 1

    def test_find_by_ticker(self):
        store = RelatedEntityStore()
        ent   = RelatedEntity.new("X", RelationshipType.ASSOCIATE, ticker="XYZ")
        store.add(ent)
        assert store.find_by_ticker("XYZ") is not None
        assert store.find_by_ticker("UNKNOWN") is None


class TestParentRelationship:
    def test_no_parent(self):
        pr = ParentRelationship()
        assert pr.has_parent is False

    def test_with_parent(self):
        pr = ParentRelationship(parent_ticker="PARENT", ownership_pct=60.0)
        assert pr.has_parent is True
        assert pr.is_majority_owned is True
        assert pr.is_wholly_owned is False

    def test_wholly_owned(self):
        pr = ParentRelationship(parent_ticker="PARENT", ownership_pct=100.0)
        assert pr.is_wholly_owned is True

    def test_update(self):
        pr = ParentRelationship()
        pr.update(parent_ticker="NEW", ownership_pct=51.0)
        assert pr.parent_ticker == "NEW"
        assert pr.is_subsidiary is True

    def test_to_dict(self):
        pr = ParentRelationship(parent_ticker="P", parent_name="Parent Corp",
                                ownership_pct=75.0, is_subsidiary=True)
        d  = pr.to_dict()
        assert d["parent_ticker"] == "P"
        assert d["ownership_pct"] == pytest.approx(75.0)


class TestOwnershipTree:
    def test_root_node(self):
        tree = OwnershipTree("RIL", "Reliance Industries")
        root = tree.root()
        assert root.ticker == "RIL"
        assert root.name   == "Reliance Industries"

    def test_add_subsidiary(self):
        tree = OwnershipTree("RIL", "Reliance Industries")
        tree.add_subsidiary(Subsidiary("Jio", 85.0, "IN", RelationshipType.SUBSIDIARY, "JIOLT"))
        assert len(tree.root().children) == 1

    def test_total_entities(self):
        tree = OwnershipTree("RIL", "Reliance Industries")
        tree.add_subsidiary(Subsidiary("Jio",    85.0, "IN"))
        tree.add_subsidiary(Subsidiary("Retail", 100.0, "IN"))
        assert tree.total_entities() == 3   # root + 2 subsidiaries

    def test_depth_no_children(self):
        tree = OwnershipTree("ROOT", "Root")
        assert tree.depth() == 0

    def test_depth_one_level(self):
        tree = OwnershipTree("ROOT", "Root")
        tree.add_subsidiary(Subsidiary("Child", 100.0, "IN"))
        assert tree.depth() == 1

    def test_set_parent(self):
        tree = OwnershipTree("SUB", "Subsidiary")
        tree.set_parent("PARENT", "Parent Corp", 80.0)
        root = tree.root()
        assert root.name == "Parent Corp"
        assert len(root.children) == 1

    def test_to_dict_serialisable(self):
        import json
        tree = OwnershipTree("RIL", "Reliance")
        tree.add_subsidiary(Subsidiary("Jio", 85.0, "IN"))
        json.dumps(tree.to_dict())

    def test_all_nodes_bfs(self):
        tree = OwnershipTree("ROOT", "Root")
        tree.add_subsidiary(Subsidiary("A", 100.0, "IN"))
        tree.add_subsidiary(Subsidiary("B",  80.0, "IN"))
        nodes = tree.all_nodes()
        assert len(nodes) == 3
        assert nodes[0].ticker == "ROOT"
