"""
Edge Ranking Engine — Edge Discovery Engine Module 5
====================================================
Maintains the complete lifecycle of every discovered edge:

  CANDIDATE → ACTIVE → DECAYING → DEPRECATED

An edge is:
  • CANDIDATE  — proposed by pattern miner, not yet live-tested
  • ACTIVE     — approved by backtest AND showing live gains
  • DECAYING   — Sharpe drifting below threshold (live performance dropping)
  • DEPRECATED — removed from strategy library

The ranking system scores each edge on:
  1. Statistical quality    (Sharpe, win-rate, expectancy)    40%
  2. Live performance       (recent trade outcomes)           40%
  3. Recency                (how recently it was validated)   20%

Top-ranked edges are promoted into the strategy library.
Decaying edges are flagged for re-testing or retirement.

Persistence: data/discovered_edges.json
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .strategy_tester import BacktestResult
from .candidate_strategy_generator import CandidateStrategy
from utils import get_logger

log = get_logger(__name__)

EDGES_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "discovered_edges.json"
)

MAX_ACTIVE_EDGES    = 10     # promote at most this many to strategy library
DECAY_SHARPE_THRESH = 0.70   # Sharpe below this → DECAYING
RETIRE_WIN_RATE     = 0.45   # live win-rate below this → DEPRECATED
MAX_AGE_DAYS        = 90     # edges older than this are re-tested


@dataclass
class EdgeRecord:
    """Persistent record of one discovered edge and its lifecycle."""
    name:              str
    pattern_id:        str
    category:          str
    direction:         str
    status:            str       # CANDIDATE | ACTIVE | DECAYING | DEPRECATED
    precision:         float
    support:           int
    sharpe_ratio:      float
    oos_win_rate:      float
    avg_return_r:      float
    max_drawdown:      float
    wf_consistency:    float
    live_trades:       int       = 0
    live_wins:         int       = 0
    live_sharpe:       float     = 0.0
    composite_score:   float     = 0.0
    expectancy_r:      float     = 0.0   # primary edge quality: (WR×AvgWin_R)−(LR×AvgLoss_R)
    created_at:        str       = field(
        default_factory=lambda: datetime.now().isoformat())
    last_tested:       str       = field(
        default_factory=lambda: datetime.now().isoformat())
    description:       str       = ""
    base_strategy:     str       = "Breakout_Volume"
    entry_conditions:  List[Dict] = field(default_factory=list)
    strategy_params:   Dict       = field(default_factory=dict)


class EdgeRankingEngine:
    """
    Manages the full edge lifecycle from discovery to retirement.

    The orchestrator calls:
      update(candidates, backtest_results)   — after each discovery cycle
      record_trade_outcome(name, won)        — after each live trade
      get_active_edges()                     — for strategy library integration
      get_ranking_report()                   — for display + Control Tower
    """

    def __init__(self) -> None:
        self._edges: Dict[str, EdgeRecord] = {}
        self._load()
        log.info("[EdgeRankingEngine] Loaded %d edges (%d active).",
                 len(self._edges),
                 sum(1 for e in self._edges.values() if e.status == "ACTIVE"))

    # ── Public API ─────────────────────────────────────────────────────────

    def update(
        self,
        candidates: List[CandidateStrategy],
        results: List[BacktestResult],
    ) -> Tuple[int, int]:
        """
        Ingest new candidates + their backtest results.

        Returns:
            (n_promoted, n_deprecated)
        """
        result_map = {r.strategy_name: r for r in results}
        n_promoted = 0
        n_deprecated = 0

        for cand in candidates:
            res  = result_map.get(cand.name)
            name = cand.name

            if name in self._edges:
                existing = self._edges[name]
                if res and res.passes_gate:
                    # Re-validated — update stats
                    existing.sharpe_ratio    = res.sharpe_ratio
                    existing.oos_win_rate    = res.oos_win_rate
                    existing.avg_return_r    = res.avg_return_r
                    existing.expectancy_r    = res.expectancy_r
                    existing.max_drawdown    = res.max_drawdown
                    existing.wf_consistency  = res.wf_consistency
                    existing.last_tested     = datetime.now().isoformat()
                    if existing.status in ("DECAYING", "CANDIDATE"):
                        existing.status  = "ACTIVE"
                        n_promoted += 1
                elif res and not res.passes_gate:
                    if existing.status == "ACTIVE":
                        existing.status = "DECAYING"
                        n_deprecated += 1
                continue

            # New edge
            if res is None:
                continue

            status = "ACTIVE" if res.passes_gate else "CANDIDATE"
            if res.passes_gate:
                n_promoted += 1

            record = EdgeRecord(
                name              = name,
                pattern_id        = cand.pattern_id,
                category          = cand.category,
                direction         = cand.direction,
                status            = status,
                precision         = cand.precision,
                support           = cand.support,
                sharpe_ratio      = res.sharpe_ratio,
                oos_win_rate      = res.oos_win_rate,
                avg_return_r      = res.avg_return_r,
                expectancy_r      = res.expectancy_r,
                max_drawdown      = res.max_drawdown,
                wf_consistency    = res.wf_consistency,
                description       = cand.description,
                base_strategy     = cand.base_strategy,
                entry_conditions  = cand.entry_conditions,
                strategy_params   = cand.to_strategy_params(),
            )
            self._edges[name] = record

        # Lifecycle management (decay, retire old edges)
        self._lifecycle_pass()

        # Recompute composite scores + trim excess active edges
        self._score_all()
        self._enforce_active_cap()

        self._save()
        return n_promoted, n_deprecated

    def record_trade_outcome(self, strategy_name: str, won: bool) -> None:
        """Called after each live trade to update live performance stats."""
        rec = self._edges.get(strategy_name)
        if rec is None:
            return
        rec.live_trades += 1
        if won:
            rec.live_wins += 1

        live_wr = rec.live_wins / rec.live_trades if rec.live_trades else 0
        # Approximate live Sharpe from win rate and avg R
        rec.live_sharpe = (live_wr - 0.5) * rec.avg_return_r * 4

        # Check for decay
        if rec.live_trades >= 10:
            if live_wr < RETIRE_WIN_RATE:
                log.warning("[EdgeRankingEngine] Retiring edge '%s' "
                            "(live win-rate=%.0f%% < %.0f%%)",
                            strategy_name, live_wr * 100,
                            RETIRE_WIN_RATE * 100)
                rec.status = "DEPRECATED"
            elif rec.live_sharpe < DECAY_SHARPE_THRESH:
                rec.status = "DECAYING"

        self._score_all()
        self._save()

    def get_active_edges(self) -> List[EdgeRecord]:
        """Return active edges sorted by composite score descending."""
        active = [e for e in self._edges.values() if e.status == "ACTIVE"]
        return sorted(active, key=lambda e: -e.composite_score)

    def get_ranking_report(self) -> str:
        """Human-readable ranking table."""
        edges = sorted(self._edges.values(),
                       key=lambda e: -e.composite_score)
        if not edges:
            return "  No edges discovered yet."

        width = 100
        lines = [
            "",
            "═" * width,
            f"  EDGE DISCOVERY RANKING   [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
            "═" * width,
            f"  {'Name':<32} {'Cat':<14} {'Status':<12} "
            f"{'Score':>6} {'Sharpe':>7} {'WR':>6} {'Exp_R':>7} {'FatTail':>8}",
            "  " + "─" * (width - 2),
        ]
        for e in edges[:15]:
            status_icon = {"ACTIVE":"✅","DECAYING":"⚠️","DEPRECATED":"❌","CANDIDATE":"🔬"}.get(e.status, "?")
            exp_sign = "+" if e.expectancy_r >= 0 else ""
            lines.append(
                f"  {e.name:<32} {e.category:<14} {status_icon} {e.status:<10} "
                f"{e.composite_score:>6.2f} {e.sharpe_ratio:>7.2f} "
                f"{e.oos_win_rate:>5.0%} {exp_sign}{e.expectancy_r:>6.3f}R "
                f"{getattr(e, 'fat_tail_pct', 0.0):>7.0%}"
            )
        lines += [
            "  " + "─" * (width - 2),
            f"  Active: {sum(1 for e in edges if e.status=='ACTIVE')}  "
            f"Decaying: {sum(1 for e in edges if e.status=='DECAYING')}  "
            f"Deprecated: {sum(1 for e in edges if e.status=='DEPRECATED')}",
            "═" * width,
        ]
        return "\n".join(lines)

    def get_all_edges(self) -> List[EdgeRecord]:
        return list(self._edges.values())

    # ── Internal ───────────────────────────────────────────────────────────

    def _lifecycle_pass(self) -> None:
        """Age-out and decay management."""
        now = datetime.now()
        for rec in self._edges.values():
            if rec.status == "DEPRECATED":
                continue
            try:
                last = datetime.fromisoformat(rec.last_tested)
                age_days = (now - last).days
            except Exception:
                age_days = 0

            if age_days > MAX_AGE_DAYS and rec.status == "ACTIVE":
                rec.status = "DECAYING"

    def _score_all(self) -> None:
        """Compute composite score for every edge (0–10 scale).
        Expectancy is the primary statistical quality metric.
        """
        for rec in self._edges.values():
            # Statistical quality (40%) — expectancy-first
            exp_norm  = min(max(rec.expectancy_r, 0.0) / 1.0, 1.0)  # 1.0R = perfect
            stat_score = (
                exp_norm                           * 0.20   # primary: expectancy
                + min(rec.sharpe_ratio / 3.0, 1.0) * 0.10   # sharpe
                + rec.oos_win_rate                 * 0.10   # win rate
            )
            # Live performance (40%)
            if rec.live_trades >= 5:
                live_wr = rec.live_wins / rec.live_trades
                live_score = live_wr * 0.25 + min(rec.live_sharpe / 3.0, 1.0) * 0.15
            else:
                live_score = stat_score * 0.4   # use stat as proxy

            # Recency (20%)
            try:
                last = datetime.fromisoformat(rec.last_tested)
                age_days = (datetime.now() - last).days
            except Exception:
                age_days = 30
            recency_score = max(0.0, 1.0 - age_days / MAX_AGE_DAYS) * 0.20

            raw = (stat_score + live_score + recency_score)

            # Status penalty
            if rec.status == "DECAYING":
                raw *= 0.5
            elif rec.status == "DEPRECATED":
                raw = 0.0
            elif rec.status == "CANDIDATE":
                raw *= 0.6

            rec.composite_score = round(raw * 10.0, 3)

    def _enforce_active_cap(self) -> None:
        """Demote excess active edges beyond MAX_ACTIVE_EDGES."""
        active = sorted(
            [e for e in self._edges.values() if e.status == "ACTIVE"],
            key=lambda e: e.composite_score,
        )
        while len(active) > MAX_ACTIVE_EDGES:
            active[0].status = "DECAYING"
            active.pop(0)

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(EDGES_DB_PATH):
            return
        try:
            with open(EDGES_DB_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for name, data in raw.items():
                self._edges[name] = EdgeRecord(**{
                    k: v for k, v in data.items()
                    if k in EdgeRecord.__dataclass_fields__
                })
        except Exception as exc:
            log.warning("[EdgeRankingEngine] Could not load edges DB: %s", exc)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(EDGES_DB_PATH), exist_ok=True)
        try:
            serialisable = {
                name: {
                    k: v for k, v in asdict(rec).items()
                }
                for name, rec in self._edges.items()
            }
            with open(EDGES_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(serialisable, f, indent=2, default=str)
        except Exception as exc:
            log.warning("[EdgeRankingEngine] Could not save edges DB: %s", exc)
