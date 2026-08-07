"""institutional_learning/ilc_market_audit.py — Phase 1: Market Opportunity Audit."""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Set

from .ilc_config import ILC_TOP_N, UNIVERSE_FILE, DNA_DB, CT_DB
from .ilc_models import MarketOpportunityItem, UniverseStatus

log = logging.getLogger(__name__)

# NSE sectors that are structurally excluded from IIOS universe by design
# (e.g. PSU banks with special governance, SME stocks, recently listed stocks)
_BY_DESIGN_PATTERNS = {
    "RVNL", "IRFC", "IRCTC", "RAILTEL",   # Railway PSUs (low float)
    "SJVN", "NLCIND", "GETBEES",           # Low-liquidity PSUs
}


def _load_universe_symbols() -> Set[str]:
    """Load the active IIOS universe symbols."""
    try:
        with open(UNIVERSE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        symbols = data.get("symbols", data) if isinstance(data, dict) else data
        if isinstance(symbols, list):
            result = set()
            for s in symbols:
                if isinstance(s, dict):
                    raw = s.get("symbol") or s.get("yahoo_ticker") or ""
                elif isinstance(s, str):
                    raw = s
                else:
                    continue
                bare = str(raw).replace(".NS", "").strip()
                if bare:
                    result.add(bare)
            return result
    except Exception as e:
        log.warning("[ILC] Universe load failed: %s", e)
    return set()


def _load_scanned_today(report_date: str) -> Set[str]:
    """Load symbols scanned today from ct_events."""
    import sqlite3
    scanned: Set[str] = set()
    if not CT_DB.exists():
        return scanned
    try:
        with sqlite3.connect(CT_DB) as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT json_extract(payload, '$.symbol') AS sym
                FROM ct_events
                WHERE DATE(ts) = ?
                  AND (event_type LIKE '%opportunity%' OR event_type LIKE '%equity%')
                """,
                (report_date,),
            ).fetchall()
            for row in rows:
                if row[0]:
                    scanned.add(str(row[0]).replace(".NS", "").strip())
    except Exception as e:
        log.debug("[ILC] ct_events scan failed: %s", e)
    return scanned


def _load_dna_coverage(symbols: List[str]) -> Dict[str, int]:
    """Count active DNA records per symbol."""
    import sqlite3
    coverage: Dict[str, int] = {s: 0 for s in symbols}
    if not DNA_DB.exists():
        return coverage
    try:
        with sqlite3.connect(DNA_DB) as conn:
            rows = conn.execute(
                "SELECT symbol, COUNT(*) FROM consensus_dna "
                "WHERE status IN ('ACTIVE', 'PROMOTED') GROUP BY symbol"
            ).fetchall()
            for sym, cnt in rows:
                bare = str(sym or "").replace(".NS", "").strip()
                if bare in coverage:
                    coverage[bare] = int(cnt)
    except Exception as e:
        log.debug("[ILC] DNA coverage load failed: %s", e)
    return coverage


def _classify_universe_status(
    symbol: str,
    universe_symbols: Set[str],
    scanned_today: Set[str],
    in_pga_analysis: bool,
) -> tuple[str, str]:
    """
    Classify why a top gainer/loser was or wasn't in the IIOS universe.

    Returns (UniverseStatus, reason_str)
    """
    # Check by-design exclusions first
    if symbol in _BY_DESIGN_PATTERNS:
        return (
            UniverseStatus.OUTSIDE_BY_DESIGN,
            f"{symbol} is intentionally excluded (low-float PSU / SME / special governance)",
        )

    # Is it in the universe?
    if symbol in universe_symbols:
        return (
            UniverseStatus.INSIDE,
            f"In IIOS universe ({len(universe_symbols)} symbols)",
        )

    # Not in universe — was it scanned anyway?
    if scanned_today:
        return (
            UniverseStatus.OUTSIDE_UNIVERSE_RULES,
            f"{symbol} not in universe but was scanned today — universe selection rule may need updating",
        )

    # Not in universe, not scanned, significant move → unexpected
    return (
        UniverseStatus.OUTSIDE_UNEXPECTED,
        f"{symbol} not in IIOS universe and produced significant move — potential universe gap",
    )


def audit_market_opportunities(
    report_date: str,
    gainers_moves: list,
    losers_moves: list,
    pga_analysis_symbols: Set[str],
) -> List[MarketOpportunityItem]:
    """
    Phase 1: Classify each top gainer/loser against the IIOS universe.

    Args:
        gainers_moves: List[StockMove] from ILC collector (top 20 gainers)
        losers_moves:  List[StockMove] from ILC collector (top 20 losers)
        pga_analysis_symbols: symbols that went through PGA analysis

    Returns list of MarketOpportunityItem sorted by |return_pct| descending
    """
    universe_symbols = _load_universe_symbols()
    scanned_today    = _load_scanned_today(report_date)

    all_moves = gainers_moves + losers_moves
    all_syms  = [m.symbol for m in all_moves]
    dna_cov   = _load_dna_coverage(all_syms)

    items: List[MarketOpportunityItem] = []
    for move in all_moves:
        sym = move.symbol
        status, reason = _classify_universe_status(
            sym, universe_symbols, scanned_today & {sym},
            sym in pga_analysis_symbols,
        )
        items.append(MarketOpportunityItem(
            symbol=sym,
            daily_return_pct=move.daily_return_pct,
            actual_direction=move.actual_direction,
            volume=move.volume,
            move_type=move.move_type,
            universe_status=status,
            universe_reason=reason,
            in_scanned_today=sym in scanned_today,
            dna_coverage=dna_cov.get(sym, 0),
            is_archived=(status == UniverseStatus.OUTSIDE_BY_DESIGN),
        ))

    items.sort(key=lambda i: abs(i.daily_return_pct), reverse=True)

    n_inside     = sum(1 for i in items if i.universe_status == UniverseStatus.INSIDE)
    n_by_design  = sum(1 for i in items if i.universe_status == UniverseStatus.OUTSIDE_BY_DESIGN)
    n_unexpected = sum(1 for i in items if i.universe_status == UniverseStatus.OUTSIDE_UNEXPECTED)
    n_rules      = sum(1 for i in items if i.universe_status == UniverseStatus.OUTSIDE_UNIVERSE_RULES)

    log.info(
        "[ILC] Phase 1 Audit: total=%d inside=%d by_design=%d unexpected=%d rules=%d",
        len(items), n_inside, n_by_design, n_unexpected, n_rules,
    )
    return items
