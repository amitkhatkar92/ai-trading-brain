"""institutional_learning/ilc_lifecycle.py — Phase 10: Knowledge Lifecycle Tracking."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ilc_config import DNA_DB, EDGES_FILE, HYP_REGISTRY_PATH, ILC_DIR, LIFECYCLE_DB_PATH
from .ilc_models import LifecycleRecord

log = logging.getLogger(__name__)


def _load_lifecycle_db() -> Dict[str, LifecycleRecord]:
    """Load lifecycle records from persistent JSON store."""
    ILC_DIR.mkdir(parents=True, exist_ok=True)
    if not LIFECYCLE_DB_PATH.exists():
        return {}
    try:
        with open(LIFECYCLE_DB_PATH, encoding="utf-8") as f:
            data = json.load(f)
        records: Dict[str, LifecycleRecord] = {}
        for item in data:
            rec = LifecycleRecord(
                item_id=item["item_id"],
                item_type=item["item_type"],
                symbol=item.get("symbol", ""),
                discovery_date=item.get("discovery_date", ""),
                validation_date=item.get("validation_date"),
                promotion_date=item.get("promotion_date"),
                current_status=item.get("current_status", "DISCOVERED"),
                verification_history=item.get("verification_history", []),
                improvement_history=item.get("improvement_history", []),
                decay_events=item.get("decay_events", []),
                retirement_date=item.get("retirement_date"),
                lifecycle_score=item.get("lifecycle_score", 0.0),
            )
            records[rec.item_id] = rec
        return records
    except Exception as e:
        log.warning("[ILC-Lifecycle] Load failed: %s", e)
        return {}


def _save_lifecycle_db(records: Dict[str, LifecycleRecord]) -> None:
    """Atomically persist lifecycle records."""
    ILC_DIR.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "item_id":             r.item_id,
            "item_type":           r.item_type,
            "symbol":              r.symbol,
            "discovery_date":      r.discovery_date,
            "validation_date":     r.validation_date,
            "promotion_date":      r.promotion_date,
            "current_status":      r.current_status,
            "verification_history": r.verification_history,
            "improvement_history": r.improvement_history,
            "decay_events":        r.decay_events,
            "retirement_date":     r.retirement_date,
            "lifecycle_score":     r.lifecycle_score,
        }
        for r in records.values()
    ]
    tmp = str(LIFECYCLE_DB_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, LIFECYCLE_DB_PATH)


def _scan_dna_records() -> List[Dict[str, Any]]:
    """Read current DNA records from institutional_dna.db."""
    if not DNA_DB.exists():
        return []
    try:
        with sqlite3.connect(DNA_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM consensus_dna ORDER BY created_at DESC LIMIT 500"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        log.debug("[ILC-Lifecycle] DNA scan failed: %s", e)
        return []


def _scan_hypotheses() -> List[Dict[str, Any]]:
    """Read current hypotheses from hypothesis registry."""
    if not HYP_REGISTRY_PATH.exists():
        return []
    try:
        with open(HYP_REGISTRY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("hypotheses", [])
        return items if isinstance(items, list) else []
    except Exception as e:
        log.debug("[ILC-Lifecycle] Hypothesis scan failed: %s", e)
        return []


def _scan_edges() -> List[Dict[str, Any]]:
    """Read current discovered edges."""
    if not EDGES_FILE.exists():
        return []
    try:
        with open(EDGES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        log.debug("[ILC-Lifecycle] Edges scan failed: %s", e)
        return []


def _lifecycle_score(rec: LifecycleRecord) -> float:
    """
    Compute a 0–100 lifecycle health score for a knowledge item.

    Considers:
    - Current status (PROMOTED = 80+, VALIDATED = 60+, DISCOVERED = 40, DECLINED = 20, RETIRED = 0)
    - Verification history (improvements add points, declines subtract)
    - Age (older validated knowledge scores higher)
    """
    status_base = {
        "PROMOTED":   80.0,
        "VALIDATED":  60.0,
        "DISCOVERED": 40.0,
        "DECLINED":   20.0,
        "RETIRED":     0.0,
        "UNDER_REVIEW": 50.0,
    }.get(rec.current_status, 40.0)

    verif_bonus = sum(
        5.0 if e.get("verdict") == "IMPROVED" else -5.0
        for e in rec.verification_history
    )
    return max(0.0, min(100.0, status_base + verif_bonus))


def update_lifecycle(
    verification_results: list,
    today: str,
    dry_run: bool = False,
) -> List[LifecycleRecord]:
    """
    Update the knowledge lifecycle database with today's verification results.

    For each verified learning record:
    - Find or create the LifecycleRecord for the relevant DNA/hypothesis/edge
    - Add a verification history entry
    - Promote / downgrade / retire as appropriate
    - Recompute lifecycle score

    Also reconciles any new DNA/hypothesis/edge items created since the last run.

    Returns all lifecycle records (current state).
    """
    lifecycle_db = _load_lifecycle_db()
    today_str    = today

    # ── 1. Reconcile with live knowledge stores ────────────────────────────
    # DNA records
    for dna_row in _scan_dna_records():
        item_id = f"DNA-{dna_row.get('dna_id') or dna_row.get('id', '')}"
        if not item_id or item_id == "DNA-":
            continue
        if item_id not in lifecycle_db:
            status = str(dna_row.get("status", "ACTIVE")).upper()
            lifecycle_db[item_id] = LifecycleRecord(
                item_id=item_id,
                item_type="DNA",
                symbol=str(dna_row.get("symbol", "")).replace(".NS", ""),
                discovery_date=str(dna_row.get("created_at", today_str))[:10],
                validation_date=str(dna_row.get("validated_at", ""))[:10] or None,
                promotion_date=str(dna_row.get("promoted_at", ""))[:10] or None,
                current_status="PROMOTED" if status == "PROMOTED" else
                               "VALIDATED" if status == "VALIDATED" else
                               "DISCOVERED",
            )

    # Hypotheses
    for hyp in _scan_hypotheses():
        hyp_id = str(hyp.get("hypothesis_id", ""))
        if not hyp_id:
            continue
        item_id = f"HYP-{hyp_id}"
        if item_id not in lifecycle_db:
            hyp_status = str(hyp.get("status", "OPEN")).upper()
            lifecycle_db[item_id] = LifecycleRecord(
                item_id=item_id,
                item_type="HYPOTHESIS",
                symbol=hyp.get("tags", [None])[0] or "",
                discovery_date=str(hyp.get("created_at", today_str))[:10],
                validation_date=str(hyp.get("validated_at", ""))[:10] or None,
                current_status="VALIDATED" if hyp_status in ("CONFIRMED", "PARTIALLY_CONFIRMED")
                               else "DECLINED" if hyp_status == "REJECTED"
                               else "DISCOVERED",
            )

    # Edges
    for edge in _scan_edges():
        edge_id = str(edge.get("edge_id", edge.get("id", "")))
        if not edge_id:
            continue
        item_id = f"EDGE-{edge_id}"
        if item_id not in lifecycle_db:
            status = str(edge.get("status", "ACTIVE")).upper()
            lifecycle_db[item_id] = LifecycleRecord(
                item_id=item_id,
                item_type="EDGE",
                symbol=str(edge.get("symbol", "")),
                discovery_date=str(edge.get("created_at", today_str))[:10],
                current_status="ACTIVE" if status == "ACTIVE" else "DISCOVERED",
            )

    # ── 2. Apply verification results to lifecycle records ─────────────────
    for vr in verification_results:
        # Find lifecycle records for this symbol
        for rec in lifecycle_db.values():
            if rec.symbol != vr.learning_id.split("-")[0] and rec.symbol:
                # Could be by symbol or by learning_id — do a loose match
                continue
            entry = {
                "date":        today_str,
                "window_days": vr.window_days,
                "verdict":     vr.verdict,
                "change_pct":  vr.change_pct,
            }
            rec.verification_history.append(entry)

            if vr.verdict == "IMPROVED":
                if rec.current_status == "DISCOVERED":
                    rec.current_status = "VALIDATED"
                    rec.validation_date = today_str
                elif rec.current_status == "VALIDATED":
                    rec.current_status = "PROMOTED"
                    rec.promotion_date = today_str
                rec.improvement_history.append(entry)

            elif vr.verdict == "DECLINED" and vr.window_days == 90:
                rec.current_status  = "RETIRED"
                rec.retirement_date = today_str
                rec.decay_events.append(entry)

    # ── 3. Recompute lifecycle scores ─────────────────────────────────────
    for rec in lifecycle_db.values():
        rec.lifecycle_score = _lifecycle_score(rec)

    # ── 4. Persist ─────────────────────────────────────────────────────────
    if not dry_run:
        _save_lifecycle_db(lifecycle_db)

    records = list(lifecycle_db.values())
    n_prom = sum(1 for r in records if r.current_status == "PROMOTED")
    n_val  = sum(1 for r in records if r.current_status in ("VALIDATED", "ACTIVE"))
    n_ret  = sum(1 for r in records if r.current_status == "RETIRED")
    log.info(
        "[ILC] Phase 10 Lifecycle: total=%d promoted=%d validated=%d retired=%d",
        len(records), n_prom, n_val, n_ret,
    )
    return records
