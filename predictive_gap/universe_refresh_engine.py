"""
predictive_gap/universe_refresh_engine.py
============================================
DTA-UNIVERSE-FRESHNESS-001 (refinement items 2-4 from the 2026-11-03
daily universe rebuild audit -- daily_universe_rebuild_audit_20261103.md):

  2. Bounded, rotating broad-market OHLCV refresh -- each day brings a
     small batch (UNIVERSE_REFRESH_BATCH_SIZE) of currently-excluded
     broad-market symbols up to date, cycling through the full excluded
     set over roughly len(excluded)/batch_size days. Without this, a
     symbol excluded from the active universe_stocks set can never be
     rediscovered even if it becomes genuinely liquid, because its
     OHLCV never gets refreshed at all (confirmed live: 412 broad
     symbols had ZERO history, 1,451 had only stale, Sept-2026 history).
  3. Reconciliation -- after each day's nifty500_universe.json rebuild,
     syncs universe_stocks.is_active to match that file's membership
     exactly, so the two artifacts (DB table that gates the daily OHLCV
     refresh, and the JSON file the scanner actually trades from) can no
     longer silently diverge.
  4. Folded into (3): any universe_stocks row not in the new file's
     membership (including legacy/ETF entries that predate the
     DTA-UNIVERSE-ETF-EXCLUSION-001 fix, e.g. GOLDBEES) is deactivated,
     never left active by omission.

Read-only w.r.t. everything except universe_stocks.is_active (never
deletes a row -- only flips the flag) and ohlcv_daily (only ever
appends/upserts real fetched bars via the exact same, already-tested
run_daily_fetch() primitive the existing daily refresh already uses).
Never raises; every public entry point fails open.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "market_behavior.db"
UNIVERSE_JSON_PATH = ROOT / "data" / "nifty500_universe.json"
_STATE_PATH = ROOT / "data" / "predictive_gap" / "universe_refresh_state.json"
_HISTORY_PATH = ROOT / "data" / "predictive_gap" / "universe_refresh_history.jsonl"

UNIVERSE_REFRESH_BATCH_SIZE = 100   # excluded symbols refreshed per day


def record_refresh_cycle_result(trading_date: str, result: Dict[str, Any]) -> None:
    """Append-only daily history so a later audit (e.g. a weekly review) can
    verify real activity/effect without depending on container log retention.
    Never raises."""
    try:
        _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {"trading_date": trading_date, **result}
        with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        log.warning("[UniverseRefresh] history write failed (non-fatal): %s", exc)


def get_refresh_cycle_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only accessor: last n recorded daily cycle results, oldest-first
    within the returned slice. Returns [] on any failure."""
    try:
        if not _HISTORY_PATH.exists():
            return []
        lines = _HISTORY_PATH.read_text(encoding="utf-8").strip().splitlines()
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except Exception:
                continue
        return records[-n:]
    except Exception as exc:
        log.warning("[UniverseRefresh] history read failed: %s", exc)
        return []


def _load_state() -> Dict[str, Any]:
    try:
        if _STATE_PATH.exists():
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("[UniverseRefresh] state read failed, treating as fresh: %s", exc)
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(_STATE_PATH)
    except Exception as exc:
        log.warning("[UniverseRefresh] state write failed (non-fatal): %s", exc)


def _bare(symbol: str) -> str:
    return symbol.replace(".NS", "").replace(".BO", "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Item 2: bounded rotating broad-market refresh
# ─────────────────────────────────────────────────────────────────────────────

def run_bounded_broad_refresh(
    batch_size: int = UNIVERSE_REFRESH_BATCH_SIZE,
    db_path: Optional[Path] = None,
    trading_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch real incremental OHLCV for the NEXT `batch_size` currently-
    excluded broad-market symbols (rotating cursor, wraps around), so the
    full excluded set is periodically re-examined for ADV ranking instead
    of staying permanently frozen/invisible. At most once per trading
    date. Never raises -- returns a summary dict with ok=False on any
    failure, never partial/undefined state.
    """
    td = trading_date or date.today().isoformat()
    state = _load_state()
    if state.get("last_broad_refresh_date") == td:
        return {"ok": True, "skipped": "already_ran_today", "attempted": 0}

    try:
        from predictive_gap.broad_market_universe import load_broad_nse_equity_symbols
        from oios.db.connection import get_connection
        from oios.data.ohlcv_fetcher import run_daily_fetch

        broad = load_broad_nse_equity_symbols()
        if not broad:
            return {"ok": False, "reason": "no_broad_list"}

        conn = get_connection()
        try:
            active_rows = conn.execute(
                "SELECT symbol FROM universe_stocks WHERE is_active=1"
            ).fetchall()
            active = {_bare(r[0]) for r in active_rows}

            excluded = sorted(s for s in broad if s not in active)
            if not excluded:
                return {"ok": True, "attempted": 0, "reason": "nothing_excluded"}

            cursor = int(state.get("cursor", 0)) % len(excluded)
            batch = (excluded * 2)[cursor: cursor + batch_size]  # wrap-around slice
            ns_batch = [f"{s}.NS" for s in batch]

            result = run_daily_fetch(conn, ns_batch, td)
            new_cursor = (cursor + batch_size) % len(excluded)
        finally:
            conn.close()

        _save_state({
            "last_broad_refresh_date": td,
            "cursor": new_cursor,
            "excluded_pool_size": len(excluded),
            "last_batch_ok": len(result.symbols_ok),
            "last_batch_failed": len(result.symbols_failed),
            "last_rows_inserted": result.rows_inserted,
        })
        log.info("[UniverseRefresh] Broad refresh batch: attempted=%d ok=%d failed=%d "
                  "rows_inserted=%d (excluded_pool=%d, cursor %d->%d)",
                  len(batch), len(result.symbols_ok), len(result.symbols_failed),
                  result.rows_inserted, len(excluded), cursor, new_cursor)
        return {
            "ok": True,
            "attempted": len(batch),
            "symbols_ok": len(result.symbols_ok),
            "symbols_failed": len(result.symbols_failed),
            "rows_inserted": result.rows_inserted,
            "excluded_pool_size": len(excluded),
        }
    except Exception as exc:
        log.warning("[UniverseRefresh] Broad refresh failed, non-fatal: %s", exc)
        return {"ok": False, "reason": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Items 3 + 4: reconcile universe_stocks.is_active with nifty500_universe.json
# ─────────────────────────────────────────────────────────────────────────────

def reconcile_universe_stocks(
    universe_json_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Sync universe_stocks.is_active to exactly match today's
    nifty500_universe.json membership: activates any file symbol not
    currently active (inserting the row if it doesn't exist yet), and
    deactivates any currently-active row absent from the file (this is
    what removes stale/legacy/ETF entries, e.g. GOLDBEES, that predate
    source filters applied only to newer additions). Never deletes a
    row -- only flips is_active. Never raises.
    """
    path = universe_json_path or UNIVERSE_JSON_PATH
    try:
        if not path.exists():
            return {"ok": False, "reason": "universe_json_missing"}
        data = json.loads(path.read_text(encoding="utf-8"))
        entry_by_symbol = {e["symbol"]: e for e in data if e.get("symbol")}
        file_symbols_bare = set(entry_by_symbol.keys())
        file_symbols_ns = {f"{s}.NS" for s in file_symbols_bare}

        from oios.db.connection import get_connection
        conn = get_connection()
        try:
            rows = conn.execute("SELECT symbol, is_active FROM universe_stocks").fetchall()
            existing = {r[0]: r[1] for r in rows}

            to_activate = [s for s in file_symbols_ns if existing.get(s) != 1]
            to_deactivate = [s for s, active in existing.items()
                             if active == 1 and s not in file_symbols_ns]

            today_iso = date.today().isoformat()
            with conn:
                for s in to_activate:
                    if s in existing:
                        conn.execute("UPDATE universe_stocks SET is_active=1, removed_date=NULL "
                                    "WHERE symbol=?", (s,))
                    else:
                        entry = entry_by_symbol.get(_bare(s), {})
                        conn.execute(
                            "INSERT INTO universe_stocks "
                            "(symbol, company_name, sector, is_active, added_date) "
                            "VALUES (?, ?, ?, 1, ?)",
                            (s, _bare(s), entry.get("sector") or "UNKNOWN", today_iso),
                        )
                for s in to_deactivate:
                    conn.execute(
                        "UPDATE universe_stocks SET is_active=0, removed_date=?, "
                        "removal_reason='UNIVERSE_RECONCILE_NOT_IN_LATEST_FILE' WHERE symbol=?",
                        (today_iso, s),
                    )
        finally:
            conn.close()

        log.info("[UniverseRefresh] Reconciled universe_stocks: activated=%d deactivated=%d "
                  "(file_count=%d)", len(to_activate), len(to_deactivate), len(file_symbols_ns))
        return {
            "ok": True,
            "activated": len(to_activate),
            "deactivated": len(to_deactivate),
            "file_count": len(file_symbols_ns),
        }
    except Exception as exc:
        log.warning("[UniverseRefresh] Reconciliation failed, non-fatal: %s", exc)
        return {"ok": False, "reason": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Combined daily entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_universe_refresh_cycle(
    batch_size: int = UNIVERSE_REFRESH_BATCH_SIZE,
) -> Dict[str, Any]:
    """
    Call once per day, after _write_universe_json() has already run.
    Order matters: the broad refresh extends OHLCV for a rotating batch
    of excluded symbols (feeds FUTURE rankings); reconciliation then
    syncs universe_stocks to TODAY's just-written file. Never raises.
    """
    refresh_result = run_bounded_broad_refresh(batch_size=batch_size)
    reconcile_result = reconcile_universe_stocks()
    cycle_result = {"broad_refresh": refresh_result, "reconciliation": reconcile_result}
    record_refresh_cycle_result(date.today().isoformat(), cycle_result)
    return cycle_result
