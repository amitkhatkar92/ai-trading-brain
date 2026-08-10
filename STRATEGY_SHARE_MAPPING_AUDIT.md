# STRATEGY SHARE MAPPING AUDIT
## Capital Risk Engine — _STRATEGY_SHARE Configuration Review

**Final Classification: SHARE_MAPPING_CONFIGURATION_GAP**  
**Date: 2026-08-10 | Read-only. No code changed. No orders placed.**

---

## 1. EXECUTIVE SUMMARY

There is a confirmed configuration gap.

The `_STRATEGY_SHARE` dict in `risk_control/capital_risk_engine.py` was built for the original
10 strategy names. Since then, 3 additional named production strategies were added to
`STRATEGY_PARAMS` (`Trend_Pullback`, `Equity_Breakout`, `Equity_Retest`) and 177 evolved
variants were approved — 175 of which use a naming scheme (`EDG_*`, `Breakout_Volume_RSI_HiVol`
style replacements) that does not match any prefix in `_STRATEGY_SHARE`.

All of these receive `_DEFAULT_SHARE = 0.10` instead of their parent's allocation.

The gap is not dangerous. The `_DEFAULT_SHARE = 0.10` is conservative, not reckless.
But it systematically under-allocates capital to the strategies that generate the most
Day-1 signals (evolved `EDG_*` Breakout_Volume variants), compressing the risk budget
by a factor of **2.8×** for the dominant production path.

---

## 2. _STRATEGY_SHARE — AS CONFIGURED

Source: `risk_control/capital_risk_engine.py`

```python
_STRATEGY_SHARE = {
    "Breakout_Volume":          0.28,
    "Momentum_Retest":          0.18,
    "Mean_Reversion":           0.22,
    "Bull_Call_Spread":         0.12,
    "Iron_Condor_Range":        0.18,
    "Hedging_Model":            0.10,
    "Short_Straddle_IV_Spike":  0.14,
    "Long_Straddle_Pre_Event":  0.08,
    "Futures_Basis_Arb":        0.14,
    "ETF_NAV_Arb":              0.12,
}
_DEFAULT_SHARE = 0.10   # "fallback for unknown / evolved variants"
```

The lookup mechanism is a prefix match:
```python
for base, base_share in _STRATEGY_SHARE.items():
    if strategy_name.startswith(base):
        share = base_share
        break
if share is None:
    share = _DEFAULT_SHARE
```

---

## 3. COMPLETE ACTIVE STRATEGY INVENTORY

### 3.1 Named Strategies (STRATEGY_PARAMS in strategy_lab/strategy_generator_ai.py)

| # | Strategy name | In `_STRATEGY_SHARE`? | Prefix match? | Share used | DEFAULT fallback? |
|---|---|---|---|---|---|
| 1 | `Breakout_Volume` | ✅ Yes | ✅ Exact | **0.28** | No |
| 2 | `Momentum_Retest` | ✅ Yes | ✅ Exact | **0.18** | No |
| 3 | `Trend_Pullback` | ❌ **No** | ❌ None | **0.10** | **YES** |
| 4 | `Mean_Reversion` | ✅ Yes | ✅ Exact | **0.22** | No |
| 5 | `Bull_Call_Spread` | ✅ Yes | ✅ Exact | **0.12** | No |
| 6 | `Iron_Condor_Range` | ✅ Yes | ✅ Exact | **0.18** | No |
| 7 | `Hedging_Model` | ✅ Yes | ✅ Exact | **0.10** | No (exact match) |
| 8 | `Short_Straddle_IV_Spike` | ✅ Yes | ✅ Exact | **0.14** | No |
| 9 | `Long_Straddle_Pre_Event` | ✅ Yes | ✅ Exact | **0.08** | No |
| 10 | `Futures_Basis_Arb` | ✅ Yes | ✅ Exact | **0.14** | No |
| 11 | `ETF_NAV_Arb` | ✅ Yes | ✅ Exact | **0.12** | No |
| 12 | `Equity_Breakout` | ❌ **No** | ❌ None | **0.10** | **YES** |
| 13 | `Equity_Retest` | ❌ **No** | ❌ None | **0.10** | **YES** |

**Summary:** 10 of 13 named strategies are correctly configured. 3 are missing.

### 3.2 Evolved Variants (data/evolved_strategies.json — approved entries)

Total approved evolved variants: **177**

| Category | Count | Prefix matches `_STRATEGY_SHARE`? | Share received | Base intended share |
|---|---|---|---|---|
| `Breakout_Volume_RSI_HiVol` | 1 | ✅ Yes (`Breakout_Volume`) | **0.28** | 0.28 |
| `Mean_Reversion_RSI_HiVol` | 1 | ✅ Yes (`Mean_Reversion`) | **0.22** | 0.22 |
| `EDG_MOMENT_*` (base=`Breakout_Volume`) | ~120 | ❌ No | **0.10** | **0.28** |
| `EDG_COMPOS_*` (base=`Breakout_Volume`) | ~15 | ❌ No | **0.10** | **0.28** |
| `EDG_MACRO_*` (base=`Breakout_Volume`) | ~9 | ❌ No | **0.10** | **0.28** |
| `EDG_VOLATI_*` (base=`Short_Straddle_IV_Spike`) | 30 | ❌ No | **0.10** | **0.14** |
| Other EDG variants (base=`Momentum_Retest`) | 1 | ❌ No | **0.10** | **0.18** |

**Breakdown by base_strategy:**

| Base strategy | Gap variants | Current share | Intended share | Multiplier |
|---|---|---|---|---|
| `Breakout_Volume` | **144** | 0.10 | **0.28** | 2.8× lower |
| `Short_Straddle_IV_Spike` | **30** | 0.10 | **0.14** | 1.4× lower |
| `Momentum_Retest` | **1** | 0.10 | **0.18** | 1.8× lower |
| **Total gap variants** | **175** | — | — | — |

**Correctly mapped:** 2 of 177 (1.1%)  
**Incorrectly defaulted:** 175 of 177 (98.9%)

---

## 4. SHARE LOOKUP MECHANISM — HOW THE GAP OCCURS

The CRE's `_strategy_budget()` method uses a prefix match:

```python
def _strategy_budget(self, strategy_name: str, deployable: float) -> float:
    share = _STRATEGY_SHARE.get(strategy_name)       # exact match first
    if share is None:
        for base, base_share in _STRATEGY_SHARE.items():
            if strategy_name.startswith(base):        # prefix match second
                share = base_share
                break
    if share is None:
        share = _DEFAULT_SHARE                        # fallback last
    return deployable * share
```

**Why older evolved variants matched but new ones don't:**

| Variant name | Prefix test against `Breakout_Volume` | Result |
|---|---|---|
| `Breakout_Volume_RSI_HiVol` | `"Breakout_Volume_RSI_HiVol".startswith("Breakout_Volume")` → True | **Match → 0.28** |
| `EDG_MOMENT_95_EE0000` | `"EDG_MOMENT_95_EE0000".startswith("Breakout_Volume")` → False | **Default → 0.10** |
| `EDG_COMPOS_92_EE0002` | `"EDG_COMPOS_92_EE0002".startswith("Breakout_Volume")` → False | **Default → 0.10** |
| `EDG_VOLATI_91_EE0004` | `"EDG_VOLATI_91_EE0004".startswith("Short_Straddle_IV_Spike")` → False | **Default → 0.10** |

The evolved variant JSON stores `base_strategy` but the CRE does not read it:
```json
"EDG_MOMENT_95_EE0000": {
    "base_strategy": "Breakout_Volume",   ← this field exists
    "approved": true,
    ...
}
```

The CRE only sees the strategy name string. It has no access to the JSON's `base_strategy` field.

---

## 5. DAY-1 PRODUCTION SIGNAL PATH

In `bull_trend` regime, equity signals are routed via `StrategyGeneratorAI._pick_strategy()`:

```python
if regime in (RegimeLabel.BULL_TREND,):
    if signal.signal_type == SignalType.EQUITY:
        evolved = self._best_evolved_variant("Breakout_Volume", active, min_signal_rr=rr)
        return evolved or _choose(["Breakout_Volume"])
```

With 144 approved `EDG_*` variants of `Breakout_Volume` in the active set, virtually
all BULL_TREND equity signals are assigned an `EDG_*` name, not `Breakout_Volume` itself.

Result: **All Day-1 equity signals received `_DEFAULT_SHARE = 0.10`** rather than the
0.28 that `Breakout_Volume` would have provided.

**Confirmed by Day-1 logs:**
```
[CRE] DEEPAKNTR → qty=0 (budget=₹800 SL=1704.02) — skipped.
[CRE] HAVELLS   → qty=0 (budget=₹800 SL=1240.66) — skipped.
[CRE] RELIANCE  → qty=0 (budget=₹800 SL=1289.54) — skipped.
```
budget = ₹800 = ₹8,000 × 0.10 (DEFAULT_SHARE) — all confirmed.

---

## 6. IS THE CURRENT MAPPING INTENTIONAL?

**For named strategies (`Trend_Pullback`, `Equity_Breakout`, `Equity_Retest`):**

These strategies are explicitly registered in `STRATEGY_PARAMS` with tuned `min_rr` and
`max_loss_pct` values, seeded in `_BACKTEST_CACHE` with full performance metrics, and
included in the regime routing table. They are fully recognised production strategies.

Their absence from `_STRATEGY_SHARE` is inconsistent with this treatment.

**Assessment: Unintentional gap** — these strategies were added to the generator and backtest
cache but the parallel update to `_STRATEGY_SHARE` was not made.

---

**For evolved variants (`EDG_*`):**

The `_DEFAULT_SHARE` comment in the code says: `"fallback for unknown / evolved variants"`.
This suggests the author was aware evolved variants would fall to the default.

However, two counterpoints:
1. The evolved strategies JSON explicitly stores `base_strategy` — this data was clearly
   intended to convey parentage, and the CRE is the natural consumer of that parentage for
   budget purposes.
2. The earlier naming convention (`Breakout_Volume_RSI_HiVol`) *does* receive the parent
   share via prefix match. When the naming scheme changed to `EDG_*`, the prefix match
   broke — but no corresponding update was made to the CRE.

**Assessment: Naming scheme evolution broke an existing linkage.** The `EDG_*` naming
scheme introduced a new prefix that was never added to `_STRATEGY_SHARE`. Whether this
was intentional (keep evolved variants conservatively funded until proven) or an oversight
cannot be determined from code alone. Both interpretations are plausible.

---

## 7. CAPITAL UTILISATION DIFFERENCE

### 7.1 Per-Signal Gap: Current vs Intended

For the dominant Day-1 path: BULL_TREND + EQUITY → `EDG_MOMENT_*` (base=`Breakout_Volume`)

| Parameter | Current (DEFAULT_SHARE 0.10) | Intended (Breakout_Volume 0.28) | Difference |
|---|---|---|---|
| Deployable fraction | 10% | 28% | 2.8× |
| Risk per trade (0.25%) | 0.025% of deployable | 0.07% of deployable | 2.8× |
| `strategy_budget` at ₹8,000 deployable | ₹800 | ₹2,240 | +₹1,440 |
| `risk_amount` at ₹8,000 deployable | ₹2.00 | ₹5.60 | +₹3.60 |

Note: The risk percentage (0.25%) is unchanged. Only the base on which it is applied differs.

### 7.2 qty Calculation Impact

For CROMPTON (cheapest Nifty stock in Day-1 signals):
| Parameter | Current | Intended |
|---|---|---|
| budget | ₹800 | ₹2,240 |
| risk_amount | ₹2.00 | ₹5.60 |
| SL distance | ₹13.56 | ₹13.56 |
| qty_by_risk | floor(2.00/13.56) = **0** | floor(5.60/13.56) = **0** |
| qty_by_budget | floor(800/250) = 3 | floor(2240/250) = **8** |
| **Final qty** | **0** (risk gate fires) | **0** (risk gate fires) |

> Both routes still produce qty=0 for CROMPTON at ₹10,000 capital.
> The intended mapping at ₹10,000 is **still insufficient** for the Nifty universe.
> The gap changes the threshold capital level at which trades become possible, not
> whether ₹10,000 itself can trade.

### 7.3 Simulation by Capital Level

**Assumptions:**
- Regime: `bull_trend` (80% deployable)
- Signal: EQUITY → `EDG_MOMENT_*` (Breakout_Volume base)
- Current share: 0.10 | Intended share: 0.28
- Stock: CROMPTON (~₹250, SL dist ~₹13.56); RELIANCE (~₹1,300, SL dist ~₹29.25)

#### ₹10,000

| | Current | Intended |
|---|---|---|
| strategy_budget | ₹800 | ₹2,240 |
| risk_amount | ₹2.00 | ₹5.60 |
| CROMPTON qty | 0 | 0 |
| RELIANCE qty | 0 | 0 |
| **Tradeable Nifty stocks** | **0** | **0** |

**Both zero.** The gap changes nothing at ₹10,000.

#### ₹50,000

| | Current | Intended |
|---|---|---|
| strategy_budget | ₹4,000 | ₹11,200 |
| risk_amount | ₹10.00 | ₹28.00 |
| CROMPTON qty (SL ₹13.56) | 0 | 2 ✅ |
| ITC qty (~₹450, SL ₹10.13) | 0 | 2 ✅ |
| NTPC qty (~₹350, SL ₹7.88) | 1 ✅ | 3 ✅ |
| ONGC qty (~₹280, SL ₹6.30) | 1 ✅ | 4 ✅ |
| RELIANCE qty (SL ₹29.25) | 0 | 0 |
| **Approx tradeable Nifty stocks** | **~10–12** | **~22–28** |

**Gap approximately doubles accessible universe at ₹50,000.**

#### ₹1,00,000

| | Current | Intended |
|---|---|---|
| strategy_budget | ₹8,000 | ₹22,400 |
| risk_amount | ₹20.00 | ₹56.00 |
| CROMPTON qty | 1 ✅ | 4 ✅ |
| ITC qty | 1 ✅ | 5 ✅ |
| SBI qty (~₹900, SL ₹20.25) | 0 | 2 ✅ |
| RELIANCE qty (SL ₹29.25) | 0 | 1 ✅ |
| DEEPAKNTR qty (~₹1,800, SL ₹95.98) | 0 | 0 |
| **Approx tradeable Nifty stocks** | **~20–25** | **~35–40** |

**Gap unlocks ~15 additional Nifty stocks at ₹1,00,000.**

#### ₹2,00,000

| | Current | Intended |
|---|---|---|
| strategy_budget | ₹16,000 | ₹44,800 |
| risk_amount | ₹40.00 | ₹112.00 |
| CROMPTON qty | 2 ✅ | 8 ✅ |
| RELIANCE qty (SL ₹29.25) | 1 ✅ | 3 ✅ |
| DEEPAKNTR qty (SL ₹95.98) | 0 | 1 ✅ |
| HDFC Bank qty (~₹1,900, SL ₹42.75) | 0 | 2 ✅ |
| TITAN qty (~₹3,800, SL ₹85.5) | 0 | 1 ✅ |
| **Approx tradeable Nifty stocks** | **~35–40** | **~45–47 (near full access)** |

**At ₹2,00,000, intended mapping achieves near-complete Nifty 50 coverage.**  
With current mapping, ~10 Nifty stocks (mostly expensive) remain blocked until ₹5,00,000.

### 7.4 Summary: Capital Threshold Shift

| Milestone | Current mapping | Intended mapping | Improvement |
|---|---|---|---|
| First live trade possible | ~₹20,000 (cheapest PSUs) | ~₹12,000 (cheapest PSUs) | ~40% lower threshold |
| 10+ stocks accessible | ~₹50,000 | ~₹25,000 | ~50% lower threshold |
| Most Nifty 50 accessible (~40 stocks) | ~₹5,00,000 | ~₹2,00,000 | ~60% lower threshold |
| Full Nifty 50 access | ~₹10,00,000 | ~₹4,00,000 | ~60% lower threshold |

---

## 8. COMPLETE MAPPING TABLE — EVERY ACTIVE STRATEGY

### Named strategies (STRATEGY_PARAMS — 13 entries)

| Strategy | Regime(s) active | Share used | Correct? | Notes |
|---|---|---|---|---|
| `Breakout_Volume` | BULL_TREND (equity) | **0.28** | ✅ | Main equity strategy |
| `Momentum_Retest` | RANGE (high-conf BUY) | **0.18** | ✅ | Pullback/momentum |
| `Trend_Pullback` | RANGE (BUY strong) fallback | **0.10** (DEFAULT) | ❌ | **Missing from _STRATEGY_SHARE** |
| `Mean_Reversion` | RANGE (default equity) | **0.22** | ✅ | RSI extremes |
| `Bull_Call_Spread` | BULL_TREND (options) | **0.12** | ✅ | Options debit spread |
| `Iron_Condor_Range` | RANGE (options) | **0.18** | ✅ | Options premium |
| `Hedging_Model` | VOLATILE / BEAR | **0.10** | ✅ (exact match) | Intentional 10% |
| `Short_Straddle_IV_Spike` | IV-spike events | **0.14** | ✅ | Premium selling |
| `Long_Straddle_Pre_Event` | Pre-event | **0.08** | ✅ | Event binary |
| `Futures_Basis_Arb` | RANGE (futures) | **0.14** | ✅ | Arb |
| `ETF_NAV_Arb` | RANGE (ETF) | **0.12** | ✅ | Arb |
| `Equity_Breakout` | **VOLATILE** (equity) | **0.10** (DEFAULT) | ❌ | **Missing from _STRATEGY_SHARE** |
| `Equity_Retest` | **VOLATILE** (equity) | **0.10** (DEFAULT) | ❌ | **Missing from _STRATEGY_SHARE** |

### Evolved variants (177 approved in evolved_strategies.json)

| Variant class | Count | Base | Share used | Correct? |
|---|---|---|---|---|
| `Breakout_Volume_RSI_HiVol` | 1 | `Breakout_Volume` | **0.28** | ✅ |
| `Mean_Reversion_RSI_HiVol` | 1 | `Mean_Reversion` | **0.22** | ✅ |
| `EDG_MOMENT_*` | ~120 | `Breakout_Volume` | **0.10** | ❌ **2.8× under-allocated** |
| `EDG_COMPOS_*` | ~15 | `Breakout_Volume` | **0.10** | ❌ **2.8× under-allocated** |
| `EDG_MACRO_*` | ~9 | `Breakout_Volume` | **0.10** | ❌ **2.8× under-allocated** |
| `EDG_VOLATI_*` | 30 | `Short_Straddle_IV_Spike` | **0.10** | ❌ **1.4× under-allocated** |
| Other (1) | 1 | `Momentum_Retest` | **0.10** | ❌ **1.8× under-allocated** |

**Correctly mapped: 12 named + 2 evolved = 14 total**  
**Incorrectly defaulted: 3 named + 175 evolved = 178 strategies receiving 0.10 default**

---

## 9. MINIMUM CORRECTION REQUIRED (described only — NOT implemented)

There are two distinct gaps requiring two different corrections.

### Gap 1 — Three named strategies missing from _STRATEGY_SHARE

The minimum correction is to add three entries to `_STRATEGY_SHARE`:

```python
# Minimum addition to _STRATEGY_SHARE (risk_control/capital_risk_engine.py)
# Not implemented — described only.

"Trend_Pullback":   0.18,  # Pullback-inside-trend; similar role to Momentum_Retest
"Equity_Breakout":  0.28,  # Volatile-regime breakout; equivalent risk profile to Breakout_Volume
"Equity_Retest":    0.18,  # Volatile-regime retest; equivalent risk profile to Momentum_Retest
```

Reasoning:
- `Trend_Pullback` is a RANGE_MARKET equity strategy. It operates alongside `Momentum_Retest`
  in range conditions and has similar risk characteristics. `Momentum_Retest` share (0.18) is
  the natural equivalent.
- `Equity_Breakout` is explicitly the VOLATILE-regime version of `Breakout_Volume`. In the
  VOLATILE regime, position sizes are halved at the strategy layer (`signal.quantity = max(1, int(signal.quantity * 0.5))`), so capital deployment is already self-limiting.
  `Breakout_Volume` share (0.28) with the existing qty-halving guard is appropriate.
- `Equity_Retest` is the VOLATILE-regime retest strategy. `Momentum_Retest` share (0.18)
  with the existing qty-halving guard.

> **Note:** These additions do NOT change the 0.25% risk rule, safety gates, or position limits.
> They only ensure capital proportional to the strategy's design role — which is what the 10
> named strategies already have.

### Gap 2 — Evolved variants receive DEFAULT_SHARE regardless of base

The minimum correction would change the fallback path in `_strategy_budget()` to consult
`base_strategy` from `STRATEGY_PARAMS` when prefix matching fails:

```python
# Conceptual description — NOT implemented.
# In _strategy_budget(), after prefix match fails and before _DEFAULT_SHARE is used:
#
# from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
# if share is None:
#     base = (STRATEGY_PARAMS.get(strategy_name) or {}).get("base_strategy")
#     if base:
#         share = _STRATEGY_SHARE.get(base)
# if share is None:
#     share = _DEFAULT_SHARE
```

This would correctly resolve `EDG_MOMENT_95_EE0000` → `base_strategy="Breakout_Volume"` → share=0.28.

**Scope of change:** 1 method in `risk_control/capital_risk_engine.py`.
**Risk assessment:** Low. The change only increases budget for evolved variants from 0.10 to
their parent's share. Safety gates (RiskControl R:R, RiskGuardian halts, MAX_POSITIONS cap)
are all downstream and remain unchanged. The maximum total deployment cannot exceed
`deployable × max(strategy_shares) = deployable × 0.28` per signal (unchanged — this is the
existing maximum for Breakout_Volume).

### Gap 2 — Alternative: No change required

If the intent of `_DEFAULT_SHARE = 0.10` is a deliberate conservative safety floor for all
evolved variants (i.e., unproven production variants should run on a smaller capital allocation
regardless of their parent strategy) — then Gap 2 is intentional and no correction is needed.

The key question for the decision-maker:
> "Should a strategy variant that has passed all quality gates (WF=100%, OvFit=1.0, XMkt=100%)
> be constrained to half the capital allocation of its base strategy — indefinitely?"

This is a business decision, not a technical one.

---

## 10. FINAL CLASSIFICATION

```
╔══════════════════════════════════════════════════════════════════════╗
║  SHARE_MAPPING_CONFIGURATION_GAP                                     ║
║                                                                      ║
║  Gap 1 (certain): 3 named strategies not in _STRATEGY_SHARE         ║
║    Trend_Pullback, Equity_Breakout, Equity_Retest                   ║
║    All receive _DEFAULT_SHARE = 0.10 instead of intended 0.18–0.28  ║
║                                                                      ║
║  Gap 2 (likely): 175 of 177 evolved variants receive 0.10 default   ║
║    because EDG_* naming breaks the prefix-match against              ║
║    _STRATEGY_SHARE. The base_strategy field in the JSON is           ║
║    not consulted by the CRE.                                         ║
║                                                                      ║
║  Effect at ₹10,000: NONE — both paths produce qty=0                 ║
║  Effect at ₹50,000: ~2× fewer accessible stocks                     ║
║  Effect at ₹1,00,000: ~15 fewer Nifty stocks accessible             ║
║  Effect at ₹2,00,000: ~10 stocks blocked that should be accessible  ║
║                                                                      ║
║  Gap 1 minimum fix: Add 3 entries to _STRATEGY_SHARE.               ║
║  Gap 2 minimum fix: Use base_strategy from STRATEGY_PARAMS when     ║
║    prefix match fails — or accept DEFAULT_SHARE as intentional.     ║
║                                                                      ║
║  No code changed. No orders placed. No risk rules changed.          ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

*Generated: 2026-08-10 | Source: risk_control/capital_risk_engine.py, strategy_lab/strategy_generator_ai.py, data/evolved_strategies.json*  
*Commit HEAD: `7c1daad` | Read-only audit — no changes made*
