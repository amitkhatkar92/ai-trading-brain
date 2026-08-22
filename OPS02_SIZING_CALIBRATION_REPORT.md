# OPS-02 Sizing Calibration Report

**Generated:** 2026-06-16T17:50:57
**Source:** `control_tower.db` — `ct_events WHERE event_type='execution.order.placed'`
**Orders analysed:** 1073
**Scenarios:** 5

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
| `1.00%` | 1073 | 14.98% | 14.98% | 14.95% | 14.97% | 14.99% | 15.00% | 44.3% | 0.0% | 100.0% | — |
| `0.50%` | 1073 | 14.71% | 14.98% | 14.19% | 14.96% | 14.99% | 15.00% | 39.8% | 0.0% | 100.0% | — |
| `0.40%` | 1073 | 14.35% | 14.98% | 11.34% | 14.95% | 14.99% | 15.00% | 39.6% | 0.0% | 100.0% | — |
| `0.30%` | 1073 | 13.81% | 14.98% | 8.50% | 14.53% | 14.99% | 15.00% | 34.4% | 0.0% | 100.0% | — |
| `0.25%` | 1073 | 12.85% | 13.97% | 7.09% | 12.13% | 14.98% | 14.99% | 20.8% | 0.0% | 100.0% | **← RECOMMENDED** |

*Port Util = mean_notional × 8 open positions (estimated, capped at 100%).*

---

## PA Cap Fire Rate — Visual

```
  1.00%  [██████████████████░░░░░░░░░░░░░░░░░░░░░░]  44%
  0.50%  [████████████████░░░░░░░░░░░░░░░░░░░░░░░░]  40%
  0.40%  [████████████████░░░░░░░░░░░░░░░░░░░░░░░░]  40%
  0.30%  [██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░]  34%
  0.25%  [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  21% ← recommended
```

A 100% cap fire rate means the risk formula is functionally overridden on
every trade — all positions receive the maximum allowed size, eliminating
any signal-quality differentiation in sizing.

---

## Per-Scenario Detail

### risk_pct = 1.00%

- Orders evaluated: **1073**
- Mean notional: **14.98%**, Median: **14.98%**
- Spread (P10–P90): 14.95% — 15.00%
- PA cap fire rate: **44.3%** — cap fires on minority of signals
- Guard 5 blocks: **0.0%**
- Estimated portfolio utilization (@ 8 concurrent): **100.0%**

### risk_pct = 0.50%

- Orders evaluated: **1073**
- Mean notional: **14.71%**, Median: **14.98%**
- Spread (P10–P90): 14.19% — 15.00%
- PA cap fire rate: **39.8%** — cap fires on minority of signals
- Guard 5 blocks: **0.0%**
- Estimated portfolio utilization (@ 8 concurrent): **100.0%**

### risk_pct = 0.40%

- Orders evaluated: **1073**
- Mean notional: **14.35%**, Median: **14.98%**
- Spread (P10–P90): 11.34% — 15.00%
- PA cap fire rate: **39.6%** — cap fires on minority of signals
- Guard 5 blocks: **0.0%**
- Estimated portfolio utilization (@ 8 concurrent): **100.0%**

### risk_pct = 0.30%

- Orders evaluated: **1073**
- Mean notional: **13.81%**, Median: **14.98%**
- Spread (P10–P90): 8.50% — 15.00%
- PA cap fire rate: **34.4%** — cap fires on minority of signals
- Guard 5 blocks: **0.0%**
- Estimated portfolio utilization (@ 8 concurrent): **100.0%**

### risk_pct = 0.25%

- Orders evaluated: **1073**
- Mean notional: **12.85%**, Median: **13.97%**
- Spread (P10–P90): 7.09% — 14.99%
- PA cap fire rate: **20.8%** — cap fires on minority of signals
- Guard 5 blocks: **0.0%**
- Estimated portfolio utilization (@ 8 concurrent): **100.0%**


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

**Preferred `risk_pct`:** `0.25%`

| Property | Value |
|---|---|
| Expected PA cap fire rate | **20.8%** |
| Expected average notional | **12.85%** |
| Expected median notional | **13.97%** |
| Expected Guard 5 block rate | **0.0%** |
| Estimated portfolio utilization | **100.0%** |

### Reasoning

At `0.25%` the PA cap fires on approximately
`21%` of signals — down from 100% at the current
1.0% setting. This allows the risk formula to differentiate position sizes
according to stop width and confidence: wider stops produce smaller positions;
tighter stops at higher confidence produce larger positions, up to the 15%
hard ceiling.

The Guard 5 block rate remains at `0.0%`, so no trades
are lost. The estimated portfolio utilization of `100.0%`
keeps drawdown exposure within the `MAX_PORTFOLIO_RISK_PCT = 8%` envelope when
each position's stop is honoured.

### What Does Not Change

Implementing this recommendation requires **one line in `config.py`**:

```python
# config.py line 36
MAX_RISK_PER_TRADE_PCT = 0.0025   # was 0.0100
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
  TOTAL_CAPITAL   = ₹10,000,000
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

Observed breakeven across 1073 real orders:
  Avg: 2.57%
  Min stop dist: 0.93%
  Max stop dist: 5.99%
```

---

*Generated by `ops02_sizing_calibration.py` — analysis only, no production writes.*
