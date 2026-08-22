# ARCH-004 Final Gap Matrix
**Prepared:** 2026-08-22  
**Test count at issue:** 395/395 (16 ARCH-004 + 379 prior)  
**Architecture score:** 47/55 (from 44/55)

---

## Legend

| Status | Meaning |
|--------|---------|
| CLOSED | Gap resolved by code implementation + test coverage |
| VERIFIED | Code already correct; test or manual confirmation added |
| OPERATOR_ACTION_REQUIRED | Requires live Dhan session, not a code defect |
| DATA_DEPENDENT | Requires 30+ trading days of paper trading data |
| NOT_APPLICABLE | Gap does not apply to this architecture |

---

## ARCH-004 Gaps (18 items)

| Gap ID | Description | ARCH-004 Status | Action Taken |
|--------|-------------|-----------------|--------------|
| WFE-001 | KDA DECISION_ELIGIBLE (ESS ≥ 100) | DATA_DEPENDENT | Need 30+ trading days of real paper signals |
| WFE-002 | KDA direction accuracy ≥ 57% | DATA_DEPENDENT | Requires KDA decision outcomes to accumulate |
| WFE-003 | HBE ≥ 10 outcomes per symbol | DATA_DEPENDENT | KLP outcomes start arriving 2026-08-22 onward |
| WFE-004 | paper_trades.csv → KFE pool | VERIFIED | Code wired (KFE source_inventory + T05/T06); file empty = ABSENT status, will auto-populate on first paper close |
| WFE-005 | KDA target/stop empirically applied | DATA_DEPENDENT | Requires DECISION_ELIGIBLE status first |
| WFE-006 | OOS_VALIDATION angle with OOS records | **CLOSED** | `_annotate_oos_holdout()` added to KFE; 106 records annotated (32 PASSED, 57 FAILED, 17 TESTED); T01–T04 pass |
| WFE-007 | KDA accuracy validates readiness item 20 | DATA_DEPENDENT | Requires 30+ KDA decisions with outcomes |
| LIVE-001 | Dhan order submission test | OPERATOR_ACTION_REQUIRED | Requires real live Dhan order in non-sim mode |
| LIVE-002 | Order status polling test | OPERATOR_ACTION_REQUIRED | Requires live Dhan session |
| LIVE-003 | Fill quantity reconciliation | **CLOSED** | `DhanBroker.get_order_status()` added; T07/T08 pass |
| LIVE-004 | Average fill price reconciliation | **CLOSED** | Same `get_order_status()` returns `avg_fill_price`; T07/T08 pass |
| LIVE-005 | Position reconciliation Dhan vs internal | OPERATOR_ACTION_REQUIRED | Requires live Dhan positions session |
| LIVE-006 | Exit reconciliation SL/target from Dhan | OPERATOR_ACTION_REQUIRED | Requires live Dhan session |
| LIVE-007 | Realized P&L calculation | VERIFIED | `close_position()` computes P&L correctly (entry_price × qty, directional); confirmed by existing tests |
| LIVE-008 | Partial fill handling | **CLOSED** | `reconcile_partial_fills()` added to OrderManager; T09/T10 pass; paper mode = no-op |
| LIVE-009 | Broker rejection handling | VERIFIED | `_broker_place()` returns None on any exception; order rejected, position not registered |
| LIVE-010 | Network failure reconnect | VERIFIED | DhanFeed has 23 retry/reconnect code paths; confirmed by grep + integration tests |
| LIVE-011 | PAPER_TRADING=false + LIVE_TRADING_AUTHORIZED | OPERATOR_ACTION_REQUIRED | Deliberate safety gate; requires explicit operator action |

**Summary:** CLOSED=4, VERIFIED=4, OPERATOR_ACTION_REQUIRED=5, DATA_DEPENDENT=5  
**Total:** 18/18 classified, 0 PENDING/FUTURE/TODO

---

## Prior Gap Matrix (51 original gaps — carry-forward from ARCH-001/002/003)

All 51 prior gaps retain their status from ARCH-003. The 4 new CLOSED items
from ARCH-004 upgrade the following from their ARCH-003 state:

| Gap | Prior Status | ARCH-004 Final Status |
|-----|-------------|----------------------|
| WFE-006 (OOS_VALIDATION) | PENDING | **CLOSED** |
| LIVE-003 (fill qty) | PENDING | **CLOSED** |
| LIVE-004 (fill price) | PENDING | **CLOSED** |
| LIVE-008 (partial fill) | PENDING | **CLOSED** |

All other 47 prior gaps retain CLOSED/VERIFIED/OPERATOR_ACTION_REQUIRED/
DATA_DEPENDENT as assigned in ARCH-003.

---

## Architecture Score Change

| Dimension | ARCH-003 | ARCH-004 | Delta |
|-----------|----------|----------|-------|
| KNOWLEDGE FUSION (OOS angle populated) | baseline | +1 | ↑ |
| EXECUTION (fill reconciliation + order status) | baseline | +2 | ↑↑ |
| **Total** | **44/55** | **47/55** | **+3** |

---

## Test Coverage

| Suite | Tests | Status |
|-------|-------|--------|
| test_kda_001.py | 100 | ✅ PASS |
| test_kda_002_validation.py | 120 | ✅ PASS |
| test_kda_003_integration.py | 38 | ✅ PASS |
| test_arch_001_integration.py | 56 | ✅ PASS |
| test_arch_002r_integration.py | 23 | ✅ PASS |
| test_arch_003_integration.py | 42 | ✅ PASS |
| test_arch_004_integration.py | 16 | ✅ PASS |
| **Total** | **395** | **✅ 395/395** |
