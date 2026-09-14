# DTA-040 Extension — Forensic Report
## Are Empirical Stop/Target Values from REGIME_DIR Evidence Statistically Appropriate for Individual Symbol Risk Parameters?

**Date:** 2026-09-01  
**Investigator:** GitHub Copilot (read-only audit)  
**Status:** COMPLETE  
**Code changes:** NONE (investigation only per explicit instruction)

---

## 1. Question Under Investigation

KDA replaces the scanner's ATR-based stop/target with empirical offsets derived from historical KLP outcomes. The previous finding (DTA-040) established that this replacement reduces R:R from 2.50 → 1.889, causing every KDA authority candidate to be rejected by RiskControl.

This extension answers: **Is it statistically valid to apply REGIME_DIR-level empirical stop/target offsets to individual symbols?**

---

## 2. Evidence Pool Composition (ground truth as of 2026-09-01)

| Metric | Value |
|---|---|
| Total HBE outcome records | 112,953 |
| Non-OOS evidence pool | 102,287 |
| **Live/paper trades** | **218 (0.2%)** |
| **Replay (backtest)** | **100,899 (98.6%)** |
| Bootstrap (historical) | 1,170 (1.1%) |
| RANGE_MARKET + BUY subpool (L4) | 39,812 |
| RANGE_MARKET + BUY, live only | **185 (0.5%)** |
| Unique symbols in L4 pool | 70 |

**Critical: 98.6% of all evidence is HISTORICAL_REPLAY — backtested synthetic data, not confirmed live P&L.** Live performance verification exists for only 218 of 102,287 records.

---

## 3. Symbol-Level Evidence Audit (all 7 authority candidates)

| Symbol | L1 (SYMBOL+DIR+REGIME) | L2 (SYMBOL+DIR) | L3 (SECTOR+DIR+REGIME) | L4 (REGIME+DIR) used |
|---|---|---|---|---|
| BHEL | **0** | **0** | **0** | ✅ 39,812 |
| RBLBANK | **0** | **0** | 5,941 | (L3 activates first) |
| PNB | **0** | **0** | 5,941 | (L3 activates first) |
| FEDERALBNK | **0** | **0** | 5,941 | (L3 activates first) |
| IDFCFIRSTB | **0** | **0** | 5,941 | (L3 activates first) |
| BANKINDIA | **0** | **0** | 5,941 | (L3 activates first) |
| NMDC | **0** | **0** | 2,691 | (L3 activates first) |

**Finding F1**: **Zero symbol-specific records exist for any of the 7 authority candidates.** Not a single live or replay trade under BHEL's symbol has been tracked to completion. Every candidate operates on fully population-level data with no symbol differentiation.

**Finding F2**: HBE activation thresholds — `_LEVEL_MIN_OBS = [None, 5, 5, 10, 10, 15, 15, 0]` — require only **5 records** for L1/L2. Even 5 live BHEL trades would unlock symbol-specific parameters. The 7 candidates have zero.

---

## 4. REGIME_DIR (L4) Population Characteristics

The L4 pool contains 70 symbols, top 10 by record count:
```
HDFCBANK(1222) NESTLEIND(1161) PIDILITIND(1114) INFY(1104) KOTAKBANK(1102)
HINDUNILVR(1077) HCLTECH(1071) DIVISLAB(1067) POWERGRID(1063) ASIANPAINT(1056)
```

**Finding F3**: The L4 pool that governs BHEL's (capital goods) stop/target is dominated by FMCG stocks (NESTLEIND, HINDUNILVR, BRITANNIA), IT stocks (INFY, HCLTECH), and banking stocks (HDFCBANK, KOTAKBANK). These sectors have fundamentally different volatility profiles, intraday move sizes, and stop/target behavior from capital goods stocks.

**Finding F4**: **BHEL, RBLBANK, IDFCFIRSTB, and BANKINDIA receive IDENTICAL empirical offsets** (`tgt_p50=6.0966%, stp_p50=3.2278%`) because they all fall back to the same L4 pool. A capital goods conglomerate and a private sector bank have the same stop distance. There is zero symbol differentiation.

---

## 5. Statistical Validity of L4 Stop/Target Offsets

### 5.1 Target and Stop Are Measured on Disjoint Subsets

```
RANGE_MARKET BUY completed outcomes (n=39,812):
  - TARGET_HIT:  3,218 records  (8.1%)  → target offset p50 = 6.10%
  - STOP_HIT:   10,695 records  (26.9%) → stop offset p50  = 3.23%
  - OTHER EXIT: 25,899 records  (65.0%) → not counted in either offset
```

The target offset (6.10%) is the median excursion of the **8.1% of trades that happened to hit their target**. The stop offset (3.23%) is the median loss of the **26.9% that hit their stop first**. These are computed on different, non-overlapping, self-selected subsets of trades.

**Finding F5**: There is no statistical constraint preventing `stop_offset_p50 / target_offset_p50 > 1/(MIN_RR_RATIO)`. The ratio is structurally determined by whichever subset of trades survived to hit target vs stop. No mechanism guarantees the resulting empirical R:R ≥ 2.0.

### 5.2 Empirical R:R Is Structurally Below System Threshold

| Level | Pool (n) | tgt_p50 | stp_p50 | Empirical R:R | vs MIN_RR=2.0 |
|---|---|---|---|---|---|
| L3 (BANK+RANGE) | 5,941 | 5.66% | 2.97% | **1.906** | ❌ BELOW |
| L3 (METALS+RANGE) | 2,691 | 7.37% | 3.97% | **1.856** | ❌ BELOW |
| L4 (ALL+RANGE) | 39,812 | 6.10% | 3.23% | **1.889** | ❌ BELOW |
| L5 (BANK+ANY) | 8,799 | 6.11% | 3.21% | **1.904** | ❌ BELOW |
| L6 (ALL+ANY) | 58,723 | 6.48% | 3.38% | **1.916** | ❌ BELOW |

**Finding F6**: **Every available evidence level (L3–L6) produces an empirical R:R below the system's MIN_RR_RATIO of 2.0.** This is not a BHEL-specific problem. It is a structural property of the historical data: in range markets, empirical median R:R across NSE stocks is ~1.89–1.91. Any signal that falls back to L3–L6 will be rejected by RiskControl.

### 5.3 Expected Value Analysis

Using regime-level probabilities to evaluate the EV of taking a BUY trade in RANGE_MARKET:

```
Target hit rate:           8.1%
Stop hit rate:            26.9%
Other outcome rate:       65.0%

Breakeven R:R (if other=0): 26.9% / 8.1% = 3.323

EV (KDA empirical, R:R=1.889): 0.081 × 6.10% − 0.269 × 3.23% = −0.374%
EV (scanner ATR 2.5×, R:R=2.50): 0.081 × 13.79% − 0.269 × 5.52% = −0.368%
```

**Finding F7**: **The regime-level data shows negative expected value for BUY trades in RANGE_MARKET regardless of which stop/target parameters are used.** The breakeven R:R (3.323) exceeds both the KDA empirical R:R (1.889) and the scanner's ATR R:R (2.50). This is the regime-level population average — individual symbols with stronger directional alignment may outperform it.

**Important nuance**: KDA issues KNOWLEDGE_BUY selectively — only for symbols where its evidence shows a directional edge above some threshold. The population-average EV does not mean the KDA-selected subset would also be negative EV. However, since the stop/target offsets **are** derived from the population average (not the KDA-selected subset), they inherit the population's R:R structure.

### 5.4 The Counterfactual: What KDA Actually Does to BHEL

```
Entry: ₹430.85

Scanner parameters (ATR-based):
  Stop loss:  ₹407.06  (−5.52% from entry, −₹23.79 per share)
  Target:     ₹490.33  (+13.79% from entry, +₹59.48 per share)
  R:R = 2.50

KDA empirical parameters (REGIME_DIR, L4):
  Stop loss:  ₹416.94  (−3.23% from entry, −₹13.91 per share) → TIGHTER by ₹9.88
  Target:     ₹457.12  (+6.10% from entry, +₹26.27 per share) → LOWER by ₹33.21
  R:R = 1.889
```

KDA makes the trade **smaller** in both dimensions: tighter stop, lower target. The R:R falls below system threshold. The effect is not that KDA found a better trade — it found a more historically-realistic trade that then fails the system's validation gate.

---

## 6. Cross-Level Consistency Assessment

### 6.1 Level-to-Level R:R Stability

| Level | tgt_p50 | stp_p50 | R:R | Interquartile R:R |
|---|---|---|---|---|
| L3 BANK+RANGE | 5.66% | 2.97% | 1.906 | p25=1.19 → p75=2.92 |
| L3 METALS+RANGE | 7.37% | 3.97% | 1.856 | p25=1.26 → p75=2.72 |
| L4 ALL+RANGE | 6.10% | 3.23% | 1.889 | p25=1.29 → p75=2.74 |
| L5 BANK+ANY | 6.11% | 3.21% | 1.904 | p25=1.14 → p75=3.06 |
| L6 ALL+ANY | 6.48% | 3.38% | 1.916 | p25=1.28 → p75=2.82 |

**Finding F8**: The median empirical R:R is remarkably consistent across levels (1.856–1.916). This suggests the finding is robust — it is not a quirk of L4 specifically. The interquartile range shows individual trades span 1.14 to 3.06 R:R, meaning about 50% of individual trades would pass the 2.0 threshold, but the **median** applied to all signals uniformly produces a block.

**Finding F9**: HBE applies the **median** (p50) as the representative offset. If it applied the p75 optimistic offset instead, the R:R would be ~2.74, passing the threshold. The choice of p50 is conservative but systematically blocks all range-market signals.

---

## 7. Verdict: Is REGIME_DIR Evidence Appropriate for Individual Symbol Stop/Target?

**NO — for three independent reasons:**

**Reason 1: Zero symbol-specific calibration.** BHEL (capital goods, heavy machinery, government-linked demand) receives the same stop/target as NESTLEIND (FMCG consumer staples) and INFY (IT services). These stocks have different betas, intraday volatility, and price behavior. Using a regime-wide median ignores all symbol-specific characteristics. The HBE hierarchy exists precisely to prevent this — L1/L2 exist to provide symbol-specific parameters — but they are empty.

**Reason 2: Structural incompatibility with system risk threshold.** REGIME_DIR empirical R:R is 1.889 across all evidence levels. MIN_RR_RATIO = 2.0. This is not a boundary case — it is a structural gap of 0.111 R:R units that persists across all evidence levels (L3 through L6). Any signal that lacks L1/L2 data will be blocked. Since no symbol currently has L1/L2 data, **100% of KDA authority candidates are permanently blocked** in range_market conditions.

**Reason 3: Self-defeating architecture.** KDA's override of ATR targets was presumably intended to produce more realistic risk parameters. But the empirical targets (6.10%) are measured from trades that actually hit their targets. These trades were placed with ATR-based targets (the scanner sets targets). So the empirical target offset reflects the median ATR excursion that resolved as a target hit — which is the tail of the ATR distribution, not the full ATR value. The result is a paradox: KDA's empirical offsets are derived from positions placed with ATR targets, but applying them to new positions causes those positions to fail the R:R gate that the ATR positions would have passed.

---

## 8. Decision Tree: Options A / B / C

### Option A — Keep Current Design

**State**: Every KDA authority candidate in range_market is permanently rejected. KDA runs in SHADOW mode producing correct directional signals but zero trades until sufficient symbol-specific data accumulates.

**When does this resolve?** When a symbol accumulates ≥5 L2 records (symbol + direction outcomes). At the current live rate of 185 live records across all 70 symbols ≈ 2.6 per symbol, and only range_market BUY trades being analyzed: likely **12–24 months** before enough per-symbol data exists.

**Assessment**: Accept if the intent is to prevent all live trades until symbol-specific evidence is proven. In the current deployment (LIVE_TRADING_AUTHORIZED=true), this means KDA generates zero live trades indefinitely.

### Option B — Restrict Empirical Override to SYMBOL_DIR (L2)

**Change**: KDA only replaces ATR stop/target if `evidence_level <= 2` (SYMBOL_DIR or SYMBOL_DIR_REGIME). For L3–L6, retain ATR-based parameters.

**Effect today**: All 7 candidates fall back to ATR parameters. R:R = 2.50. All 7 pass RiskControl. Debate decides which reach execution.

**Tradeoff**: Loses the regime-level directional signal's influence on trade sizing. KDA still controls direction (KNOWLEDGE_BUY vs KNOWLEDGE_HOLD), just not the stop/target placement.

**Assessment**: Correct architectural line. KDA should gain stop/target authority only when it has symbol-specific evidence. Directional authority (which stocks to trade) is separate from risk parameter authority (where to place stop/target).

### Option C — Separate Direction Authority from Risk Parameter Authority

**Change**: KDA provides a direction verdict (KNOWLEDGE_BUY / KNOWLEDGE_HOLD) and a confidence score. Stop/target parameters remain ATR-based unless L1 or L2 evidence exists. Regime-level evidence informs the confidence score but not the stop/target.

**Effect today**: Identical to Option B in immediate outcome (ATR parameters used, R:R=2.50). Architecturally cleaner because the authority boundary is explicit: "KDA decides WHETHER to trade; ATR/scanner decides WHERE to place risk parameters until proven symbol data exists."

**Assessment**: Most precise. Prevents scope creep where a broad-population signal (L4) influences parameters it was never calibrated to set. Recommended direction.

---

## 9. Summary of Findings

| Finding | Description |
|---|---|
| F1 | Zero symbol-specific records for all 7 authority candidates |
| F2 | Threshold to unlock L2 is only 5 records — currently unreachable |
| F3 | L4 pool dominated by FMCG/IT/banking stocks, not capital goods/metals |
| F4 | BHEL and 3 banking stocks get **identical** stop/target offsets |
| F5 | No statistical constraint prevents empirical R:R < MIN_RR_RATIO |
| F6 | **All** evidence levels L3–L6 produce R:R < 2.0 in range_market |
| F7 | Regime-level EV is negative at both KDA (−0.374%) and ATR (−0.368%) R:R |
| F8 | R:R is stable across levels (1.856–1.916) — this is not an L4-specific quirk |
| F9 | HBE uses p50 offset; p75 would pass the threshold for ~50% of trades |
| F10 | KDA's empirical targets are derived from trades placed with ATR targets — circular dependence |

---

## 10. Recommended Decision

**Option C (or B as a simpler equivalent).**

The data does not support REGIME_DIR evidence as a valid source for individual symbol stop/target override. It is valid for directional intelligence. The architectural fix is a one-line guard in KDA's `_derive_target_stop()`:

```python
# Apply empirical offsets ONLY when evidence is symbol-specific (L1 or L2)
if tgt_offset is not None and stp_offset is not None and tgt_src == "EMPIRICAL":
    if evidence_level > 2:   # L3+ = population-level; retain ATR
        pass  # fall through to ATR
    else:
        # symbol-specific: apply
        ...
```

This would:
- Unblock all 7 KDA candidates immediately (ATR targets restore R:R=2.50)
- Preserve KDA's directional authority (KNOWLEDGE_BUY still routes to Debate)
- Maintain the HBE hierarchy — empirical stop/target becomes active as L1/L2 data accumulates
- Eliminate the structural conflict between empirical R:R and MIN_RR_RATIO

**This report does not implement the fix.** Implementation awaits explicit user instruction.

---

*End of DTA-040 Extension Forensic Report*
