"""
ikn/ikn_research_bridge.py
=============================
Self-Learning Ecosystem -- Post-roadmap Priority 2: activates
IKNNetwork/IKNQueryEngine (ikn/), previously only used by standalone
scripts (kmp.py, kva.py, svp.py) and never populated with real data in
production.

Audit finding (before writing any code): IKNNetwork's own docstring
already documents its intended writers -- "ResearchCoordinator, KDE,
HKAP, CrossStudySynthesizer" -- and states "IKN only records and serves
institutional relationships. IKN never changes knowledge, promotes
discoveries, or creates hypotheses." It is a pure knowledge-graph
store: register_node()/add_relationship() are simple, safe, idempotent-
by-design operations (register_node upserts by node_id and increments a
version counter; nothing here overwrites or removes evidence).
IKNNetwork has zero live-trading callers today (confirmed via repo-wide
grep) -- unlike IDR, nothing reads IKN back into any decision, so
writing to it carries none of the live-consequence risk the KDE->IDR
bridge had to account for.

Rather than adding a Sandy poller over a permanently-empty store (a
poller alone activates nothing), this module is the actual data source:
it mirrors every hypothesis already created by the ARS scheduler
(Priority 1, autonomous_research/ars_scheduler.py) into IKN as a
HYPOTHESIS node, plus a FINDING node for its associated knowledge_gap
(if any) and a GENERATED_BY relationship between them. This gives
IKNNetwork real, meaningful graph data for the first time, using
exactly the data source its own docstring names (ResearchCoordinator/
ScientificDirector's hypothesis output).

Idempotent: register_node() safely no-ops/updates on repeat calls (by
node_id); relationships are only added if an identical one does not
already exist (checked via IKNNetwork.get_relationships() before every
add_relationship() call) -- safe to call on every ARS scheduler cycle
without ever creating duplicate relationships.

Safety: read-only w.r.t. HypothesisRegistry (only .list_all()); the
only writes are to IKN's own isolated SQLite store (data/ikn/ikn.db).
Never raises. Zero imports of execution_engine, order_manager, broker
APIs, or risk_control anywhere in this module.
"""
from __future__ import annotations

from typing import Any, Dict, List

from utils import get_logger

log = get_logger(__name__)


def sync_hypotheses_to_ikn(limit: int = 100) -> Dict[str, Any]:
    """
    Mirror up to `limit` hypotheses from HypothesisRegistry into IKN as
    HYPOTHESIS (+ FINDING for knowledge_gap) nodes and a GENERATED_BY
    relationship between them. Never raises. Returns a summary dict.
    """
    try:
        return _sync_impl(limit)
    except Exception as exc:
        log.debug("[IKNResearchBridge] sync error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _sync_impl(limit: int) -> Dict[str, Any]:
    from autonomous_research.knowledge_provider import KnowledgeProvider
    from autonomous_research.hypothesis_registry import HypothesisRegistry
    from ikn.ikn_network import IKNNetwork
    from ikn.ikn_config import IKNConfig
    from ikn.ikn_models import NodeType, RelationshipType

    reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
    hyps = reg.list_all()[:limit]

    ikn = IKNNetwork(IKNConfig())
    nodes_registered = 0
    relationships_added = 0
    try:
        for hyp in hyps:
            hyp_node_id = f"HYP-{hyp.hypothesis_id}"
            ikn.register_node(
                hyp_node_id, NodeType.HYPOTHESIS.value, hyp.title,
                metadata={
                    "status": hyp.status.value,
                    "origin": hyp.origin,
                    "confidence": hyp.confidence,
                },
            )
            nodes_registered += 1

            gap_id = getattr(hyp, "knowledge_gap", "") or ""
            if not gap_id:
                continue

            gap_node_id = f"GAP-{gap_id}"
            # NodeType has no dedicated "gap" value -- FINDING is the
            # closest existing type for an unmet-knowledge-area record.
            ikn.register_node(gap_node_id, NodeType.FINDING.value, f"Knowledge gap: {gap_id}")
            nodes_registered += 1

            existing = ikn.get_relationships(
                hyp_node_id, rel_type=RelationshipType.GENERATED_BY.value, direction="outgoing",
            )
            if any(r.target_id == gap_node_id for r in existing):
                continue

            ikn.add_relationship(
                hyp_node_id, gap_node_id, RelationshipType.GENERATED_BY.value,
                confidence=max(0.0, min(1.0, hyp.confidence or 0.5)),
            )
            relationships_added += 1
    finally:
        ikn.close()

    return {
        "status": "OK",
        "hypotheses_seen": len(hyps),
        "nodes_registered": nodes_registered,
        "relationships_added": relationships_added,
    }
