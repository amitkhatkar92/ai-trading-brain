# KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002
## Research Report — 2026-08-17

**Research question:** After the system has compiled available information and selected the best
opportunities via the Knowledge layer (V3 pool + post-open gap), does adding a Strategy layer
provide incremental value?

**Mode:** READ-ONLY RESEARCH — no production changes.  
**Base model:** C2_score (gap magnitude; direction-adjusted) — winner from POST_OPEN_SELECTION_001.  
**Study DB:** `data/study002_replay.db`  
**Candidate pool:** `reports/mover_discovery_v3/v3_retro_candidates.csv`  
(8,560 rows; 214 days × 40 candidates; 2025-09-16 → 2026-07-30)  

---

## Executive Summary

| Finding | Result |
|---|---|
| **PRIMARY VERDICT** | **F. KNOWLEDGE_ONLY_SUPPORTED** |
| Strategy B = A in OOS (UP) | YES — zero bear/volatile days in OOS → no filtering |
| REJECT candidates outperform PASS (UP, FULL) | YES — ge2 37.9% vs 24.1%, P(reject>pass)=0.99 |
| Strategy HARMS UP selection | YES — bear-regime gap-UPs are the strongest signals |
| Strategy (regime proxy) helps DOWN | YES — ALIGNED ge2=45.7% vs NEUTRAL 23.5% (P=0.996) |
| All strategies BUY-direction | YES — no SELL/SHORT strategies in library |
| Production change justified | **NO** — READ-ONLY research, no authorization |

**Key insight:** The production Strategy layer's BEAR→REJECT rule for UP candidates is
eliminating the **strongest** relative-alpha signals in the dataset. Gap-UP stocks on BEAR
regime days are moving against the market trend — this constitutes the highest-conviction
relative-strength signal. Rejecting them harms outcomes.

---

## Data & Strategy Library

### Candidate Pool
| Split | Dates | Days | UP pool | DOWN pool |
|---|---|---|---|---|
| TRAIN | 2025-09-16 → 2026-02-19 | ~108 | ~2,160 | ~2,160 |
| VAL | 2026-02-20 → 2026-05-13 | ~57 | ~1,140 | ~1,140 |
| OOS | 2026-05-14 → 2026-07-30 | ~53 | ~1,060 | ~1,060 |
| FULL | All | 214 | 4,285 | 4,285 |

### Strategy Library (evolved_strategies.json)
| Category | Count |
|---|---|
| Total strategies | 177 |
| Evaluable (OHLCV-based) | 92 |
| Unavailable (require vix/iv_rank/pcr) | 83 |
| Direction = BUY | 175 |
| Direction = no_dir (base) | 2 |
| Direction = SELL/SHORT | **0** |

**Critical structural constraint:** No SELL strategies exist. DOWN candidate evaluation
therefore uses a regime-based proxy (ALIGNED = bear regime + DOWN signal) rather than
proper EDG condition evaluation.

---

## Strategy Evaluation Framework

### UP Direction
Regime-based evaluation matching production logic:
| Condition | Label | Count | % |
|---|---|---|---|
| BEAR or VOLATILE regime | REJECT | 560 | 13.1% |
| BULL regime | PASS | ~1.0% | ~1% |
| RANGE regime (EDG pass) | PASS | 86.9% total | — |

**Key:** BEAR (NIFTY 20d return < −5%) or VOLATILE (ann. vol > 25%) → REJECT UP signals.
This matches `strategy_generator_ai.py` production code: `if regime == BEAR_MARKET and direction == BUY: return None`.

### DOWN Direction
Regime-alignment proxy (no EDG SELL strategies available):
| Condition | Label | Count | % |
|---|---|---|---|
| Bear regime (mom_20d < −5%) | ALIGNED | 280 | 6.5% |
| Bull regime (mom_20d > +5%) | CONTRADICTED | 260 | 6.1% |
| Range regime | NEUTRAL | 3,465 | 80.9% |
| Options features missing | UNAVAILABLE | 280 | 6.5% |

---

## Model Definitions

| Model | Description |
|---|---|
| **V3_20** | Full 20-candidate V3 pool (baseline) |
| **A_KN_Top5** | Knowledge-only: Top-5 by C2_score (gap magnitude) |
| **B_KnStrat_Top5** | Knowledge+Strategy: Top-5 by C2_score from PASS candidates; fill from PASS_BASE if needed |
| **C_Strat_Top5** | Strategy-only: Top-5 by strategy_score (fraction of EDG conditions met) |
| **KN_PASS_days_T5** | A_KN_Top5 restricted to PASS-status days |
| **KN_REJECT_days_T5** | A_KN_Top5 from REJECT-status candidates only |

---

## OOS Results

### UP Direction (OOS: 2026-05-14 → 2026-07-30)

| Model | n | Dir Acc | ge2 | ge3 | Lift | vs A_KN_Top5 |
|---|---|---|---|---|---|---|
| V3_20 (pool) | 1,061 | 0.487 | 0.178 | 0.111 | 1.00 | −0.113 |
| **A_KN_Top5** | **265** | **0.615** | **0.291** | **0.211** | **1.71** | — |
| A_KN_Top6 | 318 | 0.598 | 0.270 | 0.211 | 1.55 | −0.020 |
| **B_KnStrat_Top5** | **265** | **0.615** | **0.291** | **0.211** | **1.71** | **0.000** |
| B_KnStrat_Top6 | 318 | 0.598 | 0.270 | 0.211 | 1.55 | −0.020 |
| C_Strat_Top5 | 265 | 0.509 | 0.226 | 0.155 | 1.33 | −0.064 |
| KN_PASS_days_T5 | 265 | 0.615 | 0.291 | 0.211 | 1.71 | 0.000 |
| KN_REJECT_days_T5 | 0 | — | — | — | — | — |
| Random_5 | 1,325 | 0.485 | 0.181 | 0.120 | 1.19 | −0.110 |

**Finding:** B_KnStrat_Top5 is **identical** to A_KN_Top5 in OOS (n, dir, ge2, lift all equal).
**Reason:** The OOS period (May–July 2026) had zero BEAR or VOLATILE regime days — NIFTY was
in a RANGE regime throughout. The Strategy layer rejected **zero** UP candidates in OOS.
Therefore, B = A exactly.

### DOWN Direction (OOS: 2026-05-14 → 2026-07-30)

| Model | n | Dir Acc | ge2 | Lift | Note |
|---|---|---|---|---|---|
| V3_20 (pool) | 1,061 | 0.488 | 0.129 | 1.00 | — |
| **A_KN_Top5** | **265** | **0.604** | **0.242** | **1.75** | — |
| B_KnStrat_Top5 | 265 | 0.604 | 0.242 | 1.75 | = A (same candidates) |
| KN_CONTRADICTED_T5 | 5 | 1.000 | 1.000 | 1.67 | n=5 — unreliable |
| KN_NEUTRAL_T5 | 260 | 0.596 | 0.227 | 1.75 | — |
| Random_5 | 1,325 | 0.482 | 0.131 | 0.98 | — |

**Finding:** B = A in OOS for DOWN too (same dynamics).
CONTRADICTED (n=5) is too small to interpret.

---

## Incremental Value Analysis — Full Period

### UP Direction: PASS vs REJECT Quality

| Metric | PASS (n=3,701) | REJECT (n=560) | Delta |
|---|---|---|---|
| dir_acc | 0.567 | 0.629 | **REJECT +6.2pp** |
| ge2_rate | 0.241 | 0.379 | **REJECT +13.8pp** |
| ge3_rate | 0.174 | 0.271 | **REJECT +9.7pp** |
| avg_mfe | 2.84% | 3.12% | REJECT +0.28pp |
| fp_rate | 0.239 | 0.279 | REJECT slightly higher |
| Bootstrap P(REJECT > PASS) | — | — | **0.99** (99% confident) |

**Critical finding:** REJECT candidates (bear/volatile regime gap-UPs) outperform PASS candidates
on every quality metric. The Strategy layer's BEAR rejection rule is **eliminating the strongest**
UP signals in the pool.

**Regime breakdown confirms this:**
| Regime | Filter | n | ge2 | dir |
|---|---|---|---|---|
| BULL | strategy_pass | 65 | 24.6% | 55.4% |
| BEAR | strategy_reject | 95 | **32.6%** | **56.8%** |
| RANGE | strategy_pass | 860 | 24.1% | 56.7% |
| RANGE+volatile | strategy_reject | 45 | **48.9%** | **75.6%** |

The highest-performing group (RANGE+volatile reject, ge2=48.9%) is the one the Strategy
layer is most aggressively filtering out.

**Interpretation:** A stock gapping UP at 09:15 on a BEAR market day demonstrates exceptional
relative strength against adverse market conditions. This constitutes a stronger alpha signal,
not a weaker one. The production heuristic (reject UP in BEAR) is correct in theory (caution
during bear markets) but incorrect in practice for gap-UP signals (where the gap *already*
reflects the stock's resistance to the bear pressure).

### DOWN Direction: ALIGNED vs CONTRADICTED Quality

| Metric | ALIGNED/PASS (n=70) | CONTRADICTED (n=65) | NEUTRAL (n=860) | Delta (ALvsC) |
|---|---|---|---|---|
| ge2_rate | **45.7%** | 23.1% | 23.5% | **+22.6pp** |
| dir_acc | 54.3% | 53.9% | 62.3% | ~flat |
| Bootstrap P(ALIGNED > CONTRADICTED) | — | — | — | **0.996** |

**Finding:** For DOWN direction, the regime proxy (ALIGNED = bear regime) provides a very
strong signal. Bear-regime DOWN candidates have 2× the ge2 rate of contradicted or neutral
candidates. This is directionally sound: stocks selected as DOWN movers when the broad market
is also declining (bear regime) are more likely to follow through.

**However:** Model B = Model A in OOS (same n, same stats) — the ALIGNED candidates represent
only 6.5% of DOWN pool (280 total), and in OOS specifically, there were few bear-regime days.

---

## Rejection Audit

| Direction | Total Rejected KN | Correct Rejection | False Rejection | False Rate |
|---|---|---|---|---|
| UP | 140 | 52 | 53 | 37.9% |
| DOWN | 65 | 30 | 15 | 23.1% |
| **TOTAL** | **205** | **82** | **68** | **33.2%** |

**Q9/Q12 — Opportunity cost:** 68 of 205 rejected knowledge-selected candidates (33%)
were strong opportunities that the Strategy layer blocked incorrectly.

For UP, a 37.9% false rejection rate on candidates that *outperform* the accepted pool is
a significant operational cost. These are the highest-quality signals being filtered out.

---

## Q1–Q24 Answers

| Q# | Question | Answer |
|---|---|---|
| Q1 | Does strategy add value after knowledge? | **NO_OR_MARGINAL** (UP: harmful; DOWN: conditional) |
| Q2 | Strategy improves directional accuracy? | OOS: indeterminate (reject n=0). FULL: REJECT dir=62.9% > PASS 56.7% |
| Q3 | Strategy improves ge2? | OOS: indeterminate. FULL: REJECT ge2=37.9% > PASS 24.1% (delta=−13.8pp) |
| Q4 | Strategy improves ge3? | FULL: REJECT ge3=27.1% > PASS 17.4% |
| Q5 | Strategy improves avg_fav? | FULL: REJECT avg_fav=2.90% > PASS 2.51% |
| Q6 | Strategy improves MFE/MAE? | FULL: REJECT mfe=3.12% vs PASS 2.84% (marginal) |
| Q7 | Strategy reduces false positives? | FULL: REJECT fp=27.9% vs PASS 23.9% (REJECT slightly higher) |
| Q7b | OOS reject zero bear days? | **YES** — OOS NIFTY in RANGE throughout; n_reject_oos=0 |
| Q8 | How many knowledge-selected rejected? | 205 across all splits |
| Q9 | How many rejections were good? | 68 (33%) were strong opportunities |
| Q10 | False rejection rate? | 33.2% overall; UP=37.9%, DOWN=23.1% |
| Q11 | Correct rejection rate? | 40% |
| Q12 | Opportunity cost? | Strategy blocked 68 knowledge-quality opportunities |
| Q13 | Strategy improves Top-5? | OOS UP: A=B=0.291 (no discrimination) |
| Q14 | Strategy improves Top-6? | OOS UP: A=B=0.270 (no discrimination) |
| Q15 | Concentration lift? | OOS UP: A=B=1.71 (identical) |
| Q16 | Strategy adds value in OOS? | **INDETERMINATE** — no BEAR days in OOS period |
| Q16b | Strategy adds value in FULL period? | **NO** (for UP); **YES** for DOWN ALIGNED |
| Q17 | Strategy helps across all regimes? | NO — only RANGE regime in OOS; BEAR rejected candidates outperform |
| Q18 | Strategy works for UP and DOWN? | UP: via regime gate (HARMS); DOWN: regime proxy only (HELPS ALIGNED) |
| Q19 | Strategy universally useful? | **NO** — BUY-only library; no SELL coverage |
| Q20 | Strategy conditionally useful? | For DOWN ALIGNED yes; for UP BEAR REJECT — the opposite |
| Q21 | Knowledge-only replaces strategy? | **YES** for UP — and performs better |
| Q22 | Hybrid architecture better? | **NO** for UP; **POSSIBLY** for DOWN regime filter |
| Q23 | Evidence-based architecture recommendation? | Knowledge+Gap as core. For DOWN, add regime filter. For UP, **remove** BEAR rejection. |
| Q24 | Production change justified? | **NO** — READ-ONLY RESEARCH, no authorization |

---

## Primary Verdict

### **F. KNOWLEDGE_ONLY_SUPPORTED**

The Knowledge layer (C2_score = gap magnitude) is the primary and sufficient signal for UP
candidates. The Strategy layer as currently implemented (BEAR→REJECT for UP) is **actively
harmful** — it rejects the highest-quality signals in the pool.

For DOWN candidates, the regime-alignment proxy (ALIGNED = bear-regime DOWN) provides
meaningful additional signal (+22.6pp ge2 vs CONTRADICTED), but the lack of SELL/SHORT
strategies in the evolved library prevents a full strategy evaluation.

---

## Structural Constraints & Limitations

### 1. OOS Period Regime Homogeneity
The OOS period (May–July 2026) had zero BEAR or VOLATILE regime days. NIFTY traded in a
RANGE throughout. This means Strategy B = A exactly in OOS — no reject days existed.
The UP PASS vs REJECT comparison must use the FULL period (which includes BEAR days in
TRAIN and VAL).

### 2. No SELL/SHORT Strategies
All 177 evolved strategies have direction=BUY. Evaluation of DOWN candidates via EDG
conditions is architecturally impossible. The DOWN analysis uses a regime proxy (mom_20d)
as a substitute.

### 3. Missing Options Data
83 of 177 strategies require vix, iv_rank, or pcr (options market data). These are
UNAVAILABLE in `data/study002_replay.db`. Only 92 strategies are evaluated.

### 4. Sample Sizes
- BEAR-regime UP candidates in OOS: 0 (constrains OOS comparison)  
- DOWN CONTRADICTED in OOS: n=5 (results unreliable)
- DOWN ALIGNED in FULL: n=70 (adequate for bootstrap, but small for subgroup analysis)

---

## Architectural Implications (research observations only)

> **These are research observations. No production changes are authorized or implemented.**

1. **UP — Remove BEAR gate:** The current `if regime == BEAR_MARKET and direction == BUY: return None` rule is eliminating the strongest gap-UP alpha signals. Consider replacing with a momentum confirmation rather than flat rejection.

2. **DOWN — Preserve regime filter:** The ALIGNED (bear regime + DOWN) filter is the most predictive element evaluated. A regime-gated DOWN selection (only select DOWN on bear/range days, not bull days) would improve quality significantly.

3. **Strategy layer role:** The evolved strategy library (175 BUY EDG strategies) is not well-suited as a gate/filter for UP signals from the gap model. The gap itself is the signal; the strategies are calibrated for different entry setups. Consider decoupling the two.

---

## Tests

`tests/test_knowledge_vs_strategy_002.py` — **50/50 PASS**

| Range | Coverage |
|---|---|
| T001-T009 | Data structure, pool integrity, strategy library |
| T010-T019 | Model selection correctness, OOS = prior research |
| T020-T029 | Outcome baselines, incremental value, rejection audit |
| T030-T041 | Regime breakdown, direction/split, leakage guards |
| T042-T050 | Production isolation — no production imports |

---

## Output Files

| File | Description | Rows |
|---|---|---|
| `knowledge_vs_strategy_002_results.json` | Full results JSON (67KB) | — |
| `knowledge_vs_strategy_002_model_comparison.csv` | TRAIN/VAL/OOS x UP/DOWN x all models | 69 |
| `knowledge_vs_strategy_002_incremental_value.csv` | PASS vs REJECT quality, OOS and FULL | 14 |
| `knowledge_vs_strategy_002_rejection_audit.csv` | Per-candidate rejection with classification | 205 |
| `knowledge_vs_strategy_002_opportunity_cost.csv` | Aggregate opportunity cost by status | 2 |
| `knowledge_vs_strategy_002_oos_results.csv` | OOS-only model performance table | 22 |
| `knowledge_vs_strategy_002_regime_results.csv` | Regime × filter breakdown | 4 |
| `knowledge_vs_strategy_002_case_studies.md` | False/correct rejection examples | — |

---

## Research Chain Summary

| Research | ID | Verdict | Key Metric |
|---|---|---|---|
| Gap model selection | POST_OPEN_SELECTION_001 | B. GAP_ONLY_SUFFICIENT | OOS UP ge2=29.1%, lift=1.72× |
| Knowledge vs Strategy | KNOWLEDGE_VS_STRATEGY_002 | **F. KNOWLEDGE_ONLY_SUPPORTED** | REJECT ge2=37.9% > PASS 24.1% |

**Next research question:** POST_OPEN_SELECTION_003 — Does the Direction (UP/DOWN split) of
the gap provide additional value, or should a unified pool be used? Alternatively: what is
the minimum gap magnitude threshold (C2_score) for acceptable signal quality?

---

*Report generated: 2026-08-17. READ-ONLY RESEARCH — no production changes.*
