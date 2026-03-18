"""
Equity Curve Stress Test (ECST)
================================
Answers the critical question: *Is the system's profitability spread evenly
across all trades, or does it depend on a handful of outliers?*

A real edge survives the removal of its best trades.  A lucky streak or
curve-fitted system collapses immediately.

Algorithm
---------
1. Load per-trade PnL from  data/replay_trades.json  (written by run_replay.py).
2. Sort trades by PnL descending.
3. Compute baseline metrics (all trades).
4. Stress scenarios:
   A — remove top 5 most profitable trades
   B — remove top 10 most profitable trades
   C — remove top 15 % of profitable trades (rounded up)
5. Recalculate metrics per scenario.
6. Apply robustness verdict on scenario B.
7. Print structured console report.
8. Save  ECST_REPORT.md  to the project root.

Usage
-----
    # From project root:
    python simulation_replay/analytics/equity_curve_stress_test.py

    # From the analytics folder:
    python equity_curve_stress_test.py
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Resolve project root regardless of CWD or invocation style ──────────────
_THIS_FILE = Path(__file__).resolve()

# ECST lives at  <root>/simulation_replay/analytics/equity_curve_stress_test.py
# so root is two levels up.
PROJECT_ROOT = _THIS_FILE.parent.parent.parent

TRADES_PATH = PROJECT_ROOT / "data" / "replay_trades.json"
REPORT_PATH = PROJECT_ROOT / "ECST_REPORT.md"

# Robustness gate: PF after removing top-10 trades must exceed this
ROBUST_PF_GATE = 1.5

# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    symbol:       str
    strategy:     str
    direction:    str
    entry:        float
    sl:           float
    target:       float
    qty:          int
    pnl:          float
    trading_date: str
    r_multiple:   float = 0.0   # computed on load

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TradeRecord":
        entry  = float(d.get("entry", 0.0) or d.get("entry_price", 0.0) or 0.0)
        sl     = float(d.get("sl", 0.0)    or d.get("stop_loss",   0.0) or 0.0)
        target = float(d.get("target", 0.0) or d.get("target_price", 0.0) or 0.0)
        qty    = max(int(d.get("qty", 1)   or d.get("quantity", 1) or 1), 1)
        pnl    = float(d.get("pnl", 0.0)   or 0.0)
        dirn   = str(d.get("direction", "BUY")).upper()
        date   = str(d.get("trading_date", d.get("date", "unknown")))
        sym    = str(d.get("symbol", ""))
        strat  = str(d.get("strategy", ""))

        # R-multiple: pnl / (risk_per_trade)
        risk_per_share = abs(entry - sl)
        risk_total     = risk_per_share * qty
        r_mult = round(pnl / risk_total, 3) if risk_total > 0.01 else 0.0

        return cls(
            symbol=sym, strategy=strat, direction=dirn,
            entry=entry, sl=sl, target=target, qty=qty,
            pnl=pnl, trading_date=date, r_multiple=r_mult,
        )


@dataclass
class EcstMetrics:
    label:         str
    n_trades:      int       = 0
    total_pnl:     float     = 0.0
    gross_profit:  float     = 0.0
    gross_loss:    float     = 0.0
    wins:          int       = 0
    removed:       int       = 0       # trades dropped in this scenario
    trades_detail: List[TradeRecord] = field(default_factory=list)

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return round(self.gross_profit / abs(self.gross_loss), 2)

    @property
    def win_rate(self) -> float:
        return round(self.wins / self.n_trades * 100, 1) if self.n_trades else 0.0

    @property
    def avg_r(self) -> float:
        if not self.trades_detail:
            return 0.0
        return round(sum(t.r_multiple for t in self.trades_detail) / len(self.trades_detail), 3)

    @property
    def total_return_pct(self) -> float:
        """Return as % of ₹10L default capital (matches replay config)."""
        from_config = _load_total_capital()
        return round(self.total_pnl / from_config * 100, 2) if from_config else 0.0


def _load_total_capital() -> float:
    """Read TOTAL_CAPITAL from config without importing the full project tree."""
    config_path = PROJECT_ROOT / "config.py"
    try:
        for line in config_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TOTAL_CAPITAL") and "=" in line:
                val_part = line.split("=", 1)[1].split("#")[0].strip()
                # May be expression like float(os.getenv("TOTAL_CAPITAL", 1_000_000))
                # Extract numeric default
                import re
                nums = re.findall(r"[\d_]+", val_part)
                for n in reversed(nums):
                    try:
                        return float(n.replace("_", ""))
                    except ValueError:
                        continue
    except Exception:
        pass
    return 1_000_000.0   # fallback


# ── Core logic ────────────────────────────────────────────────────────────────

def _compute_metrics(label: str, trades: List[TradeRecord], removed: int = 0) -> EcstMetrics:
    m = EcstMetrics(label=label, removed=removed, trades_detail=trades)
    for t in trades:
        m.n_trades  += 1
        m.total_pnl += t.pnl
        if t.pnl > 0:
            m.wins        += 1
            m.gross_profit += t.pnl
        else:
            m.gross_loss   += abs(t.pnl)
    return m


def run_ecst(trades: List[TradeRecord]) -> Dict[str, EcstMetrics]:
    """
    Run all stress scenarios and return a dict of label → EcstMetrics.
    """
    if not trades:
        raise ValueError("No trades found in replay_trades.json — run a replay first.")

    # Sort by PnL descending; only profitable trades participate in removal
    sorted_by_profit = sorted(trades, key=lambda t: t.pnl, reverse=True)
    profitable = [t for t in sorted_by_profit if t.pnl > 0]

    results: Dict[str, EcstMetrics] = {}

    # Baseline
    results["Baseline"] = _compute_metrics("Baseline", trades)

    # Scenario A — remove top 5
    n_a = min(5, len(profitable))
    drop_a = set(id(t) for t in profitable[:n_a])
    results["Remove_Top_5"] = _compute_metrics(
        "Remove top 5 trades",
        [t for t in trades if id(t) not in drop_a],
        removed=n_a,
    )

    # Scenario B — remove top 10
    n_b = min(10, len(profitable))
    drop_b = set(id(t) for t in profitable[:n_b])
    results["Remove_Top_10"] = _compute_metrics(
        "Remove top 10 trades",
        [t for t in trades if id(t) not in drop_b],
        removed=n_b,
    )

    # Scenario C — remove top 15 % of profitable trades
    n_c = max(1, math.ceil(len(profitable) * 0.15))
    drop_c = set(id(t) for t in profitable[:n_c])
    results["Remove_Top_15pct"] = _compute_metrics(
        f"Remove top 15% winners ({n_c} trades)",
        [t for t in trades if id(t) not in drop_c],
        removed=n_c,
    )

    return results


def robustness_verdict(results: Dict[str, EcstMetrics]) -> str:
    pf_b = results["Remove_Top_10"].profit_factor
    if pf_b == float("inf"):
        return "ROBUST EDGE"
    return "ROBUST EDGE" if pf_b >= ROBUST_PF_GATE else "EDGE DEPENDS ON OUTLIERS"


# ── Reporting ─────────────────────────────────────────────────────────────────

def _pf_str(pf: float) -> str:
    return "∞" if pf == float("inf") else f"{pf:.2f}"


def _verdict_emoji(verdict: str) -> str:
    return "✅" if verdict == "ROBUST EDGE" else "⚠️"


def format_console_report(results: Dict[str, EcstMetrics], verdict: str, capital: float) -> str:
    base = results["Baseline"]
    lines = [
        "",
        "=" * 60,
        "  EQUITY CURVE STRESS TEST (ECST)",
        "=" * 60,
        "",
        f"  Capital base : ₹{capital:,.0f}",
        f"  Trades total : {base.n_trades}",
        "",
        "  Baseline:",
        f"    trades       = {base.n_trades}",
        f"    total return = {base.total_return_pct:+.2f}%  (₹{base.total_pnl:,.0f})",
        f"    profit factor= {_pf_str(base.profit_factor)}",
        f"    win rate     = {base.win_rate:.1f}%",
        f"    avg R        = {base.avg_r:+.3f}R",
        "",
    ]

    scenarios = [
        ("Remove_Top_5",    "Remove top 5 trades"),
        ("Remove_Top_10",   "Remove top 10 trades"),
        ("Remove_Top_15pct", results["Remove_Top_15pct"].label),
    ]
    for key, label in scenarios:
        m = results[key]
        lines += [
            f"  {label}:  (dropped {m.removed})",
            f"    trades       = {m.n_trades}",
            f"    total return = {m.total_return_pct:+.2f}%  (₹{m.total_pnl:,.0f})",
            f"    profit factor= {_pf_str(m.profit_factor)}",
            f"    win rate     = {m.win_rate:.1f}%",
            f"    avg R        = {m.avg_r:+.3f}R",
            "",
        ]

    pf_b = results["Remove_Top_10"].profit_factor
    v_emoji = _verdict_emoji(verdict)
    lines += [
        "-" * 60,
        f"  Robustness gate : PF after top-10 removal ≥ {ROBUST_PF_GATE}",
        f"  PF after top-10 : {_pf_str(pf_b)}",
        f"  Verdict         : {v_emoji}  {verdict}",
        "=" * 60,
        "",
    ]
    return "\n".join(lines)


def format_markdown_report(
    results: Dict[str, EcstMetrics],
    verdict: str,
    capital: float,
    trades: List[TradeRecord],
) -> str:
    base = results["Baseline"]
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    v_emoji = _verdict_emoji(verdict)
    pf_b = results["Remove_Top_10"].profit_factor

    # Top-10 profitable trades table
    top10 = sorted(trades, key=lambda t: t.pnl, reverse=True)[:10]

    md = f"""# Equity Curve Stress Test Report

**Generated :** {now}
**Capital base :** ₹{capital:,.0f}
**Data source :** data/replay_trades.json

---

## 1. Baseline (all {base.n_trades} trades)

| Metric | Value |
|--------|-------|
| Trades | {base.n_trades} |
| Total PnL | ₹{base.total_pnl:,.0f} |
| Total Return | {base.total_return_pct:+.2f}% |
| Profit Factor | {_pf_str(base.profit_factor)} |
| Win Rate | {base.win_rate:.1f}% |
| Avg R-multiple | {base.avg_r:+.3f}R |

---

## 2. Stress Scenarios

| Scenario | Trades | Dropped | Return | PF | Win Rate | Avg R |
|----------|--------|---------|--------|----|----------|-------|
| **Baseline** | {base.n_trades} | 0 | {base.total_return_pct:+.2f}% | {_pf_str(base.profit_factor)} | {base.win_rate:.1f}% | {base.avg_r:+.3f}R |
"""
    scenarios = [
        ("Remove_Top_5",     "Remove top 5 trades"),
        ("Remove_Top_10",    "Remove top 10 trades"),
        ("Remove_Top_15pct", results["Remove_Top_15pct"].label),
    ]
    for key, label in scenarios:
        m = results[key]
        md += (
            f"| {label} | {m.n_trades} | {m.removed} "
            f"| {m.total_return_pct:+.2f}% | {_pf_str(m.profit_factor)} "
            f"| {m.win_rate:.1f}% | {m.avg_r:+.3f}R |\n"
        )

    md += f"""
---

## 3. Top 10 Most Profitable Trades

| # | Date | Symbol | Strategy | PnL | R-multiple |
|---|------|--------|----------|-----|-----------|
"""
    for i, t in enumerate(top10, 1):
        md += f"| {i} | {t.trading_date} | {t.symbol} | {t.strategy} | ₹{t.pnl:,.0f} | {t.r_multiple:+.2f}R |\n"

    # Concentration analysis
    top5_pnl  = sum(t.pnl for t in top10[:5])
    top10_pnl = sum(t.pnl for t in top10)
    total_profit = base.gross_profit
    top5_conc  = (top5_pnl  / total_profit * 100) if total_profit > 0 else 0.0
    top10_conc = (top10_pnl / total_profit * 100) if total_profit > 0 else 0.0

    md += f"""
---

## 4. Profit Concentration Analysis

| Bucket | Gross Profit | % of Total Profit |
|--------|-------------|-------------------|
| Top 5 trades  | ₹{top5_pnl:,.0f}  | {top5_conc:.1f}% |
| Top 10 trades | ₹{top10_pnl:,.0f} | {top10_conc:.1f}% |
| All winners   | ₹{total_profit:,.0f} | 100.0% |

> **Healthy distribution:** top-5 trades should contribute < 40% of gross profit.
> High concentration (> 60%) signals outlier dependence.

---

## 5. Robustness Verdict

| Gate | Requirement | Actual | Pass? |
|------|------------|--------|-------|
| PF after removing top-10 | ≥ {ROBUST_PF_GATE} | {_pf_str(pf_b)} | {"✅ PASS" if pf_b >= ROBUST_PF_GATE else "❌ FAIL"} |

### {v_emoji} {verdict}

"""
    if verdict == "ROBUST EDGE":
        md += (
            "> The strategy's edge is distributed across the trade population.  "
            "Removing the 10 best trades still leaves a profitable system "
            f"(PF {_pf_str(pf_b)} ≥ {ROBUST_PF_GATE}).  "
            "Safe to proceed to paper monitoring.\n"
        )
    else:
        md += (
            "> **Warning:** The system's profitability is heavily concentrated in "
            "a small number of outlier trades.  After removing the top 10, "
            f"PF falls to {_pf_str(pf_b)} (below gate {ROBUST_PF_GATE}).  "
            "Consider widening the strategy universe or increasing trade frequency "
            "before proceeding to live capital.\n"
        )

    md += "\n---\n\n*Generated by equity_curve_stress_test.py — read-only analysis, no trading logic modified.*\n"
    return md


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # ── 1. Load trades ────────────────────────────────────────────────────────
    if not TRADES_PATH.exists():
        print(f"\n[ECST] ERROR: {TRADES_PATH} not found.")
        print("       Run a replay first:  python simulation_replay/run_replay.py --days 180")
        sys.exit(1)

    raw = json.loads(TRADES_PATH.read_text(encoding="utf-8"))
    if not raw:
        print("[ECST] No trades in replay_trades.json — nothing to analyse.")
        sys.exit(0)

    trades = [TradeRecord.from_dict(d) for d in raw]
    # Filter out zero-entry records (safety)
    trades = [t for t in trades if t.entry > 0 and t.sl > 0]

    capital = _load_total_capital()

    print(f"[ECST] Loaded {len(trades)} trades from {TRADES_PATH.name}")
    print(f"[ECST] Capital base: ₹{capital:,.0f}")

    # ── 2. Run stress scenarios ───────────────────────────────────────────────
    results = run_ecst(trades)
    verdict = robustness_verdict(results)

    # ── 3. Console report ─────────────────────────────────────────────────────
    console_text = format_console_report(results, verdict, capital)
    print(console_text)

    # ── 4. Markdown report ────────────────────────────────────────────────────
    md_text = format_markdown_report(results, verdict, capital, trades)
    REPORT_PATH.write_text(md_text, encoding="utf-8")
    print(f"[ECST] Report saved → {REPORT_PATH}")


if __name__ == "__main__":
    main()
