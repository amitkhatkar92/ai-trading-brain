# ARCH-005 KDA Authority Report
## Knowledge Decision Authority — Activation Status & Decision Distribution

**Date:** 2025  
**Status:** ACTIVATED ✅  
**KDA Pool:** 2819 KFE records | 106 OOS annotated (32 PASSED, 57 FAILED, 17 TESTED)

---

## 1. KDA Authority Activation Summary

### Before ARCH-005
KDA returned `KNOWLEDGE_WAIT` for any evidence state except `DECISION_ELIGIBLE` (ESS ≥ 100). Given that real-world signals typically have ESS 3–60, KDA was silent **99%+ of the time**. StrategyLab operated unchecked.

### After ARCH-005
KDA expresses `KNOWLEDGE_BUY` or `KNOWLEDGE_SELL` for **all evidence states** with ESS ≥ 3.0 and no material conflict. StrategyLab is demoted to shadow context. `KNOWLEDGE_HOLD` (material conflict) **blocks** StrategyLab signals.

| Evidence State | ESS Range | Decision (before) | Decision (after) | Authority |
|---|---|---|---|---|
| INSUFFICIENT | ESS < 3 | KNOWLEDGE_WAIT | KNOWLEDGE_WAIT | NONE |
| DEVELOPING | ESS 3–9 | KNOWLEDGE_WAIT ❌ | KNOWLEDGE_BUY/SELL ✅ | KNOWLEDGE |
| USEFUL | ESS 10–29 | KNOWLEDGE_WAIT ❌ | KNOWLEDGE_BUY/SELL ✅ | KNOWLEDGE |
| VALIDATED | ESS 30–99 | KNOWLEDGE_HOLD/WAIT ❌ | KNOWLEDGE_BUY/SELL ✅ | KNOWLEDGE |
| DECISION_ELIGIBLE | ESS ≥ 100 | KNOWLEDGE_BUY/SELL ✅ | KNOWLEDGE_BUY/SELL ✅ | KNOWLEDGE |

---

## 2. Decision Rules (ARCH-005 Final)

```python
# _determine_decision() — simplified pseudocode

if evidence_state == INSUFFICIENT:          # ESS < 3: no evidence basis
    return KNOWLEDGE_WAIT

n_contradict = count(CONTRADICT angles)
n_support    = count(SUPPORT angles)

if n_contradict > n_support and n_contradict >= 3:   # material conflict
    return KNOWLEDGE_HOLD                              # blocks StrategyLab

# All other states: KDA expresses directional view
if direction in (BUY, LONG):   return KNOWLEDGE_BUY
if direction in (SELL, SHORT): return KNOWLEDGE_SELL
return KNOWLEDGE_HOLD                                 # unknown direction fallback
```

```python
# _classify_authority() — simplified pseudocode

if evidence_state != INSUFFICIENT:
    return KNOWLEDGE           # KDA is intelligence authority for all non-zero evidence
return NONE
```

---

## 3. StrategyLab Shadow Status

| KDA Decision | StrategyLab Role | Outcome |
|---|---|---|
| `KNOWLEDGE_BUY` | Shadow / Context only | KDA decision enters pipeline; StrategyLab label recorded for comparison |
| `KNOWLEDGE_SELL` | Shadow / Context only | KDA decision enters pipeline |
| `KNOWLEDGE_HOLD` | **BLOCKED** | Signal dropped; StrategyLab ACCEPT is vetoed by KDA |
| `KNOWLEDGE_WAIT` | Primary | StrategyLab may proceed (KDA has no opinion) |
| `KNOWLEDGE_EXIT` | Shadow / Context only | Exit signal enters pipeline |

---

## 4. Risk Layer Independence

KDA activation does NOT disable or modify any risk controls:

| Layer | Role | Status |
|---|---|---|
| CapitalRiskEngine | Position sizing | Unchanged — still applies after KDA decision |
| RiskControl / PortfolioAllocation | Portfolio-level limits | Unchanged |
| MarketSimulation | Monte Carlo stress | Unchanged |
| RiskGuardian | Kill-switch (VIX>45, loss>2%) | Unchanged — independent VETO |
| DebateEngine | Multi-agent debate | Secondary context only; KDA upstream |
| DecisionEngine | Threshold gate (6.5) | Downstream of KDA; can still reject |

---

## 5. Knowledge Outcome Loop Status

| Component | Wired? | Function |
|---|---|---|
| KDAOutcomeEngine | ✅ | Matches closed trades to KDA decisions; updates ESS |
| KDAComparativeAnalyzer | ✅ | Compares KDA vs StrategyLab accuracy |
| KDAAuthorityReporter | ✅ | Daily authority report to SQLite + logs |
| EOD trigger | ✅ | `run_eod_knowledge_update()` called at EOD in orchestrator |

---

## 6. Material Conflict Threshold

The `KNOWLEDGE_HOLD` condition requires:
```
n_contradict > n_support  AND  n_contradict >= 3
```

**Rationale:**
- `n_contradict >= 3`: requires minimum 3 independent angles actively opposing (not just 1-2 noise angles)
- `n_contradict > n_support`: majority of opinionated angles are opposing (not a tie)
- Single-angle contradictions (n_contradict=1 or 2) do NOT trigger HOLD — KDA still expresses a view

---

## 7. Angle Evaluation Bug Fix (ARCH-005 critical finding)

`_classify_angle_verdict(name, conf, metrics)` used `n` (sample_count) in the body:
```python
elif conf < 0.20 and n >= 10:
    ...
```

But `n` was only defined in `_evaluate_angle()` and NOT passed as a parameter. This caused a `NameError` for any angle with `conf < 0.20`, which was silently caught by `evaluate()` and returned `KNOWLEDGE_WAIT + INSUFFICIENT`.

**Consequence:** The material conflict detection path (`n >= 10` low-confidence CONTRADICT) was never reachable. Tests expecting `KNOWLEDGE_WAIT` for conflicting angles were passing for the wrong reason.

**Fix:** `_classify_angle_verdict(name, conf, metrics, n=0)` — `n` added as explicit parameter.

---

## 8. Remaining Gaps (post-ARCH-005)

### Category A: Evidence depth (deferred)
- **A1**: ESS for most symbols still in DEVELOPING range (3–9). Target: USEFUL+ (ESS≥10) for active symbols after 2–4 weeks of paper trading.
- **A2**: OOS annotations: 106/2819 records annotated. More will annotate as KFE processes outcomes.

### Category B: Source completeness (deferred)
- **B1**: MARKET angle is always NEUTRAL (index not in SUPPORT list by design).
- **B2**: WalkForward test results not yet wired to OOS_VALIDATION angle.
- **B3**: StrategyPerformanceTracker metrics not yet flowing into KFE pool.

### Category C: Monitoring (deferred)
- **C1**: No real-time dashboard for KDA decision distribution by evidence state.
- **C2**: No alert when n_hold_blocked spikes (unexpected material conflict surge).

---

## 9. Acceptance Criteria Checklist

| Criterion | Status |
|---|---|
| KDA is the actual intelligence authority | ✅ |
| DECISION_ELIGIBLE works NOW | ✅ (lowered gate to DEVELOPING+) |
| StrategyLab cannot override KDA HOLD | ✅ |
| Debate cannot override KDA | ✅ (debate is downstream secondary) |
| Risk can still veto KDA | ✅ (RiskGuardian/RiskControl unchanged) |
| HBE contributes runtime evidence | ✅ (_shadow_impl Step 2) |
| KFE contributes runtime multi-angle evidence | ✅ (_shadow_impl Step 3) |
| KLP observations reach Knowledge | ✅ (MOP-RC-001 observer) |
| KDA decisions are persisted | ✅ (ledger in _shadow_impl Step 7) |
| KDA outcomes are evaluated | ✅ (run_eod_knowledge_update wired) |
| Authority reporting runs | ✅ (KDAAuthorityReporter wired in EOD) |
| PAPER_TRADING remains true (VPS) | ✅ |
| broker_calls = 0 | ✅ |
| orders = 0 (from KDA eval) | ✅ |
| 436/436 tests pass | ✅ |
