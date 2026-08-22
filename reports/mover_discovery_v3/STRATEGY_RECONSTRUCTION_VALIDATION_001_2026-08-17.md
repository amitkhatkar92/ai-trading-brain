# STRATEGY_RECONSTRUCTION_VALIDATION_001
## Replay Strategy Gate — Reconstruction Validation Study

**Generated:** 2026-08-17  
**Verdict:** A — RECONSTRUCTION_VALIDATED  
**Signal-level accuracy:** 96.5%  
**Day-level exact-match rate:** 76.7% (23/30 days)

---

## Executive Summary

This study validates whether the production StrategyLab rejection funnel from the
Jan-Mar 2026 simulation replay (286 → 82 → 23 → 6) can be reconstructed from trace
evidence using deterministic rules derived from the original codebase.

**Conclusion:** The strategy gate is **reconstructable at 96.5% signal-level accuracy**
using three deterministic rules. The remaining 10 unexplained
cases are equity signals that failed the RR check (risk_reward_ratio not stored in trace).

---

## 1. Funnel Confirmation

Source: 30 trace files in `simulation_logs/decision_trace/`

| Stage | Count | Rate |
|---|---|---|
| Raw signals | 286 | 100.0% |
| After StrategyLab | 82 | 28.7% |
| After RiskControl | 23 | 8.0% |
| Executed | 6 | 2.1% |

**Note:** `replay_summary.json` has `rejection_funnel: null`. The funnel was computed
from primary trace evidence for this study.

---

## 2. Reconstruction Rules

Three deterministic rules explain 194 of 204 rejections:

| Rule | Count | Coverage |
|---|---|---|
| D1 TYPE_LOW_RR (OPTIONS/ARB) | 180 | 88.2% |
| D2 BEAR_EQUITY_BUY | 0 | 0.0% |
| D3 REGIME_MISMATCH | 14 | 6.9% |
| Total deterministic | 194 | 95.1% |
| Indeterminate (RR check) | 10 | 4.9% |

**Critical finding — D1 (TYPE_LOW_RR):** The OPTIONS/SPREAD RR exemption was NOT
present in the original code (commit 42ee4de, active during replay 2026-01-30 to
2026-03-16). It was added in commit a2089c1 on 2026-03-27. Options/arb signals had
structurally low RR (≈0.005–0.025) far below all min_rr thresholds (≥1.2).

---

## 3. Per-Day Results

| Day | Date | Regime | Raw | Actual | Pred | Status |
|---|---|---|---|---|---|---|
|  1 | 2026-01-30 | bull_tre |  13 |  5 |  7 | GAP=+2 |
|  2 | 2026-02-02 | bull_tre |   7 |  1 |  1 | OK |
|  3 | 2026-02-03 | bull_tre |  12 |  4 |  6 | GAP=+2 |
|  4 | 2026-02-04 | bull_tre |   7 |  0 |  1 | GAP=+1 |
|  5 | 2026-02-05 | bull_tre |  10 |  3 |  4 | GAP=+1 |
|  6 | 2026-02-06 | bull_tre |  10 |  4 |  4 | OK |
|  7 | 2026-02-09 | bull_tre |  11 |  5 |  5 | OK |
|  8 | 2026-02-10 | bull_tre |  10 |  4 |  4 | OK |
|  9 | 2026-02-11 | bull_tre |  10 |  4 |  4 | OK |
| 10 | 2026-02-12 | bull_tre |   9 |  3 |  3 | OK |
| 11 | 2026-02-13 | bull_tre |   8 |  2 |  2 | OK |
| 12 | 2026-02-16 | bull_tre |   9 |  3 |  3 | OK |
| 13 | 2026-02-17 | bull_tre |   8 |  2 |  2 | OK |
| 14 | 2026-02-18 | bull_tre |  10 |  4 |  4 | OK |
| 15 | 2026-02-19 | bull_tre |   6 |  0 |  0 | OK |
| 16 | 2026-02-20 | range_ma |  12 |  6 |  6 | OK |
| 17 | 2026-02-23 | bull_tre |   8 |  2 |  2 | OK |
| 18 | 2026-02-24 | range_ma |  15 |  9 |  9 | OK |
| 19 | 2026-02-25 | bull_tre |   9 |  3 |  3 | OK |
| 20 | 2026-02-26 | bull_tre |   8 |  1 |  2 | GAP=+1 |
| 21 | 2026-02-27 | bull_tre |  11 |  4 |  5 | GAP=+1 |
| 22 | 2026-03-02 | range_ma |  14 |  8 |  8 | OK |
| 23 | 2026-03-04 | bear_mar |   6 |  0 |  0 | OK |
| 24 | 2026-03-05 | bull_tre |  10 |  2 |  4 | GAP=+2 |
| 25 | 2026-03-06 | bear_mar |   6 |  0 |  0 | OK |
| 26 | 2026-03-09 | volatile |  16 |  0 |  0 | OK |
| 27 | 2026-03-10 | range_ma |   9 |  3 |  3 | OK |
| 28 | 2026-03-11 | bear_mar |   6 |  0 |  0 | OK |
| 29 | 2026-03-12 | bear_mar |   6 |  0 |  0 | OK |
| 30 | 2026-03-13 | volatile |  10 |  0 |  0 | OK |

---

## 4. Regime Breakdown

| Regime | Days | Raw | Actual | Surv% | Day Acc | Max Gap |
|---|---|---|---|---|---|---|
| bull_trend | 20 | 186 |  56 | 30% | 65% | 2 |
| range_market |  4 |  50 |  26 | 52% | 100% | 0 |
| bear_market |  4 |  24 |   0 | 0% | 100% | 0 |
| volatile |  2 |  26 |   0 | 0% | 100% | 0 |

**Key observations:**
- RANGE days (4): 100% day-level accuracy. All equity signals survive strategy lab.
- BEAR days (4): 100% accuracy. Zero equity signals; options/arb rejected by D1.
- VOLATILE days (2): 100% accuracy. Equity rejects by D3; options/arb by D1.
- BULL days (21): 13/21 exact match.
  Gaps from RR check on equity signals (not available from trace).

---

## 5. Feature Availability

| Status | Count | Examples |
|---|---|---|
| AVAILABLE_EXACT | 8 | symbol, direction, strategy, confidence, regime, vol, vix |
| AVAILABLE_DERIVED | 2 | signal_type (from strategy), active_set (from regime+code) |
| AVAILABLE_PROXY | 2 | backtest gate (pass-through), shm_disabled (empty) |
| UNAVAILABLE | 3 | risk_reward_ratio, entry_price, target_price |

---

## 6. Accuracy Analysis

Signal-level: **96.5%** (276/286 correct)

| Category | Count | Correctly Reconstructed |
|---|---|---|
| Deterministic rejects (D1+D2+D3) | 194 | 194 (100%) |
| Indeterminate → actual PASS | 82 | 82 (100%) |
| Indeterminate → actual RR fail | 10 | 0 (unavailable) |

The 10 indeterminate-actual-fail cases are equity signals on
bull-trend days where the actual risk_reward_ratio was below the strategy min_rr threshold.
These cannot be classified without the original TradeSignal.risk_reward_ratio field.

---

## 7. Leakage Audit

All reconstruction rules pass no-look-ahead check: PASS  
- 
regime_available_before_lab: True- vol_level_available_before_lab: True- strategy_name_available_from_scanner: True- confidence_available_from_scanner: True- actual_strat_count_NOT_used_in_rules: True- rr_unavailable_confirmed: True- no_future_dates_in_regime: True- production_code_used_unchanged: True- d1_uses_only_strategy_name: True- d2_uses_only_regime_direction_type: True

---

## 8. Production Isolation

Broker/execution modules imported: None  
Broker orders placed: False  
Production DB modified: False  
VPS deployed: False

---

## 9. Verdict

**A — RECONSTRUCTION_VALIDATED**

The strategy gate logic is reconstructable at **96.5% signal-level accuracy**
(threshold: A ≥ 95%, B 85–94.9%, C < 85%).

This validation confirms:
1. The 286 → 82 funnel is real and traceable to 30 specific trace files.
2. The primary rejection mechanism is the OPTIONS/ARB RR check (no exemption in original code).
3. The regime mismatch gate explains a secondary but important rejection category.
4. The BEAR_EQUITY_BUY gate had zero activations in this replay dataset (bear days had equity=0).
5. The backtest gate was a complete pass-through (after_bt=assigned on all 30 days).

**Implication for KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE research:**
The 82 strategy-lab survivors are a valid population for incremental value analysis.
The reconstruction confirms their selection was governed by regime + signal-type rules,
not by look-ahead bias or data leakage.
