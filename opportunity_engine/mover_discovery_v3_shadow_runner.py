"""
opportunity_engine/mover_discovery_v3_shadow_runner.py
=======================================================
Phase D V3 Shadow Runner
=========================
Called from master_orchestrator._run_post_market_scan() AFTER the existing
Phase D scanner and OIOS data refresh both complete.

SAFETY INVARIANTS (must hold at all times):
  - NEVER calls CandidateStore.write()
  - NEVER creates TradeSignal or Signal objects
  - NEVER calls DecisionEngine, RiskControl, or ExecutionEngine
  - NEVER modifies portfolio or position state
  - Any exception is caught by the orchestrator; production scanner is unaffected
  - Output: append-only JSONL at data/logs/mover_discovery_v3_shadow.jsonl
  - Every written record carries no_trades_generated=True
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

_SHADOW_LOG_PATH = Path("data/logs/mover_discovery_v3_shadow.jsonl")
_MIN_HISTORY_BARS = 35  # need at least this many daily bars for V3 features


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_universe_symbols() -> List[str]:
    """
    Return active symbols from OIOS universe_stocks.
    Falls back to nifty500_universe.json if the DB is unavailable.
    """
    try:
        from oios.db.connection import get_connection
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT symbol FROM universe_stocks WHERE is_active=1"
            ).fetchall()
            if rows:
                return [r[0] for r in rows]
    except Exception as exc:
        log.warning("[V3ShadowRunner] DB universe load failed: %s — trying JSON fallback.", exc)

    try:
        uni_path = Path("data/nifty500_universe.json")
        if uni_path.exists():
            data = json.loads(uni_path.read_text(encoding="utf-8"))
            return [s["symbol"] for s in data if isinstance(s, dict) and s.get("symbol")]
    except Exception as exc2:
        log.warning("[V3ShadowRunner] JSON universe fallback also failed: %s", exc2)

    return []


def _load_ohlcv_from_db(
    symbols: List[str],
    trade_date: str,
) -> Dict[str, Dict[str, List[float]]]:
    """
    Bulk-load the last _MIN_HISTORY_BARS trading days from ohlcv_daily.

    Returns {symbol: {"closes": [...], "highs": [...], "lows": [...], "volumes": [...]}}
    Symbols with fewer than _MIN_HISTORY_BARS rows are silently dropped.
    """
    if not symbols:
        return {}

    result: Dict[str, Dict[str, List[float]]] = {}
    try:
        from oios.db.connection import get_connection
        # SQLite IN clause limit is 999; chunk if needed
        chunk_size = 900
        raw_rows: List = []
        with get_connection() as conn:
            for start in range(0, len(symbols), chunk_size):
                chunk = symbols[start: start + chunk_size]
                placeholders = ",".join("?" * len(chunk))
                rows = conn.execute(
                    f"SELECT symbol, trade_date, close, high, low, volume "
                    f"FROM ohlcv_daily "
                    f"WHERE symbol IN ({placeholders}) "
                    f"AND trade_date <= ? "
                    f"ORDER BY symbol, trade_date ASC",
                    chunk + [trade_date],
                ).fetchall()
                raw_rows.extend(rows)
    except Exception as exc:
        log.warning("[V3ShadowRunner] ohlcv_daily query failed: %s", exc)
        return {}

    # Group by symbol, keep only the last _MIN_HISTORY_BARS rows
    grouped: Dict[str, List] = {}
    for row in raw_rows:
        sym = row[0]
        if sym not in grouped:
            grouped[sym] = []
        grouped[sym].append(row)

    for sym, rows in grouped.items():
        if len(rows) < _MIN_HISTORY_BARS:
            continue
        tail = rows[-_MIN_HISTORY_BARS:]
        result[sym] = {
            "closes":  [float(r[2]) for r in tail],
            "highs":   [float(r[3]) for r in tail],
            "lows":    [float(r[4]) for r in tail],
            "volumes": [float(r[5]) for r in tail],
        }

    return result


def _resolve_trade_date() -> str:
    """Get MAX(trade_date) from ohlcv_daily; fall back to today's ISO date."""
    try:
        from oios.db.connection import get_connection
        with get_connection() as conn:
            row = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()
            if row and row[0]:
                return str(row[0])
    except Exception:
        pass
    return date.today().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_phase_d_v3_shadow(trading_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Run V3 shadow scan for Phase D.

    Uses OIOS ohlcv_daily for feature computation; reads CandidateStore
    read-only for overlap metrics. Appends per-symbol + summary records to
    data/logs/mover_discovery_v3_shadow.jsonl.

    Always returns a dict with at minimum:
        {"v3_shadow_duration_ms": float, "success": bool, "no_trades_generated": True}

    GUARANTEED: CandidateStore.write() is never called.
                DecisionEngine is never imported or called.
                RiskControl is never imported or called.
                ExecutionEngine is never imported or called.
    """
    from opportunity_engine.mover_discovery_v3 import (
        V3Config,
        compute_v3_features,
        score_universe,
        select_candidates,
        check_leakage,
    )
    from opportunity_engine.candidate_store import CandidateStore  # read-only

    t_start = time.monotonic()
    td = trading_date or _resolve_trade_date()
    now_utc = datetime.now(timezone.utc).isoformat()

    def _elapsed_ms() -> float:
        return round((time.monotonic() - t_start) * 1000, 1)

    def _abort(reason: str, **extra: Any) -> Dict[str, Any]:
        return {
            "v3_shadow_duration_ms": _elapsed_ms(),
            "success": False,
            "reason": reason,
            "no_trades_generated": True,
            **extra,
        }

    cfg = V3Config(
        enabled=False,
        shadow_mode=True,
        shadow_log_path=str(_SHADOW_LOG_PATH),
        discovery_pool_size=20,
    )
    cfg.validate()

    # ── 1. Universe ───────────────────────────────────────────────────────────
    symbols = _load_universe_symbols()
    if not symbols:
        return _abort("no_symbols")
    log.info("[V3ShadowRunner] Universe: %d symbols  trade_date=%s", len(symbols), td)

    # ── 2. OHLCV from market_behavior.db ─────────────────────────────────────
    ohlcv = _load_ohlcv_from_db(symbols, td)
    log.info("[V3ShadowRunner] OHLCV: %d/%d symbols have >= %d bars.",
             len(ohlcv), len(symbols), _MIN_HISTORY_BARS)
    if not ohlcv:
        return _abort("no_ohlcv_data")

    # ── 3. Compute V3 features ────────────────────────────────────────────────
    features: List[Dict[str, Any]] = []
    for sym, bars in ohlcv.items():
        feat = compute_v3_features(
            sym, bars["closes"], bars["highs"], bars["lows"], bars["volumes"]
        )
        if feat is not None:
            features.append(feat)

    violations = check_leakage(features)
    if violations:
        log.error("[V3ShadowRunner] LEAKAGE detected — aborting shadow scan: %s", violations[:5])
        return _abort("leakage_detected", violations=violations[:5])

    log.info("[V3ShadowRunner] Features: %d symbols pass quality gates.", len(features))
    if len(features) < 10:
        return _abort("insufficient_features", feature_count=len(features))

    # ── 4. Score + select ─────────────────────────────────────────────────────
    scored = score_universe(features, cfg)
    up_cands, down_cands = select_candidates(scored, cfg, pool_size=cfg.discovery_pool_size)

    # ── 5. Existing scanner overlap (read-only) ───────────────────────────────
    existing_candidates = CandidateStore.read() or []
    existing_symbols = {c.get("symbol", "") for c in existing_candidates if c.get("symbol")}
    existing_buckets: Dict[str, List] = {
        c["symbol"]: c.get("buckets", [])
        for c in existing_candidates if c.get("symbol")
    }

    # ── 6. Overlap metrics ────────────────────────────────────────────────────
    v3_up_syms   = {c["symbol"] for c in up_cands}
    v3_down_syms = {c["symbol"] for c in down_cands}
    v3_all       = v3_up_syms | v3_down_syms

    up_overlap_count   = len(v3_up_syms   & existing_symbols)
    down_overlap_count = len(v3_down_syms & existing_symbols)
    total_overlap      = len(v3_all       & existing_symbols)
    v3_only_count      = len(v3_all       - existing_symbols)
    existing_only      = len(existing_symbols - v3_all)

    # ── 7. Build JSONL records ────────────────────────────────────────────────
    per_symbol: List[Dict[str, Any]] = []

    for rank, cand in enumerate(up_cands, start=1):
        sym = cand["symbol"]
        per_symbol.append({
            "timestamp":                now_utc,
            "trading_date":             td,
            "phase":                    "D",
            "record_type":              "SHADOW_CANDIDATE",
            "symbol":                   sym,
            "direction":                "UP",
            "v3_rank":                  rank,
            "v3_score":                 cand.get("v3_up_score"),
            "atr_pct":                  cand.get("atr_pct"),
            "mom_5d":                   cand.get("mom_5d"),
            "rs_pct_5d":                cand.get("rs_pct_5d"),
            "vol_ratio":                cand.get("vol_ratio"),
            "mom_accel":                cand.get("mom_accel"),
            "rsi_14":                   cand.get("rsi_14"),
            "hv_20":                    cand.get("hv_20"),
            "vol_expansion":            cand.get("vol_expansion"),
            "existing_scanner_selected": sym in existing_symbols,
            "existing_bucket":          existing_buckets.get(sym, []),
            "overlap":                  sym in existing_symbols,
            "discovery_pool_size":      cfg.discovery_pool_size,
            "data_timestamp":           td,
            "no_trades_generated":      True,
        })

    for rank, cand in enumerate(down_cands, start=1):
        sym = cand["symbol"]
        per_symbol.append({
            "timestamp":                now_utc,
            "trading_date":             td,
            "phase":                    "D",
            "record_type":              "SHADOW_CANDIDATE",
            "symbol":                   sym,
            "direction":                "DOWN",
            "v3_rank":                  rank,
            "v3_score":                 cand.get("v3_down_score"),
            "atr_pct":                  cand.get("atr_pct"),
            "mom_5d":                   cand.get("mom_5d"),
            "rs_pct_5d":                cand.get("rs_pct_5d"),
            "vol_ratio":                cand.get("vol_ratio"),
            "mom_accel":                cand.get("mom_accel"),
            "neg_mom_5d":               -float(cand.get("mom_5d") or 0.0),
            "neg_mom_accel":            -float(cand.get("mom_accel") or 0.0),
            "rsi_14":                   cand.get("rsi_14"),
            "vol_expansion":            cand.get("vol_expansion"),
            "existing_scanner_selected": sym in existing_symbols,
            "existing_bucket":          existing_buckets.get(sym, []),
            "overlap":                  sym in existing_symbols,
            "discovery_pool_size":      cfg.discovery_pool_size,
            "data_timestamp":           td,
            "no_trades_generated":      True,
        })

    elapsed = _elapsed_ms()
    summary: Dict[str, Any] = {
        "timestamp":                now_utc,
        "trading_date":             td,
        "phase":                    "D",
        "record_type":              "SHADOW_SUMMARY",
        "universe_size":            len(features),
        "v3_up_count":              len(up_cands),
        "v3_down_count":            len(down_cands),
        "existing_scanner_count":   len(existing_symbols),
        "up_overlap_count":         up_overlap_count,
        "down_overlap_count":       down_overlap_count,
        "total_overlap":            total_overlap,
        "v3_only_candidates":       v3_only_count,
        "existing_only_candidates": existing_only,
        "v3_up_symbols":            [c["symbol"] for c in up_cands],
        "v3_down_symbols":          [c["symbol"] for c in down_cands],
        "v3_shadow_duration_ms":    elapsed,
        "no_trades_generated":      True,
        "no_candidatestore_write":  True,
    }

    # ── 8. Append to JSONL ────────────────────────────────────────────────────
    try:
        _SHADOW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SHADOW_LOG_PATH, "a", encoding="utf-8") as fh:
            for rec in per_symbol:
                fh.write(json.dumps(rec, default=str) + "\n")
            fh.write(json.dumps(summary, default=str) + "\n")
    except OSError as exc:
        log.warning("[V3ShadowRunner] JSONL write failed: %s", exc)

    log.info(
        "[V3ShadowRunner] SHADOW COMPLETE trade_date=%s universe=%d "
        "up=%d down=%d overlap=%d v3_only=%d duration_ms=%.1f",
        td, len(features),
        len(up_cands), len(down_cands),
        total_overlap, v3_only_count, elapsed,
    )

    return {
        "v3_shadow_duration_ms":    elapsed,
        "success":                  True,
        "trading_date":             td,
        "universe_size":            len(features),
        "v3_up_count":              len(up_cands),
        "v3_down_count":            len(down_cands),
        "existing_scanner_count":   len(existing_symbols),
        "up_overlap_count":         up_overlap_count,
        "down_overlap_count":       down_overlap_count,
        "total_overlap":            total_overlap,
        "v3_only_candidates":       v3_only_count,
        "existing_only_candidates": existing_only,
        "no_trades_generated":      True,
        "no_candidatestore_write":  True,
    }
