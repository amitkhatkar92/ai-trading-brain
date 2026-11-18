"""Mover cause attribution: why did each day's top movers actually move?

For every resolved full-universe cohort, each of the day's top gainers and losers
(already filtered for corporate-action and bad-bar artifacts) is tagged with the
observable drivers of its move, using only data the system holds: the opening gap,
the intraday trend, the volume surge, the market move and the sector move.

Company events and institutional flow are NOT inferred. Their tables
(``daily_events``, ``bulk_block_deals``) are empty in production, so every mover
carries ``event_cause = UNVERIFIED_NO_EVENT_DATA`` and the summary reports the row
counts, so the gap stays visible instead of being papered over.

The tags also say where in the day a move first becomes observable (the 09:15 gap,
or intraday), which shows how much of the movement an evening pool can ever see.
Research only: nothing here is read by a trading or risk gate.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from data_integrity.return_validity import is_implausible_return
log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "universe_selection_learning"
DB_PATH = ROOT / "data" / "market_behavior.db"
VERSION = "cause-v1"
MARKET_SYMBOL = "^NSEI"

GAP_MIN_PCT = 2.0            # an opening gap this large in the move's direction is a gap move
GAP_SHARE = 0.5              # ...and must account for at least half of the day's move
INTRADAY_MIN_PCT = 1.0
INTRADAY_SHARE = 0.5
VOLUME_SURGE_X = 2.0         # day volume versus the trailing median
VOLUME_LOOKBACK_DAYS = 40    # calendar days of history for the median (about 25 sessions)
MARKET_MIN_PCT = 0.7         # the index moved at least this much the same way
SECTOR_MIN_PCT = 1.0         # peers' median moved at least this much the same way
MIN_SECTOR_PEERS = 3
MAX_ATTRIBUTE_DATES = 10
TOP_N = 20

EVENT_CAUSE_UNVERIFIED = "UNVERIFIED_NO_EVENT_DATA"
TAGS = ("OPENING_GAP", "INTRADAY_TREND", "VOLUME_SURGE", "MARKET_LED", "SECTOR_LED", "STOCK_SPECIFIC")


def classify_mover(
    direction: str, prev_close: float, open_: float, close: float,
    volume: float | None, median_volume: float | None,
    market_ret_pct: float | None, sector_median_ret_pct: float | None, sector_peers: int,
) -> dict[str, Any]:
    """Tag one mover. Pure: depends only on its arguments."""
    sign = 1.0 if direction == "UP" else -1.0
    total = (close / prev_close - 1) * 100
    gap = (open_ / prev_close - 1) * 100
    intraday = (close / open_ - 1) * 100
    volume_ratio = (volume / median_volume) if volume and median_volume and median_volume > 0 else None
    directional_total = sign * total
    tags: list[str] = []
    if sign * gap >= GAP_MIN_PCT and sign * gap >= GAP_SHARE * directional_total:
        tags.append("OPENING_GAP")
    if sign * intraday >= INTRADAY_MIN_PCT and sign * intraday >= INTRADAY_SHARE * directional_total:
        tags.append("INTRADAY_TREND")
    if volume_ratio is not None and volume_ratio >= VOLUME_SURGE_X:
        tags.append("VOLUME_SURGE")
    market_led = market_ret_pct is not None and sign * market_ret_pct >= MARKET_MIN_PCT
    sector_led = (sector_median_ret_pct is not None and sector_peers >= MIN_SECTOR_PEERS
                  and sign * sector_median_ret_pct >= SECTOR_MIN_PCT)
    if market_led:
        tags.append("MARKET_LED")
    if sector_led:
        tags.append("SECTOR_LED")
    if not market_led and not sector_led:
        tags.append("STOCK_SPECIFIC")
    if "OPENING_GAP" in tags:
        observable_at = "OPEN_0915"
    elif "INTRADAY_TREND" in tags or "VOLUME_SURGE" in tags:
        observable_at = "INTRADAY"
    else:
        observable_at = "UNCLEAR"
    return {
        "tags": tags, "observable_at": observable_at, "total_move_pct": round(total, 4),
        "gap_pct": round(gap, 4), "intraday_pct": round(intraday, 4),
        "volume_ratio": None if volume_ratio is None else round(volume_ratio, 3),
        "market_ret_pct": None if market_ret_pct is None else round(market_ret_pct, 4),
        "sector_median_ret_pct": None if sector_median_ret_pct is None else round(sector_median_ret_pct, 4),
        "sector_peers": sector_peers, "event_cause": EVENT_CAUSE_UNVERIFIED,
    }


def _sector_map() -> dict[str, str]:
    try:
        from predictive_gap.liquid_universe_builder_001 import _load_existing_sector_map
        return {k: v for k, v in _load_existing_sector_map().items() if v and v != "UNKNOWN"}
    except Exception:
        log.debug("[CauseAttribution] sector map unavailable", exc_info=True)
        return {}


def _table_rows(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return 0


def _bars(conn: sqlite3.Connection, symbols: list[str], day: str) -> dict[str, tuple]:
    out: dict[str, tuple] = {}
    for offset in range(0, len(symbols), 900):
        batch = symbols[offset:offset + 900]
        marks = ",".join("?" * len(batch))
        try:
            rows = conn.execute(
                f"SELECT symbol, open, close, volume FROM ohlcv_daily "
                f"WHERE trade_date = ? AND symbol IN ({marks})", (day, *batch)).fetchall()
        except sqlite3.OperationalError:
            rows = [(s, o, c, None) for s, o, c in conn.execute(
                f"SELECT symbol, open, close FROM ohlcv_daily "
                f"WHERE trade_date = ? AND symbol IN ({marks})", (day, *batch))]
        out.update({r[0]: r[1:] for r in rows})
    return out


def _median_volumes(conn: sqlite3.Connection, symbols: list[str], outcome_date: str) -> dict[str, float]:
    start = (date.fromisoformat(outcome_date) - timedelta(days=VOLUME_LOOKBACK_DAYS)).isoformat()
    series: dict[str, list[float]] = {}
    for offset in range(0, len(symbols), 900):
        batch = symbols[offset:offset + 900]
        marks = ",".join("?" * len(batch))
        try:
            for symbol, volume in conn.execute(
                f"SELECT symbol, volume FROM ohlcv_daily WHERE symbol IN ({marks}) "
                f"AND trade_date >= ? AND trade_date < ? AND volume > 0", (*batch, start, outcome_date)):
                series.setdefault(symbol, []).append(float(volume))
        except sqlite3.OperationalError:
            return {}
    return {s: statistics.median(v) for s, v in series.items() if len(v) >= 5}


def attribute_report(conn: sqlite3.Connection, report: dict[str, Any],
                     sectors: dict[str, str]) -> dict[str, Any]:
    """Attribute every top mover in one resolved cohort report."""
    trade_date, outcome_date = report["trade_date"], report["outcome_date"]
    universe = [r["symbol"] for r in report.get("rows", [])]
    previous = _bars(conn, universe, trade_date)
    current = _bars(conn, universe, outcome_date)
    totals: dict[str, float] = {}
    for symbol in universe:
        prev, cur = previous.get(symbol), current.get(symbol)
        if prev and cur and prev[1] and prev[1] > 0 and cur[1]:
            totals[symbol] = (cur[1] / prev[1] - 1) * 100
    by_sector: dict[str, list[tuple[str, float]]] = {}
    for symbol, move in totals.items():
        sector = sectors.get(symbol.removesuffix(".NS"))
        if sector:
            by_sector.setdefault(sector, []).append((symbol, move))
    market_prev = _bars(conn, [MARKET_SYMBOL], trade_date).get(MARKET_SYMBOL)
    market_cur = _bars(conn, [MARKET_SYMBOL], outcome_date).get(MARKET_SYMBOL)
    market_ret = ((market_cur[1] / market_prev[1] - 1) * 100
                  if market_prev and market_cur and market_prev[1] and market_cur[1] else None)
    cards = {d["direction"]: d["reason_cards"] for d in report.get("comparisons", [])}
    baseline20 = {d["direction"]: set(d.get("baseline20", {}).get("symbols", []))
                  for d in report.get("comparisons", [])}
    plausible_totals = {s: v for s, v in totals.items() if not is_implausible_return(v)}
    total_ranked = {
        "UP": sorted(plausible_totals, key=lambda s: (-plausible_totals[s], s))[:TOP_N],
        "DOWN": sorted(plausible_totals, key=lambda s: (plausible_totals[s], s))[:TOP_N],
    }
    medians = _median_volumes(
        conn, sorted({c["symbol"] for cs in cards.values() for c in cs}
                     | {s for ss in total_ranked.values() for s in ss}), outcome_date)

    def tag_symbol(direction: str, symbol: str) -> dict[str, Any] | None:
        prev, cur = previous.get(symbol), current.get(symbol)
        if not (prev and cur and prev[1] and prev[1] > 0 and cur[0] and cur[0] > 0 and cur[1]):
            return None
        sector = sectors.get(symbol.removesuffix(".NS"))
        peers = [m for s, m in by_sector.get(sector, []) if s != symbol] if sector else []
        return {"symbol": symbol, "sector": sector, **classify_mover(
            direction, prev[1], cur[0], cur[1], cur[2], medians.get(symbol),
            market_ret, statistics.median(peers) if peers else None, len(peers))}

    directions: dict[str, Any] = {}
    for direction in ("UP", "DOWN"):
        movers = []
        for card in cards.get(direction, []):
            tagged = tag_symbol(direction, card["symbol"])
            if tagged:
                movers.append({**tagged, "in_baseline20": card.get("in_baseline20")})
        total_movers = []
        for symbol in total_ranked[direction]:
            tagged = tag_symbol(direction, symbol)
            if tagged:
                total_movers.append({**tagged, "in_baseline20": symbol in baseline20.get(direction, set())})
        directions[direction] = {
            "movers": movers, "mover_count": len(movers),
            "tag_counts": {tag: sum(tag in m["tags"] for m in movers) for tag in TAGS},
            "total_move_movers": total_movers,
            "total_move_tag_counts": {tag: sum(tag in m["tags"] for m in total_movers) for tag in TAGS},
        }
    return {
        "version": VERSION, "trade_date": trade_date, "outcome_date": outcome_date,
        "market_ret_pct": None if market_ret is None else round(market_ret, 4),
        "event_data_rows": {"daily_events": _table_rows(conn, "daily_events"),
                            "bulk_block_deals": _table_rows(conn, "bulk_block_deals")},
        "directions": directions, "research_only": True,
        "generated_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
    }


def run_mover_cause_attribution(
    db_path: Path | None = None, store: Path | None = None, max_dates: int = MAX_ATTRIBUTE_DATES,
) -> dict[str, Any]:
    """Attribute resolved cohorts that have no attribution yet. Never raises."""
    summary: dict[str, Any] = {"attributed_dates": 0, "status": "OK", "research_only": True}
    try:
        directory = store or STORE
        resolved_dir = directory / "resolved"
        if not resolved_dir.exists():
            summary["status"] = "NO_RESOLVED_COHORTS"
            return summary
        sectors = _sector_map()
        with sqlite3.connect(f"{(db_path or DB_PATH).resolve().as_uri()}?mode=ro", uri=True) as conn:
            for file in sorted(resolved_dir.glob("*.json")):
                target = directory / "causes" / file.name
                if target.exists():
                    continue
                if summary["attributed_dates"] >= max(0, max_dates):
                    break
                report = json.loads(file.read_text(encoding="utf-8"))
                if not report.get("cohort_complete", True) or not report.get("comparisons"):
                    continue
                result = attribute_report(conn, report, sectors)
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_suffix(".tmp")
                tmp.write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
                tmp.replace(target)
                summary["attributed_dates"] += 1
    except Exception as exc:
        log.warning("[CauseAttribution] failed (non-critical): %s", exc, exc_info=True)
        summary["status"] = f"ERROR: {exc}"
    return summary


def get_cause_summary(store: Path | None = None) -> dict[str, Any]:
    """Read-only roll-up across all attributed days; never triggers computation."""
    directory = (store or STORE) / "causes"
    days = []
    for file in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            days.append(json.loads(file.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    out: dict[str, Any] = {"days": len(days), "research_only": True, "directions": {}}
    if not days:
        out["status"] = "NO_ATTRIBUTION_YET"
        return out
    latest_events = days[-1].get("event_data_rows", {})
    out["event_data_rows"] = latest_events
    out["event_causes_verifiable"] = any(latest_events.values())
    def block(movers: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(movers)
        counts = {tag: sum(tag in m["tags"] for m in movers) for tag in TAGS}
        observable = {key: sum(m["observable_at"] == key for m in movers)
                      for key in ("OPEN_0915", "INTRADAY", "UNCLEAR")}
        in_pool = sum(1 for m in movers if m.get("in_baseline20"))
        return {
            "movers": total,
            "tag_share": {t: (round(c / total, 3) if total else None) for t, c in counts.items()},
            "observable_at_share": {k: (round(v / total, 3) if total else None) for k, v in observable.items()},
            "pool20_capture_rate": round(in_pool / total, 3) if total else None,
        }

    for direction in ("UP", "DOWN"):
        per_day = [d["directions"].get(direction, {}) for d in days]
        out["directions"][direction] = {
            # ranked by open-to-close return, the measure the pools are scored on
            "intraday_ranked": block([m for p in per_day for m in p.get("movers", [])]),
            # ranked by the full close-to-close day move, which includes gap-driven names
            "total_move_ranked": block([m for p in per_day for m in p.get("total_move_movers", [])]),
        }
    out["status"] = "OK"
    return out
