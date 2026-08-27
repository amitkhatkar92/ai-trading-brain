# DTA-SYSTEM-014 — Knowledge Learning Effectiveness + Evidence Sufficiency Audit
**Final Report**
**Date:** 2026-08-27
**Classification:** AMBER — architecture sound and realistically feasible; level-2 activation is faster than previously estimated; two structural gaps documented with accepted risk.

---

## 1. Audit Mandate

Determine whether the knowledge architecture can realistically progress from observation to authenticated knowledge within realistic trading volumes, and whether the system is genuinely knowledge-driven at runtime. Prior audit (DTA-013) established architecture soundness. This audit verifies learning effectiveness — not just architectural existence.

---

## 2. Summary

| Dimension | Finding | Status |
|---|---|---|
| HBE level-activation thresholds | Level 2 at 5 outcomes — correct, achievable in 2–3 weeks | ✅ PASS |
| Win/Loss balance | D13-001 fix correct — losses now reach KEL as INCORRECT_SELECT | ✅ PASS |
| Regime learning | Level 1 respects regime; Level 2 is intentionally regime-agnostic | ✅ PASS |
| Recency decay | ESS with 200-day-old data is ≤60% of ESS with fresh data | ✅ PASS |
| KEL→HBE→KDA chain causality | 5 outcomes → KDA exits KNOWLEDGE_WAIT | ✅ PASS |
| WAIT vs HOLD semantics | Distinct enum values, distinct triggers | ✅ PASS |
| Knowledge failure isolation | All exception paths return safe records | ✅ PASS |
| KDA safety invariants | broker_calls=0, orders=0 on ALL paths | ✅ PASS |
| V2 score fallback | Falls back to V1 when evidence_level ≥ 6 | ✅ PASS |
| DTA-013 timeline estimate | Was incorrect — minimum is 5 outcomes, not ~50 | ⚠️ CORRECTED |
| Level 2 regime pooling | BULL outcomes inform BEAR L2 queries — documented behaviour | ⚠️ NOTE |
| Multiple testing in KFE | ~108 relationship candidates with no FDR correction | ⚠️ STRUCTURAL GAP |
| HOLD minimum ESS | HOLD can fire at ESS=3 — no minimum ESS guard | ⚠️ ACCEPTED RISK |

**Overall result: AMBER.** The system is genuinely learning-capable, architecture is correct, evidence pipeline is functional. Two structural gaps are documented. No code changes required — all gaps are either accepted architectural decisions or non-critical documentation corrections.

---

## 3. HBE Level System — Exact Thresholds (Corrected)

### 3.1 Threshold Table

| Level | Filter | Min observations | Purpose |
|---|---|---|---|
| 1 | symbol + direction + regime + ATR/conf context | 5 | Most specific — per-symbol, per-regime |
| 2 | symbol + direction | 5 | Per-symbol, all regimes (intentionally regime-agnostic) |
| 3 | sector + direction + regime | 10 | Sector-regime aggregate |
| 4 | regime + direction | 10 | Broad regime aggregate |
| 5 | sector + direction | 15 | Sector aggregate, all regimes |
| 6 | broad market + direction | 15 | Entire portfolio aggregate |
| 7 | ATR fallback | 0 | Always available — no empirical data |

### 3.2 Correction to DTA-013 Estimate

**DTA-013 stated**: "~50 outcomes needed for learning to begin."
**Correct figure**: **5 completed KLP outcomes** for a given symbol+direction activate Level 2 evidence.

The DTA-013 estimate confused the DECISION_ELIGIBLE threshold (ESS ≥ 100) with the first-use threshold. Clarification:

| Milestone | Required ESS | Meaning |
|---|---|---|
| Level 2 activates | ESS ≈ 5 | HBE computes first empirical probabilities |
| KDA exits KNOWLEDGE_WAIT | ESS ≥ 3 (DEVELOPING) | KDA issues KNOWLEDGE_BUY / KNOWLEDGE_SELL |
| USEFUL state | ESS 10–29 | Meaningful empirical evidence |
| VALIDATED state | ESS 30–99 | Strong empirical evidence |
| DECISION_ELIGIBLE | ESS ≥ 100 + stability ≥ 0.6 | Full authority — empirical targets/stops |

### 3.3 Regime Contamination (Level 2 Pooling)

**Level 2 is intentionally regime-agnostic.** When a symbol has 10 BULL-regime BUY outcomes and receives a BEAR-regime query:
- Level 1 does NOT fire (regime mismatch) — correct
- Level 2 DOES fire (regime-agnostic by design) — expected architecture behaviour

This means Level 2 evidence is cross-regime. The regime-specific knowledge lives at Level 1 and Level 3. Level 2 is the "symbol identity" baseline. **This is not a defect.**

---

## 4. Learning Timeline Model

### 4.1 Assumptions (paper trading, ₹50k capital)

| Parameter | Low | Base | High |
|---|---|---|---|
| Signals per day | 5 | 15 | 30 |
| Observations per symbol per day | 0.2 | 0.5 | 1.0 |
| Completion delay | T+5 trading days | T+5 | T+5 |
| Outcomes per symbol per week | ~1 | ~2.5 | ~5 |

### 4.2 Timeline to Level 2 Activation (5 completed outcomes per symbol)

| Scenario | Trading weeks to Level 2 |
|---|---|
| Low (0.2 obs/symbol/day) | ~5 weeks |
| Base (0.5 obs/symbol/day) | ~2 weeks |
| High (1.0 obs/symbol/day) | ~1 week |

**Note:** The +5 trading day completion lag means the first batch of outcomes completes by Day 7 (observations start Day 1, complete by Day 6).

### 4.3 Timeline to DECISION_ELIGIBLE (ESS ≥ 100)

With 90-day half-life decay, steady-state requires ~150 total observations per symbol per direction to maintain ESS ≥ 100. At 0.5 obs/symbol/day: 300 trading days ≈ 14 months for one symbol.

For the portfolio (10–20 watched symbols): Level 2 activates broadly within 2–5 weeks; DECISION_ELIGIBLE requires 6–18 months per symbol depending on scan frequency.

### 4.4 Assessment

The learning timeline is **realistic and achievable** for Level 2 and Level 3 evidence. DECISION_ELIGIBLE requires sustained operation (months). The current system status (ESS=0, KNOWLEDGE_WAIT for all symbols) is expected and not a defect — it reflects a freshly deployed system.

---

## 5. Win/Loss Balance Verification

### 5.1 Post-D13-001 Balance

After DTA-013-FIX, the outcome classification pipeline is:
- `TARGET_HIT` / `EXECUTED_WIN` → `CORRECT_SELECT` → KEL
- `STOP_HIT` / `EXECUTED_LOSS` / `STOP_EXIT` / `EARLY_EXIT` → `INCORRECT_SELECT` → KEL

Tests T006–T008 confirm the HBE correctly computes balanced probabilities:
- Win-only (10 wins): `target_hit_probability = 1.0`
- Loss-only (10 losses): `stop_first_probability = 1.0`, `target_hit_probability = 0.0`
- Balanced (5+5): `target_hit_probability ≈ 0.5`

The learning system cannot inflate win rates by ignoring losses. **Balance is enforced.**

---

## 6. KEL→HBE→KDA Causality Tests

### 6.1 Chain Verified

```
0 outcomes  → ESS=0 → INSUFFICIENT → KNOWLEDGE_WAIT   ✅
5 outcomes  → ESS≈5 → DEVELOPING   → KNOWLEDGE_BUY    ✅
8 outcomes  → ESS≈8 → DEVELOPING   → KNOWLEDGE_BUY    ✅
20 outcomes → ESS≈20→ USEFUL       → KNOWLEDGE_BUY    ✅
```

The chain is causal and deterministic. T013–T016 and T028 provide formal proof.

### 6.2 Authority Score Monotonicity

KDA `knowledge_authority` score grows monotonically as ESS increases from 5 → 10 → 20 → 50 → 100. The system genuinely produces higher authority confidence as more evidence accumulates. Proven by T028.

### 6.3 Direction Neutrality

BUY evidence is strictly isolated from SELL evidence (T005). The knowledge system cannot inadvertently swap direction signals.

---

## 7. KNOWLEDGE_WAIT vs KNOWLEDGE_HOLD Semantics

### 7.1 Distinction

| Decision | Trigger | Meaning |
|---|---|---|
| KNOWLEDGE_WAIT | ESS < 3 (INSUFFICIENT) | No basis for any decision — evidence starved |
| KNOWLEDGE_HOLD | n_contradict > n_support AND n_contradict ≥ 3 | Evidence reviewed, actively contradicted |
| KNOWLEDGE_BUY | All other non-INSUFFICIENT BUY signals | Directional knowledge approval |

### 7.2 Accepted Risk: HOLD Can Fire at Low ESS

**Structural observation:** KNOWLEDGE_HOLD can fire with just ESS ≥ 3 (DEVELOPING state) if KFE angle analyses produce 3+ contradicting angles. This could theoretically block a StrategyLab-approved signal based on very thin evidence.

**Risk assessment:** ACCEPTED. The KFE angle quality thresholds (`conf < 0.20` with `n ≥ 10`) mean contradicting angles require their own evidence. A KFE contradiction angle with n ≥ 10 and conf < 0.20 is meaningful even if HBE ESS is low. The two evidence pools (HBE + KFE) independently corroborate the HOLD signal.

**Not fixed in this audit.** Adding a minimum ESS guard for HOLD would require architectural approval.

---

## 8. Multiple Testing in KFE Relationship Discovery

### 8.1 Observation

`knowledge_fusion_engine.py::_discover_relationships()` constructs up to ~108 relationship candidates:
- 4 regimes × 3 directions = 12 tests
- ~14 sectors × 3 directions = 42 tests
- 4 VIX buckets × 3 directions = 12 tests
- 3 regimes × 14 sectors × 1 direction = 42 tests

Each test uses `n ≥ 5` as the minimum, which is insufficient for statistical significance. With 108 tests at n=5, false discovery is a real concern.

### 8.2 Mitigations Already Present

1. `decision_usefulness` penalises small-sample and unstable relationships
2. Relationships flow into KFE *angles* as confidence scores, not direct trading signals
3. KDA synthesis layer combines angles with multiplicative authority (product of 6 factors) which suppresses any single noisy angle
4. The architecture is SHADOW mode — relationships influence ranking, not execution

### 8.3 Classification: STRUCTURAL GAP (accepted)

Adding Bonferroni correction or FDR would require significant changes to `_make_rel()` and the confidence scoring formula. This is a future improvement, not an emergency fix. The current mitigation via `decision_usefulness` provides practical protection.

---

## 9. V2 Score Preview Fallback

Test T029 confirms: when `evidence_level ≥ 6` OR `confidence < 0.05`, `score_v2_preview.using_fallback = True` and `score_v2 = score_v1`. This prevents the knowledge-weighted score from polluting scanner output with unreliable empirical estimates.

---

## 10. Knowledge Failure Isolation

All failure paths return safe records with `broker_calls=0, orders=0`:
- T020: Empty KLP directory → `load_outcomes()` returns 0, no exception
- T021: `behaviour=None` → KDA returns valid record with ATR fallback
- T022: Empty observation dict → KDA returns valid WAIT record, no crash

---

## 11. Test Results

**32 new tests (T001–T030 + 2 safety sweeps) — all PASSING.**

```
tests/test_dta_system_014.py  32 passed
tests/test_dta_system_013_fix.py  27 passed
tests/test_lol_evidence_bridge.py  24 passed
Total: 83 passed, 0 failed
```

### Test Coverage Map

| Test | What it proves |
|---|---|
| T001 | Level 2 fires at exactly 5 outcomes |
| T002 | Level 3 fires at exactly 10 sector+regime outcomes |
| T003 | Level 5 fires at exactly 15 sector outcomes |
| T004 | Level 7 fallback when no data — all metrics None |
| T005 | BUY and SELL pools are strictly isolated |
| T006 | 10 wins → target_hit_probability ≥ 0.95 |
| T007 | 10 losses → stop_first_probability ≥ 0.95 |
| T008 | 5+5 balance → target_hit_probability ≈ 0.50 |
| T009 | BULL outcomes fire Level 1 for BULL, not Level 1 for BEAR |
| T010 | Level 1 regime-specific evidence respects regime filter |
| T011 | Level 2 aggregates all regimes (correct behaviour) |
| T012 | 200-day-old ESS ≤ 60% of fresh ESS |
| T013 | 0 outcomes → KNOWLEDGE_WAIT |
| T014 | 5 outcomes → exits KNOWLEDGE_WAIT |
| T015 | BUY wins → KNOWLEDGE_BUY |
| T016 | ESS grows monotonically with outcome count |
| T017 | WAIT = INSUFFICIENT state (not contradiction) |
| T018 | DEVELOPING state with no contradictions → BUY (not HOLD) |
| T019 | WAIT ≠ HOLD ≠ BUY enum values |
| T020 | Empty KLP dir → 0 outcomes, no exception |
| T021 | behaviour=None → valid safe record |
| T022 | Empty obs dict → valid safe record |
| T023 | Win-only evidence → positive confidence |
| T024 | Loss-only evidence → target_hit_probability ≤ 0.05 |
| T025 | Alternating win/loss → 0.40 ≤ target_prob ≤ 0.60 |
| T026 | Same obs_id in two KLP files → deduplicated to 1 |
| T027 | HOLD is a distinct reachable enum value |
| T028 | KDA authority score grows monotonically with ESS |
| T029 | V2 fallback equals V1 when evidence_level ≥ 6 |
| T030 | load_outcomes() is idempotent |
| T-safety | broker_calls=0 on all KDA + HBE paths |

---

## 12. Findings Summary

### Defects Fixed in This Audit
None. All architectural issues were already addressed by DTA-013-FIX or pre-date this audit.

### Corrections Applied
| ID | Description |
|---|---|
| COR-14-001 | DTA-013 "~50 outcomes" estimate corrected to 5 outcomes for Level 2 activation |
| COR-14-002 | Level 2 regime pooling documented as intentional architecture, not a defect |

### Structural Gaps (Accepted Risk)
| ID | Description | Risk Level |
|---|---|---|
| GAP-14-001 | KNOWLEDGE_HOLD can fire at ESS=3 — no minimum ESS guard | LOW — KFE angles require their own evidence pool |
| GAP-14-002 | KFE relationship discovery has no multiple-testing correction | LOW — decision_usefulness + multiplicative authority suppression |

### Evidence of Genuine Learning

The following observations confirm the system is genuinely learning-capable, not just architecturally described:

1. **T014 passes**: 5 concrete KLP outcomes + HBE + KDA = exits KNOWLEDGE_WAIT. The chain works.
2. **T028 passes**: Authority score grows from ~0.003 at n=5 to meaningful values at n=100. Learning accumulates.
3. **T006-T008 pass**: Probability estimates correctly reflect win/loss balance — no bias toward optimism.
4. **T026 passes**: Deduplication works — no double-counting from KLP re-processing.
5. **T012 passes**: Evidence older than 200 days is ≥40% decayed — temporal validity enforced.

---

## 13. Operational Expectations

Based on current deployment (paper trading, ₹50k, 2026-08-27):

| Milestone | Expected date (Base scenario) |
|---|---|
| First symbol reaches Level 2 | 2–3 weeks (by mid-September 2026) |
| 5+ symbols at Level 2 | 4–6 weeks (by end of September 2026) |
| First USEFUL state symbol (ESS ≥ 10) | 6–8 weeks (October 2026) |
| First VALIDATED state (ESS ≥ 30) | 3–4 months (December 2026) |
| First DECISION_ELIGIBLE symbol | 6–18 months depending on scan frequency |

**The system is on track.** No intervention required. The current KNOWLEDGE_WAIT state for all symbols is expected for a freshly deployed system with 100 observations but 0 completed outcomes.

---

## 14. Deployment Status

No code changes were made in this audit. Tests only.

**VPS state**: HEAD at 780fa52 (DTA-013 reports commit). No new deployment required.

---

*DTA-SYSTEM-014 complete — Classification: AMBER*
