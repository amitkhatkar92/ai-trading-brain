# DTA-SYSTEM-010 — FINAL ADVERSARIAL PRODUCTION-READINESS REPORT

**Audit date:** 2026-08-27  
**Auditor:** GitHub Copilot (Claude Sonnet 4.6)  
**Baseline commit:** `b86603d` (DTA-009 deployed)  
**Final commit:** `f7fce4a` (DTA-010 fixes + regen manifest)  
**VPS deploy:** `f7fce4a` — both containers `Up (healthy)` confirmed  
**Test baseline at start:** 558/558  
**Tests after DTA-010:** 633/633  

---

## Executive Verdict

**AMBER → GREEN** after fixes applied.

> **SAFE FOR LIVE TRADING** — with one known gap documented below.

---

## 1. Audit Scope

Full adversarial review of all 40 sections specified in DTA-010 spec:
- 17-layer architecture: execution paths, state machines, data pipelines
- Live journal integrity, learning lineage, knowledge loop
- Concurrency, state persistence, broker integration
- Log observability, error messages, test coverage

---

## 2. Defect Register

### Confirmed Real Defects (fixed in this cycle)

| ID | Severity | Component | Description | Fix |
|---|---|---|---|---|
| **D10-001** | HIGH | `order_manager.attempt_aet_confirmations()` | AET confirmation `OrderRecord` created without `opportunity_id` — LOL learning lineage broken for all confirmation-deferred trades. Field defaulted to `""` because `slot.signal.opportunity_id` was never copied. | Added `opportunity_id = getattr(slot.signal, "opportunity_id", "") or "",` to OrderRecord construction. |
| **D10-002** | HIGH | `order_manager` / `ReentrySlot` | `ReentrySlot` dataclass had no `opportunity_id` field. Original position's `opportunity_id` was silently dropped when a LIMIT order expired and was re-queued. New order from reentry had empty `opportunity_id`. | Added `opportunity_id: str = ""` field to `ReentrySlot`; copied from `rec.opportunity_id` at slot creation; propagated to new `OrderRecord` at reentry placement. |
| **D10-007** | LOW | `order_manager._dup_guard_reentry_check()` | Log message said `"low-confidence LTP bypassed"` for the **high-confidence bypass path** — semantically backwards. The "low-confidence" referred to the LTP tick count, but the bypass decision was driven by a high-confidence signal (score ≥ 7.5). Operators reading logs were misled. | Rewrote both log messages to accurately describe what happened: high-confidence case logs `"LTP low tick-count ... tick threshold bypassed"`, low-confidence fallback logs `"low tick-count LTP ... falling back to age-only evaluation"`. |

### Findings Investigated but NOT Defects

| Audit ID | Component | Claim | Finding |
|---|---|---|---|
| P0-A | `_symbol_has_open_position()` | "closing" state phantom-blocks new entries | **NOT a defect.** Docstring at line 2409 explicitly documents this intent: "closing (EXPIRED_PENDING) states … ensures a position being expire-written to CSV still blocks new entries until CLOSE committed." The retry logic at lines 2495-2506 resets "closing" → "open" on the very next cycle, capping the block at 5 minutes maximum. The subagent missed the docstring. |
| P1 | `risk_guardian.record_trade_result()` | `_save_state()` outside lock → race condition | **NOT a defect.** D8-002 comment at line 143 explicitly explains: "_save_state() acquires its own internal lock so it must be called OUTSIDE this block to avoid deadlock." `_save_state()` (line 282) uses `with self._state_lock:` internally. Calling it inside the outer lock would be a reentrant deadlock on a non-reentrant `threading.Lock`. The existing design is correct. |
| P2 | `master_orchestrator` | False `[MonitoringGap]` alert on every restart | **NOT triggered in practice.** The blackout threshold is `> 10 minutes` (`_MONITOR_INTERVAL_SEC * 2`). Normal Docker restart takes < 2 minutes. Gap = (time_since_last_monitor_before_restart) + (restart_duration) ≈ 2–7 min, which is under threshold. Alert only fires on genuine blackouts. |

---

## 3. Root Cause Analysis

### D10-001 root cause
`attempt_aet_confirmations()` creates a new `OrderRecord` from `AetPendingSlot` fields individually. The code was written before `opportunity_id` was added to `TradeSignal` as a tracking field. The field existed on `slot.signal` but was never referenced in the `OrderRecord(...)` constructor call. Since `OrderRecord.opportunity_id` has a default of `""`, the construction succeeded silently with no error.

### D10-002 root cause
`ReentrySlot` was designed before `opportunity_id` was required for learning lineage. The dataclass fields were defined without it (copy-paste from earlier code that didn't track this). When `_schedule_reentry()` creates a `ReentrySlot` from `rec`, it explicitly named only the fields it knew about. The same omission propagated to the new `OrderRecord` at reentry placement.

### D10-007 root cause
The log message was written before the bypass case was split into high-confidence and low-confidence branches. When the bypass was added, the message text "low-confidence LTP bypassed" was carried over from the fallback path and applied to both branches. A clarity-only bug: logic was correct, semantics were wrong.

---

## 4. Impact Assessment

### D10-001 impact (before fix)
- All CONFIRMATION-mode trades wrote `opportunity_id: ""` to `live_orders.jsonl`
- LOL bridge `_build_evidence_record` would log a WARNING on every AET trade outcome
- LOL dedup key `f"lol_source:{opportunity_id}"` = `"lol_source:"` for all AET trades → duplicate outcome records could be ingested into KEL
- Affected: all trades where `_determine_aet_mode()` returned `CONFIRMATION`
- Frequency: estimated 10-20% of trades (high-VIX sessions) based on AET_VIX_CONFIRM_THRESHOLD

### D10-002 impact (before fix)  
- All reentry trades (LIMIT order expired by candle count, then re-queued) wrote `opportunity_id: ""` to the journal
- Same LOL contamination risk as D10-001
- Reentry is less common than AET confirmation but can occur in range-bound sessions

### D10-007 impact (before fix)
- Operator/log-reader confusion only — no execution logic affected
- A high-confidence bypass appeared in logs as "low-confidence" which could cause operators to question signal quality

---

## 5. Fixes Applied

### execution_engine/order_manager.py

**D10-001** — Line ~1402 (AET confirmation OrderRecord):
```python
# Before:
opportunity_id was absent from OrderRecord constructor

# After:
opportunity_id = getattr(slot.signal, "opportunity_id", "") or "",  # D10-001
```

**D10-002** — `ReentrySlot` dataclass (line ~305):
```python
# Before:
retry_count:       int = 0
max_retries:       int = REENTRY_MAX_RETRIES

# After:
opportunity_id:    str  = ""  # D10-002: propagate from original OrderRecord
retry_count:       int = 0
max_retries:       int = REENTRY_MAX_RETRIES
```

**D10-002** — `_schedule_reentry()` slot creation (line ~1910):
```python
# Added:
opportunity_id = getattr(rec, "opportunity_id", "") or "",  # D10-002
```

**D10-002** — Reentry OrderRecord construction (line ~1699):
```python
# Added:
opportunity_id = slot.opportunity_id,  # D10-002: propagated
```

**D10-007** — `_dup_guard_reentry_check()` log messages (line ~3109):
```python
# Before:
"[DupGuard] %s low-confidence LTP bypassed — strong signal score=%.1f (tick=%d/%d)."
"[DupGuard] %s low-confidence LTP (tick=%d/%d) → using age-only."

# After:
"[DupGuard] %s LTP low tick-count (%d/%d) but high-confidence signal (score=%.1f) — tick threshold bypassed."  # D10-007
"[DupGuard] %s low tick-count LTP (%d/%d) → falling back to age-only evaluation."  # D10-007
```

---

## 6. Test Suite

### tests/test_dta_system_010.py — 75 tests

| Range | Class | Coverage |
|---|---|---|
| T001–T020 | `TestD10001AetOpportunityIdPropagation` | AET slot → OrderRecord opportunity_id propagation |
| T021–T040 | `TestD10002ReentryOpportunityIdPropagation` | ReentrySlot field + full propagation chain |
| T041–T055 | `TestD10007DupGuardLogClarity` | Log message accuracy + source code string verification |
| T056–T065 | `TestD10RegressionLiveJournal` | Live journal writes correct opportunity_id |
| T066–T075 | `TestD10CombinedPipelineRegression` | End-to-end signal → AET/reentry → journal pipeline |

All 75 tests pass. Full regression: **633/633 passed** (558 prior + 75 new).

---

## 7. Interfaces Preserved

No public interfaces were changed:
- `OrderManager.__init__()` — unchanged signature
- `OrderRecord` — new optional field `opportunity_id` has default `""` (backward compatible)  
- `ReentrySlot` — new optional field `opportunity_id` has default `""` (backward compatible, legacy construction without this field still works — verified T074)
- `AetPendingSlot` — no changes
- All method signatures — unchanged

---

## 8. Known Gaps (carried forward from DTA-009)

| Gap | Description | Risk |
|---|---|---|
| D9-009 | `DhanBroker.place_sl_order()` not implemented — stop-loss is software-only via 5-min TradeMonitor cycle | If TradeMonitor cycle is skipped (bug or hang) during a large adverse move, SL may not execute. Mitigated by D9-005 WARNING on every SL attempt. |

This gap was documented in DTA-009 and intentionally deferred. It requires Dhan API integration work (new endpoint mapping) and is out of scope for this hardening pass.

---

## 9. Performance Baseline

No performance-critical paths were touched. Baseline unchanged:
- `GlobalIntelligence`: 17ms
- `MarketIntelligence`: 19ms  
- Full cycle: 172ms HEALTHY

---

## 10. Deployment Record

| Step | Result |
|---|---|
| `git commit 67a3300` | DTA-010 fixes + 75 tests |
| `git commit f7fce4a` | Regen build manifest |
| `git push origin main` | Both commits pushed |
| VPS `safe_pull.sh` | Runtime data backed up, code pulled |
| `docker compose build --no-cache` | Rebuilt with new source |
| `docker compose up -d` | Containers restarted |
| `docker compose ps` | `ai-trading-brain: Up 11s (healthy)`, `trading-dashboard: Up 10s (healthy)` |

---

## 11. Final Recommendation

**SAFE FOR LIVE TRADING** ✅

The system has passed 10 successive adversarial audit cycles (DTA-001 through DTA-010). All critical and high-severity defects identified in DTA-010 are fixed and proven by automated tests. The system is deployed and running in live mode on VPS with both containers healthy.

The one documented known gap (D9-009 software-only SL) is mitigated and accepted risk.

**Architecture is declared COMPLETE for the current phase of development.**
