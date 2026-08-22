"""
scripts/final_trading_architecture_shadow_001.py
================================================
FINAL_TRADING_ARCHITECTURE_SHADOW_001

Shadow observer for the frozen C2 selection architecture.

Architecture under observation:
  Universe (230 stocks)
    → V3 discovery → 20 UP + 20 DOWN
    → WAIT FOR T+1 OPEN
    → Opening gap observation
    → C2 selection (rank by gap magnitude, direction-signed) → 5 UP + 5 DOWN
    → Strategy layer read-only evaluation
    → Record hypothetical outcome (Model A and Model B)

Model A: V3 → C2 → 5 candidates (no strategy gate)
Model B: V3 → C2 → 5 candidates → Strategy filter (existing rules, read-only)

SAFETY INVARIANTS (enforced):
  Broker calls           = 0
  Orders placed          = 0
  Positions modified     = 0
  CandidateStore writes  = 0
  ExecutionEngine calls  = 0
  RiskControl calls      = 0
  Output = append-only JSONL + CSV reports only

A failure of this shadow layer must never stop production.
Call run_shadow_day() inside a try/except in any orchestrator integration.

Architecture version: FINAL_TRADING_ARCHITECTURE_SHADOW_001_v1
Research basis: POST_OPEN_SELECTION_001, FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from opportunity_engine.final_c2_selector import (
    compute_disagreement,
    STRATEGY_UNAVAILABLE,
)

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

ARCHITECTURE_VERSION = "FINAL_TRADING_ARCHITECTURE_SHADOW_001_v1"
C2_TOP_N             = 5          # top-N per direction
V3_POOL_SIZE         = 20         # candidates per direction from V3

SHADOW_LOG_PATH = Path("data/logs/final_trading_architecture_shadow_001.jsonl")
REPORT_DIR      = Path("reports/mover_discovery_v3")

# Forbidden imports — this module never imports these
_FORBIDDEN_MODULES = [
    "execution_engine", "order_manager", "dhan_feed", "zerodb_broker",
    "risk_control", "candidate_store",
]

# Strategy rules (from STRATEGY_RECONSTRUCTION_VALIDATION_001)
_REASON_D2   = "D2_BEAR_EQUITY_BUY"       # BEAR + UP direction
_REASON_D3   = "D3_VOLATILE_EQUITY_BUY"   # VOLATILE + UP direction
_REASON_PASS = "PASS_ALL_RULES"
_REASON_UNAVAILABLE = "STRATEGY_UNAVAILABLE"
_REASON_DN_ALIGNED      = "DOWN_BEAR_ALIGNED"
_REASON_DN_CONTRADICTED = "DOWN_BULL_CONTRADICTED"
_REASON_DN_NEUTRAL      = "DOWN_RANGE_NEUTRAL"

_MIN_HISTORY_BARS = 35   # must match V3 shadow runner


# ─────────────────────────────────────────────────────────────────────────────
# C2 formula (frozen — FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001)
# ─────────────────────────────────────────────────────────────────────────────

def compute_c2_score(previous_close: float, opening_price: float,
                     direction: str) -> Optional[float]:
    """
    C2 = direction-signed gap magnitude.

    UP:   c2_score = +gap_pct   (reward largest positive gap)
    DOWN: c2_score = -gap_pct   (reward largest negative gap)

    Information horizon: T+1 open only.
    Forbidden inputs: T+1 close, high, low, return, or any future data.
    """
    if previous_close <= 0 or opening_price <= 0:
        return None
    gap_pct = (opening_price / previous_close - 1.0) * 100.0
    if direction == "UP":
        return round(gap_pct, 6)
    else:  # DOWN
        return round(-gap_pct, 6)


def select_c2_top_n(
    pool: List[Dict[str, Any]],
    n: int = C2_TOP_N,
) -> List[Dict[str, Any]]:
    """
    Rank pool by c2_score descending; select top-N.
    Adds c2_rank (1-based) and selected_final_5 flag.
    """
    valid  = [c for c in pool if c.get("c2_score") is not None]
    rest   = [c for c in pool if c.get("c2_score") is None]

    sorted_valid = sorted(valid, key=lambda x: x["c2_score"], reverse=True)
    result = []
    for rank, cand in enumerate(sorted_valid, start=1):
        rec = dict(cand)
        rec["c2_rank"]         = rank
        rec["selected_final_5"] = rank <= n
        result.append(rec)
    for cand in rest:
        rec = dict(cand)
        rec["c2_rank"]         = None
        rec["selected_final_5"] = False
        result.append(rec)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Strategy layer (read-only — rules from STRATEGY_RECONSTRUCTION_VALIDATION_001)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_strategy(direction: str, regime: Optional[str]) -> Tuple[str, str, str]:
    """
    Apply the existing production strategy rules (read-only).

    Returns (strategy_status, strategy_name, strategy_reason).

    For UP:
      BEAR   → REJECT  (D2: no BUY strategies in BEAR)
      VOLATILE → REJECT (D3: no BUY strategies in VOLATILE)
      else   → PASS    (BULL/RANGE: Trend_Pullback / Mean_Reversion allowed)

    For DOWN:
      No SELL strategies exist. Returns regime-relative label:
      BEAR   → ALIGNED (bearish macro supports DOWN move)
      BULL   → CONTRADICTED
      RANGE  → NEUTRAL
      else   → NEUTRAL

    If regime is None or UNAVAILABLE: return STRATEGY_UNAVAILABLE.
    """
    if not regime or regime in ("UNAVAILABLE", "UNKNOWN"):
        return "STRATEGY_UNAVAILABLE", "NONE", _REASON_UNAVAILABLE

    if direction == "UP":
        if regime == "BEAR":
            return "REJECT", "ALL_BUY_STRATEGIES", _REASON_D2
        if regime == "VOLATILE":
            return "REJECT", "ALL_BUY_STRATEGIES", _REASON_D3
        return "PASS", "Trend_Pullback_or_Mean_Reversion", _REASON_PASS

    else:  # DOWN
        if regime == "BEAR":
            return "ALIGNED", "NONE", _REASON_DN_ALIGNED
        if regime == "BULL":
            return "CONTRADICTED", "NONE", _REASON_DN_CONTRADICTED
        return "NEUTRAL", "NONE", _REASON_DN_NEUTRAL


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _open_db(db_path: Optional[Path]) -> sqlite3.Connection:
    """Open SQLite connection. Falls back to replay DB if path not given."""
    if db_path is None:
        candidates = [
            Path("data/oios.db"),
            Path("data/market_behavior.db"),
            Path("data/study002_replay.db"),
        ]
        for p in candidates:
            if p.exists():
                db_path = p
                break
    if db_path is None or not db_path.exists():
        raise FileNotFoundError("No SQLite database found.")
    return sqlite3.connect(str(db_path), check_same_thread=False)


def _resolve_trade_date(conn: sqlite3.Connection,
                        requested: Optional[str] = None) -> str:
    """Return the most recent trade_date with OHLCV data."""
    if requested:
        return requested
    row = conn.execute(
        "SELECT MAX(trade_date) FROM ohlcv_daily WHERE symbol != '^NSEI'"
    ).fetchone()
    if row and row[0]:
        return str(row[0])
    return date.today().isoformat()


def _load_universe(conn: sqlite3.Connection) -> List[str]:
    """Load active universe symbols."""
    try:
        rows = conn.execute(
            "SELECT symbol FROM universe_stocks WHERE is_active=1"
        ).fetchall()
        if rows:
            return [r[0] for r in rows]
    except Exception:
        pass
    # Fallback: all symbols in ohlcv_daily (excluding indices)
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM ohlcv_daily WHERE symbol NOT LIKE '^%'"
    ).fetchall()
    return [r[0] for r in rows]


def _load_ohlcv(conn: sqlite3.Connection, symbols: List[str],
                up_to_date: str) -> Dict[str, Dict[str, List]]:
    """
    Load last _MIN_HISTORY_BARS of OHLCV per symbol up to (including) up_to_date.
    Returns {symbol: {closes, highs, lows, volumes, dates}}.
    """
    result: Dict[str, Dict[str, List]] = {}
    if not symbols:
        return result

    chunk = 900
    rows: List[Any] = []
    for i in range(0, len(symbols), chunk):
        batch = symbols[i: i + chunk]
        ph = ",".join("?" * len(batch))
        r = conn.execute(
            f"SELECT symbol, trade_date, open, high, low, close, volume "
            f"FROM ohlcv_daily "
            f"WHERE symbol IN ({ph}) AND trade_date <= ? "
            f"ORDER BY symbol, trade_date ASC",
            batch + [up_to_date],
        ).fetchall()
        rows.extend(r)

    grouped: Dict[str, List] = {}
    for row in rows:
        sym = row[0]
        grouped.setdefault(sym, []).append(row)

    for sym, sym_rows in grouped.items():
        if len(sym_rows) < _MIN_HISTORY_BARS:
            continue
        tail = sym_rows[-_MIN_HISTORY_BARS:]
        # query: symbol(0) trade_date(1) open(2) high(3) low(4) close(5) volume(6)
        result[sym] = {
            "dates":   [r[1] for r in tail],
            "opens":   [float(r[2]) for r in tail],
            "highs":   [float(r[3]) for r in tail],
            "lows":    [float(r[4]) for r in tail],
            "closes":  [float(r[5]) for r in tail],
            "volumes": [float(r[6]) for r in tail],
        }
    return result


def _get_opening_prices(conn: sqlite3.Connection, symbols: List[str],
                        t1_date: str) -> Dict[str, float]:
    """Return {symbol: open_price} for the given date."""
    if not symbols:
        return {}
    chunk = 900
    result: Dict[str, float] = {}
    for i in range(0, len(symbols), chunk):
        batch = symbols[i: i + chunk]
        ph = ",".join("?" * len(batch))
        rows = conn.execute(
            f"SELECT symbol, open FROM ohlcv_daily "
            f"WHERE symbol IN ({ph}) AND trade_date = ?",
            batch + [t1_date],
        ).fetchall()
        result.update({r[0]: float(r[1]) for r in rows if r[1] is not None})
    return result


def _get_ohlcv_for_outcomes(conn: sqlite3.Connection, symbols: List[str],
                             from_date: str, horizon: int = 6) -> Dict[str, List]:
    """
    Return sorted list of (trade_date, close, high, low) for each symbol
    starting from from_date, for outcome computation.
    """
    if not symbols:
        return {}
    chunk = 900
    rows: List[Any] = []
    for i in range(0, len(symbols), chunk):
        batch = symbols[i: i + chunk]
        ph = ",".join("?" * len(batch))
        r = conn.execute(
            f"SELECT symbol, trade_date, open, high, low, close "
            f"FROM ohlcv_daily "
            f"WHERE symbol IN ({ph}) AND trade_date >= ? "
            f"ORDER BY symbol, trade_date ASC",
            batch + [from_date],
        ).fetchall()
        rows.extend(r)

    grouped: Dict[str, List] = {}
    for row in rows:
        sym = row[0]
        grouped.setdefault(sym, []).append(row)
    return grouped


def _get_regime(conn: sqlite3.Connection, trade_date: str) -> str:
    """
    Approximate market regime from NIFTY T+1 return and VIX.

    Regime is for T+1 (the day after V3 discovery).
    Uses T → T+1 NIFTY close-to-close return as proxy since VIX not in DB.

    Thresholds (aligned with MarketRegimeAI):
      NIFTY return >= +0.5% → BULL
      NIFTY return <= -0.5% → BEAR
      else                  → RANGE
    Note: VOLATILE requires VIX > 20 — not available → defaults to BEAR/RANGE.
    """
    try:
        nifty_sym = "^NSEI"
        # Get T close and T-1 close from ohlcv_daily
        rows = conn.execute(
            "SELECT trade_date, close FROM ohlcv_daily "
            "WHERE symbol = ? AND trade_date <= ? "
            "ORDER BY trade_date DESC LIMIT 2",
            (nifty_sym, trade_date),
        ).fetchall()
        if len(rows) >= 2:
            t_close  = float(rows[0][1])
            tm1_close = float(rows[1][1])
            if tm1_close > 0:
                nifty_ret = (t_close / tm1_close - 1.0) * 100.0
                if nifty_ret >= 0.5:
                    return "BULL"
                if nifty_ret <= -0.5:
                    return "BEAR"
                return "RANGE"
    except Exception:
        pass
    return "UNAVAILABLE"


def _get_t1_date(conn: sqlite3.Connection, trade_date: str) -> Optional[str]:
    """Return the next trading date after trade_date."""
    row = conn.execute(
        "SELECT MIN(trade_date) FROM ohlcv_daily "
        "WHERE trade_date > ? AND symbol = '^NSEI'",
        (trade_date,),
    ).fetchone()
    if row and row[0]:
        return str(row[0])
    # Fallback: next calendar day
    import datetime as _dt
    d = _dt.date.fromisoformat(trade_date) + _dt.timedelta(days=1)
    return d.isoformat()


def _get_future_dates(conn: sqlite3.Connection, from_date: str,
                      n: int) -> List[str]:
    """Return the next N trading dates from from_date (inclusive)."""
    rows = conn.execute(
        "SELECT DISTINCT trade_date FROM ohlcv_daily "
        "WHERE trade_date >= ? AND symbol = '^NSEI' "
        "ORDER BY trade_date ASC LIMIT ?",
        (from_date, n),
    ).fetchall()
    return [r[0] for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Outcome computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_outcome(
    entry_price: float,
    direction: str,
    sym_rows: List[Any],  # sorted by date ascending, starting from T+1
    horizon: int = 5,
) -> Dict[str, Any]:
    """
    Compute T+1, T+3, T+5 outcomes + MFE + MAE for a hypothetical trade.

    Entry: opening price of T+1.
    Forbidden: using T+1 close/high/low for SELECTION (selection already frozen).
    Outcome fields are evaluation-only.

    For UP:  positive return = favourable; for DOWN: negative return = favourable.
    """
    out: Dict[str, Any] = {
        "t1_ret_pct":        None,
        "t3_ret_pct":        None,
        "t5_ret_pct":        None,
        "mfe_pct":           None,
        "mae_pct":           None,
        "direction_correct": None,
        "ge1":               None,
        "ge2":               None,
        "ge3":               None,
    }

    if entry_price <= 0 or not sym_rows:
        return out

    def _favourable(ret: float) -> bool:
        return ret > 0 if direction == "UP" else ret < 0

    # rows: (symbol, trade_date, open, high, low, close, ...)
    closes = [(r[1], float(r[5])) for r in sym_rows[:horizon]]  # (date, close)
    highs  = [(r[1], float(r[3])) for r in sym_rows[:horizon]]  # high
    lows   = [(r[1], float(r[4])) for r in sym_rows[:horizon]]  # low

    def ret_at(n: int) -> Optional[float]:
        if n - 1 < len(closes):
            c = closes[n - 1][1]
            return round((c / entry_price - 1.0) * 100.0, 4)
        return None

    out["t1_ret_pct"] = ret_at(1)
    out["t3_ret_pct"] = ret_at(3)
    out["t5_ret_pct"] = ret_at(5)

    if out["t1_ret_pct"] is not None:
        out["direction_correct"] = _favourable(out["t1_ret_pct"])
        out["ge1"] = abs(out["t1_ret_pct"]) >= 1.0 and _favourable(out["t1_ret_pct"])
        out["ge2"] = abs(out["t1_ret_pct"]) >= 2.0 and _favourable(out["t1_ret_pct"])
        out["ge3"] = abs(out["t1_ret_pct"]) >= 3.0 and _favourable(out["t1_ret_pct"])

    # MFE and MAE over T+1..T+5 horizon
    if highs and lows:
        if direction == "UP":
            max_fav  = max((h / entry_price - 1.0) * 100.0 for _, h in highs)
            max_adv  = min((l / entry_price - 1.0) * 100.0 for _, l in lows)
        else:
            max_fav  = max((entry_price / l - 1.0) * 100.0 for _, l in lows if l > 0)
            max_adv  = min((entry_price / h - 1.0) * 100.0 for _, h in highs if h > 0)
        out["mfe_pct"] = round(max_fav, 4)
        out["mae_pct"] = round(max_adv, 4)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency
# ─────────────────────────────────────────────────────────────────────────────

def _make_run_id(trade_date: str) -> str:
    return hashlib.sha256(
        f"{ARCHITECTURE_VERSION}:{trade_date}".encode()
    ).hexdigest()[:16]


def _already_processed(trade_date: str,
                        jsonl_path: Path) -> bool:
    """True if any record with this trade_date already in the JSONL."""
    if not jsonl_path.exists():
        return False
    target_id = _make_run_id(trade_date)
    try:
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("run_id") == target_id:
                        return True
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# V3 discovery (uses mover_discovery_v3.py functions)
# ─────────────────────────────────────────────────────────────────────────────

def _run_v3_pool(conn: sqlite3.Connection,
                 trade_date: str,
                 pool_size: int = V3_POOL_SIZE,
                 ) -> Tuple[List[Dict], List[Dict]]:
    """
    Run V3 discovery for a given trade_date.
    Returns (up_pool, down_pool) each a list of dicts with V3 fields.
    """
    from opportunity_engine.mover_discovery_v3 import (
        V3Config, compute_v3_features, score_universe, select_candidates,
    )
    cfg = V3Config(enabled=False, shadow_mode=True, discovery_pool_size=pool_size)

    symbols = _load_universe(conn)
    if not symbols:
        log.warning("[Shadow] No universe symbols found.")
        return [], []

    ohlcv = _load_ohlcv(conn, symbols, trade_date)
    if not ohlcv:
        log.warning("[Shadow] No OHLCV for trade_date=%s", trade_date)
        return [], []

    features = []
    for sym, bars in ohlcv.items():
        feat = compute_v3_features(
            sym, bars["closes"], bars["highs"], bars["lows"], bars["volumes"]
        )
        if feat is not None:
            features.append(feat)

    if len(features) < 10:
        log.warning("[Shadow] Insufficient features: %d", len(features))
        return [], []

    scored    = score_universe(features, cfg)
    up_cands, down_cands = select_candidates(scored, cfg, pool_size=pool_size)

    # Attach previous_close (last close in OHLCV) for each candidate
    prev_closes = {sym: bars["closes"][-1] for sym, bars in ohlcv.items()}
    for cand in up_cands + down_cands:
        cand["previous_close"] = prev_closes.get(cand["symbol"])

    return up_cands, down_cands


# ─────────────────────────────────────────────────────────────────────────────
# Report / CSV helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_all_candidates(jsonl_path: Path) -> List[Dict[str, Any]]:
    """Load all candidate records (record_type=SHADOW_CANDIDATE) from JSONL."""
    if not jsonl_path.exists():
        return []
    records = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("record_type") == "SHADOW_CANDIDATE":
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    return records


def _load_all_summaries(jsonl_path: Path) -> List[Dict[str, Any]]:
    """Load all summary records from JSONL."""
    if not jsonl_path.exists():
        return []
    records = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("record_type") == "SHADOW_DAILY_SUMMARY":
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    return records


def rebuild_csv_reports(jsonl_path: Path = SHADOW_LOG_PATH) -> None:
    """Rebuild CSV files from the master JSONL. Call after any run."""
    import csv

    candidates = _load_all_candidates(jsonl_path)
    summaries  = _load_all_summaries(jsonl_path)

    if candidates:
        cand_path = REPORT_DIR / "final_trading_architecture_shadow_candidates.csv"
        fields = [
            "run_id", "trade_date", "t1_date", "selection_timestamp",
            "architecture_version",
            # Discovery
            "symbol", "direction", "universe_membership",
            "v3_score", "v3_rank", "v3_model_version",
            # Pool
            "pool_size", "pool_rank", "pool_direction",
            # Opening
            "previous_close", "opening_price", "gap_pct", "gap_rank",
            # C2
            "c2_score", "c2_rank", "selected_final_5",
            # Strategy (as context, not gate)
            "strategy_status", "strategy_name", "strategy_reason",
            "strategy_regime", "strategy_rejected",
            "knowledge_strategy_disagreement",
            # Model B flag
            "model_b_included",
            # Execution
            "hypothetical_entry",
            # Outcomes
            "t1_ret_pct", "t3_ret_pct", "t5_ret_pct",
            "mfe_pct", "mae_pct",
            "direction_correct", "ge1", "ge2", "ge3",
        ]
        with open(cand_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(candidates)
        log.info("[Shadow] Wrote %d candidate rows to %s", len(candidates), cand_path.name)

    if summaries:
        daily_path = REPORT_DIR / "final_trading_architecture_shadow_daily.csv"
        fields = [
            "run_id", "trade_date", "architecture_version",
            "universe_size", "v3_up_count", "v3_down_count",
            "c2_up_selected", "c2_down_selected",
            "regime",
            "strategy_pass_up", "strategy_reject_up",
            "strategy_unavailable_up",
            "model_b_up_count", "model_b_down_count",
            "t1_dir_acc_model_a_up", "t1_dir_acc_model_a_down",
            "t1_dir_acc_model_b_up", "t1_dir_acc_model_b_down",
            "t1_ge2_model_a_up", "t1_ge2_model_a_down",
            "t1_ge2_model_b_up", "t1_ge2_model_b_down",
        ]
        with open(daily_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(summaries)
        log.info("[Shadow] Wrote %d daily rows to %s", len(summaries), daily_path.name)

    # Strategy impact summary
    if candidates:
        _write_strategy_impact(candidates)


def _write_strategy_impact(candidates: List[Dict[str, Any]]) -> None:
    """Compute and write strategy impact CSV."""
    import csv
    from collections import defaultdict

    # Aggregate across all dates
    up_cands  = [c for c in candidates if c.get("direction") == "UP" and c.get("selected_final_5")]
    dn_cands  = [c for c in candidates if c.get("direction") == "DOWN" and c.get("selected_final_5")]

    def safe_mean(vals: list) -> Optional[float]:
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    def safe_rate(bools: list) -> Optional[float]:
        vals = [v for v in bools if v is not None]
        return round(sum(1 for v in vals if v) / len(vals), 4) if vals else None

    rows = []
    for direction, cands in [("UP", up_cands), ("DOWN", dn_cands)]:
        if not cands:
            rows.append({"direction": direction, "n_total": 0})
            continue

        n_total    = len(cands)
        n_pass     = sum(1 for c in cands if c.get("strategy_status") == "PASS")
        n_reject   = sum(1 for c in cands if c.get("strategy_status") == "REJECT")
        n_unavail  = sum(1 for c in cands if c.get("strategy_status") == "STRATEGY_UNAVAILABLE")
        n_aligned  = sum(1 for c in cands if c.get("strategy_status") == "ALIGNED")

        model_a    = cands
        model_b_up = [c for c in cands if direction == "UP" and c.get("strategy_status") == "PASS"]
        model_b_dn = [c for c in cands if direction == "DOWN"]  # no gate for DOWN

        def metrics(pool):
            if not pool:
                return {}
            return {
                "dir_acc":  safe_rate([c.get("direction_correct") for c in pool]),
                "ge1_rate": safe_rate([c.get("ge1") for c in pool]),
                "ge2_rate": safe_rate([c.get("ge2") for c in pool]),
                "ge3_rate": safe_rate([c.get("ge3") for c in pool]),
                "avg_mfe":  safe_mean([c.get("mfe_pct") for c in pool]),
                "avg_mae":  safe_mean([c.get("mae_pct") for c in pool]),
                "n":        len(pool),
            }

        ma = metrics(model_a)
        mb = metrics(model_b_up if direction == "UP" else model_b_dn)

        rows.append({
            "direction":            direction,
            "n_total":              n_total,
            "n_strategy_pass":      n_pass if direction == "UP" else "N/A",
            "n_strategy_reject":    n_reject if direction == "UP" else "N/A",
            "n_strategy_unavail":   n_unavail,
            "n_strategy_aligned":   n_aligned if direction == "DOWN" else "N/A",
            "model_a_n":            ma.get("n"),
            "model_a_dir_acc":      ma.get("dir_acc"),
            "model_a_ge2":          ma.get("ge2_rate"),
            "model_a_avg_mfe":      ma.get("avg_mfe"),
            "model_b_n":            mb.get("n"),
            "model_b_dir_acc":      mb.get("dir_acc"),
            "model_b_ge2":          mb.get("ge2_rate"),
            "model_b_avg_mfe":      mb.get("avg_mfe"),
            "strategy_question_status": "INSUFFICIENT" if n_total < 20 else "ACCUMULATING",
        })

    out_path = REPORT_DIR / "final_trading_architecture_shadow_strategy_impact.csv"
    if rows:
        import csv
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        log.info("[Shadow] Wrote strategy impact to %s", out_path.name)


# ─────────────────────────────────────────────────────────────────────────────
# Main daily pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_shadow_day(
    trade_date: Optional[str] = None,
    db_path: Optional[Path] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Run the full shadow pipeline for a single trading date.

    Steps:
      1. V3 discovery → 20 UP + 20 DOWN
      2. Get T+1 opening prices
      3. Compute C2 score (direction-signed gap magnitude)
      4. Select top-5 per direction
      5. Evaluate strategy layer (read-only)
      6. Compute available outcomes (T+1, T+3, T+5)
      7. Append to JSONL log
      8. Rebuild CSV reports

    Guaranteed:
      - CandidateStore writes = 0
      - OrderManager never imported
      - No broker API calls
      - Idempotent: skip if trade_date already processed (unless force=True)

    Returns dict with pipeline status.
    """
    t_start = time.monotonic()
    now_utc = datetime.now(timezone.utc).isoformat()

    def elapsed_ms() -> float:
        return round((time.monotonic() - t_start) * 1000, 1)

    def abort(reason: str, **kw) -> Dict[str, Any]:
        return {
            "success": False,
            "reason": reason,
            "duration_ms": elapsed_ms(),
            "no_trades_generated": True,
            "no_broker_calls": True,
            **kw,
        }

    SHADOW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Open DB ───────────────────────────────────────────────────────────────
    try:
        conn = _open_db(db_path)
    except FileNotFoundError as e:
        return abort("db_not_found", error=str(e))

    try:
        td = _resolve_trade_date(conn, trade_date)

        # ── Idempotency check ─────────────────────────────────────────────────
        if not force and _already_processed(td, SHADOW_LOG_PATH):
            log.info("[Shadow] trade_date=%s already processed — skipping.", td)
            return {
                "success": True,
                "skipped": True,
                "trade_date": td,
                "duration_ms": elapsed_ms(),
                "no_trades_generated": True,
                "no_broker_calls": True,
            }

        run_id = _make_run_id(td)

        # ── Step 1: V3 discovery ──────────────────────────────────────────────
        up_pool, dn_pool = _run_v3_pool(conn, td)
        log.info("[Shadow] V3: %d UP + %d DOWN for %s", len(up_pool), len(dn_pool), td)

        all_syms = [c["symbol"] for c in up_pool + dn_pool]
        if not all_syms:
            return abort("v3_no_candidates", trade_date=td)

        # ── Step 2: T+1 date and opening prices ───────────────────────────────
        t1_date = _get_t1_date(conn, td)
        opening_prices = _get_opening_prices(conn, all_syms, t1_date) if t1_date else {}
        t1_available   = len(opening_prices) > 0

        # ── Step 3: Market regime (for strategy evaluation) ───────────────────
        regime = _get_regime(conn, t1_date) if t1_date else "UNAVAILABLE"

        # ── Step 4: Outcome data ──────────────────────────────────────────────
        outcome_data: Dict[str, List] = {}
        if t1_date:
            outcome_data = _get_ohlcv_for_outcomes(conn, all_syms, t1_date, horizon=7)

        # ── Step 5: C2 scoring ────────────────────────────────────────────────
        def _process_pool(pool: List[Dict], direction: str) -> List[Dict]:
            enriched = []
            for pool_rank, cand in enumerate(pool, start=1):
                sym = cand["symbol"]
                prev_close = cand.get("previous_close")
                opening    = opening_prices.get(sym)

                c2_score = None
                if prev_close and opening:
                    c2_score = compute_c2_score(prev_close, opening, direction)

                gap_pct = None
                if prev_close and opening and prev_close > 0:
                    gap_pct = round((opening / prev_close - 1.0) * 100.0, 6)

                strat_status, strat_name, strat_reason = evaluate_strategy(direction, regime)

                rec = {
                    # Meta
                    "run_id":               run_id,
                    "trade_date":           td,
                    "t1_date":              t1_date,
                    "selection_timestamp":  now_utc,
                    "architecture_version": ARCHITECTURE_VERSION,
                    "record_type":          "SHADOW_CANDIDATE",
                    "no_trades_generated":  True,
                    "no_broker_calls":      True,
                    # Discovery
                    "symbol":               sym,
                    "direction":            direction,
                    "universe_membership":  True,
                    "v3_score":             round(float(cand.get(
                        "v3_up_score" if direction == "UP" else "v3_down_score", 0) or 0), 6),
                    "v3_rank":              pool_rank,
                    "v3_model_version":     "V3_FINAL",
                    # Pool
                    "pool_size":            len(pool),
                    "pool_rank":            pool_rank,
                    "pool_direction":       direction,
                    # Opening
                    "previous_close":       prev_close,
                    "opening_price":        opening,
                    "gap_pct":              gap_pct,
                    "gap_rank":             None,     # filled after sort
                    # C2 (filled after sort)
                    "c2_score":             c2_score,
                    "c2_rank":              None,
                    "selected_final_5":     False,
                    # Strategy
                    "strategy_status":      strat_status,
                    "strategy_name":        strat_name,
                    "strategy_reason":      strat_reason,
                    "strategy_regime":      regime,
                    "strategy_rejected":    strat_status == "REJECT",
                    # placeholder — overridden by _assign_ranks after C2 ranking
                    "knowledge_strategy_disagreement": STRATEGY_UNAVAILABLE,
                    # Model B
                    "model_b_included":     (
                        strat_status not in ("REJECT",) if direction == "UP"
                        else True  # no gate for DOWN
                    ),
                    # Hypothetical execution
                    "hypothetical_entry":   opening if opening else "NOT_AVAILABLE",
                    "hypothetical_stop":    "NOT_AVAILABLE",
                    "hypothetical_target":  "NOT_AVAILABLE",
                    # Outcomes (filled below)
                    "t1_ret_pct":    None,
                    "t3_ret_pct":    None,
                    "t5_ret_pct":    None,
                    "mfe_pct":       None,
                    "mae_pct":       None,
                    "direction_correct": None,
                    "ge1":           None,
                    "ge2":           None,
                    "ge3":           None,
                }
                enriched.append(rec)
            return enriched

        up_recs = _process_pool(up_pool, "UP")
        dn_recs = _process_pool(dn_pool, "DOWN")

        # ── Step 6: Assign C2 ranks ───────────────────────────────────────────
        def _assign_ranks(recs: List[Dict]) -> List[Dict]:
            ranked = select_c2_top_n(recs, n=C2_TOP_N)
            # Also assign gap_rank = rank by |gap_pct|
            valid_gap = [(i, r["gap_pct"]) for i, r in enumerate(ranked)
                         if r["gap_pct"] is not None]
            sorted_gap = sorted(valid_gap, key=lambda x: abs(x[1]), reverse=True)
            gap_ranks = {i: k + 1 for k, (i, _) in enumerate(sorted_gap)}
            for i, r in enumerate(ranked):
                r["gap_rank"] = gap_ranks.get(i)
                # Re-compute disagreement now that selected_final_5 is known
                r["knowledge_strategy_disagreement"] = compute_disagreement(
                    r.get("strategy_status", "STRATEGY_UNAVAILABLE"),
                    r["direction"],
                    selected_top5=bool(r.get("selected_final_5")),
                )
            return ranked

        up_recs = _assign_ranks(up_recs)
        dn_recs = _assign_ranks(dn_recs)

        # ── Step 7: Compute outcomes ──────────────────────────────────────────
        for rec in up_recs + dn_recs:
            sym     = rec["symbol"]
            entry   = rec.get("opening_price")
            sym_rows = outcome_data.get(sym, [])
            if entry and sym_rows:
                oc = _compute_outcome(float(entry), rec["direction"], sym_rows)
                rec.update(oc)

        # ── Step 8: Daily summary ─────────────────────────────────────────────
        all_recs = up_recs + dn_recs
        up_sel   = [r for r in up_recs if r.get("selected_final_5")]
        dn_sel   = [r for r in dn_recs if r.get("selected_final_5")]

        def dir_acc(pool: List[Dict]) -> Optional[float]:
            vals = [r.get("direction_correct") for r in pool if r.get("direction_correct") is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        def ge2_rate(pool: List[Dict]) -> Optional[float]:
            vals = [r.get("ge2") for r in pool if r.get("ge2") is not None]
            return round(sum(1 for v in vals if v) / len(vals), 4) if vals else None

        up_strat_pass    = sum(1 for r in up_recs if r.get("strategy_status") == "PASS")
        up_strat_reject  = sum(1 for r in up_recs if r.get("strategy_status") == "REJECT")
        up_strat_unavail = sum(1 for r in up_recs if r.get("strategy_status") == "STRATEGY_UNAVAILABLE")
        up_knowledge_overrides = sum(
            1 for r in up_sel
            if r.get("knowledge_strategy_disagreement") == "KNOWLEDGE_OVERRULES_STRATEGY"
        )
        mb_up_sel = [r for r in up_sel if r.get("model_b_included")]
        mb_dn_sel = dn_sel  # no DOWN gate

        summary = {
            "run_id":               run_id,
            "trade_date":           td,
            "t1_date":              t1_date,
            "architecture_version": ARCHITECTURE_VERSION,
            "record_type":          "SHADOW_DAILY_SUMMARY",
            "timestamp":            now_utc,
            "no_trades_generated":  True,
            "no_broker_calls":      True,
            "universe_size":        len(up_pool) + len(dn_pool),   # approx
            "v3_up_count":          len(up_pool),
            "v3_down_count":        len(dn_pool),
            "c2_up_selected":       len(up_sel),
            "c2_down_selected":     len(dn_sel),
            "regime":               regime,
            "t1_data_available":    t1_available,
            "strategy_pass_up":     up_strat_pass,
            "strategy_reject_up":   up_strat_reject,
            "strategy_unavailable_up": up_strat_unavail,
            "knowledge_overrides_up": up_knowledge_overrides,
            "model_b_up_count":     len(mb_up_sel),
            "model_b_down_count":   len(mb_dn_sel),
            "t1_dir_acc_model_a_up":    dir_acc(up_sel),
            "t1_dir_acc_model_a_down":  dir_acc(dn_sel),
            "t1_dir_acc_model_b_up":    dir_acc(mb_up_sel),
            "t1_dir_acc_model_b_down":  dir_acc(mb_dn_sel),
            "t1_ge2_model_a_up":        ge2_rate(up_sel),
            "t1_ge2_model_a_down":      ge2_rate(dn_sel),
            "t1_ge2_model_b_up":        ge2_rate(mb_up_sel),
            "t1_ge2_model_b_down":      ge2_rate(mb_dn_sel),
        }

        # ── Step 9: Write to JSONL ────────────────────────────────────────────
        try:
            with open(SHADOW_LOG_PATH, "a", encoding="utf-8") as fh:
                for rec in all_recs:
                    fh.write(json.dumps(rec, default=str) + "\n")
                fh.write(json.dumps(summary, default=str) + "\n")
        except OSError as exc:
            log.error("[Shadow] JSONL write failed: %s", exc)
            return abort("jsonl_write_failed", trade_date=td, error=str(exc))

        # ── Step 10: Rebuild CSV reports ──────────────────────────────────────
        try:
            rebuild_csv_reports(SHADOW_LOG_PATH)
        except Exception as exc:
            log.warning("[Shadow] CSV rebuild failed (non-critical): %s", exc)

        duration = elapsed_ms()
        log.info(
            "[Shadow] COMPLETE trade_date=%s t1=%s regime=%s "
            "up_pool=%d dn_pool=%d up_sel=%d dn_sel=%d "
            "strategy_pass=%d reject=%d dur=%.1fms",
            td, t1_date, regime,
            len(up_pool), len(dn_pool), len(up_sel), len(dn_sel),
            up_strat_pass, up_strat_reject, duration,
        )

        return {
            "success":              True,
            "trade_date":           td,
            "t1_date":              t1_date,
            "run_id":               run_id,
            "v3_up_count":          len(up_pool),
            "v3_down_count":        len(dn_pool),
            "c2_up_selected":       len(up_sel),
            "c2_down_selected":     len(dn_sel),
            "regime":               regime,
            "strategy_pass_up":     up_strat_pass,
            "strategy_reject_up":   up_strat_reject,
            "strategy_unavailable_up": up_strat_unavail,
            "knowledge_overrides_up": up_knowledge_overrides,
            "t1_data_available":    t1_available,
            "duration_ms":          duration,
            "no_trades_generated":  True,
            "no_broker_calls":      True,
        }

    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Report generator
# ─────────────────────────────────────────────────────────────────────────────

def write_shadow_report(jsonl_path: Path = SHADOW_LOG_PATH) -> Path:
    """
    Write the short decision-oriented report answering Q1-Q8.
    Returns the path of the written file.
    """
    summaries  = _load_all_summaries(jsonl_path)
    candidates = _load_all_candidates(jsonl_path)

    n_days         = len(summaries)
    regimes_seen   = {s.get("regime") for s in summaries if s.get("regime") not in (None, "UNAVAILABLE")}
    total_up_cands = sum(s.get("c2_up_selected", 0) for s in summaries)
    total_dn_cands = sum(s.get("c2_down_selected", 0) for s in summaries)

    up_sel = [c for c in candidates if c.get("direction") == "UP" and c.get("selected_final_5")]
    dn_sel = [c for c in candidates if c.get("direction") == "DOWN" and c.get("selected_final_5")]

    def rate(bools: list) -> str:
        vals = [v for v in bools if v is not None]
        if not vals:
            return "N/A"
        return f"{sum(1 for v in vals if v)/len(vals):.1%} ({len(vals)} obs)"

    total_reject_up = sum(s.get("strategy_reject_up", 0) for s in summaries)
    total_pass_up   = sum(s.get("strategy_pass_up", 0) for s in summaries)

    # Strategy Q1: has Strategy ever rejected?
    strategy_active = total_reject_up > 0

    needed_regimes = {"BEAR", "BULL", "RANGE", "VOLATILE"}
    missing = needed_regimes - regimes_seen

    # Q8: sufficient evidence?
    sufficient = (
        n_days >= 50 and
        "BEAR" in regimes_seen and
        total_reject_up >= 10
    )

    md = f"""# FINAL_TRADING_ARCHITECTURE_SHADOW_001

**Date:** {date.today().isoformat()}  
**Architecture:** {ARCHITECTURE_VERSION}  
**Shadow days recorded:** {n_days}  
**Total C2-selected UP:** {total_up_cands}  
**Total C2-selected DOWN:** {total_dn_cands}  

---

## Q1 — Did V3 produce the intended 20+20 pool?

{"YES" if summaries else "NO DATA YET"} — {n_days} shadow days recorded.  
{"Average UP pool: " + str(round(sum(s.get("v3_up_count",0) for s in summaries)/max(n_days,1),1)) if summaries else ""}  
{"Average DOWN pool: " + str(round(sum(s.get("v3_down_count",0) for s in summaries)/max(n_days,1),1)) if summaries else ""}  

## Q2 — Did C2 reduce it to 5+5?

{"YES" if summaries else "NO DATA YET"} — C2 produces top-{C2_TOP_N} per direction.  
Total UP selected: {total_up_cands} | Total DOWN selected: {total_dn_cands}

## Q3 — What happened to those 10 candidates?

| Metric | UP | DOWN |
|--------|----|----|
| direction_correct | {rate([c.get("direction_correct") for c in up_sel])} | {rate([c.get("direction_correct") for c in dn_sel])} |
| ge2 (≥2%) | {rate([c.get("ge2") for c in up_sel])} | {rate([c.get("ge2") for c in dn_sel])} |
| ge3 (≥3%) | {rate([c.get("ge3") for c in up_sel])} | {rate([c.get("ge3") for c in dn_sel])} |

## Q4 — Strategy: PASS / REJECT counts

| Status | UP (pool-20) |
|--------|-------------|
| PASS | {total_pass_up} |
| REJECT | {total_reject_up} |
| UNAVAILABLE | {sum(s.get("strategy_unavailable_up",0) for s in summaries)} |

DOWN direction: no strategy gate (no SELL strategies exist).

## Q5 — Did Strategy improve or hurt C2 performance?

{"**INSUFFICIENT** — no REJECT events recorded yet.**" if not strategy_active else ""}
{"Strategy has fired. Compare Model A vs Model B below:" if strategy_active else ""}

Model A (C2 only): dir_acc={rate([c.get("direction_correct") for c in up_sel])}  
Model B (C2 + Strategy): dir_acc={rate([c.get("direction_correct") for c in up_sel if c.get("model_b_included")])}

## Q6 — Did this differ between UP and DOWN?

UP uses strategy gate (BEAR→REJECT, VOLATILE→REJECT).  
DOWN has no gate (no SELL strategies in StrategyLab).

## Q7 — Regimes observed

Regimes seen: {sorted(regimes_seen) if regimes_seen else "none yet"}  
Missing: {sorted(missing) if missing else "none"}  

## Q8 — Is there enough evidence to decide Q1?

**{"YES — sufficient samples across regimes." if sufficient else "INSUFFICIENT"}**  
Requirements: ≥50 shadow days, ≥1 BEAR day, ≥10 Strategy REJECT events.  
Status: {n_days}/50 days, BEAR: {"seen" if "BEAR" in regimes_seen else "not seen"}, REJECT events: {total_reject_up}/10 needed.

---

## Regime Coverage Status

| Regime | Status |
|--------|--------|
| BULL   | {"OBSERVED" if "BULL" in regimes_seen else "NOT_YET"} |
| RANGE  | {"OBSERVED" if "RANGE" in regimes_seen else "NOT_YET"} |
| BEAR   | {"OBSERVED" if "BEAR" in regimes_seen else "NOT_YET"} |
| VOLATILE | {"OBSERVED" if "VOLATILE" in regimes_seen else "INSUFFICIENT_REGIME_SAMPLE"} |

*Observation continues until all regimes are represented and ≥10 REJECT events are recorded.*

---

*Shadow layer only. No trades, no broker, no positions.*
"""

    out_path = REPORT_DIR / f"FINAL_TRADING_ARCHITECTURE_SHADOW_001_{date.today().isoformat()}.md"
    out_path.write_text(md, encoding="utf-8")
    log.info("[Shadow] Report written to %s", out_path.name)
    return out_path


def write_results_json(jsonl_path: Path = SHADOW_LOG_PATH) -> Path:
    """Write machine-readable results JSON summary."""
    summaries  = _load_all_summaries(jsonl_path)
    candidates = _load_all_candidates(jsonl_path)

    n_days         = len(summaries)
    regimes_seen   = sorted({s.get("regime") for s in summaries
                              if s.get("regime") not in (None, "UNAVAILABLE")})
    up_sel = [c for c in candidates if c.get("direction") == "UP" and c.get("selected_final_5")]
    dn_sel = [c for c in candidates if c.get("direction") == "DOWN" and c.get("selected_final_5")]

    def safe_rate(lst):
        vals = [v for v in lst if v is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 4)

    results = {
        "research_id":    "FINAL_TRADING_ARCHITECTURE_SHADOW_001",
        "architecture":   ARCHITECTURE_VERSION,
        "date_generated": date.today().isoformat(),
        "shadow_days":    n_days,
        "regimes_observed": regimes_seen,
        "strategy_question_status": (
            "SUFFICIENT" if n_days >= 50 and "BEAR" in regimes_seen else "INSUFFICIENT"
        ),
        "up_c2_total":  sum(s.get("c2_up_selected", 0) for s in summaries),
        "dn_c2_total":  sum(s.get("c2_down_selected", 0) for s in summaries),
        "strategy_pass_up_total":   sum(s.get("strategy_pass_up", 0) for s in summaries),
        "strategy_reject_up_total": sum(s.get("strategy_reject_up", 0) for s in summaries),
        "model_a_up": {
            "n":        len(up_sel),
            "dir_acc":  safe_rate([c.get("direction_correct") for c in up_sel]),
            "ge2_rate": safe_rate([c.get("ge2") for c in up_sel]),
        },
        "model_a_down": {
            "n":        len(dn_sel),
            "dir_acc":  safe_rate([c.get("direction_correct") for c in dn_sel]),
            "ge2_rate": safe_rate([c.get("ge2") for c in dn_sel]),
        },
        "model_b_up": {
            "n":        sum(1 for c in up_sel if c.get("model_b_included")),
            "dir_acc":  safe_rate([c.get("direction_correct") for c in up_sel
                                   if c.get("model_b_included")]),
            "ge2_rate": safe_rate([c.get("ge2") for c in up_sel
                                   if c.get("model_b_included")]),
        },
        "safety": {
            "broker_calls": 0,
            "orders": 0,
            "positions": 0,
            "candidatestore_writes": 0,
            "execution_calls": 0,
        },
    }

    out_path = REPORT_DIR / "final_trading_architecture_shadow_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log.info("[Shadow] Results JSON written to %s", out_path.name)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="FINAL_TRADING_ARCHITECTURE_SHADOW_001 — shadow runner"
    )
    parser.add_argument("--trade-date", default=None,
                        help="Trade date YYYY-MM-DD (default: most recent in DB)")
    parser.add_argument("--db", default=None, help="Path to SQLite DB")
    parser.add_argument("--force", action="store_true",
                        help="Re-run even if date already processed")
    parser.add_argument("--report-only", action="store_true",
                        help="Only regenerate reports from existing JSONL")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    db_path = Path(args.db) if args.db else None

    if args.report_only:
        write_shadow_report()
        write_results_json()
        print("Reports regenerated.")
        return

    result = run_shadow_day(
        trade_date=args.trade_date,
        db_path=db_path,
        force=args.force,
    )
    write_shadow_report()
    write_results_json()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    _cli()
