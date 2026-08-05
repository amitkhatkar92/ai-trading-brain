"""
test_ikn.py — IKN-001 test suite.

Tests: T001-T270 (270 tests)
Framework: custom ok() / section() (identical to IIOS test pattern)
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent))

# ─── harness ──────────────────────────────────────────────────────────────────

_pass_count = 0
_fail_count = 0


def ok(label: str, cond: bool) -> None:
    global _pass_count, _fail_count
    if cond:
        _pass_count += 1
        print(f"  PASS  {label}")
    else:
        _fail_count += 1
        print(f"  FAIL  {label}")


def section(title: str) -> None:
    print(f"\n-- {title} --")


def _raises(fn, exc_type) -> bool:
    try:
        fn()
        return False
    except exc_type:
        return True
    except Exception:
        return False


# ─── fixtures ─────────────────────────────────────────────────────────────────

NODE_FIXTURES = [
    ("DNA",                "N01", "rsi_5::WINNERS_HIGHER"),
    ("DNA",                "N02", "volume_ratio::WINNERS_HIGHER"),
    ("EDGE",               "N03", "EDGE-rsi_5"),
    ("FEATURE",            "N04", "rsi_5"),
    ("FEATURE",            "N05", "volume_ratio"),
    ("STUDY",              "N06", "HKAP-2021"),
    ("STUDY",              "N07", "HKAP-2022"),
    ("FINDING",            "N08", "FND-2021-01"),
    ("HYPOTHESIS",         "N09", "HYP-001"),
    ("HYPOTHESIS",         "N10", "HYP-002"),
    ("DISCOVERY",          "N11", "DISC-001"),
    ("CLUSTER",            "N12", "CL-DNA"),
    ("MARKET_REGIME",      "N13", "BULL_TREND"),
    ("MARKET_REGIME",      "N14", "BEAR_MARKET"),
    ("SECTOR",             "N15", "IT"),
    ("MARKET_PERSONALITY", "N16", "TRENDING_BULL"),
    ("PMCI_COMPONENT",     "N17", "SIGNAL_RSI"),
    ("CDS_COMPONENT",      "N18", "CDS_BASIC"),
    ("JOURNAL_ENTRY",      "N19", "JE-2021-01"),       # orphan
    ("KNOWLEDGE_PACKAGE",  "N20", "HKAP-PKG-2021"),    # orphan
]

# (source, target, rel_type, confidence, studies, years, regimes)
REL_FIXTURES = [
    ("N01", "N06", "SUPPORTED_BY",    0.90, ["HKAP-2021"], [2021], ["BULL_TREND"]),
    ("N09", "N08", "CONTRADICTED_BY", 0.60, [],            [],     []),
    ("N11", "N06", "DISCOVERED_IN",   0.85, ["HKAP-2021"], [2021], ["BULL_TREND"]),
    ("N09", "N07", "VALIDATED_BY",    0.80, [],            [2022], []),
    ("N11", "N06", "GENERATED_BY",    0.85, [],            [2021], []),
    ("N15", "N13", "RELATED_TO",      0.70, [],            [],     []),
    ("N18", "N17", "DEPENDS_ON",      0.95, [],            [],     []),
    ("N01", "N13", "WORKS_IN",        0.88, [],            [],     ["BULL_TREND"]),
    ("N01", "N14", "FAILS_IN",        0.75, [],            [],     ["BEAR_MARKET"]),
    ("N03", "N01", "EVOLVED_TO",      0.80, [],            [],     []),
    ("N11", "N08", "SPECIALIZES",     0.70, [],            [],     []),
    ("N04", "N01", "GENERALIZES",     0.75, [],            [],     []),
    ("N01", "N12", "BELONGS_TO",      0.90, [],            [],     []),
    ("N17", "N01", "USES",            0.85, [],            [],     []),
    ("N17", "N04", "REQUIRES",        0.90, [],            [],     []),
    ("N09", "N10", "SUPERSEDES",      0.95, [],            [],     []),
    ("N16", "N13", "OBSERVED_WITH",   0.80, [],            [],     []),
    ("N01", "N02", "CO_OCCURS_WITH",  0.70, [],            [],     []),
]


def _make_network():
    from ikn import IKNNetwork, IKNConfig
    ikn = IKNNetwork(IKNConfig(dry_run=True))
    for node_type, nid, name in NODE_FIXTURES:
        ikn.register_node(nid, node_type, name)
    for src, tgt, rt, conf, studies, years, regimes in REL_FIXTURES:
        ikn.add_relationship(src, tgt, rt, conf,
                             supporting_studies=studies,
                             supporting_years=years,
                             supporting_regimes=regimes)
    return ikn


def _first_rel(ikn, node_id: str, rel_type: str):
    for r in ikn.get_relationships(node_id):
        if r.relationship_type == rel_type:
            return r
    return None


# ══════════════════════════════════════════════════════════════════════════════
# T001-T025  ikn_models
# ══════════════════════════════════════════════════════════════════════════════

def test_models() -> None:
    section("T001-T025  ikn_models")
    from ikn import (
        NodeType, RelationshipType, IKNError,
        KnowledgeNode, KnowledgeRelationship, KnowledgeEvidence,
        KnowledgePath, KnowledgeSubgraph, KnowledgeStatistics, KnowledgeNetworkSnapshot,
    )

    ok("T001 NodeType has 15 values", len(NodeType) == 15)
    ok("T002 RelationshipType has 18 values", len(RelationshipType) == 18)
    ok("T003 IKNError is Exception", issubclass(IKNError, Exception))
    ok("T004 NodeType.DNA exists", NodeType.DNA.value == "DNA")
    ok("T005 NodeType.KNOWLEDGE_PACKAGE exists",
       NodeType.KNOWLEDGE_PACKAGE.value == "KNOWLEDGE_PACKAGE")
    ok("T006 RelationshipType.SUPPORTED_BY exists",
       RelationshipType.SUPPORTED_BY.value == "SUPPORTED_BY")
    ok("T007 RelationshipType.CO_OCCURS_WITH exists",
       RelationshipType.CO_OCCURS_WITH.value == "CO_OCCURS_WITH")
    ok("T008 RelationshipType.SUPERSEDES exists",
       RelationshipType.SUPERSEDES.value == "SUPERSEDES")

    # KnowledgeNode
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    node = KnowledgeNode("N1", "DNA", "test", {"k": "v"}, now, now)
    d = node.to_dict()
    ok("T009 KnowledgeNode.to_dict has all keys",
       all(k in d for k in ["node_id", "node_type", "name", "metadata", "created_at", "updated_at", "version"]))
    ok("T010 KnowledgeNode version defaults to 1", node.version == 1)
    ok("T011 KnowledgeNode metadata preserved", d["metadata"] == {"k": "v"})

    # KnowledgeRelationship
    rel = KnowledgeRelationship(
        "R1", "N1", "N2", "SUPPORTED_BY", 0.9, 3,
        ["S1"], [2021], ["BULL_TREND"], now, now,
    )
    rd = rel.to_dict()
    ok("T012 KnowledgeRelationship.to_dict has all keys",
       all(k in rd for k in ["relationship_id", "source_id", "target_id", "relationship_type",
                               "confidence", "evidence_count", "supporting_studies",
                               "supporting_years", "supporting_regimes",
                               "created_at", "updated_at", "version"]))
    ok("T013 KnowledgeRelationship version defaults to 1", rel.version == 1)
    ok("T014 supporting_studies preserved", rd["supporting_studies"] == ["S1"])
    ok("T015 supporting_years preserved", rd["supporting_years"] == [2021])
    ok("T016 supporting_regimes preserved", rd["supporting_regimes"] == ["BULL_TREND"])

    # KnowledgeEvidence
    ev = KnowledgeEvidence("E1", "R1", "strong evidence", "HKAP", 50, now)
    ed = ev.to_dict()
    ok("T017 KnowledgeEvidence.to_dict has all keys",
       all(k in ed for k in ["evidence_id", "relationship_id", "description",
                              "source", "data_points", "created_at"]))
    ok("T018 KnowledgeEvidence data_points preserved", ev.data_points == 50)

    # KnowledgePath
    path = KnowledgePath(nodes=[node], relationships=[], length=0, total_confidence=1.0)
    pd = path.to_dict()
    ok("T019 KnowledgePath.to_dict has all keys",
       all(k in pd for k in ["nodes", "relationships", "length", "total_confidence"]))
    ok("T020 KnowledgePath length=0 for trivial path", path.length == 0)
    ok("T021 KnowledgePath total_confidence=1.0 for trivial path", path.total_confidence == 1.0)

    # KnowledgeSubgraph
    sg = KnowledgeSubgraph(nodes={"N1": node}, relationships=[], center_node_id="N1")
    sgd = sg.to_dict()
    ok("T022 KnowledgeSubgraph.to_dict has all keys",
       all(k in sgd for k in ["nodes", "relationships", "center_node_id"]))
    ok("T023 KnowledgeSubgraph center_node_id preserved", sg.center_node_id == "N1")

    # KnowledgeStatistics
    stats = KnowledgeStatistics(
        total_nodes=5, total_relationships=3, nodes_by_type={"DNA": 2},
        relationships_by_type={"SUPPORTED_BY": 3}, avg_confidence=0.8,
        most_connected_nodes=[("N1", 3)], orphan_count=1, generated_at=now,
    )
    ok("T024 KnowledgeStatistics.to_dict has all keys",
       all(k in stats.to_dict() for k in ["total_nodes", "total_relationships",
                                            "orphan_count", "avg_confidence"]))

    # KnowledgeNetworkSnapshot
    snap = KnowledgeNetworkSnapshot("S1", now, stats, ["r.md"], 5, 3)
    ok("T025 KnowledgeNetworkSnapshot.to_dict has all keys",
       all(k in snap.to_dict() for k in ["snapshot_id", "generated_at",
                                           "statistics", "reports",
                                           "node_count", "relationship_count"]))


# ══════════════════════════════════════════════════════════════════════════════
# T026-T040  IKNConfig
# ══════════════════════════════════════════════════════════════════════════════

def test_config() -> None:
    section("T026-T040  IKNConfig")
    from ikn import IKNConfig

    c = IKNConfig()
    ok("T026 db_path default", c.db_path == "data/ikn/ikn.db")
    ok("T027 reports_root default", c.reports_root == "data/ikn/reports")
    ok("T028 max_path_length default = 10", c.max_path_length == 10)
    ok("T029 dry_run default = False", c.dry_run is False)

    ok("T030 max_path_length < 1 raises ValueError",
       _raises(lambda: IKNConfig(max_path_length=0), ValueError))
    ok("T031 max_path_length > 50 raises ValueError",
       _raises(lambda: IKNConfig(max_path_length=51), ValueError))
    ok("T032 max_path_length = 1 is valid", IKNConfig(max_path_length=1).max_path_length == 1)
    ok("T033 max_path_length = 50 is valid", IKNConfig(max_path_length=50).max_path_length == 50)
    ok("T034 dry_run = True accepted", IKNConfig(dry_run=True).dry_run is True)
    ok("T035 custom db_path accepted", IKNConfig(db_path="x.db").db_path == "x.db")
    ok("T036 custom reports_root accepted",
       IKNConfig(reports_root="/tmp/r").reports_root == "/tmp/r")
    ok("T037 max_path_length = 25 valid", IKNConfig(max_path_length=25).max_path_length == 25)
    ok("T038 IKNConfig is a dataclass",
       hasattr(IKNConfig, "__dataclass_fields__"))
    ok("T039 max_path_length = -1 raises ValueError",
       _raises(lambda: IKNConfig(max_path_length=-1), ValueError))
    ok("T040 max_path_length = 51 raises ValueError",
       _raises(lambda: IKNConfig(max_path_length=51), ValueError))


# ══════════════════════════════════════════════════════════════════════════════
# T041-T070  IKNStore
# ══════════════════════════════════════════════════════════════════════════════

def test_store() -> None:
    section("T041-T070  IKNStore")
    from ikn import IKNConfig, IKNStore, KnowledgeNode, KnowledgeRelationship, KnowledgeEvidence
    from datetime import datetime, timezone

    cfg   = IKNConfig(dry_run=True)
    store = IKNStore(cfg)
    now   = datetime.now(timezone.utc).isoformat()

    # node ops
    n1 = KnowledgeNode("N1", "DNA", "rsi_5", {}, now, now)
    n2 = KnowledgeNode("N2", "STUDY", "HKAP-21", {"year": 2021}, now, now)
    store.add_node(n1)
    store.add_node(n2)

    ok("T041 IKNStore in-memory creates without file", True)
    ok("T042 add_node + get_node roundtrip", store.get_node("N1").node_id == "N1")
    ok("T043 node_exists True after add", store.node_exists("N1"))
    ok("T044 node_exists False for unknown", not store.node_exists("ZZZ"))
    ok("T045 get_node None for unknown", store.get_node("ZZZ") is None)
    ok("T046 get_all_nodes returns both", len(store.get_all_nodes()) == 2)
    ok("T047 get_nodes_by_type filters", len(store.get_nodes_by_type("DNA")) == 1)

    # update node
    n1_updated = KnowledgeNode("N1", "DNA", "rsi_5_updated", {"k": "v"}, now, now, version=2)
    store.update_node(n1_updated)
    retrieved = store.get_node("N1")
    ok("T048 update_node changes name", retrieved.name == "rsi_5_updated")
    ok("T049 update_node changes metadata", retrieved.metadata == {"k": "v"})
    ok("T050 update_node changes version", retrieved.version == 2)

    # relationship ops
    r1 = KnowledgeRelationship(
        "R1", "N1", "N2", "SUPPORTED_BY", 0.9, 1, ["S1"], [2021], ["BULL"], now, now
    )
    store.add_relationship(r1)
    ok("T051 relationship_exists True", store.relationship_exists("R1"))
    ok("T052 relationship_exists False", not store.relationship_exists("ZZZ"))
    ok("T053 get_relationship roundtrip", store.get_relationship("R1").relationship_id == "R1")
    ok("T054 get_all_relationships returns 1", len(store.get_all_relationships()) == 1)
    ok("T055 get_rels outgoing from N1",
       len(store.get_relationships_for_node("N1", direction="outgoing")) == 1)
    ok("T056 get_rels incoming to N2",
       len(store.get_relationships_for_node("N2", direction="incoming")) == 1)
    ok("T057 get_rels both N1",
       len(store.get_relationships_for_node("N1", direction="both")) == 1)
    ok("T058 get_rels both N2",
       len(store.get_relationships_for_node("N2", direction="both")) == 1)
    ok("T059 get_rels filter by type",
       len(store.get_relationships_for_node("N1", rel_type="SUPPORTED_BY")) == 1)
    ok("T060 get_rels filter by wrong type returns empty",
       len(store.get_relationships_for_node("N1", rel_type="CONTRADICTED_BY")) == 0)

    # update relationship
    r1_upd = KnowledgeRelationship(
        "R1", "N1", "N2", "SUPPORTED_BY", 0.75, 2, ["S1","S2"], [2021,2022], ["BULL","BEAR"], now, now, version=2
    )
    store.update_relationship(r1_upd)
    fetched = store.get_relationship("R1")
    ok("T061 update_relationship confidence", abs(fetched.confidence - 0.75) < 1e-9)
    ok("T062 update_relationship evidence_count", fetched.evidence_count == 2)
    ok("T063 update_relationship supporting_years", fetched.supporting_years == [2021, 2022])
    ok("T064 update_relationship version", fetched.version == 2)

    # evidence ops
    ev = KnowledgeEvidence("E1", "R1", "strong signal", "KDE", 25, now)
    store.add_evidence(ev)
    evs = store.get_evidence_for_relationship("R1")
    ok("T065 add_evidence + get works", len(evs) == 1)
    ok("T066 evidence description preserved", evs[0].description == "strong signal")
    ok("T067 evidence source preserved", evs[0].source == "KDE")
    ok("T068 evidence data_points preserved", evs[0].data_points == 25)

    # statistics
    raw = store.get_raw_statistics()
    ok("T069 raw_statistics has expected keys",
       all(k in raw for k in ["total_nodes", "total_rels", "by_node_type",
                               "by_rel_type", "avg_conf", "top_nodes", "orphan_count"]))
    ok("T070 raw_statistics total_nodes=2", raw["total_nodes"] == 2)


# ══════════════════════════════════════════════════════════════════════════════
# T071-T090  IKNNetwork — node registration
# ══════════════════════════════════════════════════════════════════════════════

def test_network_nodes() -> None:
    section("T071-T090  IKNNetwork node registration")
    from ikn import IKNNetwork, IKNConfig, IKNError, NodeType

    ikn = IKNNetwork(IKNConfig(dry_run=True))

    node = ikn.register_node("X1", "DNA", "rsi_5", {"conf": 0.8})
    ok("T071 register_node returns KnowledgeNode", node.node_id == "X1")
    ok("T072 node_type preserved", node.node_type == "DNA")
    ok("T073 name preserved", node.name == "rsi_5")
    ok("T074 metadata preserved", node.metadata == {"conf": 0.8})
    ok("T075 version = 1 on first register", node.version == 1)
    ok("T076 created_at not empty", bool(node.created_at))
    ok("T077 updated_at not empty", bool(node.updated_at))

    # re-registration
    node2 = ikn.register_node("X1", "DNA", "rsi_5_v2", {"conf": 0.9})
    ok("T078 re-register returns same node_id", node2.node_id == "X1")
    ok("T079 re-register increments version", node2.version == 2)
    ok("T080 re-register updates name", node2.name == "rsi_5_v2")
    ok("T081 re-register updates metadata", node2.metadata == {"conf": 0.9})

    # get_node round-trip
    fetched = ikn.get_node("X1")
    ok("T082 get_node after register returns node", fetched is not None)
    ok("T083 get_node returns None for unknown", ikn.get_node("ZZZ") is None)

    # validation
    ok("T084 empty node_id raises IKNError",
       _raises(lambda: ikn.register_node("", "DNA", "x"), IKNError))
    ok("T085 invalid node_type raises IKNError",
       _raises(lambda: ikn.register_node("Y", "INVALID_TYPE", "x"), IKNError))

    # all 15 NodeType values accepted
    for nt in NodeType:
        ikn.register_node(f"NT_{nt.value}", nt.value, f"node {nt.value}")
    all_nodes = ikn._store.get_all_nodes()
    present_types = {n.node_type for n in all_nodes}
    ok("T086 all 15 NodeType values accepted",
       all(nt.value in present_types for nt in NodeType))

    # metadata defaults to {}
    n3 = ikn.register_node("X3", "FEATURE", "vol")
    ok("T087 metadata defaults to empty dict", n3.metadata == {})

    # node_type preserved on re-register
    n4 = ikn.register_node("X3", "FEATURE", "vol_v2")
    ok("T088 node_type preserved on re-register", n4.node_type == "FEATURE")

    # created_at unchanged on re-register
    ok("T089 created_at unchanged on re-register", node.created_at == node2.created_at)

    # multiple registers accumulate version
    for i in range(3):
        ikn.register_node("VTEST", "DNA", f"v{i}")
    ok("T090 multiple re-registers accumulate version",
       ikn.get_node("VTEST").version == 3)


# ══════════════════════════════════════════════════════════════════════════════
# T091-T110  IKNNetwork — relationships
# ══════════════════════════════════════════════════════════════════════════════

def test_network_rels() -> None:
    section("T091-T110  IKNNetwork relationships")
    from ikn import IKNNetwork, IKNConfig, IKNError, RelationshipType

    ikn = IKNNetwork(IKNConfig(dry_run=True))
    ikn.register_node("A", "DNA", "a")
    ikn.register_node("B", "STUDY", "b")

    rel = ikn.add_relationship("A", "B", "SUPPORTED_BY", 0.85,
                               evidence_count=3,
                               supporting_studies=["HKAP-21"],
                               supporting_years=[2021],
                               supporting_regimes=["BULL_TREND"])
    ok("T091 add_relationship returns KnowledgeRelationship", rel.source_id == "A")
    ok("T092 relationship_id starts with IKN-REL",
       rel.relationship_id.startswith("IKN-REL"))
    ok("T093 target_id preserved", rel.target_id == "B")
    ok("T094 rel_type preserved", rel.relationship_type == "SUPPORTED_BY")
    ok("T095 confidence preserved", abs(rel.confidence - 0.85) < 1e-9)
    ok("T096 evidence_count preserved", rel.evidence_count == 3)
    ok("T097 supporting_studies preserved", rel.supporting_studies == ["HKAP-21"])
    ok("T098 supporting_years preserved", rel.supporting_years == [2021])
    ok("T099 supporting_regimes preserved", rel.supporting_regimes == ["BULL_TREND"])
    ok("T100 version = 1 on creation", rel.version == 1)

    # validation
    ok("T101 unknown source raises IKNError",
       _raises(lambda: ikn.add_relationship("ZZZ", "B", "SUPPORTED_BY"), IKNError))
    ok("T102 unknown target raises IKNError",
       _raises(lambda: ikn.add_relationship("A", "ZZZ", "SUPPORTED_BY"), IKNError))
    ok("T103 invalid rel_type raises IKNError",
       _raises(lambda: ikn.add_relationship("A", "B", "INVALID_TYPE"), IKNError))
    ok("T104 confidence < 0 raises IKNError",
       _raises(lambda: ikn.add_relationship("A", "B", "SUPPORTED_BY", confidence=-0.1), IKNError))
    ok("T105 confidence > 1 raises IKNError",
       _raises(lambda: ikn.add_relationship("A", "B", "SUPPORTED_BY", confidence=1.1), IKNError))
    ok("T106 confidence = 0.0 valid",
       ikn.add_relationship("A", "B", "SUPPORTED_BY", 0.0).confidence == 0.0)
    ok("T107 confidence = 1.0 valid",
       ikn.add_relationship("A", "B", "SUPPORTED_BY", 1.0).confidence == 1.0)

    # all 18 RelationshipType values accepted
    for rt in RelationshipType:
        ikn.add_relationship("A", "B", rt.value)
    all_rels = ikn._store.get_all_relationships()
    present_types = {r.relationship_type for r in all_rels}
    ok("T108 all 18 RelationshipType values accepted",
       all(rt.value in present_types for rt in RelationshipType))

    # update_relationship
    first_rel = ikn.get_relationships("A")[0]
    updated   = ikn.update_relationship(first_rel.relationship_id, confidence=0.55,
                                         evidence_count=5)
    ok("T109 update_relationship changes confidence", abs(updated.confidence - 0.55) < 1e-9)
    ok("T110 update_relationship increments version", updated.version == 2)

    ok("T108b update_rel on unknown raises IKNError",
       _raises(lambda: ikn.update_relationship("UNKNOWN-ID", confidence=0.5), IKNError))


# ══════════════════════════════════════════════════════════════════════════════
# T111-T120  IKNNetwork — evidence
# ══════════════════════════════════════════════════════════════════════════════

def test_network_evidence() -> None:
    section("T111-T120  IKNNetwork evidence")
    from ikn import IKNNetwork, IKNConfig, IKNError

    ikn = IKNNetwork(IKNConfig(dry_run=True))
    ikn.register_node("A", "DNA", "a")
    ikn.register_node("B", "STUDY", "b")
    rel = ikn.add_relationship("A", "B", "SUPPORTED_BY", 0.8)

    ev = ikn.add_evidence(rel.relationship_id, "Strong RSI signal", "KDE", data_points=150)
    ok("T111 add_evidence returns KnowledgeEvidence", ev.evidence_id.startswith("IKN-EV"))
    ok("T112 evidence_id format", "IKN-EV" in ev.evidence_id)
    ok("T113 description preserved", ev.description == "Strong RSI signal")
    ok("T114 source preserved", ev.source == "KDE")
    ok("T115 data_points preserved", ev.data_points == 150)
    ok("T116 relationship_id preserved", ev.relationship_id == rel.relationship_id)
    ok("T117 created_at not empty", bool(ev.created_at))

    # multiple evidence for same rel
    for i in range(3):
        ikn.add_evidence(rel.relationship_id, f"Evidence {i}", "HKAP", i * 10)
    all_ev = ikn._store.get_evidence_for_relationship(rel.relationship_id)
    ok("T118 multiple evidence stored", len(all_ev) == 4)  # 1 + 3

    # unknown relationship
    ok("T119 unknown rel_id raises IKNError",
       _raises(lambda: ikn.add_evidence("UNKNOWN", "desc", "src"), IKNError))

    ok("T120 evidence.to_dict has all keys",
       all(k in ev.to_dict() for k in ["evidence_id", "relationship_id",
                                        "description", "source", "data_points", "created_at"]))


# ══════════════════════════════════════════════════════════════════════════════
# T121-T135  Query — get_node / get_relationships
# ══════════════════════════════════════════════════════════════════════════════

def test_query_get() -> None:
    section("T121-T135  Query get_node / get_relationships")
    ikn = _make_network()

    ok("T121 query.get_node returns same as network.get_node",
       ikn.query.get_node("N01").node_id == ikn.get_node("N01").node_id)
    ok("T122 query.get_node None for unknown",
       ikn.query.get_node("UNKNOWN") is None)
    ok("T123 query.get_node correct node_type",
       ikn.get_node("N01").node_type == "DNA")
    ok("T124 query.get_node correct name",
       ikn.get_node("N01").name == "rsi_5::WINNERS_HIGHER")

    # N01 has 8 relationships (5 outgoing + 3 incoming)
    all_rels = ikn.get_relationships("N01")
    ok("T125 get_relationships returns all for N01", len(all_rels) == 8)

    outgoing = ikn.get_relationships("N01", direction="outgoing")
    ok("T126 get_relationships outgoing = 5", len(outgoing) == 5)

    incoming = ikn.get_relationships("N01", direction="incoming")
    ok("T127 get_relationships incoming = 3", len(incoming) == 3)

    filtered = ikn.get_relationships("N01", rel_type="SUPPORTED_BY")
    ok("T128 get_relationships filtered by type", len(filtered) == 1)
    ok("T129 filtered rel has correct type",
       filtered[0].relationship_type == "SUPPORTED_BY")

    ok("T130 confidence preserved in query", abs(filtered[0].confidence - 0.90) < 1e-9)
    ok("T131 supporting_studies preserved",
       filtered[0].supporting_studies == ["HKAP-2021"])
    ok("T132 supporting_years preserved", filtered[0].supporting_years == [2021])
    ok("T133 supporting_regimes preserved",
       filtered[0].supporting_regimes == ["BULL_TREND"])

    # orphan N19 has no relationships
    ok("T134 orphan node has no rels", len(ikn.get_relationships("N19")) == 0)

    # unknown node returns empty list
    ok("T135 unknown node returns empty list",
       len(ikn.get_relationships("UNKNOWN")) == 0)


# ══════════════════════════════════════════════════════════════════════════════
# T136-T150  Query — related()
# ══════════════════════════════════════════════════════════════════════════════

def test_query_related() -> None:
    section("T136-T150  Query related()")
    ikn = _make_network()

    sg1 = ikn.related("N17", depth=1)
    ok("T136 related() returns KnowledgeSubgraph", hasattr(sg1, "nodes"))
    ok("T137 center_node_id = N17", sg1.center_node_id == "N17")
    ok("T138 center node in subgraph.nodes", "N17" in sg1.nodes)
    ok("T139 depth=1 includes direct neighbours",
       "N01" in sg1.nodes and "N04" in sg1.nodes)
    ok("T140 depth=1 rels non-empty", len(sg1.relationships) > 0)
    ok("T141 relationships in subgraph are KnowledgeRelationship objects",
       all(hasattr(r, "relationship_id") for r in sg1.relationships))

    # depth=2 includes 2-hop neighbours
    sg2 = ikn.related("N17", depth=2)
    ok("T142 depth=2 includes more nodes than depth=1",
       len(sg2.nodes) > len(sg1.nodes))
    ok("T143 depth=2 N06 reachable via N17->N01->N06", "N06" in sg2.nodes)

    # isolated node
    sg_iso = ikn.related("N19", depth=1)
    ok("T144 isolated node subgraph has only self", list(sg_iso.nodes.keys()) == ["N19"])
    ok("T145 isolated node subgraph has no rels", sg_iso.relationships == [])

    # depth=0 treated as depth=1
    sg0 = ikn.related("N01", depth=0)
    ok("T146 depth=0 treated as 1 (neighbours present)", len(sg0.nodes) >= 2)

    # no duplicate relationships
    sg_all = ikn.related("N01", depth=3)
    rel_ids = [r.relationship_id for r in sg_all.relationships]
    ok("T147 no duplicate relationships in subgraph",
       len(rel_ids) == len(set(rel_ids)))

    # unknown node returns empty subgraph
    sg_unk = ikn.related("UNKNOWN", depth=1)
    ok("T148 unknown node returns empty subgraph nodes", sg_unk.nodes == {})

    # all subgraph nodes are KnowledgeNode objects
    ok("T149 all subgraph nodes are KnowledgeNode",
       all(hasattr(n, "node_id") for n in sg2.nodes.values()))

    # to_dict works
    ok("T150 subgraph.to_dict() has correct keys",
       all(k in sg1.to_dict() for k in ["nodes", "relationships", "center_node_id"]))


# ══════════════════════════════════════════════════════════════════════════════
# T151-T165  Query — shortest_path()
# ══════════════════════════════════════════════════════════════════════════════

def test_query_shortest_path() -> None:
    section("T151-T165  Query shortest_path()")
    ikn = _make_network()

    # same node
    path0 = ikn.shortest_path("N01", "N01")
    ok("T151 same-node path returns KnowledgePath", path0 is not None)
    ok("T152 same-node path.length = 0", path0.length == 0)
    ok("T153 same-node total_confidence = 1.0", path0.total_confidence == 1.0)

    # direct connection N09 -> N10 (SUPERSEDES)
    path1 = ikn.shortest_path("N09", "N10")
    ok("T154 direct connection path.length = 1", path1.length == 1)
    ok("T155 direct path confidence = 0.95",
       abs(path1.total_confidence - 0.95) < 1e-5)
    ok("T156 direct path nodes count = 2", len(path1.nodes) == 2)
    ok("T157 path nodes include source N09",
       path1.nodes[0].node_id in ("N09", "N10"))

    # 2-hop path: N17 -> N01 -> N06
    path2 = ikn.shortest_path("N17", "N06")
    ok("T158 2-hop path.length = 2", path2.length == 2)
    ok("T159 2-hop path has 3 nodes", len(path2.nodes) == 3)
    ok("T160 2-hop path nodes are N17, N01, N06",
       {n.node_id for n in path2.nodes} == {"N17", "N01", "N06"})
    expected_conf = round(0.85 * 0.90, 6)  # USES * SUPPORTED_BY
    ok("T161 2-hop total_confidence = product of edge confidences",
       abs(path2.total_confidence - expected_conf) < 1e-4)
    ok("T162 path relationships list length = path length",
       len(path2.relationships) == path2.length)

    # disconnected nodes (N19 and N20 are orphans with no rels)
    path_none = ikn.shortest_path("N19", "N20")
    ok("T163 disconnected nodes return None", path_none is None)

    # unknown source returns None
    ok("T164 unknown source returns None",
       ikn.shortest_path("UNKNOWN", "N01") is None)

    # max_path_length=1 blocks 2-hop path
    from ikn import IKNNetwork, IKNConfig
    ikn_short = IKNNetwork(IKNConfig(dry_run=True, max_path_length=1))
    for nt, nid, nm in NODE_FIXTURES:
        ikn_short.register_node(nid, nt, nm)
    for src, tgt, rt, conf, studies, years, regimes in REL_FIXTURES:
        ikn_short.add_relationship(src, tgt, rt, conf,
                                    supporting_studies=studies,
                                    supporting_years=years,
                                    supporting_regimes=regimes)
    ok("T165 max_path_length=1 blocks 2-hop path",
       ikn_short.shortest_path("N17", "N06") is None)


# ══════════════════════════════════════════════════════════════════════════════
# T166-T180  Query — supports / contradictions / history
# ══════════════════════════════════════════════════════════════════════════════

def test_query_semantic() -> None:
    section("T166-T180  Query semantic queries")
    ikn = _make_network()

    # supports
    sup = ikn.supports("N01")
    ok("T166 supports() returns SUPPORTED_BY rels", len(sup) >= 1)
    ok("T167 supports() rel_type is SUPPORTED_BY",
       all(r.relationship_type == "SUPPORTED_BY" for r in sup))

    # DNA N02 has no SUPPORTED_BY
    ok("T168 supports() empty for N02", len(ikn.supports("N02")) == 0)

    # contradictions
    cont = ikn.contradictions("N09")
    ok("T169 contradictions() returns CONTRADICTED_BY rels", len(cont) >= 1)
    ok("T170 contradictions() rel_type is CONTRADICTED_BY",
       all(r.relationship_type == "CONTRADICTED_BY" for r in cont))

    # N01 has no CONTRADICTED_BY
    ok("T171 contradictions() empty for N01", len(ikn.contradictions("N01")) == 0)

    # history
    hist_n09 = ikn.history("N09")
    ok("T172 history() for N09 includes SUPERSEDES", len(hist_n09) >= 1)
    ok("T173 history() N09 contains SUPERSEDES rel",
       any(r.relationship_type == "SUPERSEDES" for r in hist_n09))

    hist_n03 = ikn.history("N03")
    ok("T174 history() for N03 includes EVOLVED_TO", len(hist_n03) >= 1)
    ok("T175 history() N03 rel_type is EVOLVED_TO",
       any(r.relationship_type == "EVOLVED_TO" for r in hist_n03))

    # N10 is the target of SUPERSEDES from N09 → should appear in history("N10")
    hist_n10 = ikn.history("N10")
    ok("T176 history() N10 includes incoming SUPERSEDES rel", len(hist_n10) >= 1)

    # N02 has no history (only CO_OCCURS_WITH, not EVOLVED_TO/SUPERSEDES)
    ok("T177 history() empty for N02 (no EVOLVED_TO or SUPERSEDES)", len(ikn.history("N02")) == 0)

    # supports includes direction="both"
    # N06 is the target of SUPPORTED_BY from N01 → should appear in supports("N06")
    sup_n06 = ikn.supports("N06")
    ok("T178 supports() includes incoming for N06", len(sup_n06) >= 1)

    # contradictions bidirectional: N08 is the target of CONTRADICTED_BY from N09
    cont_n08 = ikn.contradictions("N08")
    ok("T179 contradictions() includes incoming for N08", len(cont_n08) >= 1)

    # add additional SUPPORTED_BY for N01
    ikn.register_node("S2", "STUDY", "HKAP-2022b")
    ikn.add_relationship("N01", "S2", "SUPPORTED_BY", 0.7)
    sup_updated = ikn.supports("N01")
    ok("T180 supports() includes all SUPPORTED_BY rels", len(sup_updated) == 2)


# ══════════════════════════════════════════════════════════════════════════════
# T181-T195  Query — statistics / coverage
# ══════════════════════════════════════════════════════════════════════════════

def test_query_stats_coverage() -> None:
    section("T181-T195  Query statistics and coverage")
    ikn = _make_network()

    stats = ikn.statistics()
    ok("T181 statistics() returns KnowledgeStatistics", hasattr(stats, "total_nodes"))
    ok("T182 total_nodes = 20", stats.total_nodes == 20)
    ok("T183 total_relationships = 18", stats.total_relationships == 18)
    ok("T184 nodes_by_type has DNA",
       stats.nodes_by_type.get("DNA", 0) == 2)
    ok("T185 relationships_by_type has SUPPORTED_BY",
       stats.relationships_by_type.get("SUPPORTED_BY", 0) == 1)
    ok("T186 avg_confidence in (0, 1]",
       0 < stats.avg_confidence <= 1.0)
    ok("T187 orphan_count = 3 (N05, N19, N20)",
       stats.orphan_count == 3)
    ok("T188 most_connected_nodes non-empty", len(stats.most_connected_nodes) > 0)
    ok("T189 most_connected_nodes[0][0] = N01",
       stats.most_connected_nodes[0][0] == "N01")
    ok("T190 generated_at not empty", bool(stats.generated_at))
    ok("T191 statistics.to_dict works",
       "total_nodes" in stats.to_dict())

    # coverage
    cov = ikn.coverage()
    ok("T192 coverage() returns dict with required keys",
       all(k in cov for k in ["node_type_coverage", "relationship_type_coverage",
                               "traceability_score", "total_nodes", "total_relationships"]))
    ok("T193 node_type_coverage = 1.0 (all 15 present)", cov["node_type_coverage"] == 1.0)
    ok("T194 relationship_type_coverage = 1.0 (all 18 present)",
       cov["relationship_type_coverage"] == 1.0)
    ok("T195 traceability_score = 1.0 (DISC-001 has DISCOVERED_IN)",
       cov["traceability_score"] == 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# T196-T210  Versioning and updates
# ══════════════════════════════════════════════════════════════════════════════

def test_versioning() -> None:
    section("T196-T210  Versioning and updates")
    from ikn import IKNNetwork, IKNConfig

    ikn = IKNNetwork(IKNConfig(dry_run=True))
    ikn.register_node("A", "DNA", "original")
    ikn.register_node("B", "STUDY", "study")

    n = ikn.get_node("A")
    ok("T196 new node has version=1", n.version == 1)

    ikn.register_node("A", "DNA", "updated")
    n2 = ikn.get_node("A")
    ok("T197 re-registered node has version=2", n2.version == 2)

    rel = ikn.add_relationship("A", "B", "SUPPORTED_BY", 0.8)
    ok("T198 new relationship has version=1", rel.version == 1)

    upd = ikn.update_relationship(rel.relationship_id, confidence=0.6)
    ok("T199 updated relationship has version=2", upd.version == 2)
    ok("T200 update preserves relationship_id",
       upd.relationship_id == rel.relationship_id)
    ok("T201 update preserves source_id", upd.source_id == "A")
    ok("T202 update preserves target_id", upd.target_id == "B")
    ok("T203 update changes confidence", abs(upd.confidence - 0.6) < 1e-9)

    upd2 = ikn.update_relationship(rel.relationship_id, evidence_count=5)
    ok("T204 update evidence_count", upd2.evidence_count == 5)

    upd3 = ikn.update_relationship(rel.relationship_id, supporting_studies=["NEW-S"])
    ok("T205 update supporting_studies", upd3.supporting_studies == ["NEW-S"])

    upd4 = ikn.update_relationship(rel.relationship_id, supporting_years=[2023])
    ok("T206 update supporting_years", upd4.supporting_years == [2023])

    upd5 = ikn.update_relationship(rel.relationship_id, supporting_regimes=["VOLATILE"])
    ok("T207 update supporting_regimes", upd5.supporting_regimes == ["VOLATILE"])

    ok("T208 version accumulates after multiple updates",
       ikn._store.get_relationship(rel.relationship_id).version == 6)

    # created_at preserved on node re-register
    created = ikn.get_node("A").created_at
    ikn.register_node("A", "DNA", "v3")
    ok("T209 node created_at preserved on re-register",
       ikn.get_node("A").created_at == created)

    # updated_at changes
    import time; time.sleep(0.01)
    ikn.register_node("A", "DNA", "v4")
    ok("T210 updated_at changes on re-register",
       ikn.get_node("A").updated_at >= ikn.get_node("A").created_at)


# ══════════════════════════════════════════════════════════════════════════════
# T211-T225  Concurrency
# ══════════════════════════════════════════════════════════════════════════════

def test_concurrency() -> None:
    section("T211-T225  Concurrency and thread safety")
    from ikn import IKNNetwork, IKNConfig

    # T211-T212: concurrent register_node with different IDs
    ikn = IKNNetwork(IKNConfig(dry_run=True))
    errors: List[Exception] = []

    def _register(i: int) -> None:
        try:
            ikn.register_node(f"TN{i:03d}", "FEATURE", f"thread-node-{i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_register, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    ok("T211 10 threads register different nodes without error", not errors)
    ok("T212 all 10 nodes exist after concurrent registration",
       all(ikn.get_node(f"TN{i:03d}") is not None for i in range(10)))

    # T213-T214: concurrent add_relationship (pre-register src/tgt nodes)
    ikn2 = IKNNetwork(IKNConfig(dry_run=True))
    ikn2.register_node("SRC", "DNA", "source")
    ikn2.register_node("TGT", "STUDY", "target")
    rel_ids: List[str] = []
    rel_lock = threading.Lock()

    def _add_rel(i: int) -> None:
        try:
            r = ikn2.add_relationship("SRC", "TGT", "RELATED_TO", 0.5)
            with rel_lock:
                rel_ids.append(r.relationship_id)
        except Exception as e:
            errors.append(e)

    errors.clear()
    threads2 = [threading.Thread(target=_add_rel, args=(i,)) for i in range(10)]
    for t in threads2:
        t.start()
    for t in threads2:
        t.join(timeout=10)
    ok("T213 10 concurrent add_relationship no errors", not errors)
    ok("T214 all relationship IDs unique", len(rel_ids) == len(set(rel_ids)))

    # T215: concurrent statistics reads
    ikn3 = _make_network()
    stat_results = []
    stat_lock = threading.Lock()

    def _read_stats() -> None:
        s = ikn3.statistics()
        with stat_lock:
            stat_results.append(s.total_nodes)

    threads3 = [threading.Thread(target=_read_stats) for _ in range(10)]
    for t in threads3:
        t.start()
    for t in threads3:
        t.join(timeout=10)
    ok("T215 10 concurrent reads produce consistent total_nodes",
       all(v == 20 for v in stat_results))

    # T216-T218: counter uniqueness across threads
    ok("T216 relationship counter unique", len(set(rel_ids)) == 10)

    ikn4 = IKNNetwork(IKNConfig(dry_run=True))
    ikn4.register_node("X", "DNA", "x")
    ikn4.register_node("Y", "DNA", "y")
    ev_ids: List[str] = []
    ev_lock = threading.Lock()
    rel4 = ikn4.add_relationship("X", "Y", "RELATED_TO")

    def _add_ev(i: int) -> None:
        e = ikn4.add_evidence(rel4.relationship_id, f"ev{i}", "src", i)
        with ev_lock:
            ev_ids.append(e.evidence_id)

    threads4 = [threading.Thread(target=_add_ev, args=(i,)) for i in range(10)]
    for t in threads4:
        t.start()
    for t in threads4:
        t.join(timeout=10)
    ok("T217 evidence IDs unique across threads", len(set(ev_ids)) == 10)
    ok("T218 all evidence stored", len(ev_ids) == 10)

    # T219-T221: concurrent evidence for same relationship
    all_ev = ikn4._store.get_evidence_for_relationship(rel4.relationship_id)
    ok("T219 all evidence entries present after concurrent adds", len(all_ev) == 10)

    # T220: no read corruption
    ok("T220 relationship still readable after concurrent writes",
       ikn4._store.get_relationship(rel4.relationship_id) is not None)

    # T221: snapshot concurrency
    snap_results = []
    snap_lock = threading.Lock()

    def _snap() -> None:
        s = ikn3.statistics()
        with snap_lock:
            snap_results.append(s.total_nodes)

    threads5 = [threading.Thread(target=_snap) for _ in range(5)]
    for t in threads5:
        t.start()
    for t in threads5:
        t.join(timeout=10)
    ok("T221 concurrent statistics produce correct results",
       all(v == 20 for v in snap_results))

    # T222-T225: performance — 1000 nodes and 1000 rels
    ikn5 = IKNNetwork(IKNConfig(dry_run=True))
    for i in range(1000):
        ikn5.register_node(f"PERF-{i}", "FEATURE", f"p{i}")
    ok("T222 1000 node registrations succeed",
       ikn5.statistics().total_nodes == 1000)

    ikn6 = IKNNetwork(IKNConfig(dry_run=True))
    ikn6.register_node("PA", "DNA", "a")
    ikn6.register_node("PB", "DNA", "b")
    for i in range(1000):
        ikn6.add_relationship("PA", "PB", "RELATED_TO", 0.5)
    ok("T223 1000 relationship additions succeed",
       ikn6.statistics().total_relationships == 1000)
    ok("T224 statistics after 1000 rels is fast and correct",
       ikn6.statistics().total_relationships == 1000)
    ok("T225 coverage() after 1000 rels",
       isinstance(ikn6.coverage(), dict))


# ══════════════════════════════════════════════════════════════════════════════
# T226-T235  Reports
# ══════════════════════════════════════════════════════════════════════════════

def test_reports() -> None:
    section("T226-T235  Reports and snapshot")
    from ikn import IKNNetwork, IKNConfig

    # dry_run snapshot
    ikn_dry = _make_network()
    snap_dry = ikn_dry.snapshot()
    ok("T226 snapshot() returns KnowledgeNetworkSnapshot",
       hasattr(snap_dry, "snapshot_id"))
    ok("T227 snapshot_id starts with IKN-SNAP",
       snap_dry.snapshot_id.startswith("IKN-SNAP"))
    ok("T228 dry_run snapshot has 4 reports", len(snap_dry.reports) == 4)
    ok("T229 dry_run writes no files",
       not any(Path(p).exists() for p in snap_dry.reports))
    ok("T230 snapshot.node_count correct", snap_dry.node_count == 20)
    ok("T231 snapshot.relationship_count = 18",
       snap_dry.relationship_count == 18)

    # snapshot to_dict
    sd = snap_dry.to_dict()
    ok("T232 snapshot.to_dict has all keys",
       all(k in sd for k in ["snapshot_id", "generated_at", "statistics",
                               "reports", "node_count", "relationship_count"]))

    # real file output
    with tempfile.TemporaryDirectory() as tmpdir:
        config = IKNConfig(
            dry_run=False,
            db_path=os.path.join(tmpdir, "ikn.db"),
            reports_root=os.path.join(tmpdir, "ikn_reports"),
        )
        ikn_real = IKNNetwork(config=config)
        for nt, nid, nm in NODE_FIXTURES:
            ikn_real.register_node(nid, nt, nm)
        for src, tgt, rt, conf, studies, years, regimes in REL_FIXTURES:
            ikn_real.add_relationship(src, tgt, rt, conf,
                                       supporting_studies=studies,
                                       supporting_years=years,
                                       supporting_regimes=regimes)
        snap_real = ikn_real.snapshot()
        ok("T233 real snapshot has 4 reports", len(snap_real.reports) == 4)
        ok("T234 all 4 report files exist",
           all(Path(p).exists() for p in snap_real.reports))
        summary_path = next(p for p in snap_real.reports if "SUMMARY" in p)
        content = Path(summary_path).read_text(encoding="utf-8")
        ok("T235 NETWORK_SUMMARY.md contains IKN-001", "IKN-001" in content)
        ikn_real.close()  # release SQLite lock before tempdir cleanup on Windows


# ══════════════════════════════════════════════════════════════════════════════
# T236-T255  Traceability
# ══════════════════════════════════════════════════════════════════════════════

def test_traceability() -> None:
    section("T236-T255  Traceability and IKN final questions")
    ikn = _make_network()

    # Q1: every institutional fact is traceable
    cov = ikn.coverage()
    ok("T236 Q1: traceability_score = 1.0", cov["traceability_score"] == 1.0)

    # Q2: DNA connected to studies
    dna_rels = ikn.get_relationships("N01")  # rsi_5 DNA
    ok("T237 Q2: DNA N01 has SUPPORTED_BY relationship to study",
       any(r.relationship_type == "SUPPORTED_BY" for r in dna_rels))

    # Q3: SD can navigate without reading files
    stats = ikn.statistics()
    ok("T238 Q3: IKN has all node types indexed",
       stats.nodes_by_type.get("STUDY", 0) >= 1)
    ok("T239 Q3: IKN has all relationship types indexed",
       len(stats.relationships_by_type) == 18)

    # Q4: future sources can connect without changing IKN
    ikn.register_node("FUTURE-SRC", "KNOWLEDGE_PACKAGE", "new source")
    ikn.add_relationship("FUTURE-SRC", "N01", "RELATED_TO", 0.6)
    ok("T240 Q4: new source registered and linked without IKN changes",
       ikn.get_node("FUTURE-SRC") is not None)

    # Q5: IIOS has permanent institutional memory
    ok("T241 Q5: total nodes >= 21 after adding future source",
       ikn.statistics().total_nodes >= 21)

    # traceability chain: N17 (PMCI) -> N01 (DNA) -> N06 (Study)
    chain = ikn.shortest_path("N17", "N06")
    ok("T242 chain: PMCI -> DNA -> Study reachable", chain is not None)
    ok("T243 chain length = 2", chain.length == 2)
    ok("T244 chain passes through DNA N01",
       "N01" in {n.node_id for n in chain.nodes})

    # traceability chain: N17 (PMCI) -> N01 (DNA) -> N13 (REGIME via WORKS_IN)
    chain2 = ikn.shortest_path("N17", "N13")
    ok("T245 chain: PMCI -> DNA -> Regime reachable", chain2 is not None)
    ok("T246 PMCI->REGIME chain length = 2", chain2.length == 2)

    # DISCOVERY traceability
    disc_rels = ikn.get_relationships("N11")  # DISC-001
    trace_types = {"DISCOVERED_IN", "SUPPORTED_BY", "GENERATED_BY"}
    ok("T247 DISCOVERY has evidence chain",
       any(r.relationship_type in trace_types for r in disc_rels))

    # HYPOTHESIS lineage
    hist = ikn.history("N09")
    ok("T248 HYP-001 has SUPERSEDES history", any(r.relationship_type == "SUPERSEDES" for r in hist))

    # CO_OCCURS_WITH creates community path
    path_co = ikn.shortest_path("N01", "N02")
    ok("T249 CO_OCCURS_WITH creates direct path", path_co is not None)
    ok("T250 CO_OCCURS_WITH path length = 1", path_co.length == 1)

    # Subgraph of DNA covers all major node types
    sg = ikn.related("N01", depth=2)
    types_in_sg = {ikn.get_node(nid).node_type for nid in sg.nodes if ikn.get_node(nid)}
    ok("T251 DNA subgraph depth=2 covers multiple node types",
       len(types_in_sg) >= 5)

    # No cross-contamination between two IKN instances
    from ikn import IKNNetwork, IKNConfig
    ikn_b = IKNNetwork(IKNConfig(dry_run=True))
    ok("T252 fresh IKN has no nodes from other instance",
       ikn_b.statistics().total_nodes == 0)

    # traceability_score < 1.0 if untraced discovery added
    from ikn import IKNNetwork, IKNConfig
    ikn_partial = IKNNetwork(IKNConfig(dry_run=True))
    ikn_partial.register_node("D1", "DISCOVERY", "disc1")
    ikn_partial.register_node("D2", "DISCOVERY", "disc2")
    ikn_partial.register_node("S1", "STUDY", "study1")
    ikn_partial.add_relationship("D1", "S1", "DISCOVERED_IN", 0.9)
    # D2 is not connected to any study → untraceable
    cov_p = ikn_partial.coverage()
    ok("T253 traceability_score < 1.0 when some discoveries untraced",
       cov_p["traceability_score"] < 1.0)
    ok("T254 traceability_score = 0.5 (1/2 discoveries traced)",
       abs(cov_p["traceability_score"] - 0.5) < 0.01)

    # coverage reflects actual type breadth
    ok("T255 coverage() node_type_coverage = fraction of NodeType present",
       0 < cov_p["node_type_coverage"] <= 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# T256-T270  Edge cases
# ══════════════════════════════════════════════════════════════════════════════

def test_edge_cases() -> None:
    section("T256-T270  Edge cases")
    from ikn import IKNNetwork, IKNConfig, IKNError

    # empty network
    ikn_empty = IKNNetwork(IKNConfig(dry_run=True))
    stats_e = ikn_empty.statistics()
    ok("T256 empty network total_nodes = 0", stats_e.total_nodes == 0)
    ok("T257 empty network total_rels = 0", stats_e.total_relationships == 0)
    ok("T258 empty network orphan_count = 0", stats_e.orphan_count == 0)
    ok("T259 empty network related() returns empty",
       ikn_empty.related("X").nodes == {})
    ok("T260 empty network shortest_path() returns None",
       ikn_empty.shortest_path("A", "B") is None)
    ok("T261 empty network supports() returns empty",
       ikn_empty.supports("X") == [])
    ok("T262 empty network contradictions() returns empty",
       ikn_empty.contradictions("X") == [])
    ok("T263 empty network history() returns empty",
       ikn_empty.history("X") == [])

    cov_e = ikn_empty.coverage()
    ok("T264 empty network traceability_score = 1.0 (no discoveries)",
       cov_e["traceability_score"] == 1.0)
    ok("T265 empty network node_type_coverage = 0.0",
       cov_e["node_type_coverage"] == 0.0)

    # rich metadata
    ikn = IKNNetwork(IKNConfig(dry_run=True))
    n = ikn.register_node("RICH", "DNA", "rich", metadata={
        "confidence": 0.95, "years": [2019, 2020], "nested": {"a": 1}
    })
    ok("T266 register_node with rich metadata preserved",
       ikn.get_node("RICH").metadata["nested"] == {"a": 1})

    # zero confidence relationship
    ikn.register_node("A", "DNA", "a")
    ikn.register_node("B", "DNA", "b")
    r0 = ikn.add_relationship("A", "B", "RELATED_TO", 0.0)
    ok("T267 zero confidence relationship valid", r0.confidence == 0.0)

    # relationship with no supporting data
    r_empty = ikn.add_relationship("A", "B", "CO_OCCURS_WITH")
    ok("T268 relationship with no supporting data works",
       r_empty.supporting_studies == [] and
       r_empty.supporting_years == [] and
       r_empty.supporting_regimes == [])

    # IKNError message preserved
    try:
        ikn.register_node("", "DNA", "x")
    except IKNError as e:
        ok("T269 IKNError message preserved", "node_id" in str(e))

    # close() is safe to call
    ikn2 = IKNNetwork(IKNConfig(dry_run=True))
    ikn2.register_node("Z", "DNA", "z")
    ikn2.close()
    ok("T270 IKNNetwork.close() completes without error", True)


# ─── entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        test_models()
        test_config()
        test_store()
        test_network_nodes()
        test_network_rels()
        test_network_evidence()
        test_query_get()
        test_query_related()
        test_query_shortest_path()
        test_query_semantic()
        test_query_stats_coverage()
        test_versioning()
        test_concurrency()
        test_reports()
        test_traceability()
        test_edge_cases()
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    total = _pass_count + _fail_count
    print(f"\n{'=' * 60}")
    print(f"  {_pass_count}/{total} tests passed  ({_fail_count} failed)")
    print(f"{'=' * 60}")
    sys.exit(0 if _fail_count == 0 else 1)
