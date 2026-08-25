# DTA-LIVE-003 — Final Report: LOL KDA Provenance + Evidence Bridge

**Commit:** `16982a1`
**Date:** 2026-08-25
**Verdict:** ✅ GREEN

---

## 1. Executive Summary

Two gaps identified in the DTA-LIVE-002 audit have been remediated:

| Gap | Description | Status |
|-----|-------------|--------|
| GAP-001 | LOL-2 KDA provenance bug: `'kda_results' in dir()` → always False | ✅ FIXED |
| GAP-002 | LOL `OUTCOME_OBSERVED` records not reaching KDA evidence ledger | ✅ IMPLEMENTED |

Both fixes are non-invasive, additive, and do not touch any protected module.

---

## 2. GAP-001: KDA Provenance Fix

### Root Cause

In `orchestrator/master_orchestrator.py` ~line 1215, the LOL-2 decision recording hook checked:

```python
kda_results=_kda_results if 'kda_results' in dir() else {},
```

`dir()` in Python returns names of items in the current scope. The variable was named `_kda_results` (with underscore prefix). The check was for `'kda_results'` (without underscore) — which was **always absent** from `dir()`. Therefore the condition was always `False` and `kda_results` was always `{}`.

This meant every LOL `DECISION_RECORDED` event had `kda_decision: KNOWLEDGE_INSUFFICIENT_EVIDENCE` regardless of actual KDA output.

### Fix

One-line change:

```python
# Before (buggy):
kda_results=_kda_results if 'kda_results' in dir() else {},

# After (correct):
kda_results=_kda_results if '_kda_results' in locals() else {},
```

`locals()` returns the actual local variable bindings. `'_kda_results'` is now the correct key. When `_kda_results` is defined (normal case), the actual KDA result dict flows to LOL. When it is absent (KDA threw an exception earlier), the safe empty dict `{}` is used.

### Impact

- All LOL `DECISION_RECORDED` events will now carry real `kda_decision`, `kda_authority`, and `knowledge_authority_score` values
- Historical LOL records (pre-fix) were written with `kda_decision: KNOWLEDGE_INSUFFICIENT_EVIDENCE` — these remain as-is (append-only ledger); they do not retroactively corrupt evidence
- No change to any execution path

---

## 3. GAP-002: LOL → KDA Evidence Bridge

### Root Cause

LOL wrote `OUTCOME_OBSERVED` records to `data/lol/LOL_YYYY-MM-DD.jsonl`. The KDA knowledge-fusion engine (`KnowledgeFusionEngine`) read from `data/knowledge_evidence_ledger.jsonl`. No code connected these two stores. Live counterfactual outcomes never reached the evidence pipeline.

### Architecture

The existing KDA architecture was reused without modification:

```
LOL OUTCOME_OBSERVED records
        ↓
lol_evidence_bridge.ingest_lol_outcomes()    [NEW]
        ↓ (append-only, idempotent, anti-lookahead)
knowledge_evidence_ledger.jsonl
        ↓ (existing, unchanged)
KnowledgeFusionEngine._load_knowledge_evidence_ledger()
        ↓ (existing, unchanged)
KDA MultiAngleView → knowledge decisions
```

No KDA, risk, or execution modules were modified.

### New Module: `learning_system/lol_evidence_bridge.py`

**Function:** `ingest_lol_outcomes(dates, lol_data_dir, knowledge_ledger, state_path) -> Dict`

**Supported outcome class → classification mapping:**

| LOL `outcome_class` | KSL `Classification` | `MissReason` |
|---|---|---|
| `EXECUTED_WIN` | `CORRECT_SELECT` | `NOT_APPLICABLE` |
| `TARGET_EXIT` | `CORRECT_SELECT` | `NOT_APPLICABLE` |
| `REJECTED_INCORRECT` | `RANKING_MISS` | `STRATEGY_REJECTION` |
| `BLOCKED_INCORRECT` | `RANKING_MISS` | `RISK_REJECTION` |
| `MISSED_OPPORTUNITY` | `RANKING_MISS` | `NOT_APPLICABLE` |
| `KDA_FALSE_NEGATIVE` | `RANKING_MISS` | `NOT_APPLICABLE` |
| `REJECTED_CORRECT` | `CORRECT_REJECT` | `NOT_APPLICABLE` |
| `BLOCKED_CORRECT` | `CORRECT_REJECT` | `NOT_APPLICABLE` |
| All others | *(skipped — ambiguous)* | — |

**Omitted classes and rationale:**
- `EXECUTED_LOSS`, `STOP_EXIT`: KDA selected but direction wrong — no clean Classification mapping exists
- `KDA_FALSE_POSITIVE`: same issue; would pollute evidence with incorrect signal
- `KNOWLEDGE_AGREEMENT`, `KNOWLEDGE_DISAGREEMENT`: ambiguous without direction outcome
- `EXECUTED_FLAT`, `EARLY_EXIT`, `SHORTLISTED_NOT_EXECUTED`: insufficient resolution

**Idempotency:** Dedup key `lol_{observation_id}` is scanned from existing `source_run_id` fields in the ledger before each run. Duplicate writes are impossible.

**Anti-lookahead enforcement:** Only records with `lifecycle_state == OUTCOME_OBSERVED` are processed. Additionally, `outcome_at > decision_at` is verified before writing. The `no_lookahead: True` field from the source LOL record is preserved in the output evidence.

**KFE compatibility:** Records are written with `event_type: "EVIDENCE"`. The KFE's `_load_knowledge_evidence_ledger()` filters for exactly this field.

**Restart safety:** State is tracked in `data/ksl/lol_bridge_state.json`. The `_load_existing_keys()` function reads from the ledger file itself (not state) so it works correctly even after a fresh restart without state.

### Orchestrator Wiring

Added LOL-4 bridge call in `_do_eod_learning()` immediately after the `fill_pending_outcomes` LOL call:

```python
# ── LOL→KDA: Evidence bridge ───────────────────────────────────────────────
try:
    from learning_system.lol_evidence_bridge import ingest_lol_outcomes as _lol_bridge
    _lol_bridge_result = _lol_bridge()
    if _lol_bridge_result.get("new_records", 0):
        log.info("[LOL-BRIDGE] Evidence ingested: new=%d skipped=%d", ...)
except Exception as _lol_bridge_exc:
    log.debug("[LOL-BRIDGE] Bridge skipped: %s", _lol_bridge_exc)
```

Non-blocking. Any exception is suppressed and logged at DEBUG level. The production EOD cycle continues regardless.

---

## 4. Safety Contract

| Property | Verified |
|---|---|
| `broker_calls == 0` | ✅ No broker imports in bridge module |
| `orders == 0` | ✅ No order placement |
| `execution_authority == False` | ✅ Observer-only |
| `PAPER_TRADING` unchanged | ✅ Not read or set |
| Protected files unmodified | ✅ See diff audit |
| Append-only ledger writes | ✅ Only `open("a", ...)` used |
| KDA decision authority unchanged | ✅ Bridge adds evidence; never modifies KDA weights |
| No mean-field writes | ✅ Shadow strategies remain shadow-only |

---

## 5. Diff Audit

```
Files changed (DTA-LIVE-003):
  orchestrator/master_orchestrator.py    (18 lines: 1 fix + 17 bridge call)
  learning_system/lol_evidence_bridge.py  (401 lines NEW)
  tests/test_lol_evidence_bridge.py       (732 lines NEW)
```

**Protected files NOT changed:**
- `order_manager.py` ❌
- `dhan_broker.py` ❌
- `risk_guardian.py` ❌
- `risk_control/` ❌
- `decision_engine/` ❌
- `knowledge_authority/knowledge_decision_pipeline.py` ❌
- All strategy files ❌

---

## 6. Test Results

| Suite | Tests | Result |
|---|---|---|
| `test_lol_evidence_bridge.py` | 24 | ✅ 24/24 |
| `test_learning_observation_ledger.py` | 59 | ✅ 59/59 |
| `test_kda_001.py` + `test_kda_002_validation.py` | 220 | ✅ 220/220 |
| **Combined** | **303** | ✅ **303/303** |

### Gap-001 test coverage (A-F):
- A: `_kda_results` defined in locals → actual results reach LOL ✅
- B: Old `dir()` bug confirmed as always-False; new `locals()` fix is correct ✅
- C: Multi-symbol KDA dict → all entries preserved ✅
- D: `None` KDA result → no crash ✅
- E: LOL exception → production cycle continues ✅
- F: LOL module has no broker/order calls (source inspection) ✅

### Gap-002 test coverage (A-H + I-M):
- A: `REJECTED_INCORRECT` → `RANKING_MISS` EVIDENCE record ✅
- B: `REJECTED_CORRECT` → `CORRECT_REJECT` EVIDENCE record ✅
- C: `EXECUTED_WIN` → `CORRECT_SELECT` EVIDENCE record ✅
- D: `EXECUTED_LOSS` (ambiguous) → skipped, 0 records written ✅
- E: Duplicate `obs_id` → idempotent (1 record total) ✅
- F: Restart reprocessing → 0 new records (3 remain) ✅
- G: Anti-lookahead: `outcome_at <= decision_at` → skipped ✅
- H: Production authority contract: no broker/order fields ✅
- I: `lifecycle_state == OUTCOME_PENDING` → skipped ✅
- J: All 8 supported outcome classes produce correct mapping ✅
- K: Missing parent dirs created on first write ✅
- L: Corrupt JSON lines skipped; valid records processed ✅
- M: State file updated with `total_lol_records_ingested` + `last_run` ✅
- Evidence `event_type == "EVIDENCE"` for KFE compatibility ✅
- `ge1/ge2/ge3` computed correctly from `actual_return_pct` ✅
- `source_run_id` format: `lol_{obs_id}` ✅
- Existing historical records not duplicated ✅

---

## 7. Deployment

```
Commit: 16982a1
Push:   origin/main
VPS:    git pull + docker compose build --no-cache + docker compose up -d
Status: ai-trading-brain   Up (healthy)
        trading-dashboard  Up (health: starting → healthy within ~60s)
```

---

## 8. Data Accumulation Note

Both fixes require live market sessions to produce data. The bridge will begin writing to `knowledge_evidence_ledger.jsonl` with source `"lol_live"` on the first EOD cycle that has LOL `OUTCOME_OBSERVED` records (T+1 after first intraday scan). Monitor with:

```bash
# On VPS
docker exec ai-trading-brain grep '"source":"lol_live"' data/knowledge_evidence_ledger.jsonl | wc -l
docker exec ai-trading-brain grep '"_kda_results"' /proc/1/fd/1  # runtime log check
```

---

## 9. Remaining Improvement Opportunities (Deferred)

| Item | Priority | Notes |
|---|---|---|
| Backfill historical LOL records with real KDA provenance | LOW | Pre-fix records have `kda_decision: KNOWLEDGE_INSUFFICIENT_EVIDENCE` — not harmful, just less informative |
| Add `EXECUTED_LOSS` → `FALSE_SELECT` classification when KSL models add this class | LOW | Currently skipped due to no clean mapping |
| LOL-live KFE reload trigger after bridge writes | LOW | KFE already reloads daily; no immediate urgency |

---

**DTA-LIVE-003 COMPLETE. Verdict: GREEN.**
