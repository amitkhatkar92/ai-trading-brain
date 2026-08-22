# OPS04D — Governance Window Patch Verification

**Date:** 2026-06-19  
**Method:** Evidence-only. Zero code modifications.  
**Scope:** Local repository + VPS container (`ai-trading-brain` @ `178.18.252.24`)

---

## 1. Locate — File Existence

| Artefact | Local Repository | VPS Container `/app/` |
|---|---|---|
| `governance_quarantine_patches.py` | ✅ Present (root of repo) | ❌ Not copied into image (untracked, never committed) |
| `deploy_forensic_audits.py` | ✅ Present (root of repo) | ❌ Not copied into image (untracked, never committed) |
| `ExecutionWindowAudit` token in `execution_engine/order_manager.py` | ❌ **0 matches** | ❌ **0 matches** (`grep` count = 0) |
| `ExecutionWindowBlock` token in `execution_engine/order_manager.py` | ❌ **0 matches** | ❌ **0 matches** |
| `_exec_win_open` variable in `execution_engine/order_manager.py` | ❌ **0 matches** | ❌ **0 matches** |

**What these scripts are:**  
`governance_quarantine_patches.py` and `deploy_forensic_audits.py` are **standalone imperative patch scripts** — they contain Python `str.replace()` calls that would mutate source files in place. They are not importable modules and confer no protection by simply existing. They must be *executed* inside the container to take effect. Neither was ever run.

---

## 2. Verify — Loaded at Runtime / Referenced by Orchestrator

| Check | Result | Evidence |
|---|---|---|
| `ExecutionWindowBlock` in live container `order_manager.py` | ❌ Not present | `docker exec … grep -c` = **0** |
| `ExecutionWindowAudit` in live container `order_manager.py` | ❌ Not present | `docker exec … grep -c` = **0** |
| Any `09:45` or `exec_win` check in `order_manager.py` | ❌ Not present | `Select-String` = no output |
| `governance_quarantine_patches` imported by orchestrator | ❌ Never imported | No reference in any orchestrator file |
| `deploy_forensic_audits` imported anywhere | ❌ Never imported | No reference in any module |
| Time checks present in `order_manager.execute()` | ⚠️ Partial | Only **late-day** guards: `LateEntryBlock` ≥14:30 and elevated floor 13:30–14:30. No early-entry guard. |

---

## 3. Trace — Production Execution Path at 09:10

```
config.py line 94
  SCHEDULE["first_opportunity_scan"] = "09:10"
        │
        ▼
market_intelligence/market_monitor.py line 302
  deep_scan_slots = {"09:10": "first_opportunity_scan", ...}
  → fires registered orchestrator callback
        │
        ▼
orchestrator/master_orchestrator.py line 505
  elif actual_name in ("first_opportunity_scan", ...):
      self.task_queue.submit_to(
          "MasterOrchestrator",
          self.run_full_cycle,          ← direct call, NOT _guarded_cycle
          priority=Priority.HIGH,
      )
        │
        ▼
orchestrator/master_orchestrator.py  run_full_cycle()
  ┌─ checks: self._halt → skip if halted
  ├─ checks: is_trading_enabled() → skip if kill-switch active
  └─ NO _is_market_session() call  ← market-hours gate is absent here
        │
        ▼
  [full analysis pipeline runs]
  → opportunity_engine → decision_engine → order_manager.execute(signal)
        │
        ▼
execution_engine/order_manager.py  execute()
  ├─ DupGuard       — blocks same-symbol duplicate
  ├─ MaxPositions   — blocks if ≥ MAX_OPEN_POSITIONS
  ├─ LateEntryBlock — blocks if NOW ≥ 14:30
  ├─ ElevatedScore  — requires score ≥ 7.0 if NOW ≥ 13:30
  └─ (no early-entry gate)          ← 09:45 governance window not enforced
```

**Critical structural fact:**  
`_guarded_cycle()` (the only method calling `_is_market_session()`) is **only** scheduled by `start_scheduler()` at fixed slots: `09:45, 10:30, 11:30, 13:00, 14:00, 15:00`. The `first_opportunity_scan` deep scan at 09:10 enters via `run_full_cycle` directly — it **bypasses `_guarded_cycle` entirely**.

```python
# master_orchestrator.py line 5248-5252
def _guarded_cycle(self) -> None:
    """Run a full cycle only during market hours; log a skip otherwise."""
    if self._is_market_session():          # gates on 09:15, not 09:45
        self.run_full_cycle()
    else:
        log.debug("[Orchestrator] Outside market session — cycle skipped.")
```

Note: even if `first_opportunity_scan` were routed through `_guarded_cycle`, the gate is **09:15** (NSE open), not 09:45. The 09:45 rule exists only as a scheduler design choice (no slot before 09:45) — it is not enforced in code.

---

## 4. Simulate — Signal at 09:10 IST

**Scenario:** qualifying signal generated at 09:10, confidence_score ≥ 6.5, single open position, capital within limits.

| Gate | Fires at 09:10? | Result |
|---|---|---|
| `self._halt` | No | Pass |
| Kill switch (`is_trading_enabled`) | No | Pass |
| `_is_market_session()` | Never reached — not on this path | — |
| DupGuard (same symbol open) | Depends on positions | Pass (assume none open) |
| MaxPositions guard | Depends on count | Pass (assume < max) |
| `ExecutionWindowBlock` (09:45 gate) | **ABSENT** | Not reached |
| `LateEntryBlock` (≥14:30) | Not triggered at 09:10 | Pass |
| Elevated score (13:30–14:30) | Not triggered at 09:10 | Pass |
| Capital/exposure guards | Depends on notional | Pass (assume within limits) |
| Price integrity guard | Depends on price | Pass (assume clean) |

**Answer: YES — a qualifying signal at 09:10 executes.**

The order proceeds to `_place_entry_with_retry()` and is submitted to the broker.

---

## 5. Final Verdict

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   VERDICT:  PATCH NOT DEPLOYED                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

### Evidence summary

| Dimension | Finding |
|---|---|
| Patch scripts exist locally | ✅ Yes — `governance_quarantine_patches.py` and `deploy_forensic_audits.py` present in repo root |
| Patch scripts committed | ❌ No — both are untracked (`??` in `git status`), never pushed |
| Patch applied to local `order_manager.py` | ❌ No — zero tokens in source |
| Patch applied to VPS container `order_manager.py` | ❌ No — grep count = 0 (definitive) |
| Patch loaded at runtime | ❌ No — no import, no reference in any orchestrator or module |
| Early-entry time gate present anywhere in execution path | ❌ No — confirmed absent |
| OPS04B conclusion still valid | ✅ Yes — report stated "never applied"; confirmed unchanged |

### What IS enforced (existing late-day gates)

| Rule | Code | Gate |
|---|---|---|
| `LateEntryBlock` | `order_manager.py:589-599` | Blocks fresh entries **after 14:30** |
| Elevated conviction | `order_manager.py:600-606` | Score ≥ 7.0 required **13:30–14:30** |
| Max open positions | `order_manager.py:536-581` | No gate on time, only count |

### What is NOT enforced

- No block on pre-09:45 entries  
- No block on pre-09:15 entries (even `_is_market_session()` is bypassed via `first_opportunity_scan` → `run_full_cycle` direct path)  
- 09:45 governance window exists as scheduler intent only, not in code

### Recommended action (for human decision)

The `ExecutionWindowBlock` in `governance_quarantine_patches.py` (lines 24–61) is the authored fix. Applying it would add a `return None` to `order_manager.execute()` when `datetime.now() < 09:45 IST`. This requires explicit approval and deployment via the standard `git commit → push → deploy.sh` flow.

---

*Report produced from: `execution_engine/order_manager.py`, `orchestrator/master_orchestrator.py`, `config.py`, `market_intelligence/market_monitor.py`, `governance_quarantine_patches.py`, `deploy_forensic_audits.py`, live VPS `docker exec grep`. No code was modified during this investigation.*
