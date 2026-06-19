"""
analysis/d_rec_002_opening_window.py
======================================
D-REC-002  —  Opening Window Advantage

Shadow Recommendation: quantify whether executing at the opening window
(09:10–09:30 IST) produces materially better or worse outcomes than the
post-governance window (09:45+).

Evidence only. No execution is altered. No governance is altered.

Methodology
-----------
Source: replay.db::ohlcv_daily (211 symbols, 2021-01-01 to 2025-12-30)
        control_tower.db::ct_decisions (actual system decisions with timestamps)

Simulation (intraday long-only proxy):
  OPENING_WINDOW  — entry = OPEN price (proxy for 09:10–09:30 execution)
  POST_GOVERNANCE — entry = (O + H + L) / 3  (intraday VWAP proxy, represents
                    a delayed entry after the opening auction has settled,
                    proxy for 09:45+ execution)
  Exit  = CLOSE (end-of-day flat, reflecting short-duration intraday style)
  MFE   = (HIGH - entry) / entry × 100   (maximum favourable excursion %)
  MAE   = max(0, (entry - LOW) / entry × 100)  (maximum adverse excursion %)
  WIN   = CLOSE > entry
  PnL   = (CLOSE - entry) / entry × 100
  PF    = Σ(positive PnL) / |Σ(negative PnL)|

Additional sub-analyses:
  — Gap-up days  (OPEN > prev CLOSE + 0.2%)
  — Gap-down days (OPEN < prev CLOSE - 0.2%)
  — Flat-open days
  — Yearly breakdown (trend over time)
  — Actual live decisions at 09:xx (from ct_decisions)

Shadow-mode contract
--------------------
Zero imports from execution_engine, risk_control, decision_ai,
opportunity_engine.

CLI
---
  python analysis/d_rec_002_opening_window.py
  python analysis/d_rec_002_opening_window.py --summary
  python analysis/d_rec_002_opening_window.py --min-price 100 --symbols NIFTY50
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

REPLAY_DB  = os.path.join(_ROOT, "data", "replay.db")
CT_DB      = os.path.join(_ROOT, "data", "control_tower.db")
REC_DB     = os.path.join(_ROOT, "data", "recommendations.db")
OUT_DIR    = os.path.join(_ROOT, "reports", "validation")

# ── Constants ─────────────────────────────────────────────────────────────────

OPENING_LABEL   = "OPENING_WINDOW"   # 09:10–09:30 proxy
POST_GOV_LABEL  = "POST_GOVERNANCE"  # 09:45+ proxy

MIN_PRICE       = 50.0   # filter out sub-₹50 stocks (illiquid micro-caps)
MIN_VOLUME      = 10_000  # filter days with no meaningful volume

# Gap classification thresholds
GAP_UP_PCT      = 0.20   # > +0.20% vs prev close = gap-up
GAP_DOWN_PCT    = -0.20  # < -0.20% vs prev close = gap-down

# Recommendation thresholds
EDGE_THRESHOLD  = 5.0    # pp WR advantage needed to claim an edge
PF_THRESHOLD    = 0.15   # PF advantage needed
MIN_N_FOR_EDGE  = 500    # minimum samples before declaring a verdict


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class WindowRow:
    date:        str
    symbol:      str
    entry_ow:    float   # OPEN (opening window entry)
    entry_pg:    float   # (O+H+L)/3  (post-governance proxy entry)
    high:        float
    low:         float
    close:       float
    prev_close:  float
    volume:      float

    @property
    def gap_pct(self) -> float:
        if self.prev_close > 0:
            return (self.entry_ow / self.prev_close - 1.0) * 100.0
        return 0.0

    @property
    def gap_class(self) -> str:
        g = self.gap_pct
        if g > GAP_UP_PCT:
            return "GAP_UP"
        if g < GAP_DOWN_PCT:
            return "GAP_DOWN"
        return "FLAT"


@dataclass
class WindowStats:
    label:        str
    n:            int     = 0
    wins:         int     = 0
    total_pnl:    float   = 0.0
    gross_win:    float   = 0.0
    gross_loss:   float   = 0.0
    sum_mfe:      float   = 0.0
    sum_mae:      float   = 0.0
    pnl_list:     List[float] = field(default_factory=list)

    def add(self, entry: float, high: float, low: float, close: float) -> None:
        if entry <= 0:
            return
        pnl_pct = (close - entry) / entry * 100.0
        mfe_pct = (high  - entry) / entry * 100.0
        mae_pct = max(0.0, (entry - low) / entry * 100.0)
        self.n       += 1
        self.total_pnl += pnl_pct
        self.sum_mfe   += mfe_pct
        self.sum_mae   += mae_pct
        self.pnl_list.append(pnl_pct)
        if pnl_pct > 0:
            self.wins      += 1
            self.gross_win += pnl_pct
        else:
            self.gross_loss += abs(pnl_pct)

    @property
    def win_rate(self) -> float:
        return (self.wins / self.n * 100.0) if self.n > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        return (self.gross_win / self.gross_loss) if self.gross_loss > 0 else float("inf")

    @property
    def avg_pnl(self) -> float:
        return (self.total_pnl / self.n) if self.n > 0 else 0.0

    @property
    def avg_mfe(self) -> float:
        return (self.sum_mfe / self.n) if self.n > 0 else 0.0

    @property
    def avg_mae(self) -> float:
        return (self.sum_mae / self.n) if self.n > 0 else 0.0

    def summary_line(self) -> str:
        pf = self.profit_factor
        pf_str = f"{pf:.3f}" if pf < 99 else "∞"
        return (
            f"n={self.n:>6}  WR={self.win_rate:>6.1f}%  "
            f"PF={pf_str:>6}  AvgPnL={self.avg_pnl:>+7.3f}%  "
            f"MFE={self.avg_mfe:>6.3f}%  MAE={self.avg_mae:>6.3f}%"
        )


# ── Data Loading ──────────────────────────────────────────────────────────────

def _load_ohlcv(min_price: float = MIN_PRICE,
                min_volume: float = MIN_VOLUME) -> List[WindowRow]:
    """Load ohlcv_daily and compute paired entry prices for both windows."""
    if not os.path.exists(REPLAY_DB):
        raise FileNotFoundError(f"replay.db not found: {REPLAY_DB}")

    conn = sqlite3.connect(REPLAY_DB)
    # Fetch all rows ordered by symbol then date so prev_close can be computed
    rows = conn.execute("""
        SELECT trade_date, symbol, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE open > 0 AND high > 0 AND low > 0 AND close > 0
          AND open >= ? AND volume >= ?
        ORDER BY symbol, trade_date
    """, (min_price, min_volume)).fetchall()
    conn.close()

    result: List[WindowRow] = []
    prev_close_map: Dict[str, float] = {}

    for trade_date, symbol, o, h, l, c, vol in rows:
        prev_close = prev_close_map.get(symbol, 0.0)
        if prev_close > 0:   # need a valid prev day to compute gap
            vwap_proxy = (o + h + l) / 3.0
            result.append(WindowRow(
                date=trade_date, symbol=symbol,
                entry_ow=o,
                entry_pg=vwap_proxy,
                high=h, low=l, close=c,
                prev_close=prev_close,
                volume=vol,
            ))
        prev_close_map[symbol] = c

    return result


def _load_live_decisions() -> List[dict]:
    """
    Load ct_decisions for reference — actual system decisions with timestamps.
    Returns only decisions where we know the time (ts has HH:MM component).
    """
    if not os.path.exists(CT_DB):
        return []
    conn = sqlite3.connect(CT_DB)
    rows = conn.execute("""
        SELECT ts, symbol, strategy, confidence, decision
        FROM ct_decisions
        WHERE ts IS NOT NULL AND length(ts) >= 16
        ORDER BY ts
    """).fetchall()
    conn.close()
    return [
        {"ts": r[0], "symbol": r[1], "strategy": r[2],
         "confidence": r[3], "decision": r[4]}
        for r in rows
    ]


# ── Computation ───────────────────────────────────────────────────────────────

def _compute_stats(rows: List[WindowRow],
                   filter_fn=None) -> Tuple[WindowStats, WindowStats]:
    ow = WindowStats(label=OPENING_LABEL)
    pg = WindowStats(label=POST_GOV_LABEL)
    for row in rows:
        if filter_fn and not filter_fn(row):
            continue
        ow.add(row.entry_ow, row.high, row.low, row.close)
        pg.add(row.entry_pg, row.high, row.low, row.close)
    return ow, pg


def _yearly_breakdown(rows: List[WindowRow]
                       ) -> Dict[str, Tuple[WindowStats, WindowStats]]:
    years: Dict[str, List[WindowRow]] = {}
    for row in rows:
        yr = row.date[:4]
        years.setdefault(yr, []).append(row)
    result = {}
    for yr, yr_rows in sorted(years.items()):
        result[yr] = _compute_stats(yr_rows)
    return result


def _live_decision_breakdown(decisions: List[dict]
                              ) -> Dict[str, List[dict]]:
    """Split live decisions by time window."""
    ow: List[dict] = []
    pg: List[dict] = []
    other: List[dict] = []
    for d in decisions:
        ts = d["ts"]
        hhmm = ts[11:16] if len(ts) >= 16 else ""
        if "09:10" <= hhmm <= "09:30":
            ow.append(d)
        elif hhmm >= "09:45":
            pg.append(d)
        else:
            other.append(d)
    return {"OPENING_WINDOW": ow, "POST_GOVERNANCE": pg, "OTHER": other}


# ── Verdict ───────────────────────────────────────────────────────────────────

def _compute_verdict(ow: WindowStats, pg: WindowStats) -> Tuple[str, str]:
    """
    Returns (verdict_code, narrative).
    OPENING_EDGE  — opening window significantly outperforms
    GOVERNANCE_VALIDATED — post-governance significantly outperforms
    INSUFFICIENT  — not enough data
    NEUTRAL       — no material difference
    """
    if ow.n < MIN_N_FOR_EDGE or pg.n < MIN_N_FOR_EDGE:
        return "INSUFFICIENT", (
            f"Insufficient data for verdict (OW n={ow.n}, PG n={pg.n}, "
            f"minimum required: {MIN_N_FOR_EDGE})."
        )
    wr_diff  = ow.win_rate - pg.win_rate
    pf_diff  = ow.profit_factor - pg.profit_factor
    pnl_diff = ow.avg_pnl - pg.avg_pnl

    if wr_diff > EDGE_THRESHOLD and pf_diff > PF_THRESHOLD:
        return "OPENING_EDGE", (
            f"Opening window leads by {wr_diff:+.1f}pp WR and "
            f"{pf_diff:+.3f} PF. Entering at market OPEN captures "
            f"additional {pnl_diff:+.3f}% avg PnL per trade."
        )
    if -wr_diff > EDGE_THRESHOLD and -pf_diff > PF_THRESHOLD:
        return "GOVERNANCE_VALIDATED", (
            f"Post-governance window leads by {-wr_diff:+.1f}pp WR and "
            f"{-pf_diff:+.3f} PF. Delayed entry (09:45+) consistently "
            f"outperforms opening rush. Governance window is beneficial."
        )
    return "NEUTRAL", (
        f"No material difference (WR diff={wr_diff:+.1f}pp, "
        f"PF diff={pf_diff:+.3f}). Both windows produce similar outcomes. "
        f"Continue collecting live evidence."
    )


# ── Recommendation Storage ────────────────────────────────────────────────────

def _store_recommendation(verdict: str, narrative: str,
                           ow: WindowStats, pg: WindowStats,
                           run_id: str) -> None:
    """Write D-REC-002 to recommendations.db with status PENDING."""
    if not os.path.exists(REC_DB):
        return

    rec_id = "D-REC-002"
    pf_ow  = ow.profit_factor
    pf_str = f"{pf_ow:.3f}" if pf_ow < 99 else "inf"

    suggestion = (
        f"Opening Window vs Post-Governance comparison. "
        f"OW: WR={ow.win_rate:.1f}%, PF={pf_str}, PnL={ow.avg_pnl:+.3f}%. "
        f"PG: WR={pg.win_rate:.1f}%, PF={pg.profit_factor:.3f}, "
        f"PnL={pg.avg_pnl:+.3f}%. Verdict: {verdict}."
    )
    rationale = narrative

    conn = sqlite3.connect(REC_DB)
    try:
        # Upsert: update if rec_id already exists
        existing = conn.execute(
            "SELECT id FROM recommendations WHERE rec_id=?", (rec_id,)
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()

        if existing:
            conn.execute("""
                UPDATE recommendations
                SET suggestion=?, rationale=?, reviewer_notes=?,
                    run_id=?
                WHERE rec_id=?
            """, (suggestion, rationale,
                  f"[D-REC-002 updated {now[:10]}] {verdict} | "
                  f"OW n={ow.n} WR={ow.win_rate:.1f}% PF={pf_str} | "
                  f"PG n={pg.n} WR={pg.win_rate:.1f}% PF={pg.profit_factor:.3f}",
                  run_id, rec_id))
        else:
            conn.execute("""
                INSERT INTO recommendations
                  (rec_id, rec_type, target, category,
                   current_accuracy, n_obs, suggestion, rationale,
                   confidence, priority, generated_at, status,
                   reviewer_notes, requires_human_approval,
                   safe_to_auto_apply, run_id)
                VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?)
            """, (
                rec_id, "INVESTIGATE", "execution_window",
                "GOVERNANCE",
                ow.win_rate / 100.0, ow.n,
                suggestion, rationale,
                "MEDIUM" if ow.n >= MIN_N_FOR_EDGE else "LOW",
                6,
                now, "PENDING",
                f"[D-REC-002 created {now[:10]}] {verdict} | "
                f"OW n={ow.n} WR={ow.win_rate:.1f}% PF={pf_str} | "
                f"PG n={pg.n} WR={pg.win_rate:.1f}% PF={pg.profit_factor:.3f}",
                1, 0, run_id,
            ))
        conn.commit()
    finally:
        conn.close()


# ── Report ────────────────────────────────────────────────────────────────────

def _build_report(
    ow_all: WindowStats, pg_all: WindowStats,
    gap_stats: Dict[str, Tuple[WindowStats, WindowStats]],
    yearly: Dict[str, Tuple[WindowStats, WindowStats]],
    decisions: List[dict],
    verdict: str, narrative: str,
    date_str: str,
) -> str:
    live_split = _live_decision_breakdown(decisions)

    lines: List[str] = [
        f"# D-REC-002 — Opening Window Advantage",
        f"",
        f"**Date:** {date_str}  ",
        f"**Status:** SHADOW RECOMMENDATION — evidence only, no execution change  ",
        f"**Corpus:** `replay.db::ohlcv_daily` (OHLCV simulation) + live `ct_decisions`",
        f"",
        f"---",
        f"",
        f"## Methodology",
        f"",
        f"Two simulated entry scenarios compared on the same universe (211 NSE symbols,",
        f"2021–2025, ~256K trading days). Both scenarios use the same exit: day's CLOSE.",
        f"",
        f"| Window | Entry Price | Proxy For |",
        f"|---|---|---|",
        f"| **OPENING_WINDOW** | OPEN | 09:10–09:30 IST execution |",
        f"| **POST_GOVERNANCE** | (O + H + L) ÷ 3 | 09:45+ intraday average |",
        f"",
        f"- **MFE** = (HIGH − entry) / entry × 100  (best intraday point reached)",
        f"- **MAE** = max(0, (entry − LOW) / entry × 100)  (worst intraday drawdown)",
        f"- **WIN** = CLOSE > entry",
        f"- **PF** = Σ(positive PnL %) / |Σ(negative PnL %)|",
        f"",
        f"---",
        f"",
        f"## Overall Results",
        f"",
        f"| Metric | OPENING_WINDOW (09:10–09:30) | POST_GOVERNANCE (09:45+) | Delta |",
        f"|---|---|---|---|",
    ]

    def _fmt(v: float, decimals: int = 2, pct: bool = False) -> str:
        s = f"{v:.{decimals}f}"
        return s + "%" if pct else s

    wr_delta  = ow_all.win_rate - pg_all.win_rate
    pf_ow     = ow_all.profit_factor
    pf_pg     = pg_all.profit_factor
    pf_delta  = pf_ow - pf_pg
    pnl_delta = ow_all.avg_pnl - pg_all.avg_pnl
    mfe_delta = ow_all.avg_mfe - pg_all.avg_mfe
    mae_delta = ow_all.avg_mae - pg_all.avg_mae

    pf_ow_s  = f"{pf_ow:.3f}" if pf_ow < 99 else "∞"
    pf_pg_s  = f"{pf_pg:.3f}" if pf_pg < 99 else "∞"

    lines += [
        f"| N (trades) | {ow_all.n:,} | {pg_all.n:,} | — |",
        f"| Win Rate | {ow_all.win_rate:.1f}% | {pg_all.win_rate:.1f}% | {wr_delta:+.1f}pp |",
        f"| Profit Factor | {pf_ow_s} | {pf_pg_s} | {pf_delta:+.3f} |",
        f"| Avg PnL/trade | {ow_all.avg_pnl:+.3f}% | {pg_all.avg_pnl:+.3f}% | {pnl_delta:+.3f}% |",
        f"| Avg MFE | {ow_all.avg_mfe:.3f}% | {pg_all.avg_mfe:.3f}% | {mfe_delta:+.3f}% |",
        f"| Avg MAE | {ow_all.avg_mae:.3f}% | {pg_all.avg_mae:.3f}% | {mae_delta:+.3f}% |",
        f"",
        f"---",
        f"",
        f"## Gap-Day Breakdown",
        f"",
        f"| Gap Type | Window | N | WR | PF | Avg PnL | MFE | MAE |",
        f"|---|---|---|---|---|---|---|---|",
    ]

    for gap_class, (gow, gpg) in sorted(gap_stats.items()):
        for st in (gow, gpg):
            pf_s = f"{st.profit_factor:.3f}" if st.profit_factor < 99 else "∞"
            lines.append(
                f"| {gap_class} | {st.label} | {st.n:,} | "
                f"{st.win_rate:.1f}% | {pf_s} | "
                f"{st.avg_pnl:+.3f}% | {st.avg_mfe:.3f}% | {st.avg_mae:.3f}% |"
            )

    lines += [
        f"",
        f"---",
        f"",
        f"## Yearly Breakdown",
        f"",
        f"| Year | Window | N | WR | PF | Avg PnL |",
        f"|---|---|---|---|---|---|",
    ]

    for yr, (yow, ypg) in yearly.items():
        for st in (yow, ypg):
            pf_s = f"{st.profit_factor:.3f}" if st.profit_factor < 99 else "∞"
            lines.append(
                f"| {yr} | {st.label} | {st.n:,} | "
                f"{st.win_rate:.1f}% | {pf_s} | {st.avg_pnl:+.3f}% |"
            )

    lines += [
        f"",
        f"---",
        f"",
        f"## Live System Decisions (ct_decisions Reference)",
        f"",
        f"Actual system decisions classified by time-of-day:",
        f"",
        f"| Window | Count | APPROVED | REJECTED |",
        f"|---|---|---|---|",
    ]

    for key in ("OPENING_WINDOW", "POST_GOVERNANCE", "OTHER"):
        dec_list = live_split.get(key, [])
        n = len(dec_list)
        approved = sum(1 for d in dec_list if d["decision"] == "APPROVED")
        rejected = n - approved
        lines.append(f"| {key} | {n} | {approved} | {rejected} |")

    if live_split.get("OPENING_WINDOW"):
        lines += [
            f"",
            f"### Pre-09:45 Decisions Detail",
            f"",
            f"| Timestamp | Symbol | Strategy | Confidence | Decision |",
            f"|---|---|---|---|---|",
        ]
        for d in sorted(live_split["OPENING_WINDOW"], key=lambda x: x["ts"]):
            lines.append(
                f"| {d['ts'][:19]} | {d['symbol']} | {d['strategy']} | "
                f"{d['confidence']:.2f} | {d['decision']} |"
            )

    lines += [
        f"",
        f"---",
        f"",
        f"## Verdict",
        f"",
        f"```",
        f"VERDICT: {verdict}",
        f"```",
        f"",
        narrative,
        f"",
        f"### Key Observations",
        f"",
    ]

    # Derive observations
    if abs(wr_delta) < 2.0:
        lines.append(
            f"- **WR difference is minimal** ({wr_delta:+.1f}pp). "
            f"Both windows produce similar win rates across {ow_all.n:,} simulated trades."
        )
    elif wr_delta > 0:
        lines.append(
            f"- **OPENING_WINDOW has higher WR** ({ow_all.win_rate:.1f}% vs "
            f"{pg_all.win_rate:.1f}%, +{wr_delta:.1f}pp) — captures the opening impulse."
        )
    else:
        lines.append(
            f"- **POST_GOVERNANCE has higher WR** ({pg_all.win_rate:.1f}% vs "
            f"{ow_all.win_rate:.1f}%, +{-wr_delta:.1f}pp) — delayed entry avoids false breakouts."
        )

    if ow_all.avg_mfe > pg_all.avg_mfe + 0.1:
        lines.append(
            f"- **OPENING_WINDOW MFE is higher** ({ow_all.avg_mfe:.3f}% vs "
            f"{pg_all.avg_mfe:.3f}%) — entering at OPEN captures a larger favourable range."
        )
    elif pg_all.avg_mfe > ow_all.avg_mfe + 0.1:
        lines.append(
            f"- **POST_GOVERNANCE MFE is higher** ({pg_all.avg_mfe:.3f}% vs "
            f"{ow_all.avg_mfe:.3f}%) — after the opening gap, better setups are available."
        )

    if ow_all.avg_mae > pg_all.avg_mae + 0.1:
        lines.append(
            f"- **OPENING_WINDOW has higher MAE** ({ow_all.avg_mae:.3f}% vs "
            f"{pg_all.avg_mae:.3f}%) — opening entries carry more adverse drawdown risk."
        )
    elif pg_all.avg_mae > ow_all.avg_mae + 0.1:
        lines.append(
            f"- **POST_GOVERNANCE has higher MAE** ({pg_all.avg_mae:.3f}% vs "
            f"{ow_all.avg_mae:.3f}%) — mid-session entries carry higher pullback risk."
        )

    lines += [
        f"",
        f"### Recommendation Action",
        f"",
        f"**Status:** PENDING — requires human review before any action",
        f"",
        f"This is a shadow recommendation. No governance rule changes until:",
        f"1. Live trade evidence accumulated (target: ≥30 live trades per window)",
        f"2. Human review of statistical significance",
        f"3. Explicit APPROVED status in recommendations.db",
        f"",
        f"Stored as `D-REC-002` in `data/recommendations.db` with status PENDING.",
        f"",
        f"---",
        f"",
        f"*Simulation corpus: `replay.db::ohlcv_daily` {ow_all.n:,} day-instances. "
        f"Shadow-mode: zero imports from execution_engine / risk_control / "
        f"decision_ai / opportunity_engine.*",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_d_rec_002(
    min_price:  float = MIN_PRICE,
    min_volume: float = MIN_VOLUME,
    out_dir:    str   = OUT_DIR,
    store:      bool  = True,
    summary:    bool  = False,
) -> str:
    """
    Run the D-REC-002 opening-window analysis.
    Returns the path to the written report.
    """
    run_id   = datetime.now(timezone.utc).strftime("D-REC-002-%Y%m%d")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Load OHLCV simulation rows
    rows = _load_ohlcv(min_price=min_price, min_volume=min_volume)

    # Overall comparison
    ow_all, pg_all = _compute_stats(rows)

    # Gap breakdown
    gap_stats: Dict[str, Tuple[WindowStats, WindowStats]] = {}
    for gc in ("GAP_UP", "FLAT", "GAP_DOWN"):
        gap_stats[gc] = _compute_stats(rows, filter_fn=lambda r, g=gc: r.gap_class == g)

    # Yearly breakdown
    yearly = _yearly_breakdown(rows)

    # Live decisions
    decisions = _load_live_decisions()

    # Verdict
    verdict, narrative = _compute_verdict(ow_all, pg_all)

    if summary:
        print(f"\n{'='*60}")
        print(f"  D-REC-002  Opening Window Advantage")
        print(f"  Simulated trades: {ow_all.n:,}")
        print(f"{'='*60}")
        print(f"  OPENING_WINDOW : {ow_all.summary_line()}")
        print(f"  POST_GOVERNANCE: {pg_all.summary_line()}")
        print(f"  VERDICT: {verdict}")
        print(f"  {narrative}")
        print(f"{'='*60}")

    # Build and write report
    os.makedirs(out_dir, exist_ok=True)
    fname    = f"D_REC_002_{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    out_path = os.path.join(out_dir, fname)
    report   = _build_report(
        ow_all, pg_all, gap_stats, yearly, decisions,
        verdict, narrative, date_str,
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    # Store to recommendations.db
    if store:
        _store_recommendation(verdict, narrative, ow_all, pg_all, run_id)

    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="D-REC-002: Opening Window Advantage shadow analysis"
    )
    parser.add_argument("--min-price",  type=float, default=MIN_PRICE,
                        help=f"Minimum stock price filter (default: {MIN_PRICE})")
    parser.add_argument("--min-volume", type=float, default=MIN_VOLUME,
                        help=f"Minimum daily volume filter (default: {MIN_VOLUME})")
    parser.add_argument("--out",    default=OUT_DIR, help="Output directory for report")
    parser.add_argument("--no-db",  action="store_true",
                        help="Skip writing to recommendations.db")
    parser.add_argument("--summary", action="store_true",
                        help="Print summary to terminal")
    args = parser.parse_args()

    path = run_d_rec_002(
        min_price=args.min_price,
        min_volume=args.min_volume,
        out_dir=args.out,
        store=not args.no_db,
        summary=args.summary or True,
    )
    print(f"\nReport written → {path}")


if __name__ == "__main__":
    _cli()
