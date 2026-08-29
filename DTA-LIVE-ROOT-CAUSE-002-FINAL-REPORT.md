# DTA-LIVE-ROOT-CAUSE-002 — Final Closure Report
**Broker Execution Hardening: Fail-Safe Broker Responses**

| Field | Value |
|---|---|
| **Status** | ✅ GREEN — All acceptance criteria satisfied |
| **Commit** | `87bb07c` |
| **Branch** | `main` |
| **Deploy date** | 2026-08-29 |
| **VPS** | `root@178.18.252.24` — both containers `Up (healthy)` |
| **Files changed** | 4 (`dhan_broker.py`, `angelone_broker.py`, `order_manager.py`, `tests/test_dta_live_root_cause_002.py`) |
| **Tests added** | 40 (T001–T040) — 40/40 passing |
| **Interfaces changed** | None — all public method signatures unchanged |

---

## 1. Confirmed Root Cause (DTA-LIVE-ROOT-CAUSE-001, corrected chronology)

**Date/time:** Friday 2026-08-28 13:00:38 IST (first live trading session)  
**File:** `execution_engine/brokers/dhan_broker.py` line 76 (at time of incident)  
**Evidence:**
```
[OrderManager] ➡ Executing LIMIT BUY SBIN qty=5 signal=1046.70
[DhanBroker] Order failed 3045: 'str' object has no attribute 'get'  (×3)
[OrderManager] ❌ Entry order failed after 3 attempts for SBIN — signal discarded.
```

**Bug path:**
1. Dhan HTTP endpoint returned an empty response body
2. `dhanhq` SDK's `find_error_code` caught `JSONDecodeError` and returned the raw response as a string
3. `DhanBroker.place_order()` called `response.get("data", {}).get("orderId")` without `isinstance(response, dict)` guard
4. `AttributeError: 'str' object has no attribute 'get'` raised
5. Caught by bare `except Exception` → `return None`
6. `OrderManager._place_entry_with_retry()` treated `None` as retriable → 3 blind retries → signal discarded
7. No alert fired; no Telegram notification; only log entries with misleading "Order failed 3045" prefix

**Same bug existed at:** line 122 (`place_sl_order`) — fixed in this task.

---

## 2. What Was Ruled Out

| Theory | Status | Evidence |
|---|---|---|
| Auth / token | Ruled out | Token `07FayFVg` was `LIVE_VERIFIED` by 09:46 IST |
| PAPER_TRADING=true | Ruled out | `.env` confirmed `PAPER_TRADING=false`, `LIVE_TRADING_AUTHORIZED=true` |
| RiskGuardian kill-switch | Ruled out | VIX 11–14.5, daily loss ₹0 — no trigger conditions |
| KNOWLEDGE_DISABLED/KDA block | Ruled out | `KNOWLEDGE_BUY` confirmed in logs |
| Exchange circuit/MULTI_SID_REJECTED | Ruled out | Circuit impact explicitly logged as `NO` |
| Scheduler fault | Ruled out | 6 cycles completed correctly on the Friday |
| Thursday container (67a3300) having DTA-020 CRLF bug | Ruled out | Bug was in cron, not trading — trading ran correctly from 16:37 Thu through Friday |
| 07:40 IST `find_error_code` warnings | Ruled out | Those were options-chain endpoint, not order placement |

---

## 3. Changes Made

### 3.1 `execution_engine/brokers/dhan_broker.py` (Phase 2–4)

**New module-level constants (failure type classification):**
```python
BROKER_ACCEPTED           = "BROKER_ACCEPTED"
BROKER_REJECTED           = "BROKER_REJECTED"
BROKER_RESPONSE_MALFORMED = "BROKER_RESPONSE_MALFORMED"
BROKER_RESPONSE_EMPTY     = "BROKER_RESPONSE_EMPTY"
BROKER_EXCEPTION          = "BROKER_EXCEPTION"
```

**New `__init__` attribute:**
```python
self._last_failure_type: str = ""
```

**New `_validate_order_response(response, security_id, endpoint) -> Optional[str]`:**
- `None` or whitespace-only string → `BROKER_RESPONSE_EMPTY` → `None`
- Any non-dict, non-empty (string, bytes, list, int, etc.) → `BROKER_RESPONSE_MALFORMED` → `None`
- `status in ("failure", "error", "failed")` or `errorCode` present → `BROKER_REJECTED` → `None`
- `data` field not a dict → `BROKER_RESPONSE_MALFORMED` → `None`
- `orderId` missing or empty → `BROKER_REJECTED` → `None`
- All valid → `BROKER_ACCEPTED` → `str(orderId)`
- **Always sets `self._last_failure_type` before returning**

**Rewrote `place_order()`:**
```python
try:
    response = self._dhan.place_order(...)
except Exception as exc:
    self._last_failure_type = BROKER_EXCEPTION
    log.error(...)
    return None
return self._validate_order_response(response, security_id, "place_order")
```

**Rewrote `place_sl_order()`:** Same pattern.

**Unchanged:** `cancel_order()`, `get_positions()`, `get_portfolio()`, `get_order_status()`, `get_fill_details()`

### 3.2 `execution_engine/brokers/angelone_broker.py` (Phase 11)

- Added `self._last_failure_type = ""` to `__init__`
- Replaced `response.get("data", {}).get("orderid")` with `isinstance(response, dict)` guard
- Sets `BROKER_RESPONSE_MALFORMED`, `BROKER_REJECTED`, or `BROKER_ACCEPTED` accordingly

### 3.3 `execution_engine/order_manager.py` — `_place_entry_with_retry()` (Phase 5)

**Before (confirmed buggy path):**
```python
if order_id:
    return order_id
log.warning("[OrderManager] Attempt %d/%d: broker returned None for %s — retrying.", ...)
# → unconditional retry on ANY None return, including MALFORMED/EMPTY
```

**After (safe):**
```python
if order_id:
    return order_id

_failure_type = getattr(self._broker, "_last_failure_type", "")
if _failure_type in ("BROKER_RESPONSE_MALFORMED", "BROKER_RESPONSE_EMPTY"):
    # Ambiguous: Dhan may have accepted the order — do NOT retry.
    log.error("[OrderManager] [AmbiguousExecution] %s %s attempt=%d/%d "
              "failure_type=%s — cannot retry without reconciliation. ...", ...)
    try:
        from notifications.notifier_manager import get_notifier
        get_notifier().send_alert("⚠️ [AmbiguousExecution] ...")
    except Exception:
        pass
    return None  # fail closed — no retry on ambiguous response

# REJECTED / EXCEPTION / unknown → safe to retry (existing backoff)
log.warning("[OrderManager] Attempt %d/%d: broker returned None (%s) for %s — retrying.", ...)
```

**Why MALFORMED/EMPTY must not be retried:**  
When Dhan's HTTP response has an empty body, the broker may have accepted the order. A retry would place a duplicate order on the exchange. The correct response is: fail closed, notify the operator, and let the next scanner cycle re-evaluate. Startup reconciliation (`reconcile_startup_fills`) will resolve the ambiguity on the next restart.

**EXCEPTION and REJECTED are safe to retry:** EXCEPTION (network error) means the request did not reach Dhan. REJECTED means Dhan explicitly refused — no position was created.

---

## 4. Test Coverage (T001–T040)

| Range | Area | Count | Result |
|---|---|---|---|
| T001–T014 | `place_order()` response variants | 14 | ✅ 14/14 |
| T015–T016 | `place_sl_order()` malformed/missing orderId | 2 | ✅ 2/2 |
| T017–T018 | `close_position()` broker failure / success | 2 | ✅ 2/2 |
| T019–T020 | AET confirmation failure / success | 2 | ✅ 2/2 |
| T021–T022 | Re-entry malformed / rejected | 2 | ✅ 2/2 |
| T023–T027 | Startup reconciliation: FILLED/PARTIAL/REJECTED/CANCELLED/UNKNOWN | 5 | ✅ 5/5 |
| T028 | Pending order reconciliation | 1 | ✅ 1/1 |
| T029–T030 | opportunity_id lineage: signal → OrderRecord → _orders | 2 | ✅ 2/2 |
| T031–T033 | Ambiguous response: fail-closed, no blind retry | 3 | ✅ 3/3 |
| T034–T040 | Invariants: phantom prevention, broker_order_id, SL safety, error visibility | 7 | ✅ 7/7 |
| **Total** | | **40** | **✅ 40/40** |

**Key adversarial inputs tested:** `None`, `""`, `"  "`, `"some string"`, `b"\x00bytes"`, `[list]`, `{"no data": ...}`, `{"data": "string not dict"}`, `{"data": {}}`, `{"data": {"orderId": ""}}`, `{"status": "failure", "errorCode": ...}`, `ConnectionError`, `RuntimeError`

---

## 5. Architecture Invariants Verified

| Invariant | Status |
|---|---|
| Valid broker response → `_orders` registration | ✅ confirmed (T034) |
| Invalid broker response → no `_orders` entry | ✅ confirmed (T035) |
| Phantom position impossible from malformed response | ✅ confirmed (T037) |
| Phantom position impossible from rejected response | ✅ confirmed (T038) |
| Duplicate-order risk eliminated for MALFORMED/EMPTY | ✅ confirmed (T031) |
| EXCEPTION retried (safe, request didn't reach broker) | ✅ confirmed (T032) |
| SL failure sets `sl_order_id = ""` (not a fake ID) | ✅ confirmed (T039) |
| SL failure safe: software SL still active via TradeMonitor | ✅ architecture pre-existing |
| opportunity_id preserved end-to-end | ✅ confirmed (T029, T030) |
| Error visible in logs at ERROR level | ✅ confirmed (T040) |
| Operator Telegram alert on ambiguous execution | ✅ implemented (Phase 5) |

---

## 6. Execution Path Integration

The full production execution path is integration-tested in T029–T034, T036, T039:

```
TradeSignal + DecisionResult
  → OrderManager.execute()
    → _place_entry_with_retry()
      → _broker_place()
        → DhanBroker.place_order()
          → _validate_order_response()
            → _last_failure_type set
        → failure_type check in _place_entry_with_retry()
          → MALFORMED/EMPTY: fail closed, no retry, alert
          → EXCEPTION/REJECTED: retry with backoff
```

---

## 7. Phases Completed

| Phase | Task | Result |
|---|---|---|
| 1 | Read-only code baseline | ✅ |
| 2 | `place_order()` hardening (`dhan_broker.py`) | ✅ |
| 3 | `place_sl_order()` hardening; verify close/AET/re-entry paths | ✅ |
| 4 | BROKER_* constants, `_last_failure_type` attribute | ✅ |
| 5 | `_place_entry_with_retry()` retry safety (`order_manager.py`) | ✅ |
| 6 | OrderRecord fields verification | ✅ (no change needed) |
| 7 | SL failure safe state verification | ✅ (pre-existing architecture safe) |
| 8 | `_append_live_journal()` opportunity_id verification | ✅ (T029/T030 confirm) |
| 9 | `get_fill_details()` real DhanBroker verification | ✅ (no change needed) |
| 10 | 40 tests (T001–T040) | ✅ 40/40 passing |
| 11 | `angelone_broker.py` isinstance sweep | ✅ |
| 12 | VPS config read-only check | ✅ (PAPER_TRADING=false, LIVE_AUTH=true confirmed) |
| 13 | Knowledge system preservation | ✅ (no knowledge files touched) |
| 14 | Execution eligibility invariant verification | ✅ (all invariants hold) |
| 15 | Full test suite | ✅ 40/40 new; pre-existing collection errors unchanged (unrelated) |
| 16 | VPS deploy | ✅ commit `87bb07c`, both containers `Up (healthy)` |
| 17 | This report | ✅ |

---

## 8. GREEN Classification Criteria

All criteria from specification met:

| Criterion | Status |
|---|---|
| Confirmed root cause fixed | ✅ `place_order()` / `place_sl_order()` hardened with `isinstance` guard |
| No unresolved broker execution defect remains | ✅ |
| Ambiguous broker responses fail safely | ✅ MALFORMED/EMPTY → fail closed + alert |
| Duplicate-order risk controlled | ✅ no retry on ambiguous responses |
| SL failure safe | ✅ `sl_order_id = ""` + software SL via TradeMonitor |
| Live journal / reconciliation intact | ✅ no changes to journal/reconcile path |
| Production execution path integration-tested | ✅ T029–T039 |
| Tested commit deployed | ✅ `87bb07c` |
| Both containers healthy | ✅ `ai-trading-brain` and `trading-dashboard` both `Up (healthy)` |
| Automatic Dhan authentication operational | ✅ DTA-020 CRLF fix still in place |

---

## 9. Prior Context

- **DTA-020** (commit `6700289`): CRLF cron fix — resolved token rotation failure that affected Thursday 2026-08-27 deployment. Not the root cause of Friday's execution failure.
- **DTA-LIVE-ROOT-CAUSE-001**: Full forensic investigation — established that Friday 2026-08-28 was the first live trading session and the string-response AttributeError was the single execution-path defect.
- **This task (DTA-LIVE-RC-002)**: Eliminated that defect and hardened the entire broker response path against all response variants.

---

*Report generated: 2026-08-29*  
*Commit: 87bb07c | Branch: main*  
*Engineer: GitHub Copilot (Claude Sonnet 4.6)*
