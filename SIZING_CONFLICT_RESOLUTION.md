# SIZING CONFLICT RESOLUTION

**Date:** 2026-06-16T17:42:46
**Status:** Evidence-based analysis complete. Recommendation: parameter change.

---

## Problem Statement

There is a persistent mathematical incompatibility between how position sizing is
computed (Layers 6+7) and what Execution Guard 5 permits (Layer 11). This produces
a **structural 100% block rate** unless mitigated by a secondary hard cap.

| Component | File | Parameter | Current Value |
|---|---|---|---|
| `PortfolioAllocationAI._size()` | `risk_control/portfolio_allocation_ai.py` | `MAX_RISK_PER_TRADE_PCT` | **1.0%** of ₹1Cr |
| Confidence scaling | same | `0.6 + conf_norm × 0.8` | Effective 0.6%–1.4% at conf 6–10 |
| PA hard cap (secondary) | same | `_MAX_SINGLE_TRADE_FRACTION` | 15% |
| Guard 5 | `execution_engine/order_manager.py` | `MAX_CAPITAL_PER_TRADE_PCT` | **15.0%** |
| Observed result (pre-cap) | — | notional from formula | **50–2000% of capital** |
| Observed result (post-cap) | — | notional after PA 15% cap | exactly 15% |

---

## Mathematical Proof of Conflict

The sizing formula is:

```
qty              = (TOTAL_CAPITAL × risk_pct_scaled) / stop_distance
notional_pct     = qty × entry / TOTAL_CAPITAL
                 = risk_pct_scaled × (entry / stop_distance)
                 = risk_pct_scaled / stop_dist_pct          ← stop_dist as % of entry
```

Guard 5 passes only when: `notional_pct ≤ 15%`

Therefore the breakeven risk_pct is:

```
risk_pct_breakeven = 15% × stop_dist_pct
```

**Worked example (HDFCBANK, stop = 2% of entry):**

| risk_pct | Formula qty | Notional % | Guard 5 |
|---|---|---|---|
| 1.0% (current) | (10M × 1.0%) / (1720 × 2%) = 2,907 | **2,907 × 1720 / 10M = 500%** | ❌ BLOCKED |
| 0.5% | 1,453 | 250% | ❌ BLOCKED |
| 0.3% | 872 | 150% | ❌ BLOCKED |
| 0.030% (breakeven) | 87 | **15.0%** | ✅ PASSES |

The PA 15% hard cap (`_MAX_SINGLE_TRADE_FRACTION = 0.15`) always fires — silently
rescuing Guard 5 — but the risk formula's *intent* is permanently overridden.
The system always trades at maximum allowed size regardless of signal quality.

### Why the PA Hard Cap Creates a Secondary Problem

At `risk_pct = 1%`, the formula would produce 500% notional on HDFCBANK.
PA's cap forces this down to exactly 15% (₹15L notional on a ₹1Cr account).
But the intended risk at 2% stop on 15% notional = `15% × 2% = 0.30%` — which
is exactly what Scenario C achieves **directly, without the cap ever firing.**

The cap acts as a Band-Aid rather than fixing the underlying formula alignment.

---

## Empirical Analysis — 100 Signals

| Metric | Value |
|---|---|
| Signals analysed | 100 (100 from CT logs, 0 synthetic representative) |
| Uncapped formula: avg notional | **59%** |
| PA-capped output: avg notional | **15.0%** |
| PA cap fires rate | **100/100 (100%)** |
| Guard 5 would block (if uncapped) | **100/100 (100%)** |
| Guard 5 blocks (after PA cap) | **0/100 (0%)** |

**Breakeven `risk_pct` to pass Guard 5 directly (no PA cap needed):**
- Average across all signals: **0.365%**
- Minimum (tightest stop): **0.215%**
- Maximum (widest stop): **0.876%**

The current `risk_pct = 1.0%` exceeds the breakeven for every signal in the universe.
A 1% risk_pct can never pass Guard 5 without the PA hard cap overriding the formula.

### By Stop Distance Category

| Stop Width | Signals | Uncapped Notional% | PA-Capped% | Uncapped Block Rate | Breakeven risk_pct |
|---|---|---|---|---|---|
| Normal (1.0–1.5%) | 3 | 97% | 15.0% | 100% | 0.217% |
| Very Wide (>2.5%) | 31 | 46% | 15.0% | 100% | 0.466% |
| Wide   (1.5–2.5%) | 66 | 63% | 15.0% | 100% | 0.324% |


---

## Signal Sample (first 25 unique symbol/strategy pairs)

*Showing uncapped formula output vs. what actually reaches Guard 5 after PA's 15% cap.*

| Symbol | Strategy | Entry | Stop% | Uncapped Notional% | PA-Capped Notional% | PA Cap? | Guard 5 |
|---|---|---|---|---|---|---|---|
| ULTRACEMCO | Mean_Reversion_RSI_H | ₹12,521 | 2.48% | **46%** | 14.9% | ⚠️ FIRES | ✅ |
| ULTRACEMCO | Momentum_Retest | ₹13,041 | 2.38% | **59%** | 15.0% | ⚠️ FIRES | ✅ |
| BRITANNIA | Mean_Reversion_RSI_H | ₹6,162 | 4.41% | **30%** | 15.0% | ⚠️ FIRES | ✅ |
| TITAN | Mean_Reversion_RSI_H | ₹4,236 | 4.76% | **28%** | 15.0% | ⚠️ FIRES | ✅ |
| BRITANNIA | EDG_MACRO__78_EE0000 | ₹6,019 | 2.20% | **59%** | 15.0% | ⚠️ FIRES | ✅ |
| TCS | Momentum_Retest | ₹3,225 | 2.50% | **56%** | 15.0% | ⚠️ FIRES | ✅ |
| TCS | Trend_Pullback | ₹3,102 | 2.51% | **48%** | 15.0% | ⚠️ FIRES | ✅ |
| GRASIM | Trend_Pullback | ₹2,810 | 1.95% | **62%** | 15.0% | ⚠️ FIRES | ✅ |
| BRITANNIA | Trend_Pullback | ₹5,906 | 2.71% | **44%** | 14.9% | ⚠️ FIRES | ✅ |
| LT | Trend_Pullback | ₹4,025 | 2.38% | **51%** | 15.0% | ⚠️ FIRES | ✅ |
| BRITANNIA | Momentum_Retest | ₹6,130 | 2.69% | **52%** | 15.0% | ⚠️ FIRES | ✅ |
| GRASIM | Momentum_Retest | ₹2,849 | 2.36% | **59%** | 15.0% | ⚠️ FIRES | ✅ |
| LT | Momentum_Retest | ₹4,150 | 2.49% | **56%** | 15.0% | ⚠️ FIRES | ✅ |
| LT | Mean_Reversion_RSI_H | ₹4,140 | 1.58% | **84%** | 15.0% | ⚠️ FIRES | ✅ |
| M&M | Momentum_Retest | ₹3,709 | 2.11% | **66%** | 15.0% | ⚠️ FIRES | ✅ |
| M&M | Trend_Pullback | ₹3,660 | 2.54% | **47%** | 15.0% | ⚠️ FIRES | ✅ |
| MARUTI | Momentum_Retest | ₹16,585 | 2.75% | **51%** | 14.9% | ⚠️ FIRES | ✅ |
| TITAN | Momentum_Retest | ₹3,934 | 2.49% | **56%** | 15.0% | ⚠️ FIRES | ✅ |
| TITAN | Trend_Pullback | ₹3,849 | 2.59% | **46%** | 15.0% | ⚠️ FIRES | ✅ |
| ULTRACEMCO | Trend_Pullback | ₹11,617 | 2.44% | **49%** | 15.0% | ⚠️ FIRES | ✅ |
| BRITANNIA | Breakout_Volume_RSI_ | ₹6,158 | 2.75% | **49%** | 15.0% | ⚠️ FIRES | ✅ |
| MARUTI | Trend_Pullback | ₹16,186 | 2.29% | **52%** | 14.9% | ⚠️ FIRES | ✅ |
| HINDUNILVR | Momentum_Retest | ₹2,581 | 2.56% | **55%** | 15.0% | ⚠️ FIRES | ✅ |
| LT | EDG_MACRO__78_EE0000 | ₹3,668 | 1.80% | **73%** | 15.0% | ⚠️ FIRES | ✅ |
| ULTRACEMCO | EDG_MACRO__78_EE0000 | ₹12,765 | 1.81% | **77%** | 14.9% | ⚠️ FIRES | ✅ |


---

## Scenario Simulations

All 100 signals. `TOTAL_CAPITAL = ₹10,000,000`.
"PA Cap fires" = PA's 15% hard cap overrides the risk formula output.
"Guard 5 block" = trade rejected by `execute()` after PA processes it.

| Scenario | risk_pct | Guard 5 cap | Avg Notional | Avg Risk-at-Stop | Guard 5 Block | PA Cap Fires | Result | PA Cap |
|---|---|---|---|---|---|---|---|---|
| **A: risk_pct = 1.0% (current)** | 1.0% | 15% | 15.0% | 0.364% | 0% | 34% | ✅ | — sometimes |
| **B: risk_pct = 0.5%** | 0.5% | 15% | 14.9% | 0.358% | 0% | 31% | ✅ | — sometimes |
| **C: risk_pct = 0.3%** | 0.3% | 15% | 14.4% | 0.338% | 0% | 26% | ✅ | — sometimes |
| **D: max_cap = 50% (raise Guard 5)** | 1.0% | 50% | 23.0% | 0.551% | 0% | 0% | ✅ | ✅ rarely |

---

## Recommendation

### Primary Recommendation: **Reduce `MAX_RISK_PER_TRADE_PCT` from 0.01 to 0.003**

**One-line change in `config.py` line 36:**

```python
# BEFORE
MAX_RISK_PER_TRADE_PCT   = 0.01      # 1% of capital per trade

# AFTER
MAX_RISK_PER_TRADE_PCT   = 0.003     # 0.3% of capital per trade
```

**Why Scenario C (0.3%) is the correct fix:**

At 0.3%, the risk formula naturally produces notionals within the 10–15% range for
all normal NSE signals (stop distance 2–4%):

```
notional_pct = 0.3% / 2.0% = 15.0%   (tight — just at limit)
notional_pct = 0.3% / 3.0% = 10.0%   (normal)
notional_pct = 0.3% / 4.0% =  7.5%   (wide stop → conservative)
```

The formula now **expresses intent**: tighter-stop signals get larger size, wider-stop
signals get smaller size. The 15% PA cap becomes a genuine last-resort safety net for
unusually tight stops (<1%), not a constant override.

### Why Not the Other Scenarios

| Option | Block Rate | Why Rejected |
|---|---|---|
| **A (1.0%, current)** | 0% | Formula intent always overridden; PA cap always fires; all sizing is mechanical maximum |
| **B (0.5%)** | 0% | PA cap still fires 31% of the time; formula still meaningless for most signals |
| **C (0.3%) ← RECOMMENDED** | 0% | PA cap fires rarely; formula intent honoured; Guard 5 never triggers normally |
| **D (raise Guard 5 to 50%)** | 0% | Architecturally wrong: exposes ₹50L+ per trade; Guard 5 exists for catastrophic protection |

### Alternative: Strategy-Specific Sizing (Advanced)

If different strategies should have different risk tolerances:

| Strategy Type | Typical Stop | Recommended risk_pct | Expected Notional |
|---|---|---|---|
| Breakout / Momentum (tight entries) | 1.0–1.5% | 0.15% | 10–15% |
| Mean Reversion (normal stops) | 1.5–2.5% | 0.30% | 12–20% |
| Trend / Swing (wide stops) | 2.5–4.0% | 0.50% | 12–20% |

This requires changing `_size()` in `portfolio_allocation_ai.py` to look up per-strategy
rates — a larger change. Scenario C achieves equivalent results with a single parameter.

---

## What Changes vs. What Does Not

| Component | Current | After Scenario C |
|---|---|---|
| `config.py` `MAX_RISK_PER_TRADE_PCT` | `0.01` | `0.003` |
| PA 15% cap fires | 34% of signals | ~26% (tight stops only) |
| Guard 5 `MAX_CAPITAL_PER_TRADE_PCT` | 15.0% | **unchanged** |
| `_MAX_SINGLE_TRADE_FRACTION` | 0.15 | **unchanged** |
| All guard logic, thresholds, allocation | unchanged | **unchanged** |
| CRE `_strategy_budget()` | unchanged | **unchanged** |
| Max ₹ at risk per trade | ₹100,000 (1% × ₹1Cr) | ₹30,000 (0.3% × ₹1Cr) |
| Formula expressiveness | Non-functional (cap always fires) | **Functional** |

### Risk Impact

At 0.3% risk_pct:
- **Max loss per position** (stop triggered): `0.3% × ₹10,000,000 = ₹30,000`
- **Position notional** (2% stop): ₹1,500,000 (10–15% of capital)
- **Daily loss limit**: would require 30+ consecutive SL hits to breach 10% halt
- **Institutional standard**: 0.25–0.50% risk/trade is conventional; 0.3% is within norms

---

## Consistency Verification

After applying `MAX_RISK_PER_TRADE_PCT = 0.003`:

```
Pipeline consistency check:
  CRE formula → PortfolioAllocationAI → Guard 5

  Signal: HDFCBANK entry=₹1720 stop=₹1685 (stop_dist=2.0%)
    CRE formula qty  = (₹10M × 0.3%) / ₹35   = 857 shares
    PA bucket cap    = ₹4M / ₹1720            = 2,325 (does not fire)
    PA 15% hard cap  = ₹1.5M / ₹1720          = 872  (does not fire at 857)
    Notional to Guard 5 = 857 × ₹1720 = ₹1,474,040 = 14.7% ✅ PASSES
```

---

*Generated by `analyze_sizing.py` — 2026-06-16T17:42:46*
