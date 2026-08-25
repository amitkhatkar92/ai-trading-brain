"""
scripts/recover_mop_rc001_to_lol.py
=====================================
DTA-LIVE-004: Recovery utility — promote today's MOP_RC001 observations
into the Learning Observation Ledger when intraday cycles crashed before
line 971 could write LOL records.

SAFETY INVARIANTS
-----------------
• Read-only from MOP_RC001.  Append-only to LOL JSONL files.
• Uses the same deterministic obs_id hash as the main LOL engine — so
  running this script twice produces exactly the same file (idempotent).
• Records are marked with  recovery_source = "RECOVERED_FROM_MOP_RC001"
  so they can be distinguished from normal scanner observations.
• Decision fields (kda_decision, strategy_decision, etc.) are left as None
  because StrategyLab / KDA never ran for these signals.
• No KDA/StrategyLab/RiskGuardian decisions are invented.
• No broker orders are created.
• Anti-lookahead: no_lookahead = True.  Outcomes will be filled by the
  normal EOD fill_pending_outcomes() path at T+1.

USAGE
-----
  python scripts/recover_mop_rc001_to_lol.py [YYYY-MM-DD]

  Defaults to today's date if no argument supplied.

EXIT CODES
----------
  0  — success (including "nothing to recover")
  1  — error
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow running from repo root
_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO))

from utils import get_logger

log = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_MOP_DIR  = _REPO / "data" / "mop_rc001"
_LOL_DIR  = _REPO / "data" / "lol"
_LOL_VERSION = "1"
_RECOVERY_SOURCE = "RECOVERED_FROM_MOP_RC001"

# Lifecycle constants (mirrors LOL module to avoid import coupling)
_OBSERVED          = "OBSERVED"
_OUTCOME_PENDING_LC = "OUTCOME_PENDING"  # lifecycle state — eligible for outcome fill
_OUTCOME_PENDING   = "PENDING"           # outcome_class — awaiting T+1 data
_OUTCOME_HORIZON   = 5
_KDA_NOT_REACHED   = "KDA_NOT_REACHED"   # KDA never ran for these recovered signals


# ── obs_id — identical algorithm to LearningObservationLedger._make_obs_id ───

def _make_obs_id(symbol: str, trading_date: str, entry_price: float) -> str:
    import hashlib
    raw = f"{symbol}|{trading_date}|{entry_price:.4f}"
    return "LOL_" + hashlib.sha1(raw.encode()).hexdigest()[:16]


# ── Load existing LOL obs_ids to check for duplicates ─────────────────────────

def _load_existing_obs_ids(trading_date: str) -> set:
    lol_file = _LOL_DIR / f"LOL_{trading_date}.jsonl"
    seen: set = set()
    if not lol_file.exists():
        return seen
    try:
        with open(lol_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    oid = rec.get("observation_id")
                    if oid:
                        seen.add(oid)
                except json.JSONDecodeError:
                    pass
    except Exception as exc:
        log.warning("[Recovery] Could not read LOL file: %s", exc)
    return seen


# ── Build a LOL OBSERVED record from an MOP_RC001 row ─────────────────────────

def _build_lol_record(mop_row: Dict[str, Any], trading_date: str) -> Optional[Dict[str, Any]]:
    try:
        symbol     = str(mop_row.get("symbol", "")).strip().upper()
        direction  = str(mop_row.get("direction", "BUY")).upper()
        entry      = float(mop_row.get("entry_price", 0.0) or 0.0)
        stop       = float(mop_row.get("stop_loss",   0.0) or 0.0)
        target     = float(mop_row.get("target_price",0.0) or 0.0)
        conf       = float(mop_row.get("confidence",  0.0) or 0.0)
        rr         = mop_row.get("rr")
        strategy   = str(mop_row.get("strategy", "") or "")
        regime     = str(mop_row.get("regime",   "") or "")
        sector     = str(mop_row.get("sector",   "") or "")
        c_score    = mop_row.get("candidate_score")

        if not symbol or not entry:
            return None

        obs_id  = _make_obs_id(symbol, trading_date, entry)
        ts_str  = mop_row.get("ts_utc", datetime.now(timezone.utc).isoformat())

        return {
            "observation_id":         obs_id,
            "symbol":                 symbol,
            "direction":              direction,
            "trading_date":           trading_date,
            "observed_at":            ts_str,
            "decision_at":            None,
            "execution_at":           None,
            "outcome_at":             None,
            "entry_price":            entry,
            "stop_loss":              stop,
            "target_price":           target,
            "rr_ratio":               float(rr) if rr is not None else None,
            "lifecycle_state":        _OUTCOME_PENDING_LC,
            "klp_score":              float(c_score) if c_score is not None else conf,
            "klp_selected":           None,
            "klp_rank":               None,
            "strategy_decision":      "NOT_REACHED",
            "strategy_name":          strategy or None,
            "strategy_rejection_reason": None,
            "kda_decision":           _KDA_NOT_REACHED,
            "kda_evidence_state":     "NOT_REACHED",
            "authorization_source":   None,
            "executed":               False,
            "order_id":               None,
            "outcome_class":          _OUTCOME_PENDING,
            "actual_return_pct":      None,
            "target_hit":             None,
            "stop_hit":               None,
            "mfe_pct":                None,
            "mae_pct":                None,
            "t1_ret_pct":             None,
            "t3_ret_pct":             None,
            "t5_ret_pct":             None,
            "outcome_first_event":    None,
            "knowledge_provenance":   {
                "confidence":     conf,
                "strategy_name":  strategy,
                "regime":         regime,
                "sector":         sector,
                "scanner_source": "EQUITY_SCANNER",
            },
            "no_lookahead":           True,
            "outcome_fill_horizon":   _OUTCOME_HORIZON,
            "lol_version":            _LOL_VERSION,
            "recovery_source":        _RECOVERY_SOURCE,
        }
    except Exception as exc:
        log.debug("[Recovery] Could not build LOL record: %s", exc)
        return None


# ── Main recovery function ────────────────────────────────────────────────────

def recover(trading_date: str) -> Dict[str, Any]:
    """
    Recover MOP_RC001 observations for trading_date into the LOL ledger.

    Returns a summary dict:
        recovered   — new records written
        skipped     — duplicates / invalid records
        total_mop   — rows in MOP_RC001 file
        lol_file    — path written to
        status      — SUCCESS | NO_MOP_FILE | EMPTY | ERROR
    """
    mop_file = _MOP_DIR / f"MOP_RC001_{trading_date}.json"

    if not mop_file.exists():
        log.info("[Recovery] No MOP_RC001 file for %s — nothing to recover.", trading_date)
        return {"status": "NO_MOP_FILE", "trading_date": trading_date,
                "recovered": 0, "skipped": 0, "total_mop": 0}

    # Load MOP_RC001 rows
    mop_rows: List[Dict[str, Any]] = []
    try:
        with open(mop_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    mop_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception as exc:
        log.error("[Recovery] Failed to read MOP_RC001 file: %s", exc)
        return {"status": "ERROR", "trading_date": trading_date, "error": str(exc),
                "recovered": 0, "skipped": 0, "total_mop": 0}

    if not mop_rows:
        log.info("[Recovery] MOP_RC001 file for %s is empty.", trading_date)
        return {"status": "EMPTY", "trading_date": trading_date,
                "recovered": 0, "skipped": 0, "total_mop": 0}

    # Load existing LOL obs_ids for idempotency
    existing = _load_existing_obs_ids(trading_date)
    log.info(
        "[Recovery] MOP_RC001 rows=%d  existing_lol_obs=%d  date=%s",
        len(mop_rows), len(existing), trading_date,
    )

    lol_file = _LOL_DIR / f"LOL_{trading_date}.jsonl"
    _LOL_DIR.mkdir(parents=True, exist_ok=True)

    recovered = 0
    skipped   = 0

    try:
        with open(lol_file, "a", encoding="utf-8") as out:
            for row in mop_rows:
                rec = _build_lol_record(row, trading_date)
                if rec is None:
                    skipped += 1
                    continue
                oid = rec["observation_id"]
                if oid in existing:
                    skipped += 1
                    continue
                out.write(json.dumps(rec, ensure_ascii=False))
                out.write("\n")
                existing.add(oid)  # prevent duplicate within this run
                recovered += 1
    except Exception as exc:
        log.error("[Recovery] Write error: %s", exc)
        return {"status": "ERROR", "trading_date": trading_date, "error": str(exc),
                "recovered": recovered, "skipped": skipped, "total_mop": len(mop_rows)}

    log.info(
        "[Recovery] COMPLETE  date=%s  recovered=%d  skipped=%d  lol_file=%s",
        trading_date, recovered, skipped, lol_file,
    )
    return {
        "status":     "SUCCESS",
        "trading_date": trading_date,
        "recovered":  recovered,
        "skipped":    skipped,
        "total_mop":  len(mop_rows),
        "lol_file":   str(lol_file),
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    try:
        # Validate date format
        date.fromisoformat(target_date)
    except ValueError:
        print(f"ERROR: invalid date '{target_date}' — expected YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    result = recover(target_date)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] in ("SUCCESS", "NO_MOP_FILE", "EMPTY") else 1)
