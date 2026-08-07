"""predictive_gap/pga_collector.py — Collect all daily data for PGA-001."""
from __future__ import annotations

import csv
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .pga_config import (
    CT_DB, DNA_DB, EDGES_FILE, UNIVERSE_FILE, PAPER_TRADES_CSV, PGAConfig,
)

log = logging.getLogger(__name__)


@dataclass
class StockMove:
    symbol: str
    open_price: float
    close_price: float
    daily_return_pct: float       # (close - open) / open * 100
    volume: float
    move_type: str                # "GAINER" | "LOSER" | "NEUTRAL"
    actual_direction: str         # "UP" | "DOWN" | "FLAT"
    data_source: str              # "yfinance" | "estimated"


@dataclass
class SignalRecord:
    """An opportunity event from ct_events (equity_opportunity_found)."""
    symbol: str
    direction: str
    confidence: float
    strategy: str
    cycle_id: str
    event_ts: str


@dataclass
class DecisionRecord:
    """A decision from ct_decisions."""
    symbol: str
    direction: str
    confidence: float
    strategy: str
    approved: bool
    cycle_id: str
    decision_ts: str
    rejection_reason: str = ""


@dataclass
class DailyData:
    date: str
    gainers: List[StockMove] = field(default_factory=list)
    losers: List[StockMove] = field(default_factory=list)
    all_moves: Dict[str, StockMove] = field(default_factory=dict)    # symbol → StockMove
    executed_trades: List[Dict] = field(default_factory=list)
    approved_today: List[DecisionRecord] = field(default_factory=list)
    rejected_today: List[DecisionRecord] = field(default_factory=list)
    watchlist_candidates: List[SignalRecord] = field(default_factory=list)
    scanned_today: Set[str] = field(default_factory=set)
    market_stats: Dict[str, Any] = field(default_factory=dict)
    universe_symbols: List[str] = field(default_factory=list)
    dna_coverage: Dict[str, int] = field(default_factory=dict)       # symbol → count
    edge_coverage: Dict[str, int] = field(default_factory=dict)      # symbol → count


def _load_universe(max_symbols: int) -> List[str]:
    """Load NSE symbols from nifty500_universe.json."""
    try:
        with open(UNIVERSE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        symbols = data.get("symbols", data) if isinstance(data, dict) else data
        if isinstance(symbols, list):
            # Strip .NS suffix if present; handle both str items and dict items
            cleaned = []
            for s in symbols:
                if isinstance(s, dict):
                    raw = s.get("symbol") or s.get("yahoo_ticker") or ""
                elif isinstance(s, str):
                    raw = s
                else:
                    continue
                bare = str(raw).replace(".NS", "").strip()
                if bare:
                    cleaned.append(bare)
            return cleaned[:max_symbols]
    except Exception as e:
        log.warning("[PGA] Universe load failed: %s", e)
    # Fallback: NIFTY50 baseline
    return [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "ITC", "KOTAKBANK", "LT", "SBIN",
        "BAJFINANCE", "ASIANPAINT", "MARUTI", "NESTLEIND", "TITAN",
        "HCLTECH", "SUNPHARMA", "ULTRACEMCO", "WIPRO", "AXISBANK",
        "TECHM", "POWERGRID", "NTPC", "JSWSTEEL", "TATASTEEL",
        "ADANIENT", "ADANIPORTS", "ONGC", "COALINDIA", "BHARTIARTL",
        "DIVISLAB", "CIPLA", "DRREDDY", "BRITANNIA", "HEROMOTOCO",
        "BAJAJFINSV", "BAJAJ-AUTO", "EICHERMOT", "TATAMOTORS", "M&M",
        "GRASIM", "HINDALCO", "INDUSINDBK", "TATACONSUM", "VEDL",
        "BPCL", "IOC", "SHRIRAMFIN", "HDFCLIFE", "SBILIFE",
    ]


def _fetch_price_data(symbols: List[str], report_date: str) -> Dict[str, StockMove]:
    """Fetch daily OHLCV for symbols using yfinance. Returns bare-symbol dict."""
    import yfinance as yf

    result: Dict[str, StockMove] = {}
    if not symbols:
        return result

    # yfinance needs .NS suffix for NSE stocks
    ns_symbols = [f"{s}.NS" for s in symbols]

    import pandas as _pd
    from datetime import timedelta

    target_dt = datetime.strptime(report_date, "%Y-%m-%d").date()
    # Fetch a 5-day window ending on report_date to handle weekends/holidays
    end_dt   = target_dt + timedelta(days=1)
    start_dt = target_dt - timedelta(days=4)

    try:
        raw = yf.download(
            tickers=ns_symbols,
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            timeout=20,
        )
    except Exception as e:
        log.warning("[PGA] yfinance download failed: %s", e)
        return result

    if raw is None or (hasattr(raw, 'empty') and raw.empty):
        log.warning("[PGA] yfinance returned empty DataFrame for %s", report_date)
        return result

    for sym in symbols:
        ns = f"{sym}.NS"
        try:
            if isinstance(raw.columns, _pd.MultiIndex):
                # Multi-ticker download — columns are (ticker, field)
                tickers_in = raw.columns.get_level_values(0).unique()
                if ns not in tickers_in:
                    continue
                df = raw.xs(ns, axis=1, level=0)
            else:
                # Single-ticker fallback
                df = raw

            if df is None or df.empty:
                continue

            # Find the row for report_date (or the most recent trading day <= report_date)
            df.index = _pd.to_datetime(df.index)
            mask = df.index.date <= target_dt
            if not mask.any():
                continue
            row = df[mask].iloc[-1]

            o = float(row.get("Open", 0) or 0)
            c = float(row.get("Close", 0) or 0)
            v = float(row.get("Volume", 0) or 0)
            if o <= 0 or c <= 0:
                continue

            ret = (c - o) / o * 100
            result[sym] = StockMove(
                symbol=sym,
                open_price=round(o, 2),
                close_price=round(c, 2),
                daily_return_pct=round(ret, 2),
                volume=v,
                move_type="NEUTRAL",
                actual_direction="UP" if ret > 0.1 else ("DOWN" if ret < -0.1 else "FLAT"),
                data_source="yfinance",
            )
        except Exception as e:
            log.debug("[PGA] Price parse error for %s: %s", sym, e)

    return result


def _load_ct_decisions(report_date: str) -> tuple[List[DecisionRecord], List[DecisionRecord]]:
    """Load today's approved + rejected trades from Control Tower DB."""
    approved, rejected = [], []
    if not CT_DB.exists():
        return approved, rejected

    try:
        with sqlite3.connect(CT_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT d.symbol, d.direction, d.confidence, d.strategy,
                       d.decision, d.cycle_id,
                       COALESCE(d.created_at, c.started_at) AS decision_ts,
                       COALESCE(d.reasoning, '') AS reasoning
                FROM   ct_decisions d
                LEFT JOIN ct_cycles c ON d.cycle_id = c.cycle_id
                WHERE  DATE(COALESCE(d.created_at, c.started_at)) = ?
                """,
                (report_date,),
            ).fetchall()
    except Exception as e:
        log.warning("[PGA] ct_decisions load failed: %s", e)
        return approved, rejected

    for row in rows:
        dec_str = str(row["decision"] or "").upper()
        is_approved = "APPROV" in dec_str or dec_str == "YES"
        rec = DecisionRecord(
            symbol=row["symbol"] or "",
            direction=str(row["direction"] or "BUY").upper(),
            confidence=float(row["confidence"] or 0),
            strategy=row["strategy"] or "",
            approved=is_approved,
            cycle_id=row["cycle_id"] or "",
            decision_ts=row["decision_ts"] or "",
            rejection_reason="" if is_approved else str(row["reasoning"] or ""),
        )
        (approved if is_approved else rejected).append(rec)

    return approved, rejected


def _load_ct_signals(report_date: str) -> List[SignalRecord]:
    """Load today's opportunity signals from ct_events."""
    signals = []
    if not CT_DB.exists():
        return signals

    try:
        with sqlite3.connect(CT_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT e.ts, e.payload, e.cycle_id,
                       COALESCE(e.event_type, '') AS event_type
                FROM   ct_events e
                LEFT JOIN ct_cycles c ON e.cycle_id = c.cycle_id
                WHERE  DATE(e.ts) = ?
                  AND  (e.event_type LIKE '%opportunity%'
                     OR e.event_type LIKE '%equity%')
                """,
                (report_date,),
            ).fetchall()
    except Exception as e:
        log.warning("[PGA] ct_events load failed: %s", e)
        return signals

    for row in rows:
        try:
            payload = json.loads(row["payload"] or "{}")
            sym = payload.get("symbol", "")
            if not sym:
                continue
            signals.append(SignalRecord(
                symbol=sym,
                direction=str(payload.get("direction", "BUY")).upper(),
                confidence=float(payload.get("confidence", 0)),
                strategy=payload.get("strategy", ""),
                cycle_id=row["cycle_id"] or "",
                event_ts=row["ts"] or "",
            ))
        except Exception:
            pass

    return signals


def _load_executed_trades(report_date: str) -> List[Dict]:
    """Load today's executed paper trades from CSV."""
    trades = []
    # Try the canonical location from order_manager
    csv_candidates = [
        PAPER_TRADES_CSV,
        PAPER_TRADES_CSV.parent / "paper_trades.csv",
    ]
    csv_path = None
    for p in csv_candidates:
        if p.exists():
            csv_path = p
            break

    if csv_path is None:
        log.debug("[PGA] No paper trades CSV found.")
        return trades

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ts = row.get("timestamp", "")
                if not ts.startswith(report_date):
                    continue
                trades.append(dict(row))
    except Exception as e:
        log.warning("[PGA] Paper trades CSV load failed: %s", e)

    return trades


def _load_dna_coverage(symbols: List[str]) -> Dict[str, int]:
    """Count active DNA records per symbol from the institutional_dna DB."""
    coverage: Dict[str, int] = {s: 0 for s in symbols}
    if not DNA_DB.exists():
        return coverage

    try:
        with sqlite3.connect(DNA_DB) as conn:
            rows = conn.execute(
                "SELECT symbol, COUNT(*) as cnt FROM consensus_dna "
                "WHERE status IN ('ACTIVE', 'PROMOTED') GROUP BY symbol"
            ).fetchall()
            for sym, cnt in rows:
                bare = str(sym or "").replace(".NS", "").strip()
                if bare in coverage:
                    coverage[bare] = int(cnt)
    except Exception as e:
        log.debug("[PGA] DNA DB read failed: %s", e)

    return coverage


def _load_edge_coverage(symbols: List[str]) -> Dict[str, int]:
    """Count active discovered edges that apply to each symbol."""
    coverage: Dict[str, int] = {s: 0 for s in symbols}
    if not EDGES_FILE.exists():
        return coverage

    try:
        with open(EDGES_FILE, encoding="utf-8") as f:
            edges = json.load(f)
        if not isinstance(edges, list):
            edges = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("status", "")).upper() != "ACTIVE":
                continue
            for sym in symbols:
                tags = edge.get("tags", []) or []
                conditions = edge.get("conditions", {}) or {}
                if sym in tags or sym in str(conditions):
                    coverage[sym] = coverage.get(sym, 0) + 1
    except Exception as e:
        log.debug("[PGA] Edges file read failed: %s", e)

    return coverage


def _load_market_stats(report_date: str) -> Dict[str, Any]:
    """Load market stats (VIX, regime, breadth) from Control Tower."""
    stats: Dict[str, Any] = {"vix": 0.0, "regime": "UNKNOWN", "breadth": 0.5}
    if not CT_DB.exists():
        return stats

    try:
        with sqlite3.connect(CT_DB) as conn:
            row = conn.execute(
                """
                SELECT payload FROM ct_events
                WHERE  DATE(ts) = ?
                  AND  event_type LIKE '%market_regime%'
                ORDER  BY ts DESC LIMIT 1
                """,
                (report_date,),
            ).fetchone()
            if row:
                p = json.loads(row[0] or "{}")
                stats["regime"] = str(p.get("regime", "UNKNOWN"))
                stats["vix"] = float(p.get("vix", 0.0))
                stats["breadth"] = float(p.get("breadth", 0.5))
    except Exception:
        pass

    return stats


def collect_daily(report_date: str, cfg: PGAConfig) -> DailyData:
    """
    Collect all data needed for PGA analysis for a given date.

    Returns a DailyData with:
    - gainers/losers (top N by daily return)
    - all_moves (full price map for analysis)
    - executed/approved/rejected trades
    - watchlist candidates (scanned but not decided)
    - DNA + edge coverage per symbol
    - market stats (VIX, regime)
    """
    log.info("[PGA] Collecting daily data for %s", report_date)

    # ── 1. Load universe symbols ───────────────────────────────────────
    universe = _load_universe(cfg.max_symbols_for_price_fetch)
    log.info("[PGA] Universe: %d symbols", len(universe))

    # ── 2. Load market stats ───────────────────────────────────────────
    market_stats = _load_market_stats(report_date)
    log.info("[PGA] Market stats: %s", market_stats)

    # ── 3. Load CT decisions + signals ────────────────────────────────
    approved, rejected = _load_ct_decisions(report_date)
    signals = _load_ct_signals(report_date)
    executed_trades = _load_executed_trades(report_date)

    # ── 4. Build scanned_today set ─────────────────────────────────────
    scanned_today: Set[str] = {s.symbol for s in signals}
    decided_symbols: Set[str] = (
        {d.symbol for d in approved} | {d.symbol for d in rejected}
    )
    watchlist = [s for s in signals if s.symbol not in decided_symbols]

    # ── 5. Fetch price data ────────────────────────────────────────────
    # Include universe + any scanned/decided symbols not in universe
    extra_syms = (scanned_today | decided_symbols) - set(universe)
    all_symbols = universe + [s for s in extra_syms][:20]  # cap extra
    log.info("[PGA] Fetching prices for %d symbols...", len(all_symbols))
    all_moves = _fetch_price_data(all_symbols, report_date)
    log.info("[PGA] Got price data for %d symbols", len(all_moves))

    # ── 6. Classify gainers / losers ───────────────────────────────────
    for sym, move in all_moves.items():
        if move.daily_return_pct >= cfg.min_move_pct:
            move.move_type = "GAINER"
        elif move.daily_return_pct <= -cfg.min_move_pct:
            move.move_type = "LOSER"
        else:
            move.move_type = "NEUTRAL"

    sorted_moves = sorted(all_moves.values(), key=lambda m: m.daily_return_pct, reverse=True)
    gainers = sorted_moves[:cfg.top_n]
    losers = sorted_moves[-cfg.top_n:][::-1]   # bottom N, worst first

    # ── 7. DNA + Edge coverage ─────────────────────────────────────────
    interesting_syms = (
        [m.symbol for m in gainers + losers]
        + [d.symbol for d in approved + rejected]
        + list(scanned_today)
    )
    dna_coverage = _load_dna_coverage(interesting_syms)
    edge_coverage = _load_edge_coverage(interesting_syms)

    log.info(
        "[PGA] Collection complete: gainers=%d losers=%d "
        "approved=%d rejected=%d signals=%d executed=%d",
        len(gainers), len(losers),
        len(approved), len(rejected), len(signals), len(executed_trades),
    )

    return DailyData(
        date=report_date,
        gainers=gainers,
        losers=losers,
        all_moves=all_moves,
        executed_trades=executed_trades,
        approved_today=approved,
        rejected_today=rejected,
        watchlist_candidates=watchlist,
        scanned_today=scanned_today,
        market_stats=market_stats,
        universe_symbols=universe,
        dna_coverage=dna_coverage,
        edge_coverage=edge_coverage,
    )
