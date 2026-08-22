# ARCH-003 Closure Matrix

**Commit:** (pending)  
**Date:** 2026-08-22  
**Tests:** 379/379

This file maps every identified architectural gap from KDA-001, KDA-002, KDA-003,
ARCH-001, ARCH-002, and ARCH-003 to its final disposition.

---

## KDA-001 Gaps

| ID | Description | Status |
|---|---|---|
| KDA-001-G1 | KDA evaluates all scanner signals in shadow mode | ✅ CLOSED — `run_knowledge_shadow()` per signal |
| KDA-001-G2 | HBE produces behaviour profile for KDA input | ✅ CLOSED — HBE wired in `_shadow_impl()` |
| KDA-001-G3 | KFE produces multi-angle view for KDA input | ✅ CLOSED — KFE wired in `_shadow_impl()` |
| KDA-001-G4 | KDA decision persisted to ledger | ✅ CLOSED — KDALedger.record() called |
| KDA-001-G5 | broker_calls=0 safety invariant | ✅ VERIFIED — T08, T36, T40 |
| KDA-001-G6 | execution_authority=False | ✅ VERIFIED — T23, T36 |

---

## KDA-002 Gaps

| ID | Description | Status |
|---|---|---|
| KDA-002-G1 | Evidence state thresholds (INSUFFICIENT/DEVELOPING/USEFUL/VALIDATED/DECISION_ELIGIBLE) | ✅ CLOSED — KDA._classify_evidence_state() |
| KDA-002-G2 | ESS uses recency-weighted count (90-day half-life) | ✅ CLOSED — HBE + KDA |
| KDA-002-G3 | Stability check (recent 25% vs historical 75%) | ✅ CLOSED — HBE |
| KDA-002-G4 | OOS validation status tracked | ✅ CLOSED — KFE OOS_VALIDATION angle (data pending) |
| KDA-002-G5 | KDA returns KNOWLEDGE_BUY/SELL only at DECISION_ELIGIBLE | ✅ VERIFIED — KDA code + T28 |
| KDA-002-G6 | Fallback used flag in every result | ✅ VERIFIED — T11 |

---

## KDA-003 Gaps

| ID | Description | Status |
|---|---|---|
| KDA-003-G1 | KDA decisions compared against StrategyLab in EOD | ✅ CLOSED — KDAComparativeAnalyzer |
| KDA-003-G2 | Authority gate updated EOD | ✅ CLOSED — KDAAuthorityReporter |
| KDA-003-G3 | HBE reloaded after EOD to pick up new outcomes | ✅ CLOSED — T41 |
| KDA-003-G4 | KFE pool reloaded after EOD | ✅ CLOSED — T42 |
| KDA-003-G5 | run_eod_knowledge_update called in orchestrator | ✅ CLOSED — T39 |
| KDA-003-G6 | Telegram /kda command reads authority gate | ✅ CLOSED — notifications/telegram_bot.py |

---

## ARCH-001 Gaps (GAP-008 through GAP-011)

| ID | Description | Status |
|---|---|---|
| GAP-008 | KDA gate Telegram notification (when authority advances) | ✅ CLOSED — _do_eod_learning |
| GAP-009 | StrategyLab rejections → rejection_audit.db | ✅ CLOSED — _run_strategy_lab() |
| GAP-010 | /kda Telegram command | ✅ CLOSED — 13 commands in bot |
| GAP-011 | Architecture invariant tests | ✅ CLOSED — test_arch_001_integration.py (56 tests) |

---

## ARCH-002-R Gaps

| ID | Description | Status |
|---|---|---|
| ARCH-002-G1 | KDA promoted to intelligence authority (bypasses StrategyLab gate) | ✅ CLOSED — Phase 1+2 merge |
| ARCH-002-G2 | StrategyLab demoted to SHADOW/CONTEXT | ✅ CLOSED — `_sl_signal_map` comparison only |
| ARCH-002-G3 | authorization_source annotated on every signal | ✅ CLOSED — T26 |
| ARCH-002-G4 | KDA empirical target/stop applied when VALIDATED/DECISION_ELIGIBLE | ✅ CLOSED — T30 |
| ARCH-002-G5 | KDA vs StrategyLab comparison JSONL | ✅ CLOSED — T27 |
| ARCH-002-G6 | TradeSignal has 8 KDA authority fields | ✅ CLOSED — T29 |

---

## ARCH-003 Gaps (New)

| ID | Description | Status |
|---|---|---|
| GAP-A | `_kda_mc` only had 5 market context fields | ✅ CLOSED — now 10 fields (ARCH-003) |
| GAP-B | KFE did not load shadow_evidence_ledger.jsonl (405 outcome-linked records) | ✅ CLOSED — ARCH-003, T16–T17 |
| GAP-C | KFE did not load knowledge_evidence_ledger.jsonl (405 evidence records) | ✅ CLOSED — ARCH-003, T18 |
| GAP-D | shadow/knowledge evidence sources not marked as used in inventory | ✅ CLOSED — T21 |
| GAP-E | Integration tests covering full KDA stack end-to-end | ✅ CLOSED — 42 tests (T01–T42) |

---

## Wait-For-Evidence Items (Cannot be closed now — technical blocker: no data yet)

| ID | Description | Condition to close |
|---|---|---|
| WFE-001 | KDA DECISION_ELIGIBLE (ESS ≥ 100) | 30+ trading days of KDA shadow decisions |
| WFE-002 | KDA direction accuracy ≥ 57% on 30+ decisions | WFE-001 first |
| WFE-003 | HBE ≥ 10 outcomes per symbol (USEFUL evidence) | ~10+ trading days KLP-002 fills |
| WFE-004 | paper_trades.csv → KFE pool | First completed paper trade needed |
| WFE-005 | KDA target/stop empirically applied in production | WFE-001 first |
| WFE-006 | OOS_VALIDATION angle with OOS_PASSED records | Dedicated OOS run needed |
| WFE-007 | KDA accuracy validates live readiness checklist item 20 | WFE-002 first |

---

## Live Authorization Gaps (Cannot be closed during ARCH-003 — deliberate)

| ID | Description | Status |
|---|---|---|
| LIVE-001 | Dhan order submission test | ❌ NOT TESTED — requires manual operator action |
| LIVE-002 | Order status polling | ❌ NOT TESTED |
| LIVE-003–010 | Fill, reconciliation, partial fill, rejection handling | ❌ NOT TESTED |
| LIVE-011 | PAPER_TRADING=false + LIVE_TRADING_AUTHORIZED=true | ❌ DELIBERATELY NOT SET |

Live trading requires ALL items in ARCH_003_FINAL_REPORT.md §13 to pass.  
No code change can automate this. Operator must explicitly set both env vars.

---

## Summary

| Category | Total | Closed | Blocked |
|---|---|---|---|
| KDA-001 | 6 | 6 | 0 |
| KDA-002 | 6 | 6 | 0 |
| KDA-003 | 6 | 6 | 0 |
| ARCH-001 | 4 | 4 | 0 |
| ARCH-002-R | 6 | 6 | 0 |
| ARCH-003 (new) | 5 | 5 | 0 |
| Wait-for-evidence | 7 | 0 | 7 (no data yet) |
| Live authorization | 11 | 0 | 11 (deliberate) |
| **TOTAL** | **51** | **33** | **18 (data/ops)** |

All 33 architectural gaps are closed.  
18 remaining items require either evidence accumulation or manual operator action.  
No architectural gaps remain open.
