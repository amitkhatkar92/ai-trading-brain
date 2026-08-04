# AMLS Activation Certification — O-001

**Date:** 2026-05-13  
**Task:** O-001 — Wire AMLS into production `_do_eod_learning()`  
**Certifier:** MLS Phase 6 integration (no algorithm changes)

---

## Certification Answers

### Q1: Is O-001 completely resolved?

**YES.**

AMLS is now active in the production EOD workflow.  
`_do_eod_learning()` in `orchestrator/master_orchestrator.py` invokes
`self.amls.run_pipeline()` as its final action, after all existing production
learning, validation, analytics, and audit blocks have completed.

Changes applied:

| File | Change |
|---|---|
| `config.py` | Added `AMLS_ENABLED: bool = True` |
| `orchestrator/master_orchestrator.py` | `__init__`: initialise `self.amls` after `self.pig_adapter` |
| `orchestrator/master_orchestrator.py` | `_do_eod_learning()`: AMLS call at the very end |

---

### Q2: Does AMLS execute exactly once per EOD cycle?

**YES.**

`self.amls.run_pipeline()` is called in exactly one location: at the end of
`_do_eod_learning()`. `_do_eod_learning()` is itself called from
`run_eod_learning()` (line 3287), which is called by the scheduler once per day
at the end-of-day slot. No other code path invokes AMLS.

---

### Q3: Can production continue if AMLS fails?

**YES.**

The AMLS call is wrapped in a bare `try / except Exception` block:

```python
try:
    if getattr(self, "amls", None) is not None:
        _amls_run = self.amls.run_pipeline()
        ...
        log.info("[AMLS] state=... duration_ms=... ...")
    else:
        log.debug("[AMLS] Scheduler not available — skipping EOD pipeline.")
except Exception as _amls_eod_exc:
    log.warning("[AMLS] EOD pipeline failed (non-critical): %s", _amls_eod_exc)
```

Any exception — import error, `run_pipeline()` crash, log format error — is
caught, logged at WARNING level, and the method returns normally. All preceding
production learning results (PnL, trades, strategy stats, telemetry) are
already committed by the time AMLS runs.

Similarly, `self.amls` initialisation in `__init__` catches all exceptions and
falls back to `self.amls = None`, so an import failure on startup does not
prevent the orchestrator from starting.

---

### Q4: Is PIG refreshed automatically after successful MLS execution?

**YES.**

Stage 6 of the AMLS 7-stage pipeline is `STAGE_PIG_REFRESH` (`pig_refresh`).
The `AutonomousMarketLearningScheduler` calls `pig_adapter.reload_library()` on
the same `PIGTradingAdapter` instance that was injected at `self.amls` init time
(which is the same instance as `self.pig_adapter`). The result is reported in
the `[AMLS]` log line as `pig_refresh=True/False`.

The orchestrator injects the adapter at init:

```python
self.amls = AutonomousMarketLearningScheduler(pig_adapter=self.pig_adapter)
```

---

## Log Evidence (expected in production)

On a normal trading day the EOD log will contain:

```
[AMLS] state=SUCCESS duration_ms=1423 pipeline_version=phase6 \
       dna_updates=True repository_updates=14 pig_refresh=True
```

On a non-trading day (weekend / holiday), AMLS `run_pipeline()` returns early
with `state=SKIPPED`, and the log will show:

```
[AMLS] state=SKIPPED duration_ms=0 pipeline_version=phase6 \
       dna_updates=False repository_updates=0 pig_refresh=False
```

If AMLS is disabled in config (`AMLS_ENABLED=False`), `self.amls` is `None`
and the log shows only:

```
DEBUG [AMLS] Scheduler not available — skipping EOD pipeline.
```

---

## Regression Guarantee

- `AMLS_ENABLED=False` → system behaviour **identical** to before this change.
- AMLS exception → `WARNING` log, no re-raise, EOD workflow continues.
- No MLS algorithms changed.  
- No DNA logic changed.  
- No PMCI logic changed.  
- All existing `_do_eod_learning()` blocks execute unconditionally before AMLS.

---

**Verdict: O-001 COMPLETE — AMLS is active in production.**
