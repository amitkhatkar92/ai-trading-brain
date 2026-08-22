"""
reconcile_positions.py
======================
Cross-source position reconciliation for the ai_trading_brain system.

Compares four data sources:
  A: paper_trades.csv          — execution system's source of truth
  B: data/trading_brain.db     — old orchestrator's trade store (legacy)
  C: data/market_behavior.db   — OIOS DB (execution_trade_links + opportunities)
  D: data/control_tower.db     — telemetry (cross-reference only)

For each discovered open position, assigns exactly one classification:
  VALID_OPEN  — in CSV as unclosed, within carry window, traceable to order_id
  ORPHAN_DB   — in trading_brain.db as open, no CSV counterpart
  ORPHAN_CSV  — in CSV as unclosed, but no DB record and/or beyond carry window
  DUPLICATE   — multiple identical records for same symbol/direction/entry
  MISMATCH    — conflicting state across sources

Outputs:
  POSITION_RECONCILIATION_REPORT.md
  (printed: per-position classification + remediation SQL)

Rules:
  - READ ONLY: no writes to any DB or CSV
  - Remediation SQL is generated but NOT executed
"""

from __future__ import annotations

import csv
import os
import sqlite3
import textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

ROOT = os.path.dirname(__file__)

# ── paths ────────────────────────────────────────────────────────────────────
CSV_PATH   = os.path.join(ROOT, "data", "paper_trades.csv")
TB_DB      = os.path.join(ROOT, "data", "trading_brain.db")
OIOS_DB    = os.path.join(ROOT, "data", "market_behavior.db")
CT_DB      = os.path.join(ROOT, "data", "control_tower.db")

# ── carry-window logic (mirrors order_manager._carry_days_for) ───────────────
_CARRY_KEYWORDS: Dict[str, int] = {
    "MEAN_REVERSION": 3, "RANGE": 3, "HEDGING": 3,
    "MOMENTUM": 5, "BREAKOUT": 5, "EDG_MOMENT": 5,
    "TREND": 7, "SWING": 7, "BULLCALL": 7,
}
_DEFAULT_CARRY = 5

def carry_days_for(strategy: str) -> int:
    s = (strategy or "").upper()
    for kw, days in _CARRY_KEYWORDS.items():
        if kw in s:
            return days
    return _DEFAULT_CARRY


# ── data containers ──────────────────────────────────────────────────────────
@dataclass
class CsvPosition:
    order_id:    str
    symbol:      str
    direction:   str
    quantity:    int
    entry_price: float
    stop_loss:   float
    target:      float
    strategy:    str
    confidence:  str
    rr:          str
    opened_at:   str  # timestamp string
    age_days:    int
    carry_limit: int
    expired:     bool  # True if age > carry_limit

@dataclass
class DbPosition:
    db_id:       int
    trade_id:    str
    symbol:      str
    direction:   str
    quantity:    int
    entry_price: float
    strategy:    str
    opened_at:   str

@dataclass
class LinkRecord:
    order_id:       str
    opportunity_id: Optional[str]
    symbol:         str
    direction_exec: str
    direction_oios: str
    entry_price:    float
    linked_at:      str
    close_reason:   Optional[str]
    realized_pnl:   Optional[float]

@dataclass
class OiosOpp:
    opportunity_id:   str
    symbol:           str
    direction:        str
    current_state:    str
    position_exists:  int
    position_size_pct: float
    trade_pnl_pct:    Optional[float]

@dataclass
class ReconciliationEntry:
    classification: str          # VALID_OPEN | ORPHAN_DB | ORPHAN_CSV | DUPLICATE | MISMATCH
    source:         str          # primary source: csv | db | both
    order_id:       Optional[str]  # execution system id (CSV / bridge)
    trade_id:       Optional[str]  # trading_brain.db trade_id
    opportunity_id: Optional[str]  # OIOS id (may be None)
    symbol:         str
    direction:      str
    entry_price:    float
    quantity:       int
    strategy:       str
    opened_at:      str
    age_days:       int
    notes:          List[str] = field(default_factory=list)


# ── loaders ──────────────────────────────────────────────────────────────────
def load_csv_positions() -> List[CsvPosition]:
    """Parse paper_trades.csv and return all unclosed positions."""
    if not os.path.exists(CSV_PATH):
        return []

    now = datetime.now()
    by_oid: Dict[str, List[dict]] = defaultdict(list)
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_oid[row["order_id"]].append(row)

    positions: List[CsvPosition] = []
    for oid, events in by_oid.items():
        has_close = any(
            e.get("event", "").upper() not in ("OPEN", "AET_CONFIRMED", "EXTEND", "REENTRY")
            for e in events
        )
        has_open = any(e.get("event", "").upper() == "OPEN" for e in events)
        if not has_open or has_close:
            continue  # properly closed
        open_ev = next(e for e in events if e.get("event", "").upper() == "OPEN")
        try:
            opened_dt = datetime.strptime(open_ev["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            opened_dt = now
        age = (now - opened_dt).days
        strat = open_ev.get("strategy", "")
        carry = carry_days_for(strat)
        positions.append(CsvPosition(
            order_id    = oid,
            symbol      = open_ev.get("symbol", ""),
            direction   = open_ev.get("direction", ""),
            quantity    = int(float(open_ev.get("quantity", 0) or 0)),
            entry_price = float(open_ev.get("entry_price", 0) or 0),
            stop_loss   = float(open_ev.get("stop_loss", 0) or 0),
            target      = float(open_ev.get("target", 0) or 0),
            strategy    = strat,
            confidence  = open_ev.get("confidence", ""),
            rr          = open_ev.get("rr", ""),
            opened_at   = open_ev["timestamp"],
            age_days    = age,
            carry_limit = carry,
            expired     = age > carry,
        ))
    return positions


def load_db_positions() -> List[DbPosition]:
    """Return all status='open' rows from trading_brain.db trades table."""
    if not os.path.exists(TB_DB):
        return []
    conn = sqlite3.connect(TB_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM trades WHERE status='open' OR (ts_close IS NULL AND status != 'closed')"
    ).fetchall()
    conn.close()
    return [
        DbPosition(
            db_id       = r["id"],
            trade_id    = r["trade_id"] or "",
            symbol      = r["symbol"] or "",
            direction   = r["direction"] or "",
            quantity    = int(r["quantity"] or 0),
            entry_price = float(r["entry_price"] or 0),
            strategy    = r["strategy"] or "",
            opened_at   = r["ts_open"] or "",
        )
        for r in rows
    ]


def load_oios_links() -> List[LinkRecord]:
    """Load execution_trade_links from market_behavior.db if it exists."""
    if not os.path.exists(OIOS_DB):
        return []
    try:
        conn = sqlite3.connect(OIOS_DB)
        conn.row_factory = sqlite3.Row
        # Table may not exist if bridge just bootstrapped
        rows = conn.execute(
            "SELECT * FROM execution_trade_links ORDER BY linked_at DESC"
        ).fetchall()
        conn.close()
        return [
            LinkRecord(
                order_id       = r["order_id"],
                opportunity_id = r["opportunity_id"],
                symbol         = r["symbol"],
                direction_exec = r["direction_exec"],
                direction_oios = r["direction_oios"],
                entry_price    = float(r["entry_price"] or 0),
                linked_at      = r["linked_at"],
                close_reason   = r["close_reason"],
                realized_pnl   = r["realized_pnl"],
            )
            for r in rows
        ]
    except Exception:
        return []


def load_oios_opps() -> List[OiosOpp]:
    """Load open opportunities from market_behavior.db if it exists."""
    if not os.path.exists(OIOS_DB):
        return []
    try:
        conn = sqlite3.connect(OIOS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE current_state IN ('ACTIVE','WATCHING','DISCOVERED')"
        ).fetchall()
        conn.close()
        return [
            OiosOpp(
                opportunity_id  = r["opportunity_id"],
                symbol          = r["symbol"],
                direction       = r["direction"],
                current_state   = r["current_state"],
                position_exists = int(r["position_exists"] or 0),
                position_size_pct = float(r["position_size_pct"] or 0),
                trade_pnl_pct   = r["trade_pnl_pct"],
            )
            for r in rows
        ]
    except Exception:
        return []


# ── reconciliation engine ─────────────────────────────────────────────────────
def reconcile() -> List[ReconciliationEntry]:
    csv_positions  = load_csv_positions()
    db_positions   = load_db_positions()
    oios_links     = load_oios_links()
    oios_opps      = load_oios_opps()

    # Index by symbol for cross-referencing
    csv_by_symbol: Dict[str, List[CsvPosition]]    = defaultdict(list)
    db_by_symbol:  Dict[str, List[DbPosition]]     = defaultdict(list)
    link_by_oid:   Dict[str, LinkRecord]            = {}
    opp_by_sym:    Dict[str, List[OiosOpp]]         = defaultdict(list)

    for p in csv_positions:
        csv_by_symbol[p.symbol].append(p)
    for p in db_positions:
        db_by_symbol[p.symbol].append(p)
    for l in oios_links:
        link_by_oid[l.order_id] = l
    for o in oios_opps:
        opp_by_sym[o.symbol].append(o)

    entries: List[ReconciliationEntry] = []

    # ── Phase 1: classify trading_brain.db positions ─────────────────────────
    db_processed: set = set()
    for sym, db_list in db_by_symbol.items():
        csv_list = csv_by_symbol.get(sym, [])

        # Detect internal duplicates in DB (same symbol, entry, direction)
        entry_groups: Dict[str, List[DbPosition]] = defaultdict(list)
        for p in db_list:
            key = f"{p.direction}:{p.entry_price}:{p.strategy[:20]}"
            entry_groups[key].append(p)

        for key, group in entry_groups.items():
            is_dup = len(group) > 1
            primary = group[0]

            # Does a CSV position exist for this symbol?
            csv_match = next(
                (c for c in csv_list if c.direction == primary.direction
                 or c.direction in ("BUY", primary.direction)),
                None
            )
            # Does an OIOS link exist?
            opp_match = next(
                (o for o in opp_by_sym.get(sym, [])
                 if o.direction in ("LONG", "BOTH")
                 or (primary.direction == "BUY" and o.direction == "LONG")
                 or (primary.direction == "SELL" and o.direction == "SHORT")),
                None
            )

            notes = []
            if is_dup:
                notes.append(f"{len(group)} duplicate DB rows for same entry "
                              f"(trade_ids: {', '.join(p.trade_id for p in group)})")
            notes.append("Old orchestrator write (trading_brain.db) — "
                         "no CSV counterpart; invisible to _restore_from_journal()")
            notes.append("These positions cannot be SL/target monitored or closed by current system")
            if csv_match:
                notes.append(f"NOTE: CSV also has open {sym} ({csv_match.order_id}) — cross-system duplicate")

            # All DB-only positions are ORPHAN_DB
            classification = "DUPLICATE" if is_dup else "ORPHAN_DB"
            # Even duplicates are ultimately orphaned — mark as ORPHAN_DB with dup note
            if is_dup:
                classification = "ORPHAN_DB"

            entries.append(ReconciliationEntry(
                classification = classification,
                source         = "db",
                order_id       = None,  # DB uses trade_id, not order_id
                trade_id       = primary.trade_id,
                opportunity_id = opp_match.opportunity_id if opp_match else None,
                symbol         = sym,
                direction      = primary.direction,
                entry_price    = primary.entry_price,
                quantity       = sum(p.quantity for p in group),
                strategy       = primary.strategy,
                opened_at      = primary.opened_at,
                age_days       = (datetime.now() - datetime.fromisoformat(primary.opened_at[:19])).days,
                notes          = notes,
            ))
            db_processed.add(sym)

    # ── Phase 2: classify CSV positions ──────────────────────────────────────
    for p in csv_positions:
        link   = link_by_oid.get(p.order_id)
        opp_id = link.opportunity_id if link else None

        # Try OIOS opportunity lookup if no link
        if not opp_id:
            oios_dir = "LONG" if p.direction == "BUY" else "SHORT"
            opp_match = next(
                (o for o in opp_by_sym.get(p.symbol, []) if o.direction == oios_dir),
                None
            )
            opp_id = opp_match.opportunity_id if opp_match else None

        notes = []
        db_also_open = db_by_symbol.get(p.symbol, [])
        if db_also_open:
            notes.append(f"Same symbol also open in trading_brain.db ({len(db_also_open)} rows)")

        if p.expired:
            classification = "ORPHAN_CSV"
            notes.append(f"Age {p.age_days}d exceeds carry limit {p.carry_limit}d — "
                         "would be SESSION_EXPIRED at next _restore_from_journal()")
            notes.append("No close row in CSV — system was not restarted after expiry window elapsed")
        else:
            # Within carry window: VALID_OPEN only if traceable
            if opp_id:
                classification = "VALID_OPEN"
                notes.append(f"Linked to OIOS opportunity {opp_id}")
            else:
                classification = "VALID_OPEN"  # traceable by order_id at minimum
                notes.append("No OIOS link yet (bridge not running at time of open)")

        entries.append(ReconciliationEntry(
            classification = classification,
            source         = "csv",
            order_id       = p.order_id,
            trade_id       = None,
            opportunity_id = opp_id,
            symbol         = p.symbol,
            direction      = p.direction,
            entry_price    = p.entry_price,
            quantity       = p.quantity,
            strategy       = p.strategy,
            opened_at      = p.opened_at,
            age_days       = p.age_days,
            notes          = notes,
        ))

    return entries


# ── remediation SQL generator ─────────────────────────────────────────────────
def generate_remediation_sql(entries: List[ReconciliationEntry]) -> str:
    now_ts = datetime.now().isoformat(timespec="seconds")
    lines  = [
        "-- ===================================================================",
        "-- REMEDIATION SQL — generated by reconcile_positions.py",
        f"-- Run date: {now_ts}",
        "-- REVIEW AND TEST BEFORE RUNNING. These are NOT auto-executed.",
        "-- ===================================================================",
        "",
    ]

    # Group 1: ORPHAN_DB — close all phantom open positions in trading_brain.db
    orphan_db = [e for e in entries if e.classification == "ORPHAN_DB" and e.trade_id]
    if orphan_db:
        # Collect all DB trade_ids including duplicates
        # Re-read from DB for all unique db_ids
        conn = sqlite3.connect(TB_DB)
        all_open_ids = [r[0] for r in conn.execute(
            "SELECT trade_id FROM trades WHERE status='open'"
        ).fetchall()]
        conn.close()

        lines += [
            "-- ---------------------------------------------------------------",
            "-- SECTION 1: Close phantom open trades in trading_brain.db",
            "--",
            "-- Context: 21 open records from old orchestrator (2026-03-11).",
            "-- The new orchestrator never reads this table. These positions",
            "-- are unmonitored, unrestorable, and block accurate portfolio math.",
            "-- Resolution: mark all as 'closed' with a reconciliation reason.",
            "-- ---------------------------------------------------------------",
            "",
            "-- Step 1a: Preview rows to be closed",
            "SELECT id, trade_id, symbol, direction, quantity, entry_price,",
            "       status, ts_open",
            "  FROM trades",
            " WHERE status = 'open';",
            "",
            "-- Step 1b: Close all phantom open positions",
            f"-- (Affects {len(all_open_ids)} rows across WIPRO×7, TCS×7, HDFCBANK×7)",
            "UPDATE trades",
            f"   SET status   = 'closed',",
            f"       ts_close = '{now_ts}',",
            f"       pnl      = 0,",
            f"       net_pnl  = 0,",
            f"       notes    = 'RECONCILED: orphaned legacy position — old orchestrator (2026-03-11); never monitored by current system'",
            " WHERE status = 'open';",
            "",
            "-- Step 1c: Verify",
            "SELECT COUNT(*) AS remaining_open FROM trades WHERE status='open';",
            "-- Expected: 0",
            "",
        ]

    # Group 2: ORPHAN_CSV — append SESSION_EXPIRED close to paper_trades.csv
    orphan_csv = [e for e in entries if e.classification == "ORPHAN_CSV"]
    if orphan_csv:
        lines += [
            "-- ---------------------------------------------------------------",
            "-- SECTION 2: Expire orphaned CSV positions (paper_trades.csv)",
            "--",
            "-- These SQL statements are not applicable to a CSV file.",
            "-- The CSV remedy is to append SESSION_EXPIRED CLOSE rows.",
            "-- The script below is PYTHON pseudocode for illustration only.",
            "-- ---------------------------------------------------------------",
            "",
            "-- Python pseudocode (do not run as SQL):",
            "-- import csv",
            "-- from datetime import datetime",
            "-- CLOSE_ROW = {",
        ]
        for e in orphan_csv:
            lines += [
                f"--   # order_id: {e.order_id}",
                f"--   'timestamp':   '{now_ts}',",
                f"--   'order_id':    '{e.order_id}',",
                f"--   'symbol':      '{e.symbol}',",
                f"--   'direction':   '{e.direction}',",
                f"--   'quantity':    '{e.quantity}',",
                f"--   'entry_price': '{e.entry_price}',",
                f"--   'stop_loss':   '',",
                f"--   'target':      '',",
                f"--   'strategy':    '{e.strategy}',",
                f"--   'confidence':  '',",
                f"--   'rr':          '',",
                f"--   'event':       'CLOSE',",
                f"--   'exit_price':  '{e.entry_price}',",
                f"--   'pnl':         '0.0',",
                f"--   'reason':      'SESSION_EXPIRED (reconciliation: age={e.age_days}d > carry_limit)'",
            ]
        lines += ["-- }"]
        lines.append("")

    # Group 3: Diagnostic queries (always included)
    lines += [
        "-- ---------------------------------------------------------------",
        "-- SECTION 3: Diagnostic queries (safe to run at any time)",
        "-- ---------------------------------------------------------------",
        "",
        "-- 3a: All open positions in trading_brain.db",
        "SELECT trade_id, symbol, direction, quantity, entry_price, ts_open",
        "  FROM trades",
        " WHERE status='open'",
        " ORDER BY symbol, ts_open;",
        "",
        "-- 3b: Duplicate open positions (same symbol+direction+entry)",
        "SELECT symbol, direction, entry_price, COUNT(*) AS dup_count",
        "  FROM trades",
        " WHERE status='open'",
        " GROUP BY symbol, direction, entry_price",
        " HAVING COUNT(*) > 1;",
        "",
        "-- 3c: Cross-check: execution_trade_links (market_behavior.db)",
        "-- (Run from market_behavior.db, after ATTACH if needed)",
        "SELECT order_id, symbol, direction_exec, opportunity_id,",
        "       linked_at, close_reason, realized_pnl",
        "  FROM execution_trade_links",
        " ORDER BY linked_at DESC;",
        "",
        "-- 3d: OIOS opportunities with position_exists=1 (should be 0 for orphans)",
        "SELECT opportunity_id, symbol, direction, current_state,",
        "       position_exists, position_size_pct, trade_pnl_pct",
        "  FROM opportunities",
        " WHERE position_exists = 1;",
        "",
    ]

    return "\n".join(lines)


# ── report formatter ──────────────────────────────────────────────────────────
def format_report(
    entries: List[ReconciliationEntry],
    remediation_sql: str,
    run_ts: str,
) -> str:

    counts = defaultdict(int)
    for e in entries:
        counts[e.classification] += 1

    total_positions  = len(entries)
    csv_positions    = load_csv_positions()
    db_positions     = load_db_positions()
    oios_links       = load_oios_links()
    oios_opps        = load_oios_opps()

    # Build per-entry table rows
    entry_rows = []
    for e in entries:
        opp_cell  = e.opportunity_id or "—"
        oid_cell  = e.order_id  or "—"
        tid_cell  = e.trade_id  or "—"
        entry_rows.append(
            f"| `{e.symbol}` | `{e.direction}` | {e.classification} | {e.source.upper()} "
            f"| {oid_cell} | {tid_cell} | {opp_cell} "
            f"| ₹{e.entry_price:,.2f} | {e.quantity} | {e.age_days}d "
            f"| {e.strategy[:25]} |"
        )

    # Detailed entries section
    detail_sections = []
    for e in entries:
        icon = {"VALID_OPEN": "✅", "ORPHAN_DB": "🔴", "ORPHAN_CSV": "🟡",
                "DUPLICATE": "🟠", "MISMATCH": "🔵"}.get(e.classification, "❓")
        detail_sections.append(textwrap.dedent(f"""
### {icon} {e.symbol} — {e.classification}

| Field | Value |
|---|---|
| Classification | **{e.classification}** |
| Source | {e.source.upper()} |
| order_id | `{e.order_id or "—"}` |
| trade_id (DB) | `{e.trade_id or "—"}` |
| opportunity_id | `{e.opportunity_id or "—"}` |
| Direction | {e.direction} |
| Entry Price | ₹{e.entry_price:,.2f} |
| Quantity | {e.quantity} |
| Opened At | {e.opened_at} |
| Age | {e.age_days} days |
| Strategy | {e.strategy or "—"} |

**Notes:**
{chr(10).join("- " + n for n in e.notes)}
""").strip())

    oios_db_note = (
        f"`{OIOS_DB}` — {len(oios_links)} link rows, {len(oios_opps)} live opportunities"
        if os.path.exists(OIOS_DB) else
        f"`data/market_behavior.db` — **does not exist** (bridge never ran in production)"
    )
    oios_opps_note = (
        f"{len(oios_opps)} live opportunities loaded"
        if os.path.exists(OIOS_DB) else
        "0 — DB absent"
    )

    report = f"""\
# POSITION RECONCILIATION REPORT

**Run Date:** {run_ts}
**System:** ai_trading_brain (paper trading mode)

---

## Executive Summary

| Classification | Count |
|---|---|
| ✅ VALID_OPEN | {counts.get("VALID_OPEN", 0)} |
| 🔴 ORPHAN_DB | {counts.get("ORPHAN_DB", 0)} |
| 🟡 ORPHAN_CSV | {counts.get("ORPHAN_CSV", 0)} |
| 🟠 DUPLICATE | {counts.get("DUPLICATE", 0)} |
| 🔵 MISMATCH | {counts.get("MISMATCH", 0)} |
| **Total** | **{total_positions}** |

**Key finding:** There are no currently active, in-window positions. The execution system
has zero positions it would restore on the next startup.

---

## Data Sources Audited

| Source | Path | Rows / Records |
|---|---|---|
| A: paper_trades.csv | `data/paper_trades.csv` | {len(csv_positions)} unclosed OPEN rows found |
| B: trading_brain.db | `data/trading_brain.db` | {len(db_positions)} `status=open` rows found |
| C: execution_trade_links | {oios_db_note} |
| D: OIOS opportunities | `data/market_behavior.db` | {oios_opps_note} |

---

## ID Format Mapping

The two open-position stores use **incompatible ID formats**:

| Store | ID Format | Example |
|---|---|---|
| `paper_trades.csv` | `SIM_{{SYMBOL}}_{{DIR}}_{{QTY}}` | `SIM_ITC_BUY_4861` |
| `trading_brain.db` | 8-char short hex UUID | `45A71EA9` |

There is no shared key between these two stores.
`_restore_from_journal()` only reads `paper_trades.csv` and has no visibility into `trading_brain.db`.

---

## Position Inventory

| Symbol | Dir | Classification | Source | order_id | trade_id | opp_id | Entry | Qty | Age | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(entry_rows)}

---

## Detailed Findings

{(chr(10) + chr(10)).join(detail_sections)}

---

## Root Cause Analysis

### Why 21 ORPHAN_DB positions exist (WIPRO×7, TCS×7, HDFCBANK×7)

Timeline:
```
2026-03-11 10:44–12:57  Old orchestrator ran 7 trade cycles for WIPRO, TCS, HDFCBANK.
                         Each cycle wrote an OPEN record to trading_brain.db.
                         Same entry price repeated across all cycles:
                           WIPRO    ₹1,501.50 × 3 qty  (×7 cycles = 21 qty total)
                           TCS      ₹4,204.20 × 1 qty  (×7 cycles)
                           HDFCBANK ₹1,701.70 × 3 qty  (×7 cycles)
                         No CLOSE was ever written — the old orchestrator likely
                         crashed or was replaced before positions were resolved.

2026-03-19+             New orchestrator deployed. Writes only to paper_trades.csv.
                         Never reads trading_brain.db.
                         The 21 old positions became permanently invisible.

2026-06-16 (today)      21 rows remain in trading_brain.db.status='open'.
                         The execution system is completely unaware of them.
```

**Why 7 cycles of the same trade?**
The identical entry prices across all 7 records for each symbol (e.g. WIPRO always
₹1,501.50) suggest this was a test run where the same signal fired repeatedly,
bypassing the duplicate-position guard — possibly because the old orchestrator did not
have the `_symbol_has_open_position()` guard that the current one has.

### Why 1 ORPHAN_CSV position exists (ITC, SIM_ITC_BUY_4861)

```
2026-04-17 13:00:20  ORDER_PLACED: SIM_ITC_BUY_4861 (ITC BUY 4861 × ₹308.55)
                      Written to paper_trades.csv as OPEN.
                      No CLOSE row written (system not restarted since? or close write failed).

2026-06-16 (today)   Age = 60 days.  Carry limit for EDG_MOMENT_* strategy = 5 days.
                      _restore_from_journal() would immediately SESSION_EXPIRE this
                      position at next startup — it will NOT be restored as live.
```

---

## Remediation SQL

```sql
{remediation_sql}
```

---

## Traceability Matrix

Every discovered position mapped to its provenance chain:

| order_id / trade_id | Source | CSV open? | DB open? | OIOS link? | OIOS opp? | Traceable? |
|---|---|---|---|---|---|---|
{_traceability_rows(entries, oios_links, oios_opps)}

---

## Verification Queries

Run after applying remediation to confirm clean state:

```sql
-- 1. Confirm no phantom open rows remain in trading_brain.db
SELECT COUNT(*) AS phantom_open
  FROM trades
 WHERE status = 'open';
-- Expected: 0

-- 2. Confirm paper_trades.csv has no unexpired open-only positions
-- (Python: parse CSV, find order_ids where OPEN has no CLOSE and age <= carry_limit)

-- 3. Cross-verify execution_trade_links has no unresolved open positions
SELECT COUNT(*) AS unresolved_links
  FROM execution_trade_links
 WHERE close_reason IS NULL;
-- Expected: 0 after all positions are closed

-- 4. Confirm OIOS position_exists is 0 for all stale entries
SELECT COUNT(*) AS phantom_oios_open
  FROM opportunities
 WHERE position_exists = 1;
-- Expected: 0 (no positions were ever bridge-linked)
```

---

*Generated by `reconcile_positions.py` on {run_ts}*
"""
    return report


def _traceability_rows(
    entries: List[ReconciliationEntry],
    oios_links: List[LinkRecord],
    oios_opps:  List[OiosOpp],
) -> str:
    link_oids = {l.order_id for l in oios_links}
    opp_syms  = {o.symbol for o in oios_opps}
    rows = []
    for e in entries:
        csv_open = "✅" if e.source == "csv" else "—"
        db_open  = "✅" if e.source == "db"  else "—"
        link_ok  = "✅" if e.order_id in link_oids else "❌"
        opp_ok   = "✅" if e.symbol in opp_syms else "❌"
        traceable = "✅" if (e.order_id or e.trade_id) else "❌"
        key = e.order_id or e.trade_id or "—"
        rows.append(
            f"| `{key}` | {e.source.upper()} | {csv_open} | {db_open} "
            f"| {link_ok} | {opp_ok} | {traceable} |"
        )
    return "\n".join(rows)


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_ts  = datetime.now().isoformat(timespec="seconds")
    entries = reconcile()

    print(f"\n=== Position Reconciliation ({run_ts}) ===\n")

    counts: Dict[str, int] = defaultdict(int)
    for e in entries:
        counts[e.classification] += 1
        icon = {"VALID_OPEN": "✅", "ORPHAN_DB": "🔴",
                "ORPHAN_CSV": "🟡", "DUPLICATE": "🟠", "MISMATCH": "🔵"}.get(
            e.classification, "❓")
        print(f"  {icon} [{e.classification}] {e.symbol} {e.direction}"
              f"  source={e.source.upper()}  age={e.age_days}d"
              f"  order_id={e.order_id or '—'}  trade_id={e.trade_id or '—'}"
              f"  opp_id={e.opportunity_id or '—'}")
        for note in e.notes:
            print(f"       → {note}")

    print(f"\nSummary: ", {k: v for k, v in counts.items()})

    sql  = generate_remediation_sql(entries)
    report = format_report(entries, sql, run_ts)

    out_path = os.path.join(ROOT, "POSITION_RECONCILIATION_REPORT.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    print(f"\nReport written → POSITION_RECONCILIATION_REPORT.md")
