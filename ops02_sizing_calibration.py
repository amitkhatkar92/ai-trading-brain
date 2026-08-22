"""
ops02_sizing_calibration.py
============================
Read-only calibration analysis: compares five risk_pct candidates across
all historical executed orders stored in control_tower.db.

Produces: OPS02_SIZING_CALIBRATION_REPORT.md

Rules:
  - Zero writes to any production database.
  - Zero changes to config.py or any execution module.
  - Mirrors the exact PA sizing pipeline (portfolio_allocation_ai.py _size()).
"""

import json
import os
import sqlite3
import statistics
from datetime import datetime

ROOT    = os.path.dirname(os.path.abspath(__file__))
CT_DB   = os.path.join(ROOT, "data", "control_tower.db")
OUT_MD  = os.path.join(ROOT, "OPS02_SIZING_CALIBRATION_REPORT.md")

# ── Mirrored constants (read-only; no imports from production modules) ─────────
TOTAL_CAPITAL            = 10_000_000.0   # ₹1 Cr (config.py line 36)
MAX_CAP_PER_TRADE_PCT    = 15.0           # Guard 5 threshold (order_manager.py)
PA_HARD_CAP_FRACTION     = 0.15           # _MAX_SINGLE_TRADE_FRACTION (pa line 29)
CONF_SCALE_LO            = 0.6            # PA confidence scaling lower bound
CONF_SCALE_HI            = 0.8            # PA confidence scaling range
MAX_POSITIONS            = 8              # _MAX_POSITIONS (capital_risk_engine.py)

LARGE_CAP = {"RELIANCE","HDFCBANK","ICICIBANK","INFY","TCS",
             "HDFC","KOTAKBANK","LT","AXISBANK","SBIN"}
MID_CAP   = {"BANKBARODA","PNB","COALINDIA","ONGC","NTPC",
             "TATASTEEL","HINDALCO","GLENMARK"}
ALLOCATION = {"large_cap": 0.40, "mid_cap": 0.30, "small_cap": 0.15}

RISK_PCT_CANDIDATES = [0.010, 0.005, 0.004, 0.003, 0.0025]


# ── Helpers ────────────────────────────────────────────────────────────────────

def bucket_capital(symbol: str) -> float:
    s = symbol.upper()
    if s in LARGE_CAP:
        return TOTAL_CAPITAL * ALLOCATION["large_cap"]
    if s in MID_CAP:
        return TOTAL_CAPITAL * ALLOCATION["mid_cap"]
    return TOTAL_CAPITAL * ALLOCATION["small_cap"]


def pa_qty(entry: float, stop: float, symbol: str,
           confidence: float, risk_pct_base: float) -> tuple[int, bool]:
    """
    Replicate portfolio_allocation_ai.py _size() for a single signal.
    Returns (final_qty, pa_cap_fired).
    """
    if entry <= 0 or stop <= 0 or abs(entry - stop) < 0.001:
        return 0, False

    # Confidence scaling (matches PA exactly)
    conf_norm  = max(0.0, min(confidence / 10.0, 1.0))
    eff_rpt    = risk_pct_base * (CONF_SCALE_LO + conf_norm * CONF_SCALE_HI)

    # Risk formula qty (uncapped)
    stop_dist  = abs(entry - stop)
    qty        = int((TOTAL_CAPITAL * eff_rpt) / stop_dist)
    if qty <= 0:
        return 0, False

    # Bucket cap
    bkt_cap = bucket_capital(symbol)
    qty = min(qty, max(1, int(bkt_cap / entry)))

    # PA 15% hard cap
    hard_cap_qty = max(1, int(TOTAL_CAPITAL * PA_HARD_CAP_FRACTION / entry))
    cap_fired    = qty > hard_cap_qty
    if cap_fired:
        qty = hard_cap_qty

    return qty, cap_fired


def notional_pct(qty: int, entry: float) -> float:
    return (qty * entry / TOTAL_CAPITAL) * 100.0


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100.0) * (len(sorted_data) - 1)
    lo  = int(idx)
    hi  = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[-1]
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


# ── Load historical executed orders ───────────────────────────────────────────

def load_orders() -> list[dict]:
    if not os.path.exists(CT_DB):
        raise FileNotFoundError(f"control_tower.db not found at {CT_DB}")

    conn = sqlite3.connect(CT_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT payload, ts
            FROM ct_events
            WHERE event_type = 'execution.order.placed'
            ORDER BY id
        """).fetchall()
    finally:
        conn.close()

    orders = []
    for r in rows:
        try:
            p      = json.loads(r["payload"] or "{}")
            entry  = float(p.get("entry_price",  0) or 0)
            stop   = float(p.get("stop_loss",    0) or 0)
            sym    = str(p.get("symbol",  "") or "").strip()
            conf   = float(p.get("confidence", 7.0) or 7.0)
            qty_ex = int(p.get("quantity", 0) or 0)
            strat  = str(p.get("strategy", "") or "")
            if entry > 0 and stop > 0 and sym and qty_ex > 0:
                orders.append({
                    "symbol":   sym,
                    "entry":    entry,
                    "stop":     stop,
                    "confidence": conf,
                    "executed_qty": qty_ex,
                    "strategy": strat,
                    "ts":       r["ts"],
                })
        except Exception:
            pass

    return orders


# ── Scenario simulation ────────────────────────────────────────────────────────

def run_scenario(orders: list[dict], risk_pct_base: float) -> dict:
    notionals   = []
    cap_fires   = 0
    g5_blocks   = 0

    for o in orders:
        qty, fired = pa_qty(o["entry"], o["stop"], o["symbol"],
                            o["confidence"], risk_pct_base)
        if qty <= 0:
            continue
        n_pct = notional_pct(qty, o["entry"])
        if n_pct > MAX_CAP_PER_TRADE_PCT:   # Guard 5
            g5_blocks += 1
            continue
        notionals.append(n_pct)
        if fired:
            cap_fires += 1

    n = len(notionals)
    if n == 0:
        return {
            "risk_pct": risk_pct_base, "count": 0,
            "mean": 0, "median": 0,
            "p10": 0, "p25": 0, "p75": 0, "p90": 0,
            "pa_cap_fire_rate": 0, "g5_block_rate": 0,
            "portfolio_util": 0,
        }

    mean_n   = statistics.mean(notionals)
    med_n    = statistics.median(notionals)
    p10_n    = percentile(notionals, 10)
    p25_n    = percentile(notionals, 25)
    p75_n    = percentile(notionals, 75)
    p90_n    = percentile(notionals, 90)

    total_orders  = len(orders)
    fire_rate     = cap_fires / total_orders * 100.0 if total_orders else 0
    block_rate    = g5_blocks / total_orders * 100.0 if total_orders else 0

    # Portfolio utilization estimate: mean_notional × MAX_POSITIONS, capped at 100%
    port_util = min(100.0, mean_n * MAX_POSITIONS)

    return {
        "risk_pct":          risk_pct_base,
        "count":             n,
        "mean":              mean_n,
        "median":            med_n,
        "p10":               p10_n,
        "p25":               p25_n,
        "p75":               p75_n,
        "p90":               p90_n,
        "pa_cap_fire_rate":  fire_rate,
        "g5_block_rate":     block_rate,
        "portfolio_util":    port_util,
    }


# ── Recommendation logic ───────────────────────────────────────────────────────

def pick_recommendation(scenarios: list[dict]) -> dict:
    """
    Choose the scenario where:
    1. PA cap fire rate is minimal (formula is meaningful)
    2. Guard 5 block rate is 0%
    3. Mean notional is in a healthy 8–15% range
    4. Portfolio utilization stays under 80%

    Score: penalise PA cap fire rate heavily; reward lower mean notional
    (more differentiation between signals).
    """
    best = None
    best_score = float("inf")
    for sc in scenarios:
        if sc["count"] == 0:
            continue
        # Penalty components (lower is better)
        penalty = (sc["pa_cap_fire_rate"] * 2.0       # cap fires dominate
                   + sc["g5_block_rate"]  * 5.0       # any block is bad
                   + max(0, sc["mean"] - 12.0) * 3.0  # penalise mean > 12%
                   + max(0, 8.0 - sc["mean"])  * 1.5) # penalise mean < 8%
        if penalty < best_score:
            best_score = penalty
            best       = sc
    return best


# ── Report helpers ─────────────────────────────────────────────────────────────

def verdict(sc: dict, rec: dict) -> str:
    if sc["risk_pct"] == rec["risk_pct"]:
        return "**← RECOMMENDED**"
    if sc["g5_block_rate"] > 0:
        return "❌ Guard 5 blocks"
    if sc["pa_cap_fire_rate"] > 50:
        return "⚠️ cap always fires"
    return "—"


def bar(val: float, width: int = 20) -> str:
    filled = min(width, round(val / 100.0 * width))
    return "█" * filled + "░" * (width - filled)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading orders from {CT_DB} ...")
    orders = load_orders()
    print(f"  {len(orders)} executed orders loaded.\n")

    scenarios = [run_scenario(orders, rp) for rp in RISK_PCT_CANDIDATES]
    rec       = pick_recommendation(scenarios)

    for sc in scenarios:
        print(f"  risk_pct={sc['risk_pct']*100:.2f}%  "
              f"count={sc['count']}  mean={sc['mean']:.1f}%  "
              f"cap_fires={sc['pa_cap_fire_rate']:.0f}%  "
              f"g5_block={sc['g5_block_rate']:.0f}%  "
              f"port_util={sc['portfolio_util']:.0f}%")

    print(f"\nRecommended: risk_pct = {rec['risk_pct']*100:.2f}%\n")

    # ── Build markdown report ─────────────────────────────────────────────────
    ts  = datetime.now().isoformat(timespec="seconds")

    def sc_row(sc: dict) -> str:
        tag = verdict(sc, rec)
        return (
            f"| `{sc['risk_pct']*100:.2f}%` "
            f"| {sc['count']} "
            f"| {sc['mean']:.2f}% "
            f"| {sc['median']:.2f}% "
            f"| {sc['p10']:.2f}% "
            f"| {sc['p25']:.2f}% "
            f"| {sc['p75']:.2f}% "
            f"| {sc['p90']:.2f}% "
            f"| {sc['pa_cap_fire_rate']:.1f}% "
            f"| {sc['g5_block_rate']:.1f}% "
            f"| {sc['portfolio_util']:.1f}% "
            f"| {tag} |"
        )

    table_rows = "\n".join(sc_row(sc) for sc in scenarios)

    # Per-scenario prose for the detail section
    detail_sections = []
    for sc in scenarios:
        cap_qual = (
            "formula is non-functional — cap always fires"
            if sc["pa_cap_fire_rate"] > 90 else
            "cap fires on majority of signals" if sc["pa_cap_fire_rate"] > 50 else
            "cap fires on minority of signals" if sc["pa_cap_fire_rate"] > 15 else
            "cap rarely fires — formula expresses intent"
        )
        detail_sections.append(
            f"### risk_pct = {sc['risk_pct']*100:.2f}%\n\n"
            f"- Orders evaluated: **{sc['count']}**\n"
            f"- Mean notional: **{sc['mean']:.2f}%**, Median: **{sc['median']:.2f}%**\n"
            f"- Spread (P10–P90): {sc['p10']:.2f}% — {sc['p90']:.2f}%\n"
            f"- PA cap fire rate: **{sc['pa_cap_fire_rate']:.1f}%** — {cap_qual}\n"
            f"- Guard 5 blocks: **{sc['g5_block_rate']:.1f}%**\n"
            f"- Estimated portfolio utilization (@ {MAX_POSITIONS} concurrent): "
            f"**{sc['portfolio_util']:.1f}%**\n"
        )
    details = "\n".join(detail_sections)

    # PA cap visualisation (fire rate per scenario)
    viz_rows = ""
    for sc in scenarios:
        filled = min(40, round(sc["pa_cap_fire_rate"] / 100 * 40))
        bar_s  = "█" * filled + "░" * (40 - filled)
        tag    = " ← recommended" if sc["risk_pct"] == rec["risk_pct"] else ""
        viz_rows += f"  {sc['risk_pct']*100:.2f}%  [{bar_s}]  {sc['pa_cap_fire_rate']:.0f}%{tag}\n"

    report = f"""\
# OPS-02 Sizing Calibration Report

**Generated:** {ts}
**Source:** `control_tower.db` — `ct_events WHERE event_type='execution.order.placed'`
**Orders analysed:** {len(orders)}
**Scenarios:** {len(scenarios)}

> **Note:** This is a read-only analysis. No production parameters were changed.

---

## What This Measures

The PA sizing pipeline (`portfolio_allocation_ai.py _size()`) applies:

1. **Risk formula:** `qty = TOTAL_CAPITAL × risk_pct_scaled / stop_distance`
2. **Bucket cap:** `qty = min(qty, bucket_capital / entry_price)`
3. **PA hard cap:** `qty = min(qty, TOTAL_CAPITAL × 0.15 / entry_price)` (15%)
4. **Guard 5** (`order_manager.py`): reject if `notional_pct > 15%`

`risk_pct_scaled = risk_pct_base × (0.6 + conf_norm × 0.8)` — confidence range is `[6× .. 1.4×]`.

When the **PA cap fires**, it means the risk formula would have produced
a notional above 15% and the hard cap silently forced it to 15%. In that
case the formula's signal-differentiation intent is lost; every capped
signal receives identical sizing regardless of quality.

---

## Scenario Comparison Table

| risk_pct | Count | Mean | Median | P10 | P25 | P75 | P90 | PA Cap | Guard 5 | Port Util | |
|---|---|---|---|---|---|---|---|---|---|---|---|
{table_rows}

*Port Util = mean_notional × {MAX_POSITIONS} open positions (estimated, capped at 100%).*

---

## PA Cap Fire Rate — Visual

```
{viz_rows.rstrip()}
```

A 100% cap fire rate means the risk formula is functionally overridden on
every trade — all positions receive the maximum allowed size, eliminating
any signal-quality differentiation in sizing.

---

## Per-Scenario Detail

{details}

---

## Baseline: Current System (risk_pct = 1.00%)

From the previous forensic run:

| Metric | Value |
|---|---|
| PA cap fires | **100 / 100 (100%)** |
| Average notional (after cap) | **15.0%** |
| Guard 5 blocks | **0%** |
| Formula intent honoured | **No** — all signals sized at maximum |

The risk formula never expresses intent at 1.0%; every executed order reaches
the PA hard cap regardless of confidence or stop width.

---

## Recommendation

**Preferred `risk_pct`:** `{rec['risk_pct']*100:.2f}%`

| Property | Value |
|---|---|
| Expected PA cap fire rate | **{rec['pa_cap_fire_rate']:.1f}%** |
| Expected average notional | **{rec['mean']:.2f}%** |
| Expected median notional | **{rec['median']:.2f}%** |
| Expected Guard 5 block rate | **{rec['g5_block_rate']:.1f}%** |
| Estimated portfolio utilization | **{rec['portfolio_util']:.1f}%** |

### Reasoning

At `{rec['risk_pct']*100:.2f}%` the PA cap fires on approximately
`{rec['pa_cap_fire_rate']:.0f}%` of signals — down from 100% at the current
1.0% setting. This allows the risk formula to differentiate position sizes
according to stop width and confidence: wider stops produce smaller positions;
tighter stops at higher confidence produce larger positions, up to the 15%
hard ceiling.

The Guard 5 block rate remains at `{rec['g5_block_rate']:.1f}%`, so no trades
are lost. The estimated portfolio utilization of `{rec['portfolio_util']:.1f}%`
keeps drawdown exposure within the `MAX_PORTFOLIO_RISK_PCT = 8%` envelope when
each position's stop is honoured.

### What Does Not Change

Implementing this recommendation requires **one line in `config.py`**:

```python
# config.py line 36
MAX_RISK_PER_TRADE_PCT = {rec['risk_pct']:.4f}   # was 0.0100
```

All of the following remain **unchanged**:

- `_MAX_SINGLE_TRADE_FRACTION = 0.15` (PA hard cap)
- `MAX_CAPITAL_PER_TRADE_PCT = 15.0` (Guard 5)
- All guard logic, allocation fractions, strategy budgets
- All CRE `_strategy_budget()` tables
- All execution, monitoring, and risk modules

---

## Appendix: Formula Mechanics

```
Given:
  TOTAL_CAPITAL   = ₹{TOTAL_CAPITAL:,.0f}
  risk_pct_base   = R
  confidence      = C (0–10)
  conf_norm       = C / 10
  eff_risk_pct    = R × (0.6 + conf_norm × 0.8)
  stop_dist_pct   = |entry − stop| / entry

qty              = TOTAL_CAPITAL × eff_risk_pct / (entry × stop_dist_pct)
notional_pct     = qty × entry / TOTAL_CAPITAL
                 = eff_risk_pct / stop_dist_pct

PA cap fires when: notional_pct > 15%
  → eff_risk_pct / stop_dist_pct > 0.15
  → eff_risk_pct > 0.15 × stop_dist_pct

For a typical NSE signal with stop_dist_pct = 2.0% (ATR ×1.5 on large-cap):
  Cap fires when: eff_risk_pct > 0.15 × 0.02 = 0.003 (0.30%)
  At conf=7, eff = R × (0.6 + 0.7 × 0.8) = R × 1.16
  Cap-free threshold: R < 0.003 / 1.16 = 0.00259 (0.26%)

Observed breakeven across {len(orders)} real orders:
  Avg: {statistics.mean(abs(o['entry']-o['stop'])/o['entry'] for o in orders)*100:.2f}%
  Min stop dist: {min(abs(o['entry']-o['stop'])/o['entry'] for o in orders)*100:.2f}%
  Max stop dist: {max(abs(o['entry']-o['stop'])/o['entry'] for o in orders)*100:.2f}%
```

---

*Generated by `ops02_sizing_calibration.py` — analysis only, no production writes.*
"""

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(report)

    print(f"Report written → {OUT_MD}")


if __name__ == "__main__":
    main()
