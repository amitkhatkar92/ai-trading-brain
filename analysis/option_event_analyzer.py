"""
analysis/option_event_analyzer.py
===================================
OPTIONS_AUDIT_001 — Event-Driven Impact Analysis

No live trading. No execution influence. Analysis only.

Classifies which calendar events create structural edge or hazard
for option strategies. Event categories:

  EARNINGS       — company earnings release (IV crush post-event)
  EXPIRY         — weekly/monthly NSE expiry (gamma risk / roll cost)
  RBI_POLICY     — RBI monetary policy announcement
  BUDGET         — Union Budget / State Budget
  INDEX_REBAL    — NIFTY/SENSEX index rebalancing
  FII_FLOW       — large FII buy/sell days (identified post-hoc)
  GLOBAL_SHOCK   — Fed, US CPI, geopolitical event spill-over

For each event type, evaluates:
  - Avg VIX change leading up to event (IV expansion)
  - Avg VIX change post-event (IV crush)
  - Strategy P&L differential: event vs non-event sessions
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional


# ── Event Types ───────────────────────────────────────────────────────────────

class EventType:
    EARNINGS     = "EARNINGS"
    EXPIRY       = "EXPIRY"
    RBI_POLICY   = "RBI_POLICY"
    BUDGET       = "BUDGET"
    INDEX_REBAL  = "INDEX_REBAL"
    FII_FLOW     = "FII_FLOW"
    GLOBAL_SHOCK = "GLOBAL_SHOCK"
    NONE         = "NONE"

    ALL = [EARNINGS, EXPIRY, RBI_POLICY, BUDGET, INDEX_REBAL, FII_FLOW, GLOBAL_SHOCK, NONE]


# ── Strategy recommendations by event context ─────────────────────────────────

EVENT_STRATEGY_GUIDANCE = {
    EventType.EARNINGS: {
        "pre_event":  {
            "preferred": ["LONG_STRADDLE", "LONG_STRANGLE"],
            "avoid":     ["SHORT_STRANGLE", "SHORT_STRADDLE"],
            "rationale": "IV expands before earnings → long premium benefits.",
        },
        "post_event": {
            "preferred": ["SHORT_STRANGLE", "IRON_CONDOR"],
            "avoid":     ["LONG_STRADDLE", "LONG_STRANGLE"],
            "rationale": "IV crush post-earnings → short premium benefits.",
        },
    },
    EventType.EXPIRY: {
        "pre_event":  {
            "preferred": ["SHORT_STRANGLE", "IRON_CONDOR", "IRON_BUTTERFLY"],
            "avoid":     ["LONG_STRADDLE"],
            "rationale": "Theta decay accelerates approaching expiry → sell premium.",
        },
        "post_event": {
            "preferred": ["BULL_PUT_SPREAD", "BEAR_CALL_SPREAD"],
            "avoid":     ["SHORT_STRADDLE"],
            "rationale": "Post-expiry reset — directional spreads on new series.",
        },
    },
    EventType.RBI_POLICY: {
        "pre_event":  {
            "preferred": ["LONG_STRADDLE", "IRON_CONDOR"],
            "avoid":     ["SHORT_STRANGLE"],
            "rationale": "Binary outcome — either flat (iron condor) or directional (straddle).",
        },
        "post_event": {
            "preferred": ["COVERED_CALL", "SHORT_STRANGLE"],
            "avoid":     ["LONG_STRADDLE"],
            "rationale": "IV typically declines after policy clarity.",
        },
    },
    EventType.BUDGET: {
        "pre_event":  {
            "preferred": ["LONG_STRANGLE", "IRON_CONDOR"],
            "avoid":     ["SHORT_STRADDLE"],
            "rationale": "Budget = high uncertainty; wide strangles benefit from large moves.",
        },
        "post_event": {
            "preferred": ["SHORT_STRANGLE", "IRON_CONDOR"],
            "avoid":     ["LONG_STRADDLE"],
            "rationale": "Post-budget IV collapse — premium selling opportunity.",
        },
    },
    EventType.GLOBAL_SHOCK: {
        "pre_event":  {
            "preferred": ["PROTECTIVE_PUT", "LONG_STRADDLE"],
            "avoid":     ["SHORT_STRANGLE", "COVERED_CALL"],
            "rationale": "Tail-risk regime — hedge or stay flat.",
        },
        "post_event": {
            "preferred": ["BULL_PUT_SPREAD"],
            "avoid":     ["SHORT_STRANGLE"],
            "rationale": "Mean-reversion opportunity post-shock if VIX normalises.",
        },
    },
}


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class EventPeriodMetrics:
    event_type:    str
    period:        str          # "pre_event" | "post_event" | "non_event"
    strategy:      str
    trades:        int
    win_rate:      float
    profit_factor: float
    avg_pnl:       float
    total_pnl:     float
    avg_vix:       float


@dataclass
class EventImpactSummary:
    event_type:         str
    pre_event_vix_avg:  float
    post_event_vix_avg: float
    iv_crush_magnitude: float   # post minus pre (negative = crush)
    total_events:       int
    strategies_ranked:  List[dict]


# ── Event Analyser ────────────────────────────────────────────────────────────

class EventAnalyzer:
    """
    Analyses how calendar events affect option strategy profitability.

    Usage
    -----
    analyzer = EventAnalyzer(db_path)
    summaries = analyzer.analyse_all_events()
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_by_event(
        self,
        event_type: str,
        strategy:   Optional[str] = None,
    ) -> List[dict]:
        try:
            clauses = ["event_type = ?"]
            params  = [event_type]
            if strategy:
                clauses.append("strategy = ?")
                params.append(strategy)
            sql = f"SELECT * FROM option_trade_audit WHERE {' AND '.join(clauses)}"
            with self._connect() as conn:
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except sqlite3.OperationalError:
            return []

    def event_strategy_metrics(
        self,
        event_type: str,
        strategy:   str,
    ) -> EventPeriodMetrics:
        """Compute performance of one strategy on event-tagged trade days."""
        rows = self._load_by_event(event_type, strategy)
        if not rows:
            return EventPeriodMetrics(
                event_type=event_type, period="event",
                strategy=strategy, trades=0,
                win_rate=0.0, profit_factor=0.0, avg_pnl=0.0,
                total_pnl=0.0, avg_vix=0.0,
            )

        pnls  = [float(r["pnl"]) for r in rows]
        vixs  = [float(r["vix"]) for r in rows]
        wins  = [p for p in pnls if p > 0]
        losses= [p for p in pnls if p <= 0]
        n     = len(pnls)
        gw    = sum(wins)
        gl    = abs(sum(losses))

        return EventPeriodMetrics(
            event_type    = event_type,
            period        = "event",
            strategy      = strategy,
            trades        = n,
            win_rate      = round(len(wins) / n * 100, 1) if n > 0 else 0,
            profit_factor = round(gw / gl, 3) if gl > 0 else float("inf"),
            avg_pnl       = round(sum(pnls) / n, 0) if n > 0 else 0,
            total_pnl     = round(sum(pnls), 0),
            avg_vix       = round(sum(vixs) / n, 2) if n > 0 else 0,
        )

    def analyse_all_events(self) -> Dict[str, EventImpactSummary]:
        """
        For each event type, summarise VIX levels and strategy performance.
        """
        from analysis.option_strategy_evaluator import ALL_STRATEGIES

        summaries = {}
        for event_type in EventType.ALL:
            rows = self._load_by_event(event_type)
            if not rows:
                continue

            vixs  = [float(r["vix"]) for r in rows]
            avg_v = round(sum(vixs) / len(vixs), 2) if vixs else 0

            # Strategy ranking within this event type
            strategy_rows = []
            for s in ALL_STRATEGIES:
                m = self.event_strategy_metrics(event_type, s)
                if m.trades >= 3:
                    strategy_rows.append({
                        "strategy":      s,
                        "trades":        m.trades,
                        "win_rate":      m.win_rate,
                        "profit_factor": m.profit_factor,
                        "avg_pnl":       m.avg_pnl,
                    })
            strategy_rows.sort(key=lambda x: x["profit_factor"], reverse=True)

            summaries[event_type] = EventImpactSummary(
                event_type          = event_type,
                pre_event_vix_avg   = avg_v,  # simplified: same field for now
                post_event_vix_avg  = avg_v,
                iv_crush_magnitude  = 0.0,    # requires pre/post timestamp split
                total_events        = len({r.get("trade_date", "") for r in rows}),
                strategies_ranked   = strategy_rows,
            )

        return summaries

    def get_guidance(self, event_type: str, pre_event: bool = True) -> Optional[dict]:
        """
        Return pre/post event strategy guidance for an event type.

        Parameters
        ----------
        pre_event : True = guidance for holding into the event,
                    False = guidance for post-event positioning.
        """
        event_guidance = EVENT_STRATEGY_GUIDANCE.get(event_type)
        if event_guidance is None:
            return None
        key = "pre_event" if pre_event else "post_event"
        return event_guidance.get(key)
