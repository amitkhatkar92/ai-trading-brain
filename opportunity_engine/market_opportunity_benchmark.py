"""
opportunity_engine/market_opportunity_benchmark.py
=====================================================
DTA-MARKET-BENCHMARK-001 — Daily Market Opportunity Benchmark & Learning.

Collects, every trading day after market close, two independent Top-20
Gainers/Losers benchmarks:
  1. BROAD_MARKET  — the broadest reliable NSE equity universe available
                     (SEM_SERIES='EQ' from the Dhan security master,
                     ~2,460 symbols — NOT restricted to NIFTY500).
  2. NIFTY500      — the standardized large/liquid benchmark, reusing
                     predictive_gap.pga_collector's proven yfinance
                     collection path (no duplicate fetch logic).

For every mover in both benchmarks, classifies exactly where the
opportunity was lost using the taxonomy the user specified:
  A — OUTSIDE_UNIVERSE               : not in our 230-symbol trading universe
  B — IN_UNIVERSE_NOT_IN_20POOL      : in universe, but never entered the
                                        V3/shadow 20-candidate pool that day
  C — IN_20POOL_NOT_SELECTED_5       : entered the 20-pool, not in final 5
  D — SELECTED_5_REJECTED_DOWNSTREAM : in final 5 (shadow) but never
                                        reached a live DecisionEngine
                                        approval / order that day
  E — SELECTED_TRADED_FAILED         : selected AND traded/approved, but
                                        the move went the wrong direction
  F — SELECTED_TRADED_SUCCESS        : selected AND traded/approved AND
                                        direction-correct (a genuine catch,
                                        not a miss — kept for completeness)

Data sources reused (NOT duplicated):
  - data/nifty500_universe.json           (our trading universe — category A)
  - data/shadow_evidence_ledger.jsonl      (V3 20-pool / C2 final-5 / outcome
                                            classification — categories B/C/E/F,
                                            same ledger used by
                                            scripts/knowledge_system/
                                            selection_characteristic_analyzer_001.py)
  - data/control_tower.db (ct_events, ct_decisions) — live same-day scan/
                                            decision confirmation — category D
  - analysis/rejection_tracker.py (rejection_audit.db) — EXISTING persistent
                                            evidence store; missed movers are
                                            fed into it as new rows
                                            (quality_tier="MARKET_BENCHMARK_MISS")
                                            so the SAME evidence pipeline other
                                            research scripts already consume
                                            picks them up automatically. This
                                            module does NOT build a parallel
                                            research/validation system.

Validated-knowledge -> live-decision adoption: this module does NOT wire
autonomous_research.ResearchCoordinator (confirmed, documented as
intentionally disconnected from production — ARCH_006_INFORMATION_
CONSUMPTION_MATRIX.md). The existing, already-live adoption path is KDA's
evidence_state mechanism (INSUFFICIENT -> DEVELOPING -> USEFUL -> VALIDATED
-> DECISION_ELIGIBLE, knowledge_authority/knowledge_decision_pipeline.py),
which already reads from the same evidence stores this module writes into.
No new promotion/threshold-change mechanism is introduced here.

READ-ONLY with respect to trading state. Only writes to:
  - data/market_benchmark/MARKET_BENCHMARK_{date}.jsonl  (new, append-only)
  - data/market_benchmark/MARKET_BENCHMARK_{date}.md      (new, human summary)
  - data/rejection_audit.db (existing rejection_tracker, additive rows only)

Never touches: universe composition, V3/C2 scoring, StrategyLab, CRE, Risk,
Simulation, DecisionEngine, AET, Execution, position sizing, or thresholds.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UNIVERSE_FILE = DATA / "nifty500_universe.json"
SHADOW_LEDGER = DATA / "shadow_evidence_ledger.jsonl"
CT_DB = DATA / "control_tower.db"
BENCHMARK_DIR = DATA / "market_benchmark"

TOP_N_DEFAULT = 20
BROAD_MARKET_MAX_SYMBOLS_DEFAULT = 800  # batching cap; see collect_broad_market_movers


class MoverCategory(str, Enum):
    OUTSIDE_UNIVERSE = "OUTSIDE_UNIVERSE"                         # A
    IN_UNIVERSE_NOT_IN_20POOL = "IN_UNIVERSE_NOT_IN_20POOL"       # B
    IN_20POOL_NOT_SELECTED_5 = "IN_20POOL_NOT_SELECTED_5"         # C
    SELECTED_5_REJECTED_DOWNSTREAM = "SELECTED_5_REJECTED_DOWNSTREAM"  # D
    SELECTED_TRADED_FAILED = "SELECTED_TRADED_FAILED"             # E
    SELECTED_TRADED_SUCCESS = "SELECTED_TRADED_SUCCESS"           # F (not a miss)
    UNRESOLVED = "UNRESOLVED"                                     # outcome not yet available


@dataclass
class MoverRecord:
    """One Top-20 gainer/loser from either benchmark, with full provenance."""
    trade_date:      str
    symbol:          str
    benchmark_type:  str     # "BROAD_MARKET" | "NIFTY500"
    move_type:       str     # "GAINER" | "LOSER"
    daily_return_pct: float
    direction:       str     # "UP" | "DOWN"
    source:          str     # "yfinance"
    methodology:     str
    universe_size:   int
    collected_at:    str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ClassifiedMover:
    mover:    MoverRecord
    category: MoverCategory
    detail:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self.mover)
        d["category"] = self.category.value
        d["detail"] = self.detail
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Collection
# ─────────────────────────────────────────────────────────────────────────────

def collect_nifty500_movers(trade_date: str, top_n: int = TOP_N_DEFAULT
                             ) -> Tuple[List[MoverRecord], List[MoverRecord]]:
    """Standardized large/liquid benchmark. Reuses
    predictive_gap.pga_collector.collect_daily() (proven yfinance path,
    dry_run=True so nothing is written by PGA itself). No duplicate fetch
    logic. Returns ([], []) on any failure — never raises."""
    try:
        from predictive_gap.pga_collector import collect_daily
        from predictive_gap.pga_config import PGAConfig
        cfg = PGAConfig(top_n=top_n, dry_run=True)
        daily = collect_daily(trade_date, cfg)
    except Exception as exc:
        log.warning("[MarketBenchmark] NIFTY500 collection failed: %s", exc)
        return [], []

    universe_size = len(daily.universe_symbols) if getattr(daily, "universe_symbols", None) else 230
    methodology = ("yfinance daily OHLCV over nifty500_universe.json symbols "
                   "(reused from predictive_gap.pga_collector.collect_daily)")
    # Defensive: exclude any NaN returns (e.g. delisted/no-data symbols) at
    # this boundary. Does not modify pga_collector.py itself.
    import math
    valid_gainers = [m for m in daily.gainers
                     if m.daily_return_pct is not None and not math.isnan(m.daily_return_pct)]
    valid_losers = [m for m in daily.losers
                    if m.daily_return_pct is not None and not math.isnan(m.daily_return_pct)]
    gainers = [
        MoverRecord(trade_date=trade_date, symbol=m.symbol, benchmark_type="NIFTY500",
                    move_type="GAINER", daily_return_pct=m.daily_return_pct,
                    direction="UP", source=m.data_source, methodology=methodology,
                    universe_size=universe_size)
        for m in valid_gainers
    ]
    losers = [
        MoverRecord(trade_date=trade_date, symbol=m.symbol, benchmark_type="NIFTY500",
                    move_type="LOSER", daily_return_pct=m.daily_return_pct,
                    direction="DOWN", source=m.data_source, methodology=methodology,
                    universe_size=universe_size)
        for m in valid_losers
    ]
    return gainers, losers


def collect_broad_market_movers(
    trade_date: str,
    top_n: int = TOP_N_DEFAULT,
    max_symbols: Optional[int] = BROAD_MARKET_MAX_SYMBOLS_DEFAULT,
    batch_size: int = 150,
) -> Tuple[List[MoverRecord], List[MoverRecord]]:
    """Broadest reliable Indian-equity benchmark. Symbol list from
    predictive_gap.broad_market_universe (Dhan security master, SEM_SERIES=
    'EQ' — NOT NIFTY500-restricted). Price fetch reuses
    predictive_gap.pga_collector._fetch_price_data() (same yfinance path
    already used and proven for NIFTY500), batched to keep each yfinance
    call reasonably sized. Direct nseindia.com scraping is NOT used (confirmed
    blocked, HTTP 503/Akamai, from this environment).

    max_symbols caps the collection to keep daily EOD runtime bounded --
    honestly documented in the methodology string, not hidden. Pass None
    for the full ~2,460-symbol universe (slower, more yfinance calls).
    Returns ([], []) on total failure -- never raises.
    """
    try:
        from predictive_gap.pga_collector import _fetch_price_data
        from predictive_gap.broad_market_universe import load_broad_nse_equity_symbols
    except Exception as exc:
        log.warning("[MarketBenchmark] Broad-market collector import failed: %s", exc)
        return [], []

    universe = load_broad_nse_equity_symbols()
    if not universe:
        log.warning("[MarketBenchmark] Broad-market universe empty — collection skipped.")
        return [], []
    total_universe_size = len(universe)
    if max_symbols is not None:
        universe = universe[:max_symbols]

    all_moves: Dict[str, Any] = {}
    failures = 0
    for i in range(0, len(universe), batch_size):
        chunk = universe[i:i + batch_size]
        try:
            moves = _fetch_price_data(chunk, trade_date)
            all_moves.update(moves)
        except Exception as exc:
            failures += 1
            log.debug("[MarketBenchmark] Broad-market batch %d-%d failed: %s",
                      i, i + len(chunk), exc)

    log.info(
        "[MarketBenchmark] Broad-market: %d/%d symbols priced (%d batch failures, "
        "universe capped at %s of %d total EQ symbols).",
        len(all_moves), len(universe), failures,
        max_symbols if max_symbols is not None else "ALL", total_universe_size,
    )

    if not all_moves:
        return [], []

    # Delisted / no-data symbols can yield NaN returns from yfinance --
    # exclude them so they never contaminate the ranked gainers/losers list.
    import math
    valid_moves = [
        m for m in all_moves.values()
        if m.daily_return_pct is not None and not math.isnan(m.daily_return_pct)
    ]
    if not valid_moves:
        return [], []

    sorted_moves = sorted(valid_moves, key=lambda m: m.daily_return_pct, reverse=True)
    gainers_raw = sorted_moves[:top_n]
    losers_raw = sorted_moves[-top_n:][::-1]

    methodology = (
        f"yfinance daily OHLCV over {len(universe)} NSE equities "
        f"(SEM_SERIES='EQ' from Dhan security master, capped from "
        f"{total_universe_size} total; batch_size={batch_size}, "
        f"{failures} batch failures)"
    )
    gainers = [
        MoverRecord(trade_date=trade_date, symbol=m.symbol, benchmark_type="BROAD_MARKET",
                    move_type="GAINER", daily_return_pct=m.daily_return_pct,
                    direction="UP", source=m.data_source, methodology=methodology,
                    universe_size=total_universe_size)
        for m in gainers_raw
    ]
    losers = [
        MoverRecord(trade_date=trade_date, symbol=m.symbol, benchmark_type="BROAD_MARKET",
                    move_type="LOSER", daily_return_pct=m.daily_return_pct,
                    direction="DOWN", source=m.data_source, methodology=methodology,
                    universe_size=total_universe_size)
        for m in losers_raw
    ]
    return gainers, losers


# ─────────────────────────────────────────────────────────────────────────────
# Classification (categories A-F)
# ─────────────────────────────────────────────────────────────────────────────

def _load_universe_symbols() -> set:
    try:
        data = json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))
        return {str(e.get("symbol", "")).upper() for e in data if isinstance(e, dict)}
    except Exception as exc:
        log.warning("[MarketBenchmark] Universe load failed: %s", exc)
        return set()


def _load_shadow_records_for_date(trade_date: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Return {(symbol, direction): latest record} for the given trade_date."""
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not SHADOW_LEDGER.exists():
        return out
    try:
        with open(SHADOW_LEDGER, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("trade_date") != trade_date:
                    continue
                key = (str(rec.get("symbol", "")).upper().replace(".NS", ""), rec.get("direction", "UP"))
                existing = out.get(key)
                if existing is None or rec.get("processed_at", "") > existing.get("processed_at", ""):
                    out[key] = rec
    except Exception as exc:
        log.warning("[MarketBenchmark] Shadow ledger read failed: %s", exc)
    return out


def _scanned_and_decided_today(trade_date: str) -> Tuple[set, Dict[str, str]]:
    """From control_tower.db: symbols scanned (opportunity.equity.found) and
    symbols with a DecisionEngine decision, for the given date."""
    scanned: set = set()
    decided: Dict[str, str] = {}
    if not CT_DB.exists():
        return scanned, decided
    try:
        conn = sqlite3.connect(f"file:{CT_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT payload FROM ct_events WHERE ts LIKE ? AND event_type='opportunity.equity.found'",
            (f"{trade_date}%",),
        )
        for r in cur.fetchall():
            try:
                p = json.loads(r["payload"] or "{}")
                sym = p.get("symbol")
                if sym:
                    scanned.add(str(sym).upper().replace(".NS", ""))
            except Exception:
                pass
        cur.execute("SELECT symbol, decision FROM ct_decisions WHERE ts LIKE ?", (f"{trade_date}%",))
        for r in cur.fetchall():
            decided[str(r["symbol"]).upper()] = r["decision"]
        conn.close()
    except Exception as exc:
        log.warning("[MarketBenchmark] control_tower.db read failed: %s", exc)
    return scanned, decided


def classify_mover(
    symbol: str,
    direction: str,
    trade_date: str,
    universe_symbols: set,
    shadow_records: Dict[Tuple[str, str], Dict[str, Any]],
    scanned_today: set,
    decided_today: Dict[str, str],
) -> Tuple[MoverCategory, Dict[str, Any]]:
    """Classify exactly where (if anywhere) this mover was lost. Pure
    function of the pre-loaded lookups above (no I/O) so it's cheap to call
    per-mover and easy to unit test."""
    sym = symbol.upper().replace(".NS", "")

    if sym not in universe_symbols:
        return MoverCategory.OUTSIDE_UNIVERSE, {"reason": "not in nifty500_universe.json"}

    shadow = shadow_records.get((sym, direction))
    if shadow is None:
        # In universe but no shadow/V3 record for this exact date+direction.
        # Distinguish "not even scanned live today" for extra detail, but
        # the category is the same either way -- available, didn't reach
        # the 20-pool that day.
        detail = {"reason": "no V3/shadow record for this trade_date",
                   "scanned_live_today": sym in scanned_today}
        return MoverCategory.IN_UNIVERSE_NOT_IN_20POOL, detail

    if shadow.get("v3_score") is None:
        return MoverCategory.IN_UNIVERSE_NOT_IN_20POOL, {
            "reason": "shadow record exists but v3_score is None (did not enter 20-pool)",
        }

    if not shadow.get("selected_final_5", False):
        return MoverCategory.IN_20POOL_NOT_SELECTED_5, {
            "v3_score": shadow.get("v3_score"), "c2_rank": shadow.get("c2_rank"),
            "miss_reason": shadow.get("miss_reason"),
        }

    # selected_final_5 == True from here on
    classification = shadow.get("classification")
    live_decision = decided_today.get(sym)

    if classification == "SELECTED_BUT_FAILED":
        return MoverCategory.SELECTED_TRADED_FAILED, {
            "t1_ret_pct": shadow.get("t1_ret_pct"), "live_decision": live_decision,
        }
    if classification == "CORRECT_SELECT":
        return MoverCategory.SELECTED_TRADED_SUCCESS, {
            "t1_ret_pct": shadow.get("t1_ret_pct"), "live_decision": live_decision,
        }
    if classification == "UNRESOLVED" or shadow.get("t1_ret_pct") is None:
        return MoverCategory.UNRESOLVED, {"reason": "outcome not yet resolved"}

    # selected_final_5=True but no live decision reached today and outcome
    # unclear -- treat as a downstream loss (category D).
    if live_decision is None:
        return MoverCategory.SELECTED_5_REJECTED_DOWNSTREAM, {
            "reason": "selected in shadow 5/5 but no live DecisionEngine decision today",
            "classification": classification,
        }
    return MoverCategory.SELECTED_5_REJECTED_DOWNSTREAM, {
        "reason": "selected in shadow 5/5, live decision present but outcome inconclusive",
        "classification": classification, "live_decision": live_decision,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Persistence + evidence feed
# ─────────────────────────────────────────────────────────────────────────────

def _feed_miss_into_rejection_tracker(cm: ClassifiedMover) -> None:
    """Missed movers (A/B/C/D) are fed into the EXISTING rejection_audit.db
    evidence store (same one StrategyLab/RiskManagerAI/CapitalRiskEngine
    already write into) -- NOT a new parallel research system. Wrapped in
    its own try/except; never raises, never affects trading."""
    if cm.category not in (
        MoverCategory.OUTSIDE_UNIVERSE, MoverCategory.IN_UNIVERSE_NOT_IN_20POOL,
        MoverCategory.IN_20POOL_NOT_SELECTED_5, MoverCategory.SELECTED_5_REJECTED_DOWNSTREAM,
    ):
        return
    try:
        from analysis.rejection_tracker import get_rejection_tracker
        get_rejection_tracker().ingest_rejection(
            symbol=cm.mover.symbol,
            strategy="MARKET_BENCHMARK",
            trade_date=cm.mover.trade_date,
            decision_score=0.0,
            quality_score=abs(cm.mover.daily_return_pct),
            quality_tier="MARKET_BENCHMARK_MISS",
            rejected_reason=cm.category.value[:200],
            price_at_rejection=0.0,
            direction=cm.mover.direction,
            market_regime="UNKNOWN",
            notes=json.dumps({
                "benchmark_type": cm.mover.benchmark_type,
                "move_type": cm.mover.move_type,
                "daily_return_pct": cm.mover.daily_return_pct,
                **cm.detail,
            })[:500],
        )
    except Exception as exc:
        log.debug("[MarketBenchmark] rejection_tracker ingest skipped for %s: %s",
                  cm.mover.symbol, exc)


def _write_outputs(trade_date: str, classified: List[ClassifiedMover]) -> Dict[str, int]:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = BENCHMARK_DIR / f"MARKET_BENCHMARK_{trade_date}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for cm in classified:
            fh.write(json.dumps(cm.to_dict(), default=str) + "\n")

    counts: Dict[str, int] = {}
    for cm in classified:
        counts[cm.category.value] = counts.get(cm.category.value, 0) + 1

    md_path = BENCHMARK_DIR / f"MARKET_BENCHMARK_{trade_date}.md"
    lines = [f"# Daily Market Opportunity Benchmark — {trade_date}", ""]
    for bt in ("BROAD_MARKET", "NIFTY500"):
        lines.append(f"## {bt}")
        subset = [cm for cm in classified if cm.mover.benchmark_type == bt]
        for cm in subset:
            lines.append(
                f"- {cm.mover.symbol:12s} {cm.mover.move_type:6s} "
                f"{cm.mover.daily_return_pct:+.2f}%  -> {cm.category.value}"
            )
        lines.append("")
    lines.append("## Category counts (all benchmarks combined)")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {cat}: {n}")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_market_benchmark(
    trade_date: Optional[str] = None,
    top_n: int = TOP_N_DEFAULT,
    broad_max_symbols: Optional[int] = BROAD_MARKET_MAX_SYMBOLS_DEFAULT,
) -> Dict[str, Any]:
    """Full pipeline: collect both benchmarks, classify every mover,
    persist outputs, feed misses into the existing evidence store. Never
    raises -- returns a summary dict with an 'error' key on failure so the
    EOD caller can log it without aborting."""
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    try:
        universe_symbols = _load_universe_symbols()
        shadow_records = _load_shadow_records_for_date(trade_date)
        scanned_today, decided_today = _scanned_and_decided_today(trade_date)

        nifty_gainers, nifty_losers = collect_nifty500_movers(trade_date, top_n)
        broad_gainers, broad_losers = collect_broad_market_movers(
            trade_date, top_n, max_symbols=broad_max_symbols)

        all_movers = nifty_gainers + nifty_losers + broad_gainers + broad_losers
        classified: List[ClassifiedMover] = []
        for m in all_movers:
            cat, detail = classify_mover(
                m.symbol, m.direction, trade_date,
                universe_symbols, shadow_records, scanned_today, decided_today,
            )
            cm = ClassifiedMover(mover=m, category=cat, detail=detail)
            classified.append(cm)
            _feed_miss_into_rejection_tracker(cm)

        counts = _write_outputs(trade_date, classified)

        summary = {
            "trade_date": trade_date,
            "nifty500_gainers": len(nifty_gainers), "nifty500_losers": len(nifty_losers),
            "broad_market_gainers": len(broad_gainers), "broad_market_losers": len(broad_losers),
            "total_classified": len(classified),
            "category_counts": counts,
        }
        log.info("[MarketBenchmark] %s: %s", trade_date, summary)
        return summary
    except Exception as exc:
        log.warning("[MarketBenchmark] run_daily_market_benchmark failed: %s", exc)
        return {"trade_date": trade_date, "error": str(exc)}


def run_daily_market_benchmark_silent(trade_date: Optional[str] = None) -> Dict[str, Any]:
    """EOD-hook-safe wrapper. Never raises under any circumstance."""
    try:
        return run_daily_market_benchmark(trade_date)
    except Exception as exc:
        log.error("[MarketBenchmark] Unexpected failure in silent wrapper: %s", exc)
        return {"error": str(exc)}
