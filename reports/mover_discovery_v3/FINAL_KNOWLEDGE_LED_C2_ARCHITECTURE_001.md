# FINAL_KNOWLEDGE_LED_C2_ARCHITECTURE_001
**Status:** ACTIVE — SHADOW VALIDATION  
**Date:** 2026-08-18  
**Version:** FINAL_C2_SELECTOR_v1  
**Research basis:** POST_OPEN_SELECTION_RESEARCH_001 · FINAL_20_TO_5_CONSOLIDATED_RESEARCH_001

---

## 1. Architecture Summary

```
Universe (230 NSE stocks)
  │
  ▼  T close (evening)
  V3 Discovery
  → 20 UP candidates  (v3_up_score ranked)
  → 20 DOWN candidates (v3_down_score ranked)
  │
  ▼  T+1 market open (09:15 IST)
  Opening-gap observation
  → gap_pct = (T1_open / T0_close − 1) × 100
  │
  ▼  C2 Selection (PRIMARY — FROZEN)
  UP:   c2_score = +gap_pct   → rank desc → select top-5
  DOWN: c2_score = −gap_pct   → rank desc → select top-5
  │
  ▼  Strategy evaluation (CONTEXT — non-veto)
  → Read strategy rules
  → Record strategy_status, knowledge_strategy_disagreement
  → Never remove a Knowledge-selected candidate
  │
  ▼  Output
  → 5 UP + 5 DOWN candidates (hypothetical positions)
  → Outcome tracking: T+1, T+3, T+5 · MFE · MAE
  → Model A (C2 only) vs Model B (counterfactual: C2 ∩ Strategy)
```

---

## 2. C2 Formula — FROZEN

**Formula:**
```
gap_pct  = (T1_open / T0_close − 1) × 100
UP:   c2_score = +gap_pct
DOWN: c2_score = −gap_pct
```

**Information boundary:** T+1 opening price only.  
**Forbidden:** T+1 close, high, low, return, or any post-open data.

**OOS Anchors (53 trading days, 2026-05-14 → 2026-07-30):**

| Metric | UP | DOWN |
|--------|----|------|
| dir_acc (top-5) | 0.6151 | 0.6000 |
| ge2 rate (top-5) | 0.2906 | 0.2377 |
| Full-pool dir_acc | 0.4787 | 0.4787 |
| Lift (top-5 / pool) | 1.285× | 1.253× |

---

## 3. Knowledge-Led Principle

**C2 is PRIMARY.** It selects the 5 candidates per direction. Nothing overrides this selection.

**Strategy is CONTEXT.** It provides evidence but no veto. The shadow system records:

| `knowledge_strategy_disagreement` | Meaning |
|----------------------------------|---------|
| `AGREE_PASS` | Knowledge selects; Strategy also passes |
| `KNOWLEDGE_OVERRULES_STRATEGY` | Knowledge selects; Strategy would reject |
| `STRATEGY_SUPPORTS_KNOWLEDGE` | Down + BEAR regime: both aligned |
| `STRATEGY_UNAVAILABLE` | No regime data available |
| `NO_STRATEGY_MATCH` | Candidate not selected by Knowledge |

**Why:** OOS evidence shows Strategy has a 32.6% false-rejection rate on UP candidates.
The BEAR+UP rule has only 5 fired OOS events — insufficient to trust as a gate.
Strategy evidence should accumulate in shadow before any gating role.

---

## 4. Model A / Model B (Counterfactual)

| Model | Definition | Purpose |
|-------|-----------|---------|
| **Model A** | C2 selects 5 (Knowledge only) | Primary tracking |
| **Model B** | C2 ∩ Strategy (counterfactual: PASS-only) | What strategy gating would have produced |

Both models are tracked simultaneously in shadow. Model B never executes — it is evidence collection.

---

## 5. Output Files

| File | Contents |
|------|---------|
| `data/logs/final_trading_architecture_shadow_001.jsonl` | Master append-only log (all 40 candidates + daily summary) |
| `reports/mover_discovery_v3/final_trading_architecture_shadow_candidates.csv` | Full 40-candidate rows |
| `reports/mover_discovery_v3/final_trading_architecture_shadow_daily.csv` | Per-day summary |
| `reports/mover_discovery_v3/final_trading_architecture_shadow_strategy_impact.csv` | Model A vs B comparison |

---

## 6. Questions This Architecture Answers

| Q# | Question | Answered by |
|----|----------|------------|
| Q1 | Does V3 reliably produce 20+20 candidates? | daily v3_up_count / v3_down_count |
| Q2 | Does C2 reduce to 5+5? | c2_rank + selected_top5 |
| Q3 | What outcomes do the 10 candidates achieve? | t1_ret_pct, ge1/ge2/ge3, MFE, MAE |
| Q4 | How often does Strategy fire? | strategy_reject_up per day |
| Q5 | Does Strategy improve or hurt Model A? | dir_acc(A) vs dir_acc(B) over time |
| Q6 | When Knowledge overrules Strategy, what happens? | KNOWLEDGE_OVERRULES_STRATEGY rows + outcomes |
| Q7 | What is the disagreement rate by regime? | knowledge_strategy_disagreement × regime |
| Q8 | Is the evidence sufficient to promote or demote Strategy? | See FINAL_ARCHITECTURE_PROMOTION_POLICY_001 |

---

## 7. Safety Invariants (Permanent)

```
broker_calls          = 0
orders_placed         = 0
CandidateStore_writes = 0
ExecutionEngine_calls = 0
RiskControl_calls     = 0
production_changes    = 0
```

A failure in the shadow layer must never stop production.  
All shadow calls must be wrapped in `try/except` at the orchestrator level.

---

## 8. Deployment Status

- **Shadow mode:** ACTIVE (collecting live data)
- **Production mode:** NOT YET (requires 50-day OOS evidence + promotion criteria met)
- **Code location:**
  - `opportunity_engine/final_c2_selector.py` — C2 selection module
  - `scripts/final_trading_architecture_shadow_001.py` — daily shadow runner
  - `tests/test_final_knowledge_led_c2_001.py` — 95 tests (100% pass)
  - `tests/test_final_trading_architecture_shadow_001.py` — 77 tests (100% pass)
