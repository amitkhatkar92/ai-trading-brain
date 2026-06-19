"""
analysis/option_strategy_evaluator.py
=======================================
OPTIONS_AUDIT_001 — Strategy Evaluation Engine

No live trading. No execution influence. Analysis only.

Evaluates historical option strategy performance across:
  - Overall (all regimes combined)
  - Per market regime (HIGH_VOL / TRENDING / RANGING)
  - Per VIX bucket (LOW / MEDIUM / HIGH / EXTREME)
  - Per holding period (0-1 DTE, 2-7 DTE, 8-21 DTE, 21+ DTE)

Strategies covered:
  SHORT_STRANGLE, IRON_CONDOR, BULL_PUT_SPREAD,
  BEAR_CALL_SPREAD, LONG_STRADDLE, LONG_STRANGLE,
  SHORT_STRADDLE, IRON_BUTTERFLY, COVERED_CALL, PROTECTIVE_PUT
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# ── Strategy definitions ──────────────────────────────────────────────────────

ALL_STRATEGIES = [
    "SHORT_STRANGLE",
    "IRON_CONDOR",
    "BULL_PUT_SPREAD",
    "BEAR_CALL_SPREAD",
    "LONG_STRADDLE",
    "LONG_STRANGLE",
    "SHORT_STRADDLE",
    "IRON_BUTTERFLY",
    "COVERED_CALL",
    "PROTECTIVE_PUT",
]

# DTE bucket boundaries (days-to-expiry at entry)
DTE_BUCKETS = [
    (0,  1,  "0-1 DTE"),
    (2,  7,  "2-7 DTE"),
    (8,  21, "8-21 DTE"),
    (22, 999,"22+ DTE"),
]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class StrategyMetrics:
    strategy:       str
    trades:         int
    wins:           int
    losses:         int
    win_rate:       float
    gross_win:      float
    gross_loss:     float
    profit_factor:  float
    avg_win:        float
    avg_loss:       float
    avg_pnl:        float
    total_pnl:      float
    max_win:        float
    max_loss:       float
    avg_days_held:  float
    avg_return_pct: float


@dataclass
class RegimeStrategyResult:
    """Strategy metrics broken down by market regime."""
    strategy: str
    by_regime: Dict[str, StrategyMetrics]   # regime → metrics
    overall:   StrategyMetrics


@dataclass
class StrategyRanking:
    rank:          int
    strategy:      str
    profit_factor: float
    win_rate:      float
    trades:        int
    total_pnl:     float
    best_regime:   str
    worst_regime:  str


# ── Core metrics computation ──────────────────────────────────────────────────

def compute_metrics(strategy: str, trade_rows: List[dict]) -> StrategyMetrics:
    """
    Compute performance metrics for one strategy from a list of trade records.

    Parameters
    ----------
    trade_rows : list of dicts, each with keys:
        pnl (float), return_pct (float), days_held (int)
    """
    if not trade_rows:
        return StrategyMetrics(
            strategy=strategy, trades=0, wins=0, losses=0,
            win_rate=0.0, gross_win=0.0, gross_loss=0.0,
            profit_factor=0.0, avg_win=0.0, avg_loss=0.0,
            avg_pnl=0.0, total_pnl=0.0, max_win=0.0, max_loss=0.0,
            avg_days_held=0.0, avg_return_pct=0.0,
        )

    pnls = [float(r["pnl"]) for r in trade_rows]
    rets = [float(r.get("return_pct", 0)) for r in trade_rows]
    days = [int(r.get("days_held", 0)) for r in trade_rows]

    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    n      = len(pnls)
    gw     = sum(wins)
    gl     = abs(sum(losses))

    return StrategyMetrics(
        strategy       = strategy,
        trades         = n,
        wins           = len(wins),
        losses         = len(losses),
        win_rate       = round(len(wins) / n * 100, 2),
        gross_win      = round(gw, 0),
        gross_loss     = round(gl, 0),
        profit_factor  = round(gw / gl, 3) if gl > 0 else float("inf"),
        avg_win        = round(gw / len(wins), 0) if wins else 0.0,
        avg_loss       = round(gl / len(losses), 0) if losses else 0.0,
        avg_pnl        = round(sum(pnls) / n, 0),
        total_pnl      = round(sum(pnls), 0),
        max_win        = round(max(pnls), 0),
        max_loss       = round(min(pnls), 0),
        avg_days_held  = round(sum(days) / n, 1),
        avg_return_pct = round(sum(rets) / n, 3),
    )


# ── Strategy Evaluator ────────────────────────────────────────────────────────

class StrategyEvaluator:
    """
    Central engine for evaluating options strategy performance.

    Usage
    -----
    evaluator = StrategyEvaluator(db_path)
    results   = evaluator.evaluate_all()
    rankings  = evaluator.rank_strategies(results)
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_trades(
        self,
        strategy:      Optional[str] = None,
        regime:        Optional[str] = None,
        vix_bkt:       Optional[str] = None,
        dte_min:       Optional[int] = None,
        dte_max:       Optional[int] = None,
    ) -> List[dict]:
        """Load trades from DB with optional filters."""
        clauses = []
        params  = []

        if strategy:
            clauses.append("strategy = ?")
            params.append(strategy)
        if regime:
            clauses.append("market_regime = ?")
            params.append(regime)
        if vix_bkt:
            clauses.append("vix_bucket = ?")
            params.append(vix_bkt)
        if dte_min is not None:
            clauses.append("days_held >= ?")
            params.append(dte_min)
        if dte_max is not None:
            clauses.append("days_held <= ?")
            params.append(dte_max)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql   = f"SELECT * FROM option_trade_audit {where}"

        try:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            return []

    def evaluate_strategy(
        self,
        strategy: str,
        regime:   Optional[str] = None,
    ) -> StrategyMetrics:
        """Evaluate a single strategy, optionally filtered by regime."""
        rows = self._load_trades(strategy=strategy, regime=regime)
        return compute_metrics(strategy, rows)

    def evaluate_all(self) -> Dict[str, StrategyMetrics]:
        """
        Evaluate all strategies on the full dataset (no regime filter).
        Returns dict keyed by strategy name.
        """
        return {s: self.evaluate_strategy(s) for s in ALL_STRATEGIES}

    def evaluate_by_regime(self) -> Dict[str, RegimeStrategyResult]:
        """
        For every strategy, compute metrics per regime and overall.
        """
        regimes = ["HIGH_VOL", "TRENDING", "RANGING"]
        results = {}
        for strategy in ALL_STRATEGIES:
            by_regime = {r: self.evaluate_strategy(strategy, regime=r) for r in regimes}
            overall   = self.evaluate_strategy(strategy)
            results[strategy] = RegimeStrategyResult(
                strategy  = strategy,
                by_regime = by_regime,
                overall   = overall,
            )
        return results

    def evaluate_by_vix_bucket(self) -> Dict[str, Dict[str, StrategyMetrics]]:
        """
        For every strategy × VIX bucket, compute metrics.
        Returns {strategy: {vix_bucket: StrategyMetrics}}
        """
        buckets = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
        result  = {}
        for strategy in ALL_STRATEGIES:
            result[strategy] = {}
            for bkt in buckets:
                rows = self._load_trades(strategy=strategy, vix_bkt=bkt)
                result[strategy][bkt] = compute_metrics(strategy, rows)
        return result

    def evaluate_by_dte(self) -> Dict[str, Dict[str, StrategyMetrics]]:
        """
        For every strategy × DTE bucket, compute metrics.
        Returns {strategy: {dte_label: StrategyMetrics}}
        """
        result = {}
        for strategy in ALL_STRATEGIES:
            result[strategy] = {}
            for d_min, d_max, label in DTE_BUCKETS:
                rows = self._load_trades(
                    strategy=strategy,
                    dte_min=d_min,
                    dte_max=d_max,
                )
                result[strategy][label] = compute_metrics(strategy, rows)
        return result

    def rank_strategies(
        self,
        overall_results: Dict[str, StrategyMetrics],
        min_trades: int = 5,
    ) -> List[StrategyRanking]:
        """
        Rank strategies by Profit Factor (primary), Win Rate (secondary).
        Only includes strategies with ≥ min_trades closed trades.

        Returns sorted list, highest PF first.
        """
        regime_results = self.evaluate_by_regime()
        ranked = []

        for strategy, m in overall_results.items():
            if m.trades < min_trades:
                continue

            # Find best/worst regime
            by_regime = regime_results.get(strategy, {}).by_regime if strategy in regime_results else {}
            regime_pfs = {
                r: m2.profit_factor
                for r, m2 in by_regime.items()
                if m2.trades >= 3
            }
            best_regime  = max(regime_pfs, key=regime_pfs.get) if regime_pfs else "N/A"
            worst_regime = min(regime_pfs, key=regime_pfs.get) if regime_pfs else "N/A"

            ranked.append(StrategyRanking(
                rank          = 0,  # filled below
                strategy      = strategy,
                profit_factor = m.profit_factor,
                win_rate      = m.win_rate,
                trades        = m.trades,
                total_pnl     = m.total_pnl,
                best_regime   = best_regime,
                worst_regime  = worst_regime,
            ))

        ranked.sort(key=lambda x: (x.profit_factor, x.win_rate), reverse=True)
        for i, r in enumerate(ranked, 1):
            r.rank = i
        return ranked

    def to_json(self, results: Dict[str, StrategyMetrics]) -> str:
        """Serialise overall results to JSON (matches requested output format)."""
        output = {}
        for strategy, m in results.items():
            if m.trades == 0:
                continue
            output[strategy] = {
                "trades":        m.trades,
                "win_rate":      m.win_rate,
                "profit_factor": m.profit_factor,
                "avg_pnl":       m.avg_pnl,
                "total_pnl":     m.total_pnl,
            }
        return json.dumps(output, indent=4)
