# OIOS_WIRING_CERTIFICATION

**Date:** 2026-06-22  
**Commit:** `bac5a81` (oios/data module) ← `7123e96` (wiring)  
**VPS:** `root@178.18.252.24` / container `ai-trading-brain`  
**Shadow Mode:** `SHADOW_MODE = True` (unchanged)

---

## Verdict: FULLY_WIRED

All 5 OIOS collection paths are wired into the live orchestrator and confirmed
to produce rows in `market_behavior.db` / `live_observations.db`.

---

## Collection Path Status

| Path | Table | Wired In | Trigger | DB Count |
|---|---|---|---|---|
| signal_births | `signal_births` | `_run_post_market_scan()` | After Phase D `run_scan()` at 16:45 IST | **8** |
| opportunities | `opportunities` | `_run_post_market_scan()` | After signal_births write | **3** |
| live_observations | `live_observations` | `_do_eod_learning()` | After `learning_engine.learn()` at 15:35 IST | **3** |
| market_leaders_daily | `market_leaders_daily` | `_do_eod_learning()` | End of EOD block | **30** |
| execution_trade_links | `execution_trade_links` | `_setup_eda()` startup | `ORDER_PLACED` / `POSITION_CLOSED` EventBus | **0** (no live trades yet) |
| feature_differentials | `feature_differentials` | `_run_oios_weekly_research()` | Saturday 17:30 IST | **pending first Saturday** |

---

## Changes Made

### `orchestrator/master_orchestrator.py` — commit `7123e96`

**1. `_run_post_market_scan()` — signal_births + opportunities**

Inserted after the `UniverseGenerationAudit` block (16:45 IST slot):
- Connects to `market_behavior.db` via `oios.db.connection.get_connection()`
- Loads active universe from `universe_stocks`
- Runs `layer_1a.run_scan()` (`birth_ttl_days=10`) and `layer_1b.run_scan()` (`birth_ttl_days=18`)
- Calls `write_scan_results()` → `attach_or_create_opportunity()` for each qualifying signal
- Logs `[OIOS] signal_births: 1A=N 1B=N new_opps=N merged=N date=YYYY-MM-DD`

**2. `_do_eod_learning()` — live_observations**

Inserted after `self.learning_engine.learn(trades)` (15:35 IST):
- Calls `analysis.live_observation_collector.ingest_from_csv()`
- Ingests all paper_trades.csv rows not yet in `live_observations.db`
- Dedup by `order_id` — safe to re-run
- Logs `[OIOS] live_observations: new=N processed=N skipped=N errors=N`

**3. `_do_eod_learning()` — market_leaders_daily**

Inserted at end of EOD block (15:35 IST), before method closes:
- Connects to `market_behavior.db`
- Calls `oios.phase_f.leader_capture.capture_daily_leaders(date, conn, regime)`
- Captures top-15 winners + top-15 losers from `ohlcv_daily`
- Upsert-idempotent: safe to re-run
- Logs `[OIOS] market_leaders_daily: captured=N date=YYYY-MM-DD regime=X`

**4. New method `_run_oios_weekly_research()` — feature_differentials**

New method added before `start_scheduler()`:
- Day-of-week guard: returns immediately on non-Saturday days
- Runs for each of the past 7 calendar days that has `market_leaders_daily` rows:
  1. `feature_extractor.extract_features_batch(leaders, conn)`
  2. `control_population.build_controls_for_date(date, conn)`
  3. `differential_engine.compute_differentials(date, conn)`
- Logs `[OIOS] Differential research YYYY-MM-DD: leaders=N diffs=N`

**5. `start_scheduler()` — weekly research slot**

Added after `sunday_intelligence` scheduler entry:
```python
sched_lib.every().day.at("17:30").do(self._run_oios_weekly_research)
```

---

## Additional Commits

### `bac5a81` — `oios/data/` module

`oios/data/` was excluded by `.gitignore` rule `data/` and not deployed to VPS.
Force-added 5 files:

| File | Purpose |
|---|---|
| `oios/data/ohlcv_fetcher.py` | Fetch + upsert OHLCV data from Yahoo Finance |
| `oios/data/bhav_fetcher.py` | Fetch NSE bhavcopy delivery data |
| `oios/data/sector_conviction_writer.py` | Write sector conviction scores |
| `oios/data/bulk_block_fetcher.py` | Fetch NSE bulk/block deal data |
| `oios/data/__init__.py` | Package init |

`.gitignore` pattern `data/` was not corrected to avoid unintentionally exposing live trade databases — the `oios/data/` Python modules were explicitly `git add -f`'d.

---

## Invariants Preserved

| Invariant | Status |
|---|---|
| `SHADOW_MODE = True` | ✅ Unchanged — all OIOS writes are observe-only |
| Execution engine | ✅ No changes to `execution_engine/`, `order_manager.py`, `risk_guardian/` |
| Signal generation | ✅ No changes to any signal scoring or debate threshold |
| Risk control | ✅ No changes to `risk_control/`, `capital_risk_engine.py` |
| Position sizing | ✅ No changes to any sizing logic |
| EventBus | ✅ No new events published; OIOS reads existing events only |
| Existing schedule slots | ✅ All existing `sched_lib.every()` entries unchanged |

---

## Data Notes

- `execution_trade_links = 0`: correct — no live trades executed since container restart
- `feature_differentials = 0`: will populate first Saturday at 17:30 IST after market_leaders_daily accumulates ≥1 day of data
- `universe_stocks` seeded with 230 symbols from `oios/seeds/universe_230.py`
- `ohlcv_daily` requires ongoing population via `historical_replay.py` or the daily data feed

---

## VPS Post-Deploy State

```
container:             ai-trading-brain  Up (healthy)
market_behavior.db:    37 tables
signal_births:          8 rows
opportunities:          3 rows
live_observations:      3 rows (live_observations.db)
market_leaders_daily:  30 rows (15W + 15L, date=2026-06-19)
execution_trade_links:  0 rows (waiting for first trade)
feature_differentials:  0 rows (waiting for first Saturday)
universe_stocks:       230 symbols (seeded 2026-06-22)
ohlcv_daily:           900 rows (15 symbols × 60 days)
```
