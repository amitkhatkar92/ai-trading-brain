"""
production_readiness/ph1_edge_gate.py — Phase 1: DECAYING Edge Gate.

Public API:
    is_edge_allowed(edge_dict)          -> bool
    filter_edges(edges_dict)            -> dict (only ACTIVE + CANDIDATE)
    get_edge_gate_summary(edges_dict)   -> EdgeGateResult
    patch_knowledge_provider()          -> None  (called once at startup)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from .prr_config import (
    BLOCKED_EDGE_STATUSES,
    DATA,
    DECAYING_EDGE_CONTRIBUTION,
    EDGE_STATUS_CANDIDATE,
    EDGE_STATUS_DECAYING,
    EDGE_STATUS_RETIRED,
    EDGE_STATUS_FULL,
)
from .prr_models import EdgeGateResult

log = logging.getLogger(__name__)

_EDGES_FILE = DATA / "discovered_edges.json"


def is_edge_allowed(edge: dict) -> bool:
    """
    Return True if the edge may contribute to live signals/decisions.
    DECAYING and RETIRED edges are always blocked.
    """
    status = (edge.get("status") or "").upper()
    if status in BLOCKED_EDGE_STATUSES:
        log.debug(
            "[EdgeGate] BLOCKED edge %s (status=%s) — Ignored because edge is %s",
            edge.get("name", "?"), status, status,
        )
        return False
    return True


def filter_edges(edges: dict) -> dict:
    """
    Return a copy of the edges dict with DECAYING/RETIRED entries removed.
    Logs each blocked edge for decision trace inclusion.
    """
    allowed: dict = {}
    for edge_id, edge in edges.items():
        if is_edge_allowed(edge):
            allowed[edge_id] = edge
        else:
            log.info(
                "[EdgeGate] Decision trace: edge=%s status=%s "
                "→ Ignored because edge is %s. Contribution=%.1f",
                edge_id, edge.get("status","?"), edge.get("status","?"),
                DECAYING_EDGE_CONTRIBUTION,
            )
    return allowed


def get_edge_gate_summary(edges: dict | None = None) -> EdgeGateResult:
    """
    Load edges from file (or accept pre-loaded dict) and compute gate summary.
    """
    if edges is None:
        try:
            with open(_EDGES_FILE, encoding="utf-8") as f:
                edges = json.load(f)
        except Exception as e:
            log.warning("[EdgeGate] Cannot load edges: %s", e)
            edges = {}

    total     = len(edges)
    active    = sum(1 for e in edges.values() if (e.get("status","") or "").upper() == EDGE_STATUS_FULL)
    candidate = sum(1 for e in edges.values() if (e.get("status","") or "").upper() == EDGE_STATUS_CANDIDATE)
    decaying  = sum(1 for e in edges.values() if (e.get("status","") or "").upper() == EDGE_STATUS_DECAYING)
    retired   = sum(1 for e in edges.values() if (e.get("status","") or "").upper() == EDGE_STATUS_RETIRED)
    blocked   = decaying + retired
    blocked_ids = [
        eid for eid, e in edges.items()
        if (e.get("status","") or "").upper() in BLOCKED_EDGE_STATUSES
    ]
    pct_blocked = round(100 * blocked / max(total, 1), 1)

    result = EdgeGateResult(
        total_edges=total,
        active_edges=active,
        candidate_edges=candidate,
        decaying_blocked=decaying,
        retired_blocked=retired,
        pct_blocked=pct_blocked,
        blocked_edge_ids=blocked_ids,
        audit_timestamp=datetime.now().isoformat(),
    )
    log.info(
        "[EdgeGate] Audit: total=%d active=%d candidate=%d "
        "decaying_blocked=%d retired_blocked=%d (%.1f%% blocked)",
        total, active, candidate, decaying, retired, pct_blocked,
    )
    return result


def patch_knowledge_provider() -> None:
    """
    Monkey-patch KnowledgeProvider.list_edges() to always filter
    DECAYING/RETIRED edges before returning them to any caller.

    Called once at system startup (from prr_runner or orchestrator).
    Idempotent — double-patching is safe.
    """
    try:
        from autonomous_research.knowledge_provider import KnowledgeProvider

        if getattr(KnowledgeProvider, "_edge_gate_patched", False):
            return

        _original_list_edges = KnowledgeProvider.list_edges

        def _gated_list_edges(self, status=None, min_composite_score=None):
            edges = _original_list_edges(self, status=status, min_composite_score=min_composite_score)
            # Filter out DECAYING and RETIRED edges
            allowed = []
            for edge in edges:
                edge_status = (getattr(edge, "status", None) or "").upper()
                if edge_status in BLOCKED_EDGE_STATUSES:
                    log.info(
                        "[EdgeGate] KP.list_edges: blocked edge=%s status=%s — "
                        "Ignored because edge is %s",
                        getattr(edge, "edge_id", "?"), edge_status, edge_status,
                    )
                else:
                    allowed.append(edge)
            if len(allowed) < len(edges):
                log.info(
                    "[EdgeGate] KnowledgeProvider.list_edges: returned %d/%d edges "
                    "(%d blocked: DECAYING/RETIRED)",
                    len(allowed), len(edges), len(edges) - len(allowed),
                )
            return allowed

        KnowledgeProvider.list_edges = _gated_list_edges
        KnowledgeProvider._edge_gate_patched = True
        log.info("[EdgeGate] KnowledgeProvider.list_edges() patched — DECAYING/RETIRED edges gated.")

    except Exception as e:
        log.warning("[EdgeGate] Could not patch KnowledgeProvider: %s", e)
