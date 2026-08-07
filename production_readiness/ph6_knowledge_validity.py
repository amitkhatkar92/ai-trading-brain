"""
production_readiness/ph6_knowledge_validity.py — Phase 6: Knowledge Validity.

Tracks and enforces expiry dates for all institutional knowledge:
  - DNA records (stale threshold: 90 days since last_seen)
  - Discovered edges (stale threshold: 60 days since last update)
  - Hypothesis registry (stale threshold: 180 days since last review)
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .prr_config import (
    DNA_DB,
    DNA_STALE_THRESHOLD_DAYS,
    EDGE_STALE_THRESHOLD_DAYS,
    HYPOTHESIS_STALE_THRESHOLD_DAYS,
    DATA,
)
from .prr_models import KnowledgeItem, KnowledgeValidityReport

log = logging.getLogger(__name__)

_EDGES_FILE     = DATA / "discovered_edges.json"
_HYP_REGISTRY  = DATA / "ars_hypothesis_registry.json"


def _days_since(date_str: str, now: datetime) -> int:
    """Parse ISO date string and return integer days since then. Returns 999 on error."""
    if not date_str:
        return 999
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (now - dt).days)
    except Exception:
        return 999


def _validity_status(days: int, threshold: int) -> str:
    if days > threshold:
        return "STALE"
    if days > threshold // 2:
        return "AGING"
    return "VALID"


def _load_dna_items(now: datetime) -> List[KnowledgeItem]:
    items: List[KnowledgeItem] = []
    if not DNA_DB.exists():
        return items
    try:
        with sqlite3.connect(DNA_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, feature_name, category, lifecycle, confidence,
                       last_seen, created_at, updated_at
                FROM dna WHERE is_current = 1
                ORDER BY last_seen ASC
            """).fetchall()
        for r in rows:
            last_seen = r["last_seen"] or r["updated_at"] or r["created_at"] or ""
            days      = _days_since(last_seen, now)
            status    = _validity_status(days, DNA_STALE_THRESHOLD_DAYS)
            blocks    = status == "STALE"
            items.append(KnowledgeItem(
                item_id       = str(r["id"]),
                item_type     = "DNA",
                created_date  = str(r["created_at"] or ""),
                last_verified = last_seen,
                days_since_verified = days,
                validity_status     = status,
                expiry_date   = "",   # computed dynamically from threshold
                blocks_trading= blocks,
                detail        = f"category={r['category']} lifecycle={r['lifecycle']} confidence={r['confidence']}",
            ))
    except Exception as e:
        log.warning("[KnowledgeValidity] DNA load failed: %s", e)
    return items


def _load_edge_items(now: datetime) -> List[KnowledgeItem]:
    items: List[KnowledgeItem] = []
    if not _EDGES_FILE.exists():
        return items
    try:
        with open(_EDGES_FILE, encoding="utf-8") as f:
            edges = json.load(f)
        for edge_id, edge in edges.items():
            last_seen    = edge.get("last_seen") or edge.get("updated_at") or ""
            days         = _days_since(last_seen, now)
            edge_status  = (edge.get("status") or "").upper()
            # Retired edges are blocked by Phase 1; here we just track validity
            status       = _validity_status(days, EDGE_STALE_THRESHOLD_DAYS)
            blocks       = status == "STALE" or edge_status in ("DECAYING", "RETIRED")
            items.append(KnowledgeItem(
                item_id       = edge_id,
                item_type     = "EDGE",
                created_date  = str(edge.get("created_at", "")),
                last_verified = last_seen,
                days_since_verified = days,
                validity_status     = status,
                expiry_date   = "",
                blocks_trading= blocks,
                detail        = f"status={edge_status} precision={edge.get('precision',0)} score={edge.get('score',0)}",
            ))
    except Exception as e:
        log.warning("[KnowledgeValidity] Edge load failed: %s", e)
    return items


def _load_hypothesis_items(now: datetime) -> List[KnowledgeItem]:
    items: List[KnowledgeItem] = []
    if not _HYP_REGISTRY.exists():
        return items
    try:
        with open(_HYP_REGISTRY, encoding="utf-8") as f:
            reg = json.load(f)
        hyps = reg.get("hypotheses", {})
        for hyp_id, hyp in hyps.items():
            last_review = (
                hyp.get("validated_at")
                or hyp.get("last_tested")
                or hyp.get("created_at")
                or ""
            )
            days   = _days_since(last_review, now)
            status = _validity_status(days, HYPOTHESIS_STALE_THRESHOLD_DAYS)
            blocks = status == "STALE" and hyp.get("status") != "CONFIRMED"
            items.append(KnowledgeItem(
                item_id       = hyp_id,
                item_type     = "HYPOTHESIS",
                created_date  = str(hyp.get("created_at", "")),
                last_verified = last_review,
                days_since_verified = days,
                validity_status     = status,
                expiry_date   = "",
                blocks_trading= blocks,
                detail        = f"status={hyp.get('status','?')} statement={str(hyp.get('statement',''))[:80]}",
            ))
    except Exception as e:
        log.warning("[KnowledgeValidity] Hypothesis load failed: %s", e)
    return items


def build_knowledge_validity_report(
    today: Optional[str] = None,
) -> KnowledgeValidityReport:
    """Load all knowledge sources and compute validity status for each item."""
    today = today or datetime.now().date().isoformat()
    now   = datetime.now(timezone.utc)

    dna_items  = _load_dna_items(now)
    edge_items = _load_edge_items(now)
    hyp_items  = _load_hypothesis_items(now)
    all_items  = dna_items + edge_items + hyp_items

    total   = len(all_items)
    valid   = sum(1 for i in all_items if i.validity_status == "VALID")
    stale   = sum(1 for i in all_items if i.validity_status == "STALE")
    expired = sum(1 for i in all_items if i.blocks_trading)   # blocks_trading = strict expired

    by_type: Dict[str, Dict[str, int]] = {}
    for item in all_items:
        t = item.item_type
        if t not in by_type:
            by_type[t] = {"VALID": 0, "AGING": 0, "STALE": 0}
        by_type[t][item.validity_status] = by_type[t].get(item.validity_status, 0) + 1

    log.info(
        "[KnowledgeValidity] total=%d valid=%d stale=%d trading_blocked=%d",
        total, valid, stale, expired,
    )
    return KnowledgeValidityReport(
        date=today,
        total_items=total,
        valid_items=valid,
        stale_items=stale,
        expired_items=expired,
        trading_blocked_items=expired,
        by_type=by_type,
        items=all_items,
    )
