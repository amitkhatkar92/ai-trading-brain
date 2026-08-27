# DTA-SYSTEM-011 — FINAL ADVERSARIAL PRODUCTION-READINESS REPORT

**Audit date:** 2026-08-27  
**Baseline commit:** `e043267` (local) / `67a3300` (container manifest)  
**Auditor:** GitHub Copilot (Claude Sonnet 4.6)  
**Mode:** AUDIT ONLY — no code modified  
**System:** LIVE / Dhan / ₹50,000 / `PAPER_TRADING=false` / `LIVE_TRADING_AUTHORIZED=true`  

---

## 1. EXECUTIVE VERDICT

**🔴 AMBER — TRADING SHOULD BE PAUSED UNTIL F11-001 AND F11-002 ARE FIXED**

Two critical/high defects affect live capital safety:

1. **F11-001 CRITICAL**: `FailSafeRiskGuardian.record_trade_result()` is **never called** in any production code path. Daily loss kill-switch (≥2% daily loss) and consecutive-loss circuit breaker are **permanently inactive**. `_daily_pnl` stays `0.0` forever. VPS state file confirms: `{"daily_pnl": 0.0, "consec_losses": 0}` all day regardless of actual trading losses. PRODUCTION_SAFETY_REPORT.md claim "record_trade_result(pnl, won) called on every fill ✅" is **FALSE**.

2. **F11-002 HIGH**: `attempt_all_reentries()` has no `_reconcile_fill()` call. A broker-rejected reentry order creates a phantom open position in `_orders` and `_portfolio.positions`. The phantom blocks all new signals for the same symbol for the rest of the session (DupGuard sees it as open). `reconcile_partial_fills()` cannot detect it either (it skips `filled_qty=0`).

All other findings are medium or lower severity and do not require immediate trading halt, but **must be fixed in DTA-011-FIX** before declaring the system production-certified.

---

## 2. CURRENT DEPLOYMENT BASELINE

| Item | Value |
|---|---|
| Local HEAD | `e043267` |
| Container manifest commit | `67a3300` |
| Container code matches | YES (DTA-010 markers confirmed in container) |
| Git branch | `main` |
| VPS container status | Both `Up (healthy)`, 0 restarts |
| Working tree modifications | `data/paper_trades.csv`, `pytest_out.txt` (runtime, untracked) |
| Broker | `dhan` |
| PAPER_TRADING | `False` |
| LIVE_TRADING_AUTHORIZED | `true` |
| TOTAL_CAPITAL | ₹50,000 |
| Test baseline (prior DTA) | 633/633 ✅ |
| Scheduler | Running (`python main.py --schedule`) |

**Deployment drift:** None. Container `order_manager.py` MD5 differs from host only due to CRLF→LF conversion during Docker build. DTA-010 markers (`D10-001`, `D10-002`, `D10-007`) and D9-011 fix (`halt_reason[:100]`) confirmed in container.

---

## 3. TOP→BOTTOM TRACE

**Path:** Scanner → Decision → OrderManager → Broker → Position

| Boundary | Status |
|---|---|
| Scanner generates `TradeSignal` with `opportunity_id` | ✅ UUID assigned at line 1440 if missing |
| KDA shadow evaluation per signal | ✅ `knowledge_pipeline.run_knowledge_shadow()` line 1138 |
| RiskGuardian.evaluate() before execute() | ✅ Called each cycle; VIX/halt/exposure checks active |
| execute() price integrity guard | ✅ Line 800: blocks wrong-band entry_price |
| execute() stop_loss=0 guard | ❌ **F11-004** — warning only, does not block |
| execute() → _reconcile_fill() | ✅ Called before position registration |
| execute() REJECTED guard | ✅ Line 907: REJECTED → return None, no position created |
| execute() journal before _orders registration | ✅ D-011 fix confirmed |
| AET confirmation → _reconcile_fill() | ✅ Called; REJECTED check present at line 1409 |
| AET confirmation → opportunity_id | ✅ D10-001 fix confirmed |
| Reentry → _reconcile_fill() | ❌ **F11-002** — MISSING |
| Reentry → opportunity_id | ✅ D10-002 fix confirmed |
| close_position() → risk_guardian.record_trade_result() | ❌ **F11-001** — NEVER called anywhere |
| close_position() → EventBus POSITION_CLOSED | ✅ Published |
| POSITION_CLOSED subscriber (ExecutionBridge) → risk_guardian | ❌ Not wired |

---

## 4. BOTTOM→TOP TRACE

**Path:** Broker fill → learning feedback

| Stage | Status | Verification Level |
|---|---|---|
| Broker fill → _reconcile_fill() | ✅ | STATIC + TEST VERIFIED |
| fill_status="FILLED" → position registered | ✅ | STATIC + TEST VERIFIED |
| TradeMonitor SL/target hit → close_position() | ✅ | STATIC VERIFIED |
| close_position() → PnL calculated | ✅ | STATIC VERIFIED |
| close_position() → risk_guardian.record_trade_result() | ❌ MISSING | STATIC CONFIRMED BROKEN |
| close_position() → LOL outcome filled | ✅ (via EOD) | STATIC VERIFIED |
| EOD → ingest_lol_outcomes() → KEL | ✅ | STATIC VERIFIED |
| KEL → KFE.analyse_record() via run_eod_knowledge_update() | ✅ | STATIC VERIFIED |
| KFE → KDA authority score | ✅ | STATIC VERIFIED |
| KDA score → decision gating (KNOWLEDGE_HOLD blocks trade) | ✅ | STATIC VERIFIED |
| strategy_performance_tracker.record_trade() | ✅ (from EOD) | STATIC VERIFIED |
| LearningEngine.learn() | ✅ (from EOD) | STATIC VERIFIED |

**Runtime verified on VPS:** Only that containers are healthy and scheduler is running. No trade has been executed in this session (live_orders.jsonl absent). All bottom→top stages are **STATIC VERIFIED** only.

---

## 5. OPPORTUNITY LINEAGE

| Stage | opportunity_id status |
|---|---|
| Scanner signal creation | ✅ UUID generated if absent (line 1440) |
| execute() → OrderRecord | ✅ `getattr(signal, "opportunity_id", "") or ""` |
| AET confirmation → OrderRecord | ✅ D10-001 fix: `getattr(slot.signal, "opportunity_id", "") or ""` |
| Reentry slot creation | ✅ D10-002 fix: `getattr(rec, "opportunity_id", "") or ""` |
| Reentry OrderRecord | ✅ `slot.opportunity_id` |
| live_orders.jsonl (journal write) | ✅ Written by `_append_live_journal()` |
| Journal restore (_restore_from_live_journal) | ✅ `row.get("opportunity_id") or ""` |
| LOL observation_id (obs_id hash) | ⚠️ **F11-015** — hash of `(symbol, date, entry_price)` excludes UUID |
| LOL obs_id multi-cycle dedup | ⚠️ **F11-015** — same symbol+date+price on 2nd scan → first UUID in LOL, second UUID in OrderRecord |
| KEL evidence opportunity_id | ✅ Propagated from LOL record |
| SmartSwap eviction | ❌ NOT TRACED — new signal opportunity_id is set, but evicted position's opportunity_id is not linked |

**Summary:** The D10 fixes ensure `opportunity_id` survives AET and reentry. The main remaining gap is F11-015: LOL dedup uses `(symbol, date, entry_price)` hash, not the UUID. If the scanner re-generates a new UUID for the same setup across cycles, the OrderRecord has UUID-B but LOL has UUID-A. The lineage join from OrderRecord → LOL is broken for multi-cycle setups.

---

## 6. EXACTLY-ONCE / IDEMPOTENCY

| Operation | Can Run Twice? | Safe? |
|---|---|---|
| LOL observation write | Yes (same obs_id → skipped via `_pending`) | ✅ Idempotent |
| LOL outcome fill | Yes (lifecycle_state check) | ✅ Idempotent |
| LOL→KEL bridge | Yes (dedup by `source_run_id`) | ✅ Idempotent |
| KEL batch write | Yes, partial line dropped on crash, re-written next run | ✅ Safe |
| EOD status write | On crash before write: EOD re-runs next restart | ⚠️ **F11-013** |
| strategy_performance record_trade() | No order_id dedup | ⚠️ **F11-014** double-counts |
| broker reconciliation | Idempotent (broker is source of truth) | ✅ |
| live journal append | Append-only, each event is unique | ✅ |
| AET slots | In-memory only, lost on restart | ✅ (no duplicate risk) |
| Reentry slots | In-memory only, lost on restart | ✅ (no duplicate risk) |

---

## 7. CRASH + RESTART SAFETY

| Scenario | Safety |
|---|---|
| Crash between broker_place() and journal write (execute) | ✅ No journal → no position → next cycle rescans |
| Crash between journal write and _orders[id]=rec | ✅ Journal restore rebuilds position on restart |
| Crash between _orders registration and _update_portfolio() | ✅ Journal restore rebuilds both from OPEN event |
| Crash during EOD status file write | ⚠️ **F11-013** — EOD re-runs for same day, double-counts |
| Restart with PENDING fill_status | ✅ reconcile_startup_fills() verifies all JOURNAL_RESTORED |
| Restart with RiskGuardian halt | ✅ _load_state() restores halt; daily_pnl=0 (hollow) per F11-001 |
| Restart with daily loss > 2% | ❌ **F11-001** — daily_pnl was never updated, state=0 forever |
| Restart with AET pending | ✅ Slots lost; scanner will re-generate on next cycle |
| Restart with reentry pending | ✅ Slots lost; LIMIT order in broker already placed; reconcile handles |
| 3-day stale OPEN in paper_trades.csv | ⚠️ **F11-031** — will rehydrate as phantom positions on paper restart |

---

## 8. BROKER RECONCILIATION

| Scenario | Handling |
|---|---|
| place_order() returns None | ✅ Caught via _place_entry_with_retry(); retried up to MAX_ORDER_RETRIES |
| place_order() raises exception | ✅ Caught in _place_entry_with_retry() per attempt; returns None after retries |
| get_fill_details() returns None | ✅ _reconcile_fill() handles via status="UNKNOWN" |
| get_fill_details() raises exception | ✅ _reconcile_fill() has try/except; sets fill_status="API_ERROR" |
| FILLED → actual_fill_price=0 | ✅ D9-002 fix: UNRESOLVED + ERROR log |
| PARTIALLY_FILLED → filled_qty=0 | ⚠️ **F11-007** — quantity not updated; original qty stays |
| PARTIALLY_FILLED → rec.quantity updates | ✅ D9-006 fix: quantity = filled_qty when fill_price > 0 |
| PENDING status — intraday retry loop | ❌ **F11-006** — no intraday re-reconciliation; PENDING stays until restart |
| Reentry path after _broker_place() | ❌ **F11-002** — no _reconcile_fill() call at all |
| Auto-square-off by broker at 15:20 | ✅ TradeMonitor detects position gone via check_and_expire_stale_limits(); ORPHAN_CLOSE |
| Place_order → broker rejected (reentry) | ❌ **F11-002** — position registered regardless |

---

## 9. RISKGUARDIAN SAFETY

**Invariants:**

| Invariant | Status | Evidence |
|---|---|---|
| VIX kill-switch (≥45) | ✅ Active | evaluate() checks VIX each cycle |
| Daily loss halt (≥2%) | ❌ PERMANENTLY INACTIVE | **F11-001**: record_trade_result() never called; _daily_pnl=0 always |
| Consecutive loss circuit (≥3) | ❌ PERMANENTLY INACTIVE | **F11-001**: _consec_losses=0 always |
| Max open trades governor (≥8) | ❌ PERMANENTLY INACTIVE | **F11-001**: _open_trades=0 always (record_open_trade never called) |
| Position size governor (drawdown tiers) | ❌ Returns 1.0 always | get_position_governor_factor(): daily_loss_pct=0% always |
| Halt survives restart | ✅ Conditional | VIX halts persist; daily-loss halts impossible to trigger |
| Corrupt state fails closed | ✅ | _load_state(): json.JSONDecodeError → reverts to zeros (safe) |
| AET path bypasses kill-switch re-check | ⚠️ **F11-010** | AET checks relative VIX, not absolute KILL_SWITCH_VIX (45) |
| Reentry path bypasses kill-switch re-check | ⚠️ **F11-010** | No kill-switch re-evaluation before deferred placement |

**VPS state confirmation:** `data/risk_guardian_state.json` shows `{"daily_pnl": 0.0, "consec_losses": 0}` even after a day of scheduler activity. This is runtime proof that record_trade_result() was never called.

---

## 10. ANTI-LOOKAHEAD

| Component | Temporal Correctness |
|---|---|
| LOL observation recording | ✅ `trading_date = date.today()`, `observed_at` = wall clock |
| LOL outcome fill (T+1..T+5 bars) | ✅ `if t1 > today: continue` anti-lookahead guard |
| `no_lookahead` flag computation | ✅ `_to_utc(outcome_at) > _to_utc(decision_at)` |
| `outcome_at` when bar has no date | ⚠️ **F11-021** — falls back to `datetime.now()` (wall clock) |
| KEL timestamp ordering | ✅ LOL bridge verifies temporal order before admitting |
| KFE/KDA historical analysis | ✅ Reads from historical ledger, no current-day contamination |
| Scanner price reads | ✅ Current prices only used for current-cycle decisions |
| MetaModel/StrategyLab | ✅ Only historical OHLCV used in backtesting |

---

## 11. LEARNING LOOP

**End-to-end learning status:**

```
Scanner Signal → [KDA shadow per cycle] → KDA writes KDALedger JSONL
                                                    ↑
Trade Outcome → EOD: fill_pending_outcomes()        ↓
             → EOD: ingest_lol_outcomes()       KFE reads KEL daily
             → KEL (knowledge_evidence_ledger.jsonl)
                    ↓
             KnowledgeDecisionPipeline.run_eod_knowledge_update()
                    ↓ (next day)
             run_knowledge_shadow() → KNOWLEDGE_HOLD blocks signal
                                    → KNOWLEDGE_BUY/SELL adds to candidates
```

The closed-loop connection exists in code. However:
- **NOT YET RUNTIME VERIFIED** — no trade has been fully executed and EOD'd in recent sessions (live_orders.jsonl absent)
- **ARCHITECTURE_GAP_REGISTER.md line 56** documents that LearningEngine.learn() writes per-strategy stats to `data/learning_db.json` but this does NOT flow into KLP/HBE/KFE. Two learning systems exist in parallel without joining.
- The KDA KNOWLEDGE_HOLD override IS wired (line 1156: StrategyLab pass overridden).

---

## 12. STATE MACHINE

**OrderRecord lifecycle states:**

```
(new) → "open" → "closing" → "open" (retry)
                           → "closed"
        "open" → "cancelled"
        "open" → "closed"
```

**No illegal transitions found.** The `"closing" → "open"` retry is intentional (documented).

**fill_status transitions:**

```
"" (default) → "FILLED" | "PARTIALLY_FILLED" | "REJECTED" | "PENDING"
             | "UNRESOLVED" | "API_ERROR" | "UNKNOWN"
             | "PAPER" | "SIM" | "JOURNAL_RESTORED"
```

**Gap:** fill_status="PENDING" for live orders has no intraday resolution path (F11-006).

**REJECTED status in execute() path:** ✅ Position not created.  
**REJECTED status in AET confirmation path:** ✅ Position not created.  
**REJECTED status in reentry path:** ❌ F11-002 — _reconcile_fill() not called, fill_status="" throughout.

---

## 13. CONCURRENCY

**Shared mutable state:**

| Object | Protected by lock? | Concurrent writers |
|---|---|---|
| `self._orders` | ❌ NO | execute() (main cycle) + attempt_aet_confirmations() (TradeMonitor) + attempt_all_reentries() (TradeMonitor) |
| `self._portfolio.positions` | ❌ NO | Same as _orders |
| `self._aet_pending` | ❌ NO | execute() + attempt_aet_confirmations() |
| `self._reentry_slots` | ❌ NO | close_position() (expire path) + attempt_all_reentries() |
| `self._journal_lock` | ✅ YES | paper_trades.csv writes |
| `self._expiry_sidecar_lock` | ✅ YES | expiry_retries.json writes |
| `RiskGuardian._state_lock` | ✅ YES | record_trade_result() (never called per F11-001) |

**F11-027 CONFIRMED:** `get_open_orders()` (line 1204) iterates `self._orders.values()` without `list()` snapshot. `get_open_order_ids()` (line 1210) iterates `self._orders.items()` without `list()`. If execute() inserts a new key into `self._orders` while the TradeMonitor worker iterates the same dict, Python raises `RuntimeError: dictionary changed size during iteration`. Task queue catches this but monitoring cycle is aborted for that pass.

**In practice:** CPython GIL prevents true simultaneous execution, reducing but not eliminating the risk. Under load (multiple symbols scanning + monitoring active), GIL can yield between `for oid, rec in self._orders.items()` and an insert.

---

## 14. FAILURE / SILENT FAILURE

**Dangerous silent success patterns found:**

| Location | Pattern | Classification |
|---|---|---|
| `order_manager.py` pre-order price guard (~L808) | `except Exception as _pv_exc: log.debug(...)` — proceeds with execution | **DANGEROUS**: price guard can be silently bypassed |
| `order_manager.py` transaction costs (~L1062) | `except Exception: pass` — proceeds without cost deduction | SAFE FALLBACK (PnL slightly wrong) |
| `order_manager.py` Telegram notification (~L1115) | `except Exception: pass` | SAFE FALLBACK |
| `order_manager.py` EventBus publish (~L1120) | `except Exception: pass` | SAFE FALLBACK |
| `order_manager.py` exit_analytics (~L1162) | `except Exception: pass` | SAFE FALLBACK (research only) |
| `lol_evidence_bridge.py` ingest_lol_outcomes (~L130) | `except Exception: log.debug(...)` — returns empty dict | **DANGEROUS**: learning failures are DEBUG-level invisible |
| `master_orchestrator.py` KDA shadow (~L1138) | Wrapped in try/except → returns empty dict | SAFE: trading proceeds without KDA input |
| `risk_guardian.py` _save_state | `except Exception: log.warning(...)` | ACCEPTABLE: non-critical state write |

**Most dangerous:** The pre-order price guard is wrapped in `log.debug` fallback. If `get_price_validator()` import fails (module missing, circular import), the price integrity check is silently bypassed and the trade proceeds without any entry price validation.

---

## 15. TEST QUALITY

| Safety Function | Positive Test | Negative Test | Integration Test | Restart Test | Assessment |
|---|---|---|---|---|---|
| record_trade_result() | ✅ 13 tests | ✅ lock tests | ❌ NO wiring test | ✅ via state file | **F11-039**: isolated tests cannot detect missing caller |
| close_position() | ✅ | ✅ | ❌ NO risk_guardian call | N/A | Caller wiring untested |
| _reconcile_fill() REJECTED | ✅ | ✅ | ✅ | N/A | OK |
| reentry broker rejection | ❌ NO TEST | ❌ | ❌ | ❌ | **F11-040**: F11-002 undetectable |
| concurrent _orders mutation | ❌ NO TEST | ❌ | ❌ | ❌ | **F11-041**: F11-027 undetectable |
| opportunity_id through AET | ✅ 20 tests | ✅ | ✅ | N/A | OK (D10-001) |
| opportunity_id through reentry | ✅ 20 tests | ✅ | ✅ | N/A | OK (D10-002) |
| stop_loss=0 execution block | ❌ NO TEST | ❌ | ❌ | ❌ | **F11-004** undetectable |
| AET/reentry kill-switch re-check | ❌ NO TEST | ❌ | ❌ | ❌ | **F11-010** undetectable |
| EOD double-run prevention | ❌ NO TEST | ❌ | ❌ | ❌ | **F11-013** undetectable |

**Root structural problem:** Tests for safety functions verify the functions in isolation (unit tests). The integration tests that verify a function is called from its correct place in the production call chain are largely absent. This means any regression that removes a function call from the production path goes undetected.

---

## 16. DEPLOYMENT DRIFT

| File | Container MD5 | Host MD5 | Status |
|---|---|---|---|
| `execution_engine/order_manager.py` | `86e1a902...` | `8260c41f...` | CRLF/LF diff — content same (6 DTA-010 markers confirmed) |
| `risk_guardian/risk_guardian.py` | `3d752db0...` | Different | CRLF/LF only |
| `orchestrator/master_orchestrator.py` | `7f37bfba...` | Different | CRLF/LF only |
| `learning_system/lol_evidence_bridge.py` | `02e72a56...` | Different | CRLF/LF only |

**Verdict: No functional deployment drift.** All DTA-009 and DTA-010 fixes confirmed in container. Container manifest shows `67a3300` (the DTA-010 code commit). Commits `f7fce4a` (manifest regen) and `e043267` (report doc) contain no production code changes.

---

## 17. DATA INTEGRITY

| File | Status |
|---|---|
| `data/strategy_performance.json` | ✅ Valid JSON, 2 strategies, no NaN/Inf |
| `data/risk_guardian_state.json` (VPS) | ✅ Valid JSON, `daily_pnl=0.0` (reflects F11-001 — never updated) |
| `data/paper_trades.csv` | ⚠️ **F11-031**: 2 OPEN events from 2026-08-24 (3 days stale), no CLOSE events |
| `data/live/live_orders.jsonl` | ✅ Not present (no live trades in current session) |
| `data/live/` (VPS) | 11 CANCELLED records for COALINDIA; 0 phantom OPENs |
| `data/borderline_rejections.json` | ✅ Present and valid |

---

## 18. OPTIONS / EQUITY

| Aspect | Status |
|---|---|
| Separate execution module (`options_order_manager.py`) | ✅ Distinct from equity OM |
| Separate performance tracker (`options_performance_tracker.py`) | ✅ |
| options_order_manager calls get_options_performance_tracker().record_closed_trade() | ✅ Line 1408 |
| Equity OM calls risk_guardian.record_trade_result() | ❌ F11-001 — never |
| Options OM calls risk_guardian.record_trade_result() | ❌ NOT found in any production code |
| Shared RiskGuardian.evaluate() gate | ✅ Both should use same kill-switch |
| Options can bypass equity RiskGuardian | NOT CONFIRMED — options_order_manager not fully audited |

---

## 19. MISSING INFORMATION / LEARNING GAPS

| Information | Currently Persisted? | Learnable Later? |
|---|---|---|
| Signals blocked by RiskGuardian | ❌ **F11-033** — log only | NO — false-rejection rate unanalyzable |
| Near-miss signals (below score threshold) | ❌ **F11-034** | NO — threshold calibration impossible |
| Slippage (actual vs requested fill price) | Collected on OrderRecord | ⚠️ **F11-035** — never passed to LearningEngine |
| Broker fill latency | ❌ Not measured | NO |
| Stale data events | ❌ Log only | NO |
| Correlated signals (same cycle, different symbols) | ❌ No cycle_id | NO |
| Failed exits (broker returned None) | ✅ ORPHAN_CLOSE tag | PARTIAL |
| Transaction costs | ✅ Deducted from PnL | YES |
| R-multiple at close | ✅ Written to _RECENT_CLOSE_TIMES, CLOSE event | PARTIAL |

---

## 20. PRODUCTION SAFETY INVARIANTS

| # | Invariant | Status | Evidence |
|---|---|---|---|
| I1 | Learning cannot place an order | ✅ PASS | No broker call in any learning module |
| I2 | KDA cannot bypass RiskGuardian | ✅ PASS | KDA outputs are advisory; execute() still requires risk_guardian.evaluate() |
| I3 | Rejected broker order cannot create position | ⚠️ PARTIAL | execute()/AET: ✅ PASS. Reentry: ❌ FAIL — **F11-002** |
| I4 | Partial fill cannot become full fill without reconciliation | ✅ PASS | D9-006 fix; PARTIALLY_FILLED+zero-price → UNRESOLVED |
| I5 | Failed close cannot remove position from risk accounting | ✅ PASS | close_position() returns False on exit fail; status stays "open" |
| I6 | Restart cannot erase daily loss | ⚠️ HOLLOW | _load_state() works mechanically, but daily_pnl is always 0 (F11-001) |
| I7 | Restart cannot erase trading halt | ⚠️ CONDITIONAL | VIX halts persist ✅; daily-loss halts impossible to trigger |
| I8 | Restart cannot create phantom position | ✅ PASS | Journal restore + reconcile_startup_fills() |
| I9 | Duplicate EOD cannot duplicate learning | ⚠️ PARTIAL | LOL/KEL idempotent ✅; strategy_performance.json not guarded — **F11-013/F11-014** |
| I10 | Duplicate bridge cannot duplicate evidence | ✅ PASS | KEL dedup by source_run_id |
| I11 | Future data cannot enter today's decision | ✅ PASS | Anti-lookahead guard; F11-021 is LOW risk edge case |
| I12 | Every executed trade traceable to opportunity_id | ⚠️ PARTIAL | D10 fixes cover AET/reentry; F11-015 breaks multi-cycle re-scan lineage |
| I13 | Every closed trade traceable to actual broker fill price | ✅ PASS | actual_fill_price on OrderRecord; used in PnL if > 0 |
| I14 | Every learning record traceable to source observation | ⚠️ PARTIAL | F11-015 — obs_id hash may not match order's opportunity_id |
| I15 | Every KDA decision traceable to evidence | ✅ PASS | KDALedger written per signal with evidence_state |
| I16 | Corrupted state file fails closed | ✅ PASS | json.JSONDecodeError → reverts to zeros (safe defaults) |
| I17 | Broker/API failure cannot silently become successful execution | ⚠️ PARTIAL | execute(): ✅. AET/reentry: exception propagates and aborts, no phantom — ✅. But pre-order price guard exception is silently swallowed |
| I18 | Container restart cannot create duplicate orders | ✅ PASS | AET/reentry slots not persisted; journal dedup |
| I19 | Missed scheduler slot cannot replay old trading decision | ✅ PASS | Scheduler skips missed slots; fresh scan each cycle |
| I20 | No hidden alternate broker execution path | ✅ PASS | All broker calls route through OrderManager._broker_place() |

---

## 21. NEW DEFECT REGISTER

### 🔴 CRITICAL

#### D11-001 — `record_trade_result()` never called in production
- **File:** All production files — call is ABSENT
- **Function:** `FailSafeRiskGuardian.record_trade_result()`
- **Root cause:** The method was implemented and tested in isolation. No call was wired into `close_position()` (order_manager.py) or `TradeMonitor._close_at_price()` (trade_monitor.py). PRODUCTION_SAFETY_REPORT.md falsely claims this is wired.
- **Exact evidence:** `grep -r "record_trade_result(" --include="*.py"` — matches only definition in `risk_guardian.py` and 44 test file calls. Zero production code calls.
- **VPS runtime evidence:** `data/risk_guardian_state.json` shows `"daily_pnl": 0.0, "consec_losses": 0` all day regardless of actual trading.
- **Production impact:** Daily loss kill-switch (≥2%), consecutive-loss circuit breaker (≥3), position size governor, and max-open-trades governor are ALL permanently inactive. A catastrophic drawdown day is possible with no automatic halt.
- **Learning/data-loss impact:** None direct, but position sizing is always at 100% without drawdown-based reduction.
- **Reproduction:** Start trading. Accumulate losses. Check `data/risk_guardian_state.json` — `daily_pnl` stays 0.0.
- **Smallest safe fix:** Add `self._risk_guardian.record_trade_result(pnl, pnl >= 0)` in `close_position()` before the `return True` statement (line 1163).
- **Required tests:** Integration test verifying `risk_guardian.record_trade_result(pnl, won)` is called with correct PnL from `close_position()`.

---

### 🟠 HIGH

#### D11-002 — Reentry path creates phantom position on broker rejection
- **File:** `execution_engine/order_manager.py` lines 1700–1733
- **Function:** `attempt_all_reentries()`
- **Root cause:** `_reconcile_fill()` was added to `execute()` and `attempt_aet_confirmations()` paths but the reentry path was never updated.
- **Exact evidence:** Line 1700 → `new_oid = self._broker_place(...)` then line 1710 → `rec = OrderRecord(...)` then line 1720 → `self._orders[new_oid] = rec` and line 1733 → `self._portfolio.positions[slot.symbol] = pos` — **no `self._reconcile_fill(rec)` between them**.
- **Additional gap:** `reconcile_partial_fills()` at line 1250 skips any order with `filled_qty=0` — so a REJECTED reentry order (which has 0 filled qty) is never caught by any intraday cleanup.
- **Production impact:** Phantom "open" position persists in `_orders` and `_portfolio.positions` for the entire session. DupGuard blocks all new signals for the same symbol. Capital is misallocated. TradeMonitor sends SL/target checks to broker for a position that doesn't exist.
- **Reproduction:** Paper mode won't expose this (paper SIM IDs always succeed). Live mode: any broker rejection (margin, circuit, delisting) of a reentry limit order creates the phantom.
- **Smallest safe fix:** Add `self._reconcile_fill(rec)` + REJECTED guard after OrderRecord creation in `attempt_all_reentries()`, mirroring the AET pattern (lines 1406–1418).
- **Required tests:** Mock `_broker_place()` to return a non-None ID, mock `get_fill_details()` to return REJECTED, verify position NOT in `_orders` or `_portfolio.positions`.

#### D11-003 — No mutex on `self._orders`, `_portfolio.positions`, `_aet_pending`, `_reentry_slots`
- **File:** `execution_engine/order_manager.py` lines 367–390
- **Function:** `OrderManager.__init__()`
- **Root cause:** Concurrent design was not anticipated when the shared dicts were created.
- **Exact evidence:** `self._journal_lock = threading.Lock()` protects only file writes. No lock for `self._orders`. `get_open_orders()` (line 1204) and `get_open_order_ids()` (line 1210) iterate without `list()` snapshots.
- **Concurrent writers:** execute() (main scheduling thread) + attempt_aet_confirmations() + attempt_all_reentries() + close_position() — all called from different task queue workers.
- **Production impact:** `RuntimeError: dictionary changed size during iteration` during `get_open_orders()` if execute() inserts during iteration. Crashes the TradeMonitor worker task. Under CPython, GIL reduces frequency but does not eliminate the hazard.
- **Smallest safe fix:** Add `self._orders_lock = threading.RLock()`. Wrap all `self._orders[id] = rec` and `del self._orders[id]` with `with self._orders_lock:`. Change `get_open_orders()` to `list(self._orders.values())`.

---

### 🟡 MEDIUM

#### D11-004 — `stop_loss=0` does not block execution
- **File:** `execution_engine/order_manager.py` line 1007
- **Root cause:** The `initial_stop_loss <= 0` check was placed in `close_position()` where it's a warning only, not in `execute()` where it should be a hard block.
- **Evidence:** `grep "stop_loss.*<=.*0"` in order_manager.py returns only line 1007 — in `close_position()`, WARNING only, execution proceeds. No check in `execute()` before `_place_stop_loss()`.
- **Production impact:** If scanner generates signal with `stop_loss=0` (float default), trade executes without any stop protection. In live mode, `_place_stop_loss()` called with `trigger_price=0` → broker rejects SL → `sl_id=None` → software-only monitoring with target of ≤0 (never triggers).
- **Smallest safe fix:** Add `if signal.stop_loss <= 0: log.error("[OrderManager] stop_loss=0 — order blocked"); return None` in `execute()` before `_place_stop_loss()`.

#### D11-005 — PENDING fill status has no intraday re-reconciliation
- **File:** `execution_engine/order_manager.py` line 2274
- **Evidence:** Comment says "will retry on next reconciliation cycle" but no such cycle exists during a running session. `reconcile_startup_fills()` runs startup-only.
- **Production impact:** A limit order that stays at broker in PENDING state (network delay, broker queue) is counted as an open position. If it actually fills 30 minutes later, the system doesn't know. TradeMonitor runs SL checks, but `actual_fill_price=0` so R-multiple calculations are wrong.
- **Smallest safe fix:** In `_do_monitor()`, add a pass that calls `_reconcile_fill(rec)` for every order with `fill_status in ("PENDING", "UNRESOLVED")`.

#### D11-006 — `PARTIALLY_FILLED` with `filled_quantity=0` leaves wrong quantity
- **File:** `execution_engine/order_manager.py` lines 2243–2260
- **Evidence:** `if rec.fill_status == "PARTIALLY_FILLED" and rec.filled_quantity > 0:` — zero-qty partial fill skips the quantity update entirely. `rec.quantity` retains the originally requested quantity.
- **Production impact:** Position registered with wrong (inflated) quantity. PnL, R-multiple, and capital allocation are wrong.
- **Smallest safe fix:** Add `elif rec.fill_status == "PARTIALLY_FILLED" and rec.filled_quantity == 0: rec.fill_status = "UNRESOLVED"; log.error(...)`.

#### D11-007 — AET and reentry paths skip hard kill-switch re-check
- **File:** `execution_engine/order_manager.py`, `attempt_aet_confirmations()` and `attempt_all_reentries()`
- **Evidence:** AET path checks `current_vix >= AET_VIX_CONFIRM_THRESHOLD` (relative VIX gate) but NOT `KILL_SWITCH_VIX = 45` (absolute halt). Reentry path checks `_vix_spike_guard()` (relative change) but not absolute kill-switch. `risk_guardian.evaluate()` is NOT called before deferred placements.
- **Production impact:** If VIX spikes to 50 (absolute kill-switch trigger) between the original evaluate() and the deferred AET/reentry confirmation (up to 25 minutes later), the deferred orders are placed despite a market-panic condition. The kill-switch triggers only on the NEXT full evaluate() call.
- **Smallest safe fix:** Add `if self._risk_guardian and self._risk_guardian._trading_halted: return` at the top of both `attempt_aet_confirmations()` and `attempt_all_reentries()`.

#### D11-008 — EOD double-run double-counts `strategy_performance.json`
- **File:** `orchestrator/master_orchestrator.py` EOD status write (~line 4940), `learning_system/strategy_performance_tracker.py` lines 228–260
- **Evidence:** EOD status write failure (disk full, permissions) logs WARNING and continues. On restart, `_last_eod_date` = None and file shows old date → EOD re-runs for same day. `record_trade()` has no order_id dedup.
- **Production impact:** All today's trades are double-counted in strategy performance metrics: total_trades, wins, losses, total_R, expectancy. Leads to inflated win rates and distorted Sharpe ratios.
- **Smallest safe fix:** Add `order_id` dedup set to `StrategyPerformanceTracker`; log ERROR (not continue) when EOD status write fails.

#### D11-009 — LOL `obs_id` hash excludes `opportunity_id` — multi-cycle re-scan breaks lineage
- **File:** `learning_system/learning_observation_ledger.py` line 161
- **Evidence:** `_make_obs_id(symbol, trading_date, entry_price)` — no UUID component. Same symbol+date+price on 2nd scan → LOL skips (sees obs_id as existing). But OrderRecord has a new UUID from the 2nd scan. Learning lineage from OrderRecord → LOL is broken.
- **Production impact:** For any setup that the scanner re-evaluates (regime change, VIX spike cleared), the LOL record has a different `opportunity_id` than the OrderRecord and live journal. KEL evidence cannot be joined back to the executed trade.
- **Smallest safe fix:** Include `opportunity_id` in the hash: `raw = f"{symbol}|{trading_date}|{entry_price:.4f}|{opportunity_id}"`. Or use `opportunity_id` as the primary key directly.

#### D11-010 — 3-day stale OPEN positions in `paper_trades.csv` will rehydrate as phantom positions
- **File:** `data/paper_trades.csv` (runtime file)
- **Evidence:** 2 OPEN events from 2026-08-24 for SUZLON and TATASTEEL (both `SIM_` order IDs) with no corresponding CLOSE events. `_restore_from_journal()` would restore these as open positions on next paper-mode restart.
- **Production impact (paper mode):** DupGuard would block new SUZLON and TATASTEEL signals. Capital tied up to these phantom positions. Paper trading PnL misleading.
- **Smallest safe fix:** Run cleanup: add `SIM_*` order IDs to `data/live/closed_orders_YYYY.txt` before next paper restart, OR add an age-based expiry in `_restore_from_journal()` for SIM orders older than 1 trading day.

---

### 🟢 LOW

#### D11-011 — `outcome_at` falls back to `datetime.now()` when bar has no date
- **File:** `learning_system/learning_observation_ledger.py` line 681
- **Evidence:** `updated["outcome_at"] = datetime.now(timezone.utc).isoformat()` when `bars[0].get("date")` returns None. `no_lookahead` check then passes (processing time > decision_at). Actual outcome values from a bar with no verified date.
- **Probability:** Low — yfinance bars almost always have a date field.
- **Smallest safe fix:** `if not _outcome_bar_date: updated["no_lookahead"] = False; log.warning(...)`.

#### D11-012 — Pre-order price guard exception silently bypassed
- **File:** `execution_engine/order_manager.py` line 808
- **Evidence:** `except Exception as _pv_exc: log.debug("[OrderManager] Pre-order price guard skipped: %s", _pv_exc)` — DEBUG level means this bypass is invisible in production logs.
- **Smallest safe fix:** Change `log.debug` to `log.warning` so operators see when price validation is being skipped.

#### D11-013 — RiskGuardian-blocked signals not persisted for learning
- **File:** `orchestrator/master_orchestrator.py` ~line 1566
- **Evidence:** RiskGuardian rejections emit EventBus events but are NOT written to `rejection_audit.db` (StrategyLab rejections ARE).
- **Production impact:** Cannot analyze false-rejection rate or calibrate risk thresholds from evidence.

#### D11-014 — Near-miss signals not persisted
- **File:** `opportunity_engine/equity_scanner_ai.py` — scanner confidence filter
- **Evidence:** Signals below confidence floor never reach any persistence layer. Scanner threshold cannot be calibrated from evidence.

#### D11-015 — Slippage fields on OrderRecord never fed to LearningEngine
- **File:** `execution_engine/order_manager.py` lines 267–268 vs `learning_system/learning_engine.py`
- **Evidence:** `slippage_abs` and `slippage_pct` computed in `_reconcile_fill()` but ignored by `LearningEngine.learn()`.

---

## 22. PREVIOUS DEFECT VERIFICATION

| DTA | ID | Status in current code |
|---|---|---|
| DTA-009 | D9-001/D9-005 | ✅ `_place_stop_loss()` WARNING confirmed |
| DTA-009 | D9-002/D9-006 | ✅ Zero fill price → UNRESOLVED confirmed |
| DTA-009 | D9-008 | ✅ zone_price defaults to entry_price confirmed |
| DTA-009 | D9-010 | ✅ Atomic EOD write confirmed |
| DTA-009 | D9-011 | ✅ `halt_reason[:100]` confirmed in container |
| DTA-010 | D10-001 | ✅ AET confirms opportunity_id; 6 markers in container |
| DTA-010 | D10-002 | ✅ ReentrySlot.opportunity_id field present; propagation confirmed |
| DTA-010 | D10-007 | ✅ Old misleading log string absent from source |
| DTA-010 | D10-003 (false +) | ✅ RiskGuardian lock design intentional |
| DTA-010 | D10-001A (false +) | ✅ "closing" state intentional per docstring |

---

## 23. RUNTIME-VERIFIED VS STATIC-VERIFIED MATRIX

| Component | STATIC VERIFIED | TEST VERIFIED | VPS RUNTIME VERIFIED | REAL BROKER VERIFIED | EOD VERIFIED |
|---|---|---|---|---|---|
| Scanner signal generation | ✅ | ✅ | Partial (scheduler runs) | ❌ | ❌ |
| RiskGuardian VIX halt | ✅ | ✅ | ❌ | ❌ | ❌ |
| RiskGuardian daily-loss halt | ✅ method | ✅ isolated | ❌ **BROKEN** (F11-001) | ❌ | ❌ |
| execute() → broker order | ✅ | ✅ mocked | ❌ | ❌ | ❌ |
| _reconcile_fill() live broker | ✅ | ✅ mocked | ❌ | ❌ | ❌ |
| TradeMonitor SL hit | ✅ | ✅ | ❌ | ❌ | ❌ |
| close_position() PnL | ✅ | ✅ | ❌ | ❌ | ❌ |
| EOD learning flow | ✅ | ✅ partial | ❌ | ❌ | ❌ |
| KDA → KNOWLEDGE_HOLD | ✅ | ✅ | ❌ | ❌ | ❌ |
| LOL dedup | ✅ | ✅ | ❌ | ❌ | ❌ |
| KEL write | ✅ | ✅ | ❌ | ❌ | ❌ |
| Restart recovery (live) | ✅ | ✅ partial | ❌ | ❌ | ❌ |
| D10-001/D10-002 fixes | ✅ | ✅ 75 tests | ✅ container confirmed | ❌ | ❌ |

---

## 24. PRIORITY ACTION PLAN

### P0 — Immediately required for capital safety

**1. D11-001** (🔴): Wire `_risk_guardian.record_trade_result(pnl, pnl >= 0)` into `close_position()`. Also wire `record_open_trade()` at order registration and `record_closed_trade()` at `close_position()`. Add integration test verifying the wiring.

### P1 — Required before extended live trading

**2. D11-002** (🟠): Add `_reconcile_fill(rec)` + REJECTED guard to `attempt_all_reentries()`.

**3. D11-003** (🟠): Add `threading.RLock` for `self._orders`; convert bare iterations to `list()` snapshots.

**4. D11-004** (🟡): Add `stop_loss <= 0` hard block in `execute()`.

### P2 — Within 1 week

**5. D11-007** (🟡): Add `_trading_halted` check at top of `attempt_aet_confirmations()` and `attempt_all_reentries()`.

**6. D11-005** (🟡): Add intraday PENDING re-reconciliation loop in `_do_monitor()`.

**7. D11-008** (🟡): Add order_id dedup to `StrategyPerformanceTracker.record_trade()`; make EOD status write failure ERROR + skip rather than WARNING + continue.

### P3 — Learning integrity (non-blocking)

**8. D11-009** (🟡): Include opportunity_id in LOL obs_id hash.

**9. D11-006** (🟡): Handle PARTIALLY_FILLED + filled_qty=0 case.

**10. D11-010** (🟡): Clean up 3-day stale SIM positions from paper_trades.csv.

**11. D11-011 through D11-015** (🟢): LOW severity improvements.

---

## 25. FINAL CLASSIFICATION

**System Classification: 🔴 AMBER — NOT SAFE FOR UNATTENDED LIVE TRADING UNTIL D11-001 IS FIXED**

The system has correct execution path mechanics, correct broker wiring, correct journal+restart safety, and a functioning learning loop. The KDA knowledge authority IS wired and influences decisions.

However, **the daily loss kill-switch is permanently inactive** (D11-001). The system can accumulate unlimited intraday losses without any automatic halt. Given a live capital of ₹50,000 and no automatic drawdown protection, a single bad day could wipe the account before any software intervention occurs.

**Once D11-001 is implemented and verified: GREEN — SAFE FOR LIVE TRADING** with D11-002 through D11-003 scheduled for the same fix pass.

The system architecture is sound. The learning loop is connected. The deployment integrity is confirmed. The primary gap is a wiring omission that is straightforward to fix and test.
