"""
tests/test_ikn_research_bridge.py
====================================
Self-Learning Ecosystem -- Post-roadmap Priority 2: activation of
IKNNetwork via ikn/ikn_research_bridge.py.

T01  Hypotheses are mirrored into IKN as HYPOTHESIS nodes with correct
     metadata (status/origin/confidence)
T02  A hypothesis with a knowledge_gap also gets a FINDING node and a
     GENERATED_BY relationship linking hypothesis -> gap
T03  A hypothesis with no knowledge_gap creates only a HYPOTHESIS node,
     no relationship
T04  Idempotent: running sync twice does not create a duplicate
     relationship for the same hypothesis/gap pair
T05  limit= is respected (only the first N hypotheses are processed)
T06  Fail-open: never raises when HypothesisRegistry.list_all() raises
T07  Fail-open: never raises when IKNNetwork construction raises
T08  Safety contract: zero imports of execution_engine/order_manager/
     dhan_feed/broker/risk_control anywhere in this module
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import ikn.ikn_research_bridge as bridge
from ikn.ikn_network import IKNNetwork as _RealIKNNetwork
from ikn.ikn_config import IKNConfig as _RealIKNConfig


def _fake_hyp(hid="H1", title="Test hypothesis", status_value="PROPOSED",
              origin="scientific_director", confidence=0.5, knowledge_gap=""):
    return SimpleNamespace(
        hypothesis_id=hid, title=title,
        status=SimpleNamespace(value=status_value),
        origin=origin, confidence=confidence, knowledge_gap=knowledge_gap,
    )


def _open_ikn(db_path):
    return _RealIKNNetwork(_RealIKNConfig(db_path=db_path))


@pytest.fixture
def _db_path(tmp_path):
    return str(tmp_path / "ikn.db")


def _patch_registry(hyps):
    mock_reg = MagicMock()
    mock_reg.list_all.return_value = hyps
    return patch("autonomous_research.hypothesis_registry.HypothesisRegistry", return_value=mock_reg)


def _patch_ikn_to_path(db_path):
    """The bridge always calls IKNNetwork(IKNConfig()) -- redirect that
    construction to a real, temp-isolated, file-backed IKNNetwork so
    assertions can reopen the same file afterward (the bridge closes its
    own instance in a finally-block, so we must NOT reuse that same
    Python object for post-call assertions)."""
    return patch("ikn.ikn_network.IKNNetwork", side_effect=lambda config=None: _open_ikn(db_path))


def test_t01_hypothesis_mirrored_with_metadata(_db_path):
    hyp = _fake_hyp(hid="H1", title="Gap in VOLATILE regime", confidence=0.42)
    with _patch_registry([hyp]), _patch_ikn_to_path(_db_path):
        result = bridge.sync_hypotheses_to_ikn()

    assert result["status"] == "OK"
    assert result["nodes_registered"] >= 1

    check = _open_ikn(_db_path)
    node = check.get_node("HYP-H1")
    check.close()
    assert node is not None
    assert node.name == "Gap in VOLATILE regime"
    assert node.metadata["status"] == "PROPOSED"
    assert node.metadata["origin"] == "scientific_director"
    assert abs(node.metadata["confidence"] - 0.42) < 1e-9


def test_t02_gap_creates_finding_and_relationship(_db_path):
    hyp = _fake_hyp(hid="H2", knowledge_gap="GAP-42")
    with _patch_registry([hyp]), _patch_ikn_to_path(_db_path):
        result = bridge.sync_hypotheses_to_ikn()
    assert result["relationships_added"] == 1

    check = _open_ikn(_db_path)
    gap_node = check.get_node("GAP-GAP-42")
    rels = check.get_relationships("HYP-H2", direction="outgoing")
    check.close()
    assert gap_node is not None
    assert len(rels) == 1
    assert rels[0].target_id == "GAP-GAP-42"
    assert rels[0].relationship_type == "GENERATED_BY"


def test_t03_no_gap_no_relationship(_db_path):
    hyp = _fake_hyp(hid="H3", knowledge_gap="")
    with _patch_registry([hyp]), _patch_ikn_to_path(_db_path):
        result = bridge.sync_hypotheses_to_ikn()
    assert result["relationships_added"] == 0

    check = _open_ikn(_db_path)
    rels = check.get_relationships("HYP-H3", direction="outgoing")
    check.close()
    assert rels == []


def test_t04_idempotent_no_duplicate_relationship(_db_path):
    hyp = _fake_hyp(hid="H4", knowledge_gap="GAP-7")
    with _patch_registry([hyp]), _patch_ikn_to_path(_db_path):
        r1 = bridge.sync_hypotheses_to_ikn()
    with _patch_registry([hyp]), _patch_ikn_to_path(_db_path):
        r2 = bridge.sync_hypotheses_to_ikn()

    assert r1["relationships_added"] == 1
    assert r2["relationships_added"] == 0

    check = _open_ikn(_db_path)
    rels = check.get_relationships("HYP-H4", direction="outgoing")
    check.close()
    assert len(rels) == 1


def test_t05_limit_respected(_db_path):
    hyps = [_fake_hyp(hid=f"H{i}") for i in range(5)]
    with _patch_registry(hyps), _patch_ikn_to_path(_db_path):
        result = bridge.sync_hypotheses_to_ikn(limit=2)
    assert result["hypotheses_seen"] == 2

    check = _open_ikn(_db_path)
    n0 = check.get_node("HYP-H0")
    n1 = check.get_node("HYP-H1")
    n2 = check.get_node("HYP-H2")
    check.close()
    assert n0 is not None
    assert n1 is not None
    assert n2 is None


def test_t06_fail_open_registry_raises():
    with patch("autonomous_research.hypothesis_registry.HypothesisRegistry",
               side_effect=RuntimeError("boom")):
        result = bridge.sync_hypotheses_to_ikn()
    assert result["status"] == "ERROR"


def test_t07_fail_open_ikn_construction_raises():
    with _patch_registry([_fake_hyp()]), \
         patch("ikn.ikn_network.IKNNetwork", side_effect=RuntimeError("boom")):
        result = bridge.sync_hypotheses_to_ikn()
    assert result["status"] == "ERROR"


def test_t08_no_forbidden_imports():
    import os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ikn", "ikn_research_bridge.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src, f"forbidden import found: {forbidden}"
        assert f"from {forbidden}" not in src, f"forbidden import found: {forbidden}"
