"""
cle_learning_executor/cle_executor.py — Cat-E Automatic DNA Learning Executor.

Entry point: run_cat_e_learning(dry_run=False) -> dict

Flow:
  1. Load the ILC learning registry.
  2. Find all Cat-E records that are PENDING and not yet executed by CLE.
  3. For each:
       a. Skip CAPITAL_EXECUTION_CONSTRAINT or non-DNA-gap misses.
       b. Call run_historical_research() from cle_research.
       c. Update registry record: executed=True, outcome=<result.status>.
  4. Save the updated registry.
  5. Return a summary dict.

SAFETY INVARIANTS (never violate):
  - lifecycle in IDR is ALWAYS "DISCOVERED" (enforced in cle_research.py).
  - This module never imports live-trading modules (risk_guardian, execution_engine,
    order_manager, dhan_feed, broker, or any order-routing path).
  - Registry failures are logged and skipped; the function always returns
    a valid dict and never raises.
  - dry_run=False is the production default; set True for offline testing.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import date
from pathlib import Path
from typing import Dict, List

log = logging.getLogger(__name__)

# ── Registry constants (mirrored from ilc_config to avoid circular imports) ──
_ROOT       = Path(__file__).parent.parent
_DATA       = _ROOT / "data"
_ILC_DIR    = _DATA / "ilc"
_REGISTRY   = _ILC_DIR / "learning_registry.json"
_CLE_DIR    = _DATA / "cle"

# CLE-specific execution records (separate from main ILC registry)
_CLE_LOG    = _CLE_DIR / "cle_execution_log.json"

# Share the same lock as ilc_verification to prevent concurrent registry writes.
# ilc_verification._REGISTRY_LOCK is a module-level threading.Lock(); importing
# it here gives us the same object (Python modules are singletons).
try:
    from institutional_learning.ilc_verification import _REGISTRY_LOCK
except Exception:
    _REGISTRY_LOCK = threading.Lock()   # fallback if ilc_verification unavailable


# ── Registry helpers ──────────────────────────────────────────────────────────

def _load_registry() -> List[dict]:
    """Load the raw registry JSON (list of dicts)."""
    if not _REGISTRY.exists():
        return []
    try:
        with open(_REGISTRY, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.warning("[CLE] Registry load failed: %s", exc)
        return []


def _save_registry(records: List[dict]) -> None:
    """Atomically persist the raw registry JSON."""
    _ILC_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(_REGISTRY) + ".cle.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
        os.replace(tmp, str(_REGISTRY))
    except Exception as exc:
        log.error("[CLE] Registry save failed: %s", exc)


def _save_cle_log(entries: List[dict]) -> None:
    """Append CLE execution entries to a dedicated CLE log file."""
    _CLE_DIR.mkdir(parents=True, exist_ok=True)
    existing: List[dict] = []
    if _CLE_LOG.exists():
        try:
            with open(_CLE_LOG, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.extend(entries)
    tmp = str(_CLE_LOG) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, default=str)
        os.replace(tmp, str(_CLE_LOG))
    except Exception as exc:
        log.warning("[CLE] CLE log save failed: %s", exc)


# ── Payload helpers ───────────────────────────────────────────────────────────

def _is_capital_constraint(record: dict) -> bool:
    """
    Returns True if the miss was caused by a capital/portfolio execution
    constraint — not a prediction failure.  These must NOT create DNA.

    We detect this from the description field (PGA writes the explanation
    there) or any explicit primary_cause stored in the record.
    """
    desc  = (record.get("description") or "").lower()
    cause = (record.get("primary_cause") or "").lower()

    capital_keywords = (
        "portfolioconstraint", "portfolio constraint",
        "capital constraint", "capitalconstraint",
        "riskfilter", "risk filter",
        "max position", "position limit",
    )
    for kw in capital_keywords:
        if kw in desc or kw in cause:
            return True
    return False


def _already_executed_by_cle(record: dict) -> bool:
    """
    Returns True if CLE has already completed processing for this record.

    CLE-COMPLETED outcomes (execution finished, no re-processing needed):
        CANDIDATE_CREATED            — DNA was created (or already existed)
        INSUFFICIENT_DATA            — not enough history to form evidence
        NO_ACTIONABLE_DNA            — evidence below quality gates
        FAILED                       — research error
        CAPITAL_EXECUTION_CONSTRAINT — portfolio/risk filter miss, not prediction failure
        SKIPPED                      — missing symbol/direction data

    Outcomes that are NOT completed (CLE should still process):
        LOGGED_FOR_REVIEW            — initial PGA default
        CLE_SCHEDULED                — explicitly scheduled for CLE (pga_learning.py hook)
        DRY_RUN                      — run with dry_run=True; research not yet written
    """
    cle_completed_outcomes = {
        "CANDIDATE_CREATED",
        "INSUFFICIENT_DATA",
        "NO_ACTIONABLE_DNA",
        "FAILED",
        "CAPITAL_EXECUTION_CONSTRAINT",
        "SKIPPED",
    }
    return record.get("outcome", "") in cle_completed_outcomes


# ── Main entry point ──────────────────────────────────────────────────────────

def run_cat_e_learning(dry_run: bool = False) -> dict:
    """
    Process all pending Cat-E learning actions.

    Returns a summary dict:
        n_found       — Cat-E PENDING records found
        n_processed   — records processed this run
        n_candidates  — DNA candidate records created
        n_no_dna      — records where evidence was insufficient
        n_skipped     — records skipped (capital constraint, etc.)
        n_failed      — records that errored during research
        dry_run       — echo of the dry_run flag
    """
    from .cle_research import run_historical_research

    summary: Dict[str, int] = {
        "n_found":      0,
        "n_processed":  0,
        "n_candidates": 0,
        "n_no_dna":     0,
        "n_skipped":    0,
        "n_failed":     0,
        "dry_run":      int(dry_run),
    }

    today = date.today().isoformat()

    try:
        with _REGISTRY_LOCK:
            records = _load_registry()

            # ── Filter to Cat-E records not yet CLE-executed ─────────────
            cat_e_pending = [
                r for r in records
                if r.get("category") == "E"
                and not _already_executed_by_cle(r)
            ]

            summary["n_found"] = len(cat_e_pending)
            if not cat_e_pending:
                log.info("[CLE] No pending Cat-E records to process.")
                return summary

            log.info("[CLE] Processing %d pending Cat-E records (dry_run=%s)",
                     len(cat_e_pending), dry_run)

            cle_log_entries: List[dict] = []

            for rec in cat_e_pending:
                action_id = rec.get("learning_id", "UNKNOWN")
                symbol    = rec.get("symbol", "")
                try:
                    # ── Safety gate: skip capital constraints ─────────────
                    if _is_capital_constraint(rec):
                        rec["executed"] = True
                        rec["outcome"]  = "CAPITAL_EXECUTION_CONSTRAINT"
                        summary["n_skipped"] += 1
                        cle_log_entries.append({
                            "action_id": action_id,
                            "symbol":    symbol,
                            "date":      today,
                            "status":    "CAPITAL_EXECUTION_CONSTRAINT",
                            "reason":    "Skipped: portfolio/capital constraint miss",
                        })
                        log.info("[CLE] Skipping %s %s — capital/portfolio constraint miss",
                                 action_id, symbol)
                        continue

                    # ── Extract payload ────────────────────────────────────
                    direction  = _extract_direction(rec)
                    return_pct = _extract_return_pct(rec)

                    if not direction or not symbol:
                        rec["executed"] = True
                        rec["outcome"]  = "SKIPPED"
                        summary["n_skipped"] += 1
                        log.warning("[CLE] %s missing symbol/direction — skipping", action_id)
                        continue

                    # ── Run historical research ────────────────────────────
                    research = run_historical_research(
                        action_id=action_id,
                        symbol=symbol,
                        direction=direction,
                        return_pct=abs(return_pct),
                        today=today,
                        dry_run=dry_run,
                    )

                    # ── Update registry record ─────────────────────────────
                    rec["executed"] = True
                    rec["outcome"]  = research.status

                    if research.status == "CANDIDATE_CREATED":
                        summary["n_candidates"] += 1
                    elif research.status in ("INSUFFICIENT_DATA", "NO_ACTIONABLE_DNA"):
                        summary["n_no_dna"] += 1
                    elif research.status == "FAILED":
                        summary["n_failed"] += 1

                    summary["n_processed"] += 1

                    cle_log_entries.append({
                        "action_id":    action_id,
                        "symbol":       symbol,
                        "direction":    direction,
                        "return_pct":   return_pct,
                        "date":         today,
                        "status":       research.status,
                        "dna_id":       research.dna_id,
                        "sample_count": research.sample_count,
                        "win_rate":     research.win_rate,
                        "lift":         research.lift,
                        "reason":       research.reason,
                        "dry_run":      dry_run,
                    })

                    log.info(
                        "[CLE] %s %s %s → %s (dna=%s, n=%d, wr=%.2f, lift=%.2f)",
                        action_id, symbol, direction, research.status,
                        research.dna_id, research.sample_count,
                        research.win_rate, research.lift,
                    )

                except Exception as exc:
                    log.error("[CLE] Unexpected error processing %s %s: %s",
                              action_id, symbol, exc)
                    rec["executed"] = True
                    rec["outcome"]  = "FAILED"
                    summary["n_failed"]    += 1
                    summary["n_processed"] += 1
                    cle_log_entries.append({
                        "action_id": action_id,
                        "symbol":    symbol,
                        "date":      today,
                        "status":    "FAILED",
                        "reason":    str(exc),
                    })

            # ── Persist changes ────────────────────────────────────────────
            if not dry_run and summary["n_processed"] > 0:
                _save_registry(records)
                log.info("[CLE] Registry saved — %d records updated",
                         summary["n_processed"])

            # Always persist CLE-specific log (for report generation)
            if cle_log_entries:
                _save_cle_log(cle_log_entries)

    except Exception as outer_exc:
        log.error("[CLE] Fatal error in run_cat_e_learning: %s", outer_exc)
        summary["n_failed"] = summary.get("n_failed", 0) + 1

    log.info(
        "[CLE] Complete: found=%d processed=%d candidates=%d no_dna=%d "
        "skipped=%d failed=%d",
        summary["n_found"], summary["n_processed"],
        summary["n_candidates"], summary["n_no_dna"],
        summary["n_skipped"], summary["n_failed"],
    )
    return summary


# ── Payload extraction helpers ────────────────────────────────────────────────

def _extract_direction(record: dict) -> str:
    """
    Extract direction from a registry record's description.

    Expected description format (from pga_learning._plan_cat_e):
        "Create candidate DNA for DRREDDY: moved +4.0% with zero DNA coverage"
        "Create candidate DNA for VEDL: moved -3.5% with zero DNA coverage"
    """
    desc = (record.get("description") or "")

    # Primary: look for "moved +N.N%" or "moved -N.N%"
    match = re.search(r"moved\s+([+\-−])\s*\d", desc)
    if match:
        return "UP" if match.group(1) == "+" else "DOWN"

    # Secondary: any signed percentage in the description
    match = re.search(r"([+\-−])\s*\d+\.?\d*\s*%", desc)
    if match:
        return "UP" if match.group(1) == "+" else "DOWN"

    # Tertiary: winner → UP, loser → DOWN
    desc_lower = desc.lower()
    if "winner" in desc_lower:
        return "UP"
    if "loser" in desc_lower:
        return "DOWN"

    return ""   # unknown — caller will skip this record


def _extract_return_pct(record: dict) -> float:
    """Extract the trigger return magnitude from a registry record's description."""
    desc = (record.get("description") or "")
    match = re.search(r"([+\-−]?\s*\d+\.?\d*)\s*%", desc)
    if match:
        try:
            return abs(float(match.group(1).replace("−", "-").replace(" ", "")))
        except ValueError:
            pass
    return 1.0  # default: 1% move threshold
