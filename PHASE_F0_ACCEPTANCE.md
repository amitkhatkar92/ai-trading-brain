# Phase F — Market Research Engine
## Acceptance Document (F0.1)

**Date:** 2026-06-19  
**Status:** ACCEPTED — implementation begins  
**Sponsor:** Operator  
**Owner:** Research Layer  

---

## Purpose

Phase F answers two questions the trading system cannot currently answer:

> **Why did the market reward certain stocks?**

> **Why did similar-looking stocks fail?**

This is a **market research engine**, not a trading engine.  
Phase F observes, collects, and reports. It never trades and never modifies any A–E table.

---

## Scope

### Included

| Deliverable | Description |
|---|---|
| **Top 15 Winners** | Daily top-15 gainers from the active universe, by `day_return_pct` |
| **Top 15 Losers** | Daily bottom-15 by `day_return_pct` (deepest declines) |
| **Feature Extraction** | Technical + OIOS + structural features per leader, stored per day |
| **Outcome Tracking** | 1D, 3D, 5D, 10D, 20D return horizons; MFE and MAE; outcome class |
| **Control Population** | 3–10 stocks per winner that matched the fingerprint but did not move |
| **Failure Attribution** | Candidate reasons scored when an expected winner failed |
| **Weekly Reports** | Text summaries: common winner factors, loser factors, control comparison |

### Excluded

| Activity | Reason |
|---|---|
| **Learning** | Phase F only observes — it does not feed back into OIOS scores |
| **Threshold Changes** | All OIOS thresholds remain frozen during Phase F |
| **Auto Tuning** | No automated parameter adjustment from research findings |
| **Strategy Modification** | No changes to archetypes, weights, or TTL values |
| **Risk Changes** | `config.py` risk constants are immutable from Phase F |
| **OIOS Writes** | Phase F **must not** write to: `opportunities`, `signal_births`, `decision_log`, `pending_adjustments`, `sector_conviction_daily`, `theme_phase_history` |

---

## Tables Created (Phase F)

| Table | Purpose |
|---|---|
| `market_leaders_daily` | Identity row: who moved, how much, when |
| `market_leader_features` | Feature store: one row per feature per leader |
| `market_leader_outcomes` | Multi-horizon return tracking |
| `market_research_controls` | Control group: lookalikes that failed |
| `failure_attribution` | Candidate reasons for unexpected failures |

---

## Services Delivered

| File | Phase | Role |
|---|---|---|
| `oios/phase_f/leader_capture.py` | F1 | Capture top-15 winners + losers daily |
| `oios/phase_f/feature_extractor.py` | F1 | Extract 12 technical + OIOS + structural features |
| `oios/phase_f/outcome_tracker.py` | F2 | Update multi-horizon returns; classify outcome type |
| `oios/phase_f/control_population.py` | F3 | Build fingerprint + find similar non-winners |
| `oios/phase_f/failure_analyzer.py` | F4 | Score failure candidate reasons |
| `oios/phase_f/weekly_market_research.py` | F5 | Weekly summary report |
| `oios/phase_f/phase_f_shadow.py` | F6 | Research shadow engine — read-only output |

---

## Governance

| Control | Specification |
|---|---|
| **Write fence** | `phase_f_audit.py` verifies zero writes to A–E tables from any Phase F module |
| **Shadow mode** | `phase_f_shadow.py` outputs suggestions only — no writes, no DB side-effects |
| **Test coverage** | ≥ 95% of Phase F code paths covered by `tests/oios/test_phase_f_*.py` |
| **Readiness gate** | `PHASE_F_READINESS.md` produced after all deliverables verified |

---

## Outcome Classification

| Class | Condition |
|---|---|
| `ONE_DAY_SPIKE` | return_3d ≤ 0.5 × return_1d (move reversed quickly) |
| `SHORT_RUNNER` | return_5d > 0 but return_10d ≤ 0 (faded by week 2) |
| `MULTI_WEEK_WINNER` | return_10d > 3% and return_20d > 2% |
| `LONG_TREND_WINNER` | return_20d > 5% (sustained across full 4-week window) |
| `UNKNOWN` | Horizon data not yet available |

---

## Failure Candidate Reasons

| Reason | Description |
|---|---|
| `CROWDING` | Too many participants → mean-reversion forced |
| `WEAK_BREADTH` | Sector participation collapsed same day |
| `LOW_DELIVERY` | Delivery % below 40% → speculative, no institutional follow |
| `NO_FLOW` | No bulk/block deal evidence of institutional accumulation |
| `NEGATIVE_EARNINGS` | Negative earnings surprise in window |
| `SECTOR_DIVERGENCE` | Stock moved against sector direction |
| `MARKET_WEAKNESS` | Broad market sold off — not stock-specific failure |

---

## Research Isolation Contract

Phase F is isolated from the trading system by design:

1. **Separate DB tables** — 5 new tables; no foreign keys referencing A–E tables  
2. **Read-only access** to A–E — only `SELECT` from `ohlcv_daily`, `sector_conviction_daily`, `theme_phase_history`, `universe_stocks`  
3. **No EventBus emissions** — Phase F services do not call `get_bus().emit()`  
4. **No OrderManager calls** — Phase F has zero coupling to `execution_engine`  
5. **Audit-enforced** — `phase_f_audit.py` catches violations at CI time  
