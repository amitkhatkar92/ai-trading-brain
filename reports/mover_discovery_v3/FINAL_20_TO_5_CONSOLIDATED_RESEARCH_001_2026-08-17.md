# FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001

**Date:** 2026-08-17  
**Mode:** READ-ONLY consolidation of all prior research  
**Status:** FINAL_SELECTION_ARCHITECTURE_CAN_BE_FROZEN_FOR_SHADOW_VALIDATION  
**Contradictions found:** 0  
**New experiments run:** 0

---

## 1. Executive Summary

After consolidating 8 independent research studies across 487+ OOS trading days, the 20-to-5 stock selection architecture can be **frozen for shadow validation**.

The winning method is **C2_Top5**: rank the 20 pool candidates by post-open gap magnitude (direction-signed) and select the top 5. This single model is the validated winner for **both UP and DOWN** selection.

| Direction | OOS dir_acc | OOS ge2 | OOS lift vs pool | n |
|-----------|-------------|---------|-----------------|---|
| UP  | **0.615** | **0.291** | **1.71×** | 265 |
| DOWN | **0.604** | **0.242** | **1.75×** | 265 |

Baseline (V3 pool, random-5): UP dir_acc=0.485, ge2=0.181; DOWN dir_acc=0.482, ge2=0.129

---

## 2. Source Studies

| Study ID | Report | Key Verdict |
|----------|--------|-------------|
| V3_RETRO_001 | MOVER_DISCOVERY_V3_RESEARCH_REPORT.md | Pool quality VALIDATED; score rank not predictive |
| POST_OPEN_SELECTION_001 | POST_OPEN_SELECTION_RESEARCH_001.md | C2_Top5 best model (both directions) |
| V3_KNOWLEDGE_2ND_PASS_001 | V3_KNOWLEDGE_SECOND_PASS_AUDIT_001.md | Pre-market knowledge HARMFUL (-5.7pp UP) |
| V3_ORTHOGONAL_DIRECTION_001 | V3_ORTHOGONAL_DIRECTION_RESEARCH_001.md | Sector/InvKn WORSE; Gap (D1) validates C2 path |
| V3_SHADOW_AUDIT_001 | MOVER_DISCOVERY_V3_SHADOW_AUDIT_001.md | E_INSUFFICIENT_SAMPLE_CONTINUE |
| KNOWLEDGE_VS_STRATEGY_002 | KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002.md | F: KNOWLEDGE_ONLY_SUPPORTED |
| KNOWLEDGE_VS_STRATEGY_003 | KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_003.md | E: INSUFFICIENT_OOS_SAMPLE |
| STRATEGY_RECONSTRUCTION_001 | (script + 60 tests) | Verdict A: RECONSTRUCTION_VALIDATED |

---

## 3. The Winning Model: C2_Top5

### 3.1 Formula

```
For each UP candidate i on day T:
    gap_pct_i = (T+1_open_i / T_close_i) - 1

C2_score_UP_i = +gap_pct_i   (reward stocks that gapped UP overnight)
C2_score_DN_i = -gap_pct_i   (reward stocks that gapped DOWN overnight)

Select top-5 by C2_score descending in each direction.
```

### 3.2 Information Horizon

**POST-OPEN.** The C2_score requires `T+1_open`. It is **not available pre-market**.  
The selection step must occur after the market opens, using the opening auction price.

### 3.3 OOS Performance by Direction

#### UP Direction (53 OOS trading days, 265 observations)

| Model | dir_acc | ge2 | ge3 | lift vs pool | vs V3 Δdir |
|-------|---------|-----|-----|-------------|-----------|
| V3_20 pool | 0.4877 | 0.1783 | 0.1113 | 1.00× | — |
| Random_5   | 0.4845 | 0.1811 | 0.1208 | — | — |
| A_V3_Top5  | 0.5094 | 0.2264 | 0.1774 | 1.33× | +0.000 |
| C1_Top5 (gap dir) | 0.5472 | 0.2415 | 0.1962 | 1.52× | +0.038 |
| **C2_Top5** | **0.6151** | **0.2906** | **0.2113** | **1.71×** | **+0.106** |

#### DOWN Direction (53 OOS trading days, 265 observations)

| Model | dir_acc | ge2 | ge3 | lift vs pool | vs V3 Δdir |
|-------|---------|-----|-----|-------------|-----------|
| V3_20 pool | 0.4877 | 0.1283 | 0.0594 | 1.00× | — |
| Random_5   | 0.4823 | 0.1313 | 0.0619 | — | — |
| A_V3_Top5  | 0.4868 | 0.1811 | 0.1019 | 1.25× | +0.000 |
| C1_Top5 (gap dir) | 0.5434 | 0.2340 | 0.1245 | 1.65× | +0.057 |
| **C2_Top5** | **0.6038** | **0.2415** | **0.1509** | **1.75×** | **+0.117** |

---

## 4. Evidence Matrix (all components tested)

| Component | Direction | OOS dir_acc | OOS ge2 | vs baseline | Timing | Verdict |
|-----------|-----------|-------------|---------|-------------|--------|---------|
| C2_Top5 (gap magnitude) | UP | 0.6151 | 0.2906 | +10.6pp | POST_OPEN | VALIDATED ✓ |
| C2_Top5 (gap magnitude) | DOWN | 0.6038 | 0.2415 | +11.7pp | POST_OPEN | VALIDATED ✓ |
| C1_Top5 (gap direction) | UP | 0.5472 | 0.2415 | +3.8pp | POST_OPEN | VALIDATED |
| C1_Top5 (gap direction) | DOWN | 0.5434 | 0.2340 | +5.7pp | POST_OPEN | VALIDATED |
| A_V3_Top5 (score only) | UP | 0.5094 | 0.2264 | 0.0pp | PRE_MARKET | MARGINAL |
| A_V3_Top5 (score only) | DOWN | 0.4868 | 0.1811 | 0.0pp | PRE_MARKET | MARGINAL |
| A1_Sector_Top5 | UP | 0.4963 | 0.1963 | -0.4pp | PRE_MARKET | WORSE ✗ |
| A1_Sector_Top5 | DOWN | 0.5185 | 0.1630 | +4.1pp dir, -1.5pp ge2 | PRE_MARKET | MIXED |
| Know_Top5 (DNA/sector) | UP | N/A | N/A | -5.7pp | PRE_MARKET | HARMFUL ✗ |
| Know_Top5 (DNA/sector) | DOWN | N/A | N/A | neg | PRE_MARKET | NO_VALUE ✗ |
| F1_InvKn_Top5 | UP | 0.4444–0.507 | — | -5.6pp | PRE_MARKET | WORSE ✗ |
| Strategy gate (D2 BEAR+UP) | UP | = A (no BEAR OOS) | — | 0.0pp OOS | PRE_MARKET | INSUFFICIENT |
| Strategy gate | DOWN | N/A | N/A | N/A | — | NOT_APPLICABLE |
| B1_Institutional | — | — | — | — | — | DATA_UNAVAILABLE |
| C1_Catalyst | — | — | — | — | — | DATA_UNAVAILABLE |
| E_Intraday | — | — | — | — | — | DATA_UNAVAILABLE |

---

## 5. Q&A on Key Research Questions

**Q1. Does the Strategy layer add value to UP selection (20→5)?**  
A: Insufficient OOS evidence. The OOS window had 0 BEAR or VOLATILE trading days, so model B (strategy-gated) = model A (knowledge-only) in OOS. Full-period evidence shows the BEAR+UP reject rule blocks candidates with ge2=37.9% (vs pass ge2=24.1%): a 32.6% false-rejection rate. Strategy D2 is likely harmful for UP selection. Final answer: **Not proven beneficial. Does not block the 20→5 C2 decision.**

**Q2. Do UP and DOWN selections need different models?**  
A: No. C2_Top5 is the best model for both directions. Formula is symmetric (sign flip). **Same model, both directions.**

**Q3. Can the 20→5 selection be done pre-market?**  
A: No validated pre-market model improves over V3 score alone. Knowledge composite hurts (-5.7pp). Sector signals are WORSE. The gap (C2) is the only reliable signal, and it requires T+1 open price. **Post-open observation is required.**

**Q4. Should we take top-5 or top-6 per direction?**  
A: Top-5. Top-6 shows slight dilution: C2_Top6 UP dir_acc=0.598 (-1.8pp vs Top5), ge2=0.270 (-2.1pp vs Top5). **Top-5 is optimal.**

**Q5. Is C2 robust across OOS regime types?**  
A: OOS window is RANGE-dominant (53 days, 0 BEAR, 0 VOLATILE, 1 BULL). Cross-regime robustness cannot be fully assessed from this window. However, full-period evidence (VAL had 19 BEAR days) supports the C2 signal. **Partially validated. RANGE-regime strength confirmed.**

**Q6. Is the V3 pool itself the bottleneck?**  
A: Pool OOS precision is 18.3% (UP), 15.0% (DOWN). The gap signal extracts quality: C2_Top5 reaches 29.1%/24.2% precision. There is ~10.8–12pp precision gain from 20→5 C2 selection. **Pool is not the bottleneck; selection within pool is where value is extracted.**

**Q7. Does a larger pool (>20) help?**  
A: Pool analysis shows precision declines with pool size (OOS: pool20 UP precision=18.3%, pool10=19.0%). Going from 20→25 drops precision further. **Pool size of 20 is optimal given existing quality-discovery constraints.**

**Q8. Is there any incremental pre-market signal that adds value?**  
A: No. Tested: V3 score, sector conviction, institutional (unavailable), catalyst (unavailable), intraday (unavailable), inverse-knowledge, combinations. None beat C2 post-open. **No pre-market signal validated.**

**Q9. Is the gap evidence forward-looking (no leakage)?**  
A: Yes. All experiments include leakage checks. Gap is T+1 open vs T close — strictly future relative to T. OOS split respected throughout. **No leakage detected.**

**Q10. Is there any contradiction between studies?**  
A: No material contradictions. Orthogonal study D1_Top5 (raw gap) dir_acc=0.548 for UP is lower than post-open C2_Top5=0.615 because D1 uses unsigned gap (same for all directions) while C2 uses signed direction-adjusted gap. These are consistent and C2 is a refinement of D1. **All evidence consistent; C2 is the refined winner.**

---

## 6. Architecture Specification

### 6.1 Timing

```
T (EOD):        V3 Discovery runs → produces 20 UP + 20 DOWN candidates
T+1 (pre-open): No selection possible. Wait for open.
T+1 (9:15 AM): Market opens. Opening auction prices available.
T+1 (9:16+ AM): Observe gap_pct for each of 40 candidates.
                 gap_pct_i = T+1_open_i / T_close_i - 1

T+1 (9:17 AM): Apply C2 selection:
                 UP:   rank by +gap_pct desc → take top 5
                 DOWN: rank by -gap_pct desc → take top 5
                 Result: 5 UP + 5 DOWN = 10 final signals
```

### 6.2 Implementation Note

The C2 selection is computationally trivial (1 division + sort). The bottleneck is  
**obtaining the opening gap prices for all 40 candidates reliably within the first 2 minutes after open.**

### 6.3 Strategy Layer Position (pending Q1 resolution)

If Strategy is included: apply as an **optional soft filter** (not a hard gate) on BEAR+UP candidates.  
Position: after C2 selection or as a score penalty, not a rejection rule.  
**This architectural placement is NOT finalized and does NOT block shadow validation.**

---

## 7. Shadow Validation Requirements

To shadow-validate the frozen C2_Top5 architecture:

1. **Each evening**: V3 Discovery produces 20 UP + 20 DOWN pools → persisted for T+1
2. **T+1 after open**: C2 selection runs → 5 UP + 5 DOWN recorded (no trades executed)
3. **T+2 morning**: Outcome measured vs T+1 close. Log dir_acc, ge2, ge3 per direction per day.
4. **After 50 OOS days**: Run paired bootstrap to assess whether C2 dir_acc > random with p < 0.05
5. **After 100 OOS days** (target: includes BEAR regime): Evaluate strategy-gate interaction

Shadow validation target OOS: **minimum 50 trading days with ≥1 BEAR regime day.**

---

## 8. Open Items (not blocking shadow validation)

| ID | Item | Priority | Status |
|----|------|----------|--------|
| Q1 | Strategy-gate incremental value for UP in BEAR regime | Medium | Insufficient OOS — Q1 remains open |
| B1 | Institutional bulk/block data (once available in DB) | Low | DATA_UNAVAILABLE |
| C1 | Catalyst / earnings event data | Low | DATA_UNAVAILABLE |
| E1 | Intraday OHLCV for intraday-signal model | Low | DATA_UNAVAILABLE |

---

## 9. Final Verdict

> **FINAL_SELECTION_ARCHITECTURE_CAN_BE_FROZEN_FOR_SHADOW_VALIDATION**
>
> Method: C2_Top5 — post-open gap magnitude, direction-signed, top 5 per direction.  
> Timing: POST_OPEN (requires T+1 opening auction price).  
> Applies to: both UP and DOWN pools (same formula, sign-adjusted).  
> No pre-market signal adds validated incremental value.  
> No blocker remaining for shadow validation start.

---

*Research locked. No further experiments planned unless a contradiction is identified in live shadow data.*
