"""
historical_replay.py

Historical Replay Framework for OIOS.

Replays the full Phase A/B pipeline (Layer 1A + 1B + Sector Conviction +
Opportunity Lifecycle) against 5 years of historical OHLCV data using
the same scanner and state machine code that runs in production.

Purpose:
  NOT a substitute for live data collection.
  IS a source of empirical evidence to validate:
    - Archetype firing frequencies
    - TTL default accuracy
    - Lifecycle diversity (does the population cycle between states?)
    - Sector conviction behavior across regimes
    - Path curves for RE formula calibration (Phase C)

What it can validate:
  ✓ Archetypes fire at plausible frequencies on real market data
  ✓ TTL defaults are appropriate for typical opportunity durations
  ✓ State machine produces diversity (DISCOVERED/ACTIVE/WATCHING/INVALID)
  ✓ Sector conviction scores are differentiated (not all PARTIAL)
  ✓ Theme phases activate after 30-day history guard

What it cannot validate:
  ✗ Operational data pipeline (live-feed failures, missing BHAV files)
  ✗ Real-time symbol renames and delistings
  ✗ Future regime behavior
  ✗ Live readiness gates (those require actual live production data)

Usage:
  # Phase 1: Download historical OHLCV
  python historical_replay.py --phase load --start 2021-01-01 --end 2025-12-31

  # Phase 2: Run simulation
  python historical_replay.py --phase simulate --start 2021-01-01 --end 2025-12-31

  # Both phases (default)
  python historical_replay.py --start 2021-01-01 --end 2025-12-31

  # Custom DB path
  python historical_replay.py --db data/replay.db --phase all

  # Resume simulation (skip re-download)
  python historical_replay.py --phase simulate

Output:
  - Writes to a separate replay DB (default: data/replay.db)
  - Does NOT touch data/market_behavior.db (live DB is never modified)
  - Prints daily progress every 20 trading days
  - Prints final summary matching check_phase_c_ready.py criteria
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import time
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NIFTY50_SYMBOL = "^NSEI"       # yfinance symbol for NIFTY50 Index
DEFAULT_DB_PATH = "data/replay.db"
DEFAULT_START   = "2021-01-01"
DEFAULT_END     = "2025-12-31"

# Phase B proxy conviction rule (replaces Phase C RE — deterministic only)
# Each confirming signal contributes this many conviction points.
# ACTIVE_THRESHOLD = 6.0 (from state_machine.py).
# With 3 confirming signals: 3 × 2.5 = 7.5 → ACTIVE.
CONVICTION_PER_CONFIRMING = 2.5
CONVICTION_PER_CONFLICTING = 1.0    # deducted per conflicting signal
ACTIVE_THRESHOLD = 6.0              # must match state_machine.ACTIVE_THRESHOLD

# Edge consumed thresholds (Phase B proxy — Phase C will compute RE properly)
EC_FOR_WATCHING  = 0.50    # ACTIVE → WATCHING when 50% of expected move consumed
EC_FOR_RECOVERY  = 0.30    # WATCHING → ACTIVE when EC drops back to 30%

# Regime detection (NIFTY50-based)
REGIME_TREND_THRESHOLD_PCT = 2.0    # 20d change must exceed ±2% to call TREND
REGIME_SMA_BAND = 0.02              # must be ±2% from SMA200 to call TREND

# Rate limiting
INTER_SYMBOL_DELAY_S = 0.25         # seconds between yfinance requests
BHAV_RETRY_DELAY_S   = 1.0          # seconds between BHAV requests

# Report interval
REPORT_EVERY_N_DAYS = 20            # print progress this often


# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

def open_replay_db(db_path: str) -> sqlite3.Connection:
    """
    Open (or create) the replay database.
    Applies Phase B schema + seeds universe.
    Safe to call on an existing DB — all operations are idempotent.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    from oios.db.migrations import apply_phase_b
    from oios.db.universe import seed_universe

    apply_phase_b(conn)
    seed_universe(conn)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM universe_stocks WHERE is_active = 1").fetchone()[0]
    log.info("[Replay] DB ready at %s — %d active universe symbols", db_path, count)
    return conn


# ---------------------------------------------------------------------------
# Phase 1: Historical data loading
# ---------------------------------------------------------------------------

def _populate_trading_calendar(
    conn: sqlite3.Connection,
    nifty_rows: list[tuple],
    start: str,
    end: str,
) -> int:
    """
    Derive NSE trading days from NIFTY50 OHLCV dates and populate trading_calendar.
    Non-trading days (weekends + holidays) are marked is_trading_day=0.
    Returns count of trading days inserted.
    """
    trading_dates = {row[1] for row in nifty_rows}   # row[1] = trade_date

    d     = date.fromisoformat(start)
    end_d = date.fromisoformat(end)

    calendar_rows = []
    while d <= end_d:
        ds = d.isoformat()
        calendar_rows.append((ds, 1 if ds in trading_dates else 0, None))
        d += timedelta(days=1)

    conn.executemany("""
        INSERT OR IGNORE INTO trading_calendar (calendar_date, is_trading_day, holiday_name)
        VALUES (?, ?, ?)
    """, calendar_rows)
    conn.commit()

    return len(trading_dates)


def load_historical_ohlcv(
    conn: sqlite3.Connection,
    start: str,
    end: str,
    inter_symbol_delay: float = INTER_SYMBOL_DELAY_S,
) -> dict:
    """
    Download NIFTY50 + all 230 universe symbols via yfinance.
    Writes to ohlcv_daily and trading_calendar.

    Returns summary with keys:
      symbols_ok, symbols_failed, rows_inserted, trading_days
    """
    from oios.data.ohlcv_fetcher import fetch_symbol_ohlcv, upsert_ohlcv_rows

    summary = {
        "symbols_ok":     0,
        "symbols_failed": 0,
        "rows_inserted":  0,
        "trading_days":   0,
    }

    # ── NIFTY50: trading calendar anchor ─────────────────────────────────
    log.info("[Load] Downloading NIFTY50 (%s) for trading calendar", NIFTY50_SYMBOL)
    nifty_rows = fetch_symbol_ohlcv(NIFTY50_SYMBOL, start, end)

    if not nifty_rows:
        log.error("[Load] NIFTY50 download failed — trading calendar cannot be populated")
        log.error("[Load] Check network connectivity and retry with --phase load")
        return summary

    # Insert NIFTY50 into ohlcv_daily (^NSEI is not in universe_stocks but the
    # table has no FK constraint to universe_stocks, so this is fine).
    # We use it only for regime detection — not for scanning.
    conn.executemany("""
        INSERT OR IGNORE INTO ohlcv_daily
            (symbol, trade_date, open, high, low, close, volume, adjusted_close, data_source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, nifty_rows)

    trading_days = _populate_trading_calendar(conn, nifty_rows, start, end)
    summary["trading_days"] = trading_days
    summary["rows_inserted"] += len(nifty_rows)
    log.info("[Load] Trading calendar: %d NSE trading days in [%s, %s]", trading_days, start, end)

    # ── Universe symbols ─────────────────────────────────────────────────
    symbols = [
        r[0] for r in conn.execute(
            "SELECT symbol FROM universe_stocks WHERE is_active = 1 ORDER BY symbol"
        ).fetchall()
    ]
    total = len(symbols)
    log.info("[Load] Downloading OHLCV for %d symbols...", total)

    for i, symbol in enumerate(symbols, 1):
        rows = fetch_symbol_ohlcv(symbol, start, end)
        if not rows:
            log.warning("[Load] %s: no data returned — will be skipped in simulation", symbol)
            summary["symbols_failed"] += 1
        else:
            n = upsert_ohlcv_rows(conn, rows)
            summary["rows_inserted"] += n
            summary["symbols_ok"] += 1

        if i % 50 == 0:
            conn.commit()
            log.info("[Load] %d/%d symbols loaded (ok=%d failed=%d)",
                     i, total, summary["symbols_ok"], summary["symbols_failed"])

        time.sleep(inter_symbol_delay)

    conn.commit()
    log.info(
        "[Load] OHLCV complete: %d ok / %d failed / %d rows total",
        summary["symbols_ok"], summary["symbols_failed"], summary["rows_inserted"],
    )
    return summary


def load_historical_bhav(
    conn: sqlite3.Connection,
    start: str,
    end: str,
) -> dict:
    """
    Attempt to download NSE BHAV copies for each trading day in [start, end].
    Silently skips days that fail (rate-limit, network, or archive unavailable).
    Older archives (pre-2022) may not be accessible — this is expected.

    Returns summary with keys: days_attempted, days_ok, days_failed, rows_inserted.
    """
    from oios.data.bhav_fetcher import fetch_bhav, upsert_bhav_rows, has_bhav_for_date

    summary = {
        "days_attempted": 0,
        "days_ok":        0,
        "days_failed":    0,
        "rows_inserted":  0,
    }

    trading_days = [
        r[0] for r in conn.execute("""
            SELECT calendar_date FROM trading_calendar
            WHERE is_trading_day = 1
              AND calendar_date BETWEEN ? AND ?
            ORDER BY calendar_date
        """, (start, end)).fetchall()
    ]

    log.info("[Load] Attempting BHAV download for %d trading days...", len(trading_days))

    for td in trading_days:
        if has_bhav_for_date(conn, td):
            continue                      # already loaded in a prior run

        summary["days_attempted"] += 1

        rows = fetch_bhav(td)              # returns [] on any failure
        if not rows:
            summary["days_failed"] += 1
        else:
            n = upsert_bhav_rows(conn, rows)
            summary["rows_inserted"] += n
            summary["days_ok"] += 1

        time.sleep(BHAV_RETRY_DELAY_S)

    conn.commit()
    log.info(
        "[Load] BHAV complete: %d ok / %d failed / %d rows",
        summary["days_ok"], summary["days_failed"], summary["rows_inserted"],
    )
    return summary


# ---------------------------------------------------------------------------
# Regime detection (simplified NIFTY50-based)
# ---------------------------------------------------------------------------

def _detect_regime(conn: sqlite3.Connection, as_of_date: str) -> str:
    """
    Returns TRENDING_UP | TRENDING_DOWN | SIDEWAYS based on NIFTY50 position.
    Uses SMA200 and 20-day return as proxies for the full Layer 2 MarketIntelligence.

    This is intentionally simple — Phase C validation does not require precise
    regime labels, only plausible ones. The live system uses the full Layer 2
    regime which includes VIX, options data, and breadth metrics.
    """
    rows = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT 220
    """, (NIFTY50_SYMBOL, as_of_date)).fetchall()

    if len(rows) < 25:
        return "SIDEWAYS"

    closes = [r[0] for r in reversed(rows)]
    current = closes[-1]

    sma_window = min(200, len(closes))
    sma = sum(closes[-sma_window:]) / sma_window

    change_20d = 0.0
    if len(closes) >= 21:
        change_20d = (current / closes[-21] - 1.0) * 100.0

    above_sma = current > sma * (1 + REGIME_SMA_BAND)
    below_sma = current < sma * (1 - REGIME_SMA_BAND)

    if above_sma and change_20d > REGIME_TREND_THRESHOLD_PCT:
        return "TRENDING_UP"
    if below_sma and change_20d < -REGIME_TREND_THRESHOLD_PCT:
        return "TRENDING_DOWN"
    return "SIDEWAYS"


# ---------------------------------------------------------------------------
# Signal birth assembly
# ---------------------------------------------------------------------------

def _raw_signal_to_signal_birth(
    raw,
    sector: str,
    theme_phase: Optional[str] = None,
    consensus_score: Optional[float] = None,
) -> object:
    """
    Convert a RawSignal (from layer_1a or layer_1b) to a SignalBirth domain object.
    The sector and current theme_phase are injected from the caller.
    """
    from oios.domain.models import SignalBirth

    sb = SignalBirth(
        signal_id                = str(uuid.uuid4()),
        symbol                   = raw.symbol,
        archetype_id             = raw.archetype_id,
        signal_type              = raw.signal_type,
        detected_at              = raw.detected_at,
        birth_price              = raw.birth_price,
        base_score               = raw.base_score,
        regime_at_birth          = raw.regime,
        expected_ttl_days        = raw.expected_ttl_days,
        expected_move_direction  = raw.direction,
        expected_move_pct        = raw.expected_move_pct,
        expected_move_pct_source = raw.expected_move_pct_source,
        archetype_version        = raw.archetype_version,
        theme_phase_at_birth     = theme_phase,
        consensus_score_at_birth = consensus_score,
    )
    # Inject sector as a dynamic attribute for _create_new() in opportunity_service.py
    # (uses getattr(signal, "sector", "UNKNOWN"))
    object.__setattr__(sb, "sector", sector) if hasattr(type(sb), "__slots__") else setattr(sb, "sector", sector)
    return sb


# ---------------------------------------------------------------------------
# Conviction (Phase B proxy)
# ---------------------------------------------------------------------------

def _recompute_conviction(conn: sqlite3.Connection, opportunity_id: str) -> float:
    """
    Phase B deterministic conviction proxy.
    Phase C will replace this with RE-based scoring.

    Formula: confirming_count × 2.5 − conflicting_count × 1.0, clamped [0, 10].
    Reaches ACTIVE_THRESHOLD (6.0) with 3 confirming signals.
    """
    row = conn.execute("""
        SELECT confirming_count, conflicting_count
        FROM opportunities WHERE opportunity_id = ?
    """, (opportunity_id,)).fetchone()
    if not row:
        return 0.0
    score = (row["confirming_count"] * CONVICTION_PER_CONFIRMING
             - row["conflicting_count"] * CONVICTION_PER_CONFLICTING)
    return max(0.0, min(10.0, score))


# ---------------------------------------------------------------------------
# Edge consumed computation
# ---------------------------------------------------------------------------

def _compute_edge_consumed(
    conn: sqlite3.Connection,
    symbol: str,
    birth_price: float,
    expected_move_pct: float,
    direction: str,
    as_of_date: str,
) -> float:
    """
    EC = actual_move / expected_move, capped at [0, 1].
    For LONG: (current − birth) / expected_move
    For SHORT: (birth − current) / expected_move
    Returns 0.0 when no current price data is available.
    """
    row = conn.execute("""
        SELECT close FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 1
    """, (symbol, as_of_date)).fetchone()

    if not row or birth_price <= 0:
        return 0.0

    expected_move = birth_price * expected_move_pct / 100.0
    if expected_move <= 0:
        return 0.0

    current_price = row[0]
    if direction == "LONG":
        raw_ec = (current_price - birth_price) / expected_move
    else:
        raw_ec = (birth_price - current_price) / expected_move

    return max(0.0, min(1.0, raw_ec))


# ---------------------------------------------------------------------------
# Opportunity lifecycle tick (one day)
# ---------------------------------------------------------------------------

def _persist_result(
    conn: sqlite3.Connection,
    opp,
    transitions: list,
) -> None:
    """Persist state machine output to DB."""
    from oios.db import repository as R

    for t in transitions:
        try:
            R.append_transition(conn, t)
        except Exception as exc:
            log.debug("[Replay] Transition persist error for %s: %s", opp.opportunity_id, exc)
    if opp:
        try:
            R.update_opportunity_state(conn, opp)
        except Exception as exc:
            log.debug("[Replay] Opportunity update error for %s: %s", opp.opportunity_id, exc)


def tick_opportunity(
    conn: sqlite3.Connection,
    opportunity_id: str,
    today: str,
    regime: str,
) -> None:
    """
    Advance one opportunity through one day's lifecycle:
      1. Increment age
      2. Recompute EC (edge consumed)
      3. Recompute Phase B proxy conviction
      4. Run state machine transitions: expiry check, terminal conditions,
         ACTIVE↔WATCHING cycling
    """
    from oios.db import repository as R
    from oios.domain.models import OpportunityState
    from oios.domain.state_machine import (
        expire_discovered,
        check_terminal_conditions,
        try_activate,
        try_watch,
        try_reactivate,
        TriggerCause,
    )

    opp = R.get_opportunity(conn, opportunity_id)
    if opp is None or opp.current_state == OpportunityState.INVALID:
        return

    # ── Advance age ────────────────────────────────────────────────────────
    opp.age_trading_days += 1

    # ── Edge consumed ──────────────────────────────────────────────────────
    if opp.first_signal_id:
        sb_row = conn.execute("""
            SELECT birth_price, expected_move_pct, expected_move_direction
            FROM signal_births WHERE signal_id = ?
        """, (opp.first_signal_id,)).fetchone()
        if sb_row:
            opp.edge_consumed_pct = _compute_edge_consumed(
                conn,
                symbol             = opp.symbol,
                birth_price        = sb_row["birth_price"],
                expected_move_pct  = sb_row["expected_move_pct"] or 8.0,
                direction          = sb_row["expected_move_direction"],
                as_of_date         = today,
            )

    # ── Phase B proxy conviction ───────────────────────────────────────────
    opp.conviction_score = _recompute_conviction(conn, opportunity_id)
    R.update_opportunity_state(conn, opp)

    # ── DISCOVERED: expiry check then activation attempt ──────────────────
    if opp.current_state == OpportunityState.DISCOVERED:
        opp, transitions, _ = expire_discovered(opp, today)
        _persist_result(conn, opp, transitions)
        if opp.current_state == OpportunityState.INVALID:
            return
        opp, transitions, _ = try_activate(opp, regime=regime)
        _persist_result(conn, opp, transitions)
        return

    # ── ACTIVE / WATCHING: terminal conditions ────────────────────────────
    opp, transitions, _ = check_terminal_conditions(opp, today, regime=regime)
    _persist_result(conn, opp, transitions)
    if opp.current_state == OpportunityState.INVALID:
        return

    # ── ACTIVE → WATCHING when EC exceeds midpoint ────────────────────────
    if opp.current_state == OpportunityState.ACTIVE and opp.edge_consumed_pct >= EC_FOR_WATCHING:
        opp, transitions, _ = try_watch(
            opp,
            trigger_cause=TriggerCause.EC_THRESHOLD,
            regime=regime,
        )
        _persist_result(conn, opp, transitions)
        return

    # ── WATCHING → ACTIVE when EC falls back ─────────────────────────────
    if opp.current_state == OpportunityState.WATCHING and opp.edge_consumed_pct <= EC_FOR_RECOVERY:
        opp, transitions, _ = try_reactivate(opp, regime=regime)
        _persist_result(conn, opp, transitions)


# ---------------------------------------------------------------------------
# Phase 2: Simulation loop
# ---------------------------------------------------------------------------

def run_simulation(
    conn: sqlite3.Connection,
    start: str,
    end: str,
) -> dict:
    """
    Run the full OIOS pipeline day-by-day across [start, end].

    For each trading day:
      1. Detect regime from NIFTY50
      2. Run Layer 1A + 1B scanners
      3. Write qualifying signals → attach/create opportunities
      4. Run Sector Conviction (Layer 1.5)
      5. Tick all live opportunities through the state machine

    Returns a summary dict for final reporting.
    """
    from oios.db.universe import get_active_symbols
    from oios.db import repository as R
    from oios.data.sector_conviction_writer import run_sector_conviction
    from oios.domain.opportunity_service import attach_or_create_opportunity
    import oios.scanners.layer_1a as l1a
    import oios.scanners.layer_1b as l1b

    # Build symbol→sector lookup
    sector_map: dict[str, str] = {
        r[0]: r[1] for r in conn.execute(
            "SELECT symbol, sector FROM universe_stocks WHERE is_active = 1"
        ).fetchall()
    }
    symbols = list(sector_map.keys())

    # Get all trading days in range
    trading_days = [
        r[0] for r in conn.execute("""
            SELECT calendar_date FROM trading_calendar
            WHERE is_trading_day = 1
              AND calendar_date BETWEEN ? AND ?
            ORDER BY calendar_date
        """, (start, end)).fetchall()
    ]

    if not trading_days:
        log.error("[Sim] No trading days found in [%s, %s]. Run --phase load first.", start, end)
        return {"error": "no_trading_days"}

    log.info("[Sim] Simulating %d trading days from %s to %s", len(trading_days), start, end)

    summary = {
        "days_simulated": 0,
        "signals_written": 0,
        "opportunities_created": 0,
        "opportunities_merged": 0,
        "state_changes": 0,
    }

    day_count = len(trading_days)

    for day_idx, today in enumerate(trading_days, 1):

        regime = _detect_regime(conn, today)

        # ── Layer 1A scan ────────────────────────────────────────────────
        scan_1a = l1a.run_scan(conn, symbols, today, regime)

        # ── Layer 1B scan ────────────────────────────────────────────────
        scan_1b = l1b.run_scan(conn, symbols, today, regime)

        # ── Process qualifying signals ────────────────────────────────────
        all_qualifying = list(scan_1a.qualifying_signals) + list(scan_1b.qualifying_signals)

        # Get current theme phase per sector for signal birth annotation
        theme_phases: dict[str, Optional[str]] = {}
        for sector in set(sector_map.values()):
            ph_row = conn.execute("""
                SELECT phase FROM theme_phase_history
                WHERE sector = ? AND exited_at IS NULL
                ORDER BY entered_at DESC LIMIT 1
            """, (sector,)).fetchone()
            theme_phases[sector] = ph_row["phase"] if ph_row else None

        # Get current sector conviction scores for consensus_score_at_birth
        conviction_scores: dict[str, Optional[float]] = {}
        for sector in set(sector_map.values()):
            sc_row = conn.execute("""
                SELECT sector_conviction_score FROM sector_conviction_daily
                WHERE sector = ? AND record_date <= ?
                ORDER BY record_date DESC LIMIT 1
            """, (sector, today)).fetchone()
            conviction_scores[sector] = sc_row["sector_conviction_score"] if sc_row else None

        with conn:
            for raw in all_qualifying:
                sector = sector_map.get(raw.symbol, "UNKNOWN")
                theme_phase = theme_phases.get(sector)
                consensus_score = conviction_scores.get(sector)

                sb = _raw_signal_to_signal_birth(raw, sector, theme_phase, consensus_score)

                # Persist signal birth
                try:
                    R.create_signal_birth(conn, sb)
                except Exception as exc:
                    log.debug("[Sim] Signal birth persist failed for %s: %s", raw.symbol, exc)
                    continue

                # Attach to or create opportunity
                ttl = raw.expected_ttl_days
                try:
                    opp, is_new = attach_or_create_opportunity(
                        conn, sb, ttl, regime, theme_phase, today
                    )
                    if is_new:
                        summary["opportunities_created"] += 1
                    else:
                        summary["opportunities_merged"] += 1
                    summary["signals_written"] += 1
                except Exception as exc:
                    log.debug("[Sim] Opportunity attach failed for %s: %s", raw.symbol, exc)

        # ── Sector Conviction (Layer 1.5) ─────────────────────────────────
        try:
            run_sector_conviction(conn, today, regime)
        except Exception as exc:
            log.debug("[Sim] Sector conviction failed on %s: %s", today, exc)

        # ── Tick all live opportunities ────────────────────────────────────
        live_ids = [
            r[0] for r in conn.execute("""
                SELECT opportunity_id FROM opportunities
                WHERE current_state IN ('DISCOVERED', 'ACTIVE', 'WATCHING')
            """).fetchall()
        ]

        with conn:
            for opp_id in live_ids:
                try:
                    tick_opportunity(conn, opp_id, today, regime)
                except Exception as exc:
                    log.debug("[Sim] Tick failed for %s on %s: %s", opp_id, today, exc)

        summary["days_simulated"] += 1

        if day_idx % REPORT_EVERY_N_DAYS == 0 or day_idx == day_count:
            _print_daily_progress(conn, day_idx, day_count, today, regime, summary)

    return summary


def _print_daily_progress(
    conn: sqlite3.Connection,
    day_idx: int,
    day_count: int,
    today: str,
    regime: str,
    summary: dict,
) -> None:
    """Print a compact progress line during simulation."""
    live = conn.execute("""
        SELECT current_state, COUNT(*) AS n
        FROM opportunities
        WHERE current_state != 'INVALID'
        GROUP BY current_state
    """).fetchall()
    live_str = "  ".join(f"{r['current_state']}={r['n']}" for r in live)
    total_signals = conn.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
    total_opps    = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]

    log.info(
        "[Sim] Day %d/%d  %s  regime=%-12s  signals=%d  opps=%d  live:[%s]",
        day_idx, day_count, today, regime, total_signals, total_opps, live_str,
    )


# ---------------------------------------------------------------------------
# Final report (mirrors check_phase_c_ready.py output)
# ---------------------------------------------------------------------------

def print_replay_report(conn: sqlite3.Connection, sim_summary: dict) -> None:
    """
    Print a Phase C readiness summary based on replay data.
    Mirrors the criteria checked by check_phase_c_ready.py so the output
    can be compared directly with live data when it arrives.
    """
    SEP = "-" * 65

    print(f"\n{SEP}")
    print("  HISTORICAL REPLAY — PHASE C READINESS ESTIMATE")
    print(f"{SEP}")
    print(f"  Days simulated:        {sim_summary.get('days_simulated', 0)}")
    print(f"  Signals written:       {sim_summary.get('signals_written', 0)}")
    print(f"  Opportunities created: {sim_summary.get('opportunities_created', 0)}")
    print(f"  Opportunities merged:  {sim_summary.get('opportunities_merged', 0)}")

    # C-Ready-1: signal births
    n_births = conn.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
    by_arch = conn.execute("""
        SELECT archetype_id, COUNT(*) AS n FROM signal_births
        GROUP BY archetype_id ORDER BY n DESC
    """).fetchall()

    print(f"\n  C-Ready-1  signal_births total: {n_births}")
    for r in by_arch:
        print(f"    {r['archetype_id']:<38} {r['n']}")

    # C-Ready-2: sector conviction
    conviction_rows = conn.execute("""
        SELECT sector, COUNT(*) AS full_rows
        FROM sector_conviction_daily
        WHERE data_quality = 'FULL'
        GROUP BY sector ORDER BY full_rows DESC
    """).fetchall()
    print(f"\n  C-Ready-2  FULL conviction rows per sector:")
    for r in conviction_rows:
        badge = "✓" if r["full_rows"] >= 30 else "✗"
        print(f"    {badge} {r['sector']:<22}  {r['full_rows']}")

    # C-Ready-3: theme phase history
    n_phases = conn.execute("SELECT COUNT(*) FROM theme_phase_history").fetchone()[0]
    print(f"\n  C-Ready-3  theme_phase_history records: {n_phases}")

    # C-Ready-4: archetype rates
    total_days = conn.execute(
        "SELECT COUNT(DISTINCT detected_at) FROM signal_births"
    ).fetchone()[0]
    if total_days > 0:
        print(f"\n  C-Ready-4  archetype daily rates (over {total_days} days):")
        for r in by_arch:
            rate = r["n"] / total_days
            print(f"    {r['archetype_id']:<38} {rate:.2f}/day")

    # C-Ready-5: lifecycle diversity
    states = conn.execute("""
        SELECT current_state, COUNT(*) AS n
        FROM opportunities GROUP BY current_state ORDER BY n DESC
    """).fetchall()
    total_opps = sum(r["n"] for r in states)
    print(f"\n  C-Ready-5  opportunity lifecycle ({total_opps} total):")
    for r in states:
        pct = r["n"] / total_opps * 100 if total_opps > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"    {r['current_state']:<12}  {r['n']:>5}  ({pct:5.1f}%)  {bar}")

    inv_reasons = conn.execute("""
        SELECT invalidation_reason, COUNT(*) AS n
        FROM opportunities
        WHERE invalidation_reason IS NOT NULL
        GROUP BY invalidation_reason ORDER BY n DESC
    """).fetchall()
    if inv_reasons:
        print("    Invalidation reasons:")
        for r in inv_reasons:
            print(f"      {r['invalidation_reason']:<30}  {r['n']}")

    print(f"\n{SEP}")
    print("  NOTE: Replay data ≠ live data. Use check_phase_c_ready.py")
    print("  against data/market_behavior.db for the authoritative gate.")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OIOS Historical Replay — generates empirical population data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Replay database path (default: {DEFAULT_DB_PATH}). "
             f"NEVER points to data/market_behavior.db.",
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help=f"Start date ISO-8601 (default: {DEFAULT_START})",
    )
    parser.add_argument(
        "--end",
        default=DEFAULT_END,
        help=f"End date ISO-8601 (default: {DEFAULT_END})",
    )
    parser.add_argument(
        "--phase",
        choices=["load", "simulate", "all"],
        default="all",
        help="load = download OHLCV only; simulate = run pipeline only; "
             "all = download then simulate (default)",
    )
    parser.add_argument(
        "--skip-bhav",
        action="store_true",
        help="Skip BHAV delivery data download (DNA_1B_DELIVERY_EXPANSION will not fire)",
    )
    parser.add_argument(
        "--inter-symbol-delay",
        type=float,
        default=INTER_SYMBOL_DELAY_S,
        metavar="SECONDS",
        help=f"Delay between yfinance requests (default: {INTER_SYMBOL_DELAY_S}s)",
    )

    args = parser.parse_args()

    # Safety guard: refuse to overwrite the live database
    live_db = Path("data/market_behavior.db").resolve()
    replay_db = Path(args.db).resolve()
    if replay_db == live_db:
        print("\n[FATAL] --db must not point to data/market_behavior.db")
        print("        The replay always uses a separate database.")
        print("        Use --db data/replay.db or any other path.")
        raise SystemExit(1)

    conn = open_replay_db(args.db)

    if args.phase in ("load", "all"):
        log.info("[Replay] === PHASE 1: LOAD ===")
        load_historical_ohlcv(conn, args.start, args.end, args.inter_symbol_delay)
        if not args.skip_bhav:
            log.info("[Replay] Attempting BHAV download (use --skip-bhav to skip)")
            load_historical_bhav(conn, args.start, args.end)
        else:
            log.info("[Replay] BHAV skipped — DNA_1B_DELIVERY_EXPANSION will not fire")

    if args.phase in ("simulate", "all"):
        log.info("[Replay] === PHASE 2: SIMULATE ===")
        sim_summary = run_simulation(conn, args.start, args.end)
        print_replay_report(conn, sim_summary)

    conn.close()


if __name__ == "__main__":
    main()
