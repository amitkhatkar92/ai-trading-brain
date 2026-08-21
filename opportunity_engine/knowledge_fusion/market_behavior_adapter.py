"""
opportunity_engine/knowledge_fusion/market_behavior_adapter.py
===============================================================
KLP-005 PART 4 — Read-only adapter for market_behavior.db

Joins market_leaders_daily + market_leader_outcomes on leader_id
and returns normalized MarketLeaderRecord objects for use by the
KnowledgeFusionEngine LEADER_OUTCOME angle.

SAFETY CONTRACT
---------------
• broker_calls = 0, orders = 0, modifications = 0
• Read-only SQLite access — no writes to any database
• No look-ahead: outcome data is historical only
• Never modifies StrategyLab, RiskControl, DecisionEngine, or OrderManager
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).parent.parent.parent
_MB_DB = _ROOT / "data" / "market_behavior.db"


@dataclass(frozen=True)
class MarketLeaderRecord:
    """Normalized record from market_leaders_daily + market_leader_outcomes."""

    leader_id: str
    trade_date: str           # ISO date string "YYYY-MM-DD"
    symbol: str               # .NS suffix stripped
    symbol_raw: str           # original value from DB
    leader_type: str          # "WINNER" | "LOSER"
    rank_position: int
    day_return_pct: float
    volume_ratio: Optional[float]
    sector: str
    theme_phase: Optional[str]
    regime: Optional[str]
    # Outcome fields (may be None if not yet filled)
    return_1d: Optional[float]
    return_3d: Optional[float]
    return_5d: Optional[float]
    return_10d: Optional[float]
    return_20d: Optional[float]
    max_favorable: Optional[float]
    max_adverse: Optional[float]
    outcome_class: Optional[str]
    outcome_available: bool

    @property
    def trade_date_obj(self) -> Optional[date]:
        try:
            return date.fromisoformat(self.trade_date)
        except (ValueError, TypeError):
            return None


def load_market_leader_records(
    db_path: Optional[Path] = None,
    limit: int = 2000,
) -> List[MarketLeaderRecord]:
    """
    Load all market leader records by joining both tables.

    Parameters
    ----------
    db_path : path to market_behavior.db (defaults to project data dir)
    limit   : maximum rows to return (most recent by trade_date)

    Returns
    -------
    List[MarketLeaderRecord], empty list if DB absent or query fails.
    """
    path = db_path or _MB_DB
    if not path.exists() or path.stat().st_size == 0:
        return []

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                d.leader_id,
                d.trade_date,
                d.symbol,
                d.leader_type,
                d.rank_position,
                d.day_return_pct,
                d.volume_ratio,
                d.sector,
                d.theme_phase,
                d.regime,
                o.return_1d,
                o.return_3d,
                o.return_5d,
                o.return_10d,
                o.return_20d,
                o.max_favorable,
                o.max_adverse,
                o.outcome_class
            FROM market_leaders_daily d
            LEFT JOIN market_leader_outcomes o ON d.leader_id = o.leader_id
            ORDER BY d.trade_date DESC, d.rank_position ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()

        records: List[MarketLeaderRecord] = []
        for r in rows:
            symbol_raw = r["symbol"] or ""
            symbol = symbol_raw.replace(".NS", "").replace(".BO", "").upper().strip()
            has_outcome = r["return_1d"] is not None or r["return_5d"] is not None
            records.append(
                MarketLeaderRecord(
                    leader_id=r["leader_id"],
                    trade_date=r["trade_date"],
                    symbol=symbol,
                    symbol_raw=symbol_raw,
                    leader_type=(r["leader_type"] or "UNKNOWN").upper(),
                    rank_position=int(r["rank_position"] or 0),
                    day_return_pct=float(r["day_return_pct"] or 0.0),
                    volume_ratio=float(r["volume_ratio"]) if r["volume_ratio"] is not None else None,
                    sector=r["sector"] or "UNKNOWN",
                    theme_phase=r["theme_phase"],
                    regime=r["regime"] or None,
                    return_1d=float(r["return_1d"]) if r["return_1d"] is not None else None,
                    return_3d=float(r["return_3d"]) if r["return_3d"] is not None else None,
                    return_5d=float(r["return_5d"]) if r["return_5d"] is not None else None,
                    return_10d=float(r["return_10d"]) if r["return_10d"] is not None else None,
                    return_20d=float(r["return_20d"]) if r["return_20d"] is not None else None,
                    max_favorable=float(r["max_favorable"]) if r["max_favorable"] is not None else None,
                    max_adverse=float(r["max_adverse"]) if r["max_adverse"] is not None else None,
                    outcome_class=r["outcome_class"],
                    outcome_available=has_outcome,
                )
            )
        return records

    except Exception:
        return []


def get_sector_leader_stats(
    sector: str,
    leader_type: str = "WINNER",
    records: Optional[List[MarketLeaderRecord]] = None,
) -> Dict[str, Any]:
    """
    Aggregate outcome statistics for a sector + leader_type combination.

    Returns a dict with keys:
      n, win_rate_1d, avg_return_5d, avg_return_10d,
      avg_max_favorable, avg_max_adverse, outcome_classes
    """
    pool = records if records is not None else load_market_leader_records()
    relevant = [
        r for r in pool
        if r.sector.upper() == sector.upper()
        and r.leader_type == leader_type.upper()
        and r.outcome_available
    ]
    n = len(relevant)
    if n == 0:
        return {"n": 0}

    win_1d = sum(1 for r in relevant if (r.return_1d or 0) > 0)
    r5_vals = [r.return_5d for r in relevant if r.return_5d is not None]
    r10_vals = [r.return_10d for r in relevant if r.return_10d is not None]
    fav_vals = [r.max_favorable for r in relevant if r.max_favorable is not None]
    adv_vals = [r.max_adverse for r in relevant if r.max_adverse is not None]

    from collections import Counter
    oc = Counter(r.outcome_class for r in relevant if r.outcome_class)

    return {
        "n": n,
        "win_rate_1d": round(win_1d / n, 4),
        "avg_return_5d": round(sum(r5_vals) / len(r5_vals), 4) if r5_vals else None,
        "avg_return_10d": round(sum(r10_vals) / len(r10_vals), 4) if r10_vals else None,
        "avg_max_favorable": round(sum(fav_vals) / len(fav_vals), 4) if fav_vals else None,
        "avg_max_adverse": round(sum(adv_vals) / len(adv_vals), 4) if adv_vals else None,
        "outcome_classes": dict(oc.most_common(5)),
    }


def get_symbol_leader_stats(
    symbol: str,
    records: Optional[List[MarketLeaderRecord]] = None,
) -> Dict[str, Any]:
    """
    Aggregate outcome statistics for a specific symbol's leader appearances.
    """
    pool = records if records is not None else load_market_leader_records()
    clean = symbol.replace(".NS", "").replace(".BO", "").upper().strip()
    relevant = [r for r in pool if r.symbol == clean and r.outcome_available]
    n = len(relevant)
    if n == 0:
        return {"n": 0, "symbol": clean}

    win_1d = sum(1 for r in relevant if (r.return_1d or 0) > 0)
    r5_vals = [r.return_5d for r in relevant if r.return_5d is not None]
    fav_vals = [r.max_favorable for r in relevant if r.max_favorable is not None]
    adv_vals = [r.max_adverse for r in relevant if r.max_adverse is not None]

    leader_types = {}
    for r in relevant:
        leader_types[r.leader_type] = leader_types.get(r.leader_type, 0) + 1

    return {
        "n": n,
        "symbol": clean,
        "win_rate_1d": round(win_1d / n, 4),
        "avg_return_5d": round(sum(r5_vals) / len(r5_vals), 4) if r5_vals else None,
        "avg_max_favorable": round(sum(fav_vals) / len(fav_vals), 4) if fav_vals else None,
        "avg_max_adverse": round(sum(adv_vals) / len(adv_vals), 4) if adv_vals else None,
        "leader_types": leader_types,
    }
