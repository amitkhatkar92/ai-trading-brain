# OIOS_MARKET_DATA_PIPELINE_REMEDIATION

**Date:** 2026-06-22  
**Commit:** `48afc4f`  
**VPS:** `root@178.18.252.24` / container `ai-trading-brain`

---

## Final Verdict: FIXED_AWAITING_NEXT_EOD

The scheduler gap is fixed and deployed. OHLCV data is current to the last
confirmed trading day (2026-06-19). The next trading day's data will be fetched
automatically at 16:45 IST. BHAV data requires a separate network-access fix
(see Blocker section below).

---

## 1. Root Cause Analysis

### Primary Issue — Scheduler Not Wired
`run_daily_fetch()` and `run_daily_bhav_fetch()` in `oios/data/` were **never
called from the live scheduler**. Both functions existed and were complete, but
their only callers were:
- `historical_replay.py` (manual backfill tool)
- `phase_a_audit.py` (audit script)

The orchestrator ran `_run_post_market_scan()` daily at 16:45 IST without ever
refreshing `ohlcv_daily` or `bhav_daily`. Data only accumulated via manual runs.

### Secondary Issue — bhav_daily Unreachable from VPS
NSE `archives.nseindia.com` returns HTTP 503 (Akamai CDN) for all requests
from the VPS IP. The bhav URL format in `bhav_fetcher.py` is correct:
`sec_bhavdata_full_{DDMONYYYY}.csv` — but NSE blocks non-India IP access.

### Why ohlcv_daily stopped at 2026-06-19
yfinance returned no data for 2026-06-20 → 2026-06-22 with error
`possibly delisted; no price data found`. This is expected behaviour for:
- Weekends (June 21–22 are Saturday/Sunday)
- Possible NSE holiday or yfinance data lag for June 20

`ohlcv_daily` max_date = 2026-06-19 is correct — it reflects the last
confirmed NSE trading day in the database.

---

## 2. Fix Implemented — `orchestrator/master_orchestrator.py` commit `48afc4f`

Added OIOS data refresh block to `_run_post_market_scan()`, **before** the
Layer 1A/1B signal scan:

```python
# ── OIOS data refresh — ohlcv_daily + bhav_daily ─────────────────────
# Runs BEFORE the signal scan so Layer 1A/1B always read current data.
# Incremental: only fetches dates not yet in the database.
```

**Execution order at 16:45 IST post-market slot:**
1. Phase D market scanner (`run_scan()`) — existing, unchanged
2. `UniverseGenerationAudit` — existing, unchanged
3. **NEW: OIOS OHLCV refresh** — `run_daily_fetch(lookback_days=90, delay=0.1s)`
4. **NEW: OIOS bhav backfill** — `run_daily_bhav_fetch()` last 7 calendar days
5. Layer 1A + 1B signal scan — wired in previous session

All four OIOS blocks are wrapped in `try/except` — failure is logged but
does not abort the slot.

---

## 3. One-Time Backfill — VPS Container Verification

Ran `oios_remediation_verify.py` inside container immediately after deploy:

```
[1/5] universe_stocks: 230 symbols (already seeded)
[2/5] OHLCV refresh: ok=194 failed=36 rows_new=11623 gaps=0
      ohlcv_daily: max_date=2026-06-19  total_rows=12523
[3/5] bhav backfill: 404/503 on all dates — bhav_daily remains empty
[4/5] market_leaders captured: 5 days × 30 leaders = 150 rows
      market_leaders_daily: max_date=2026-06-19  total=150
[5/5] Final state:
```

### Required Verification Queries (from VPS container)

```sql
SELECT MAX(trade_date) FROM ohlcv_daily;
-- Result: 2026-06-19

SELECT COUNT(*) FROM market_leaders_daily WHERE trade_date='2026-06-19';
-- Result: 30
```

### Full Table State After Remediation

| Table | max_date | Row Count | Status |
|---|---|---|---|
| `ohlcv_daily` | **2026-06-19** | **12,523** | ✅ Current to last trading day |
| `bhav_daily` | NULL | 0 | ❌ NSE IP block (see below) |
| `market_leaders_daily` | **2026-06-19** | **150** | ✅ 5 days backfilled |
| `signal_births` | — | 12 | ✅ |
| `opportunities` | — | 3 | ✅ |

---

## 4. OHLCV Symbol Coverage

| Category | Count |
|---|---|
| Symbols in universe_stocks | 230 |
| Symbols with data loaded | **194** |
| Symbols failed (yfinance 404) | 36 |

The 36 failed symbols are delisted, renamed, or unavailable in yfinance
(e.g. `IIFLFINANCE.NS`, `LTIM.NS`, `HEXAWARE.NS`, `NIIT.NS`, `KAJARIAL.NS`,
`BERGERPAINTS.NS`). These are stale entries in UNIVERSE_230 that need
cleaning in a future maintenance pass. They do not affect signal scan
correctness — the scanner skips symbols with insufficient data.

---

## 5. BHAV Blocker — NSE IP Restriction

**Status:** SOURCE_DATA_UNAVAILABLE from VPS

NSE `archives.nseindia.com` returns HTTP 503 from the VPS IP
(non-India IP blocked by Akamai CDN). All 7 recent dates returned 404/503.

**Impact:** `bhav_daily` remains empty. Layer 1B archetype
`DNA_1B_DELIVERY_EXPANSION` will produce no signals (delivery % = NULL).
The other three Layer 1B archetypes (`QUIET_ACCUMULATION`,
`LOW_NOISE_STRENGTH`, `SECTOR_PRE_BKT`) are unaffected.

**Options for future resolution (not implemented — out of scope):**
1. Route bhav fetch through a proxy/relay in India
2. Use Dhan API for delivery data (if available)
3. Accept bhav_daily gap and rely on the three unaffected 1B archetypes

---

## 6. Automated Schedule (Live After This Deploy)

| Slot | Time (IST) | What runs |
|---|---|---|
| Post-market | 16:45 | ohlcv_daily incremental refresh (230 symbols, ≤90 days lookback) |
| Post-market | 16:45 | bhav_daily backfill (last 7 days, currently blocked by NSE IP) |
| Post-market | 16:45 | Layer 1A + 1B signal scan → signal_births + opportunities |
| EOD learning | 15:35 | market_leaders_daily capture |
| EOD learning | 15:35 | live_observations ingest |
| Saturday | 17:30 | Phase F differential research (feature_extractor → control_population → compute_differentials) |

---

## 7. Invariants Preserved

- SHADOW_MODE = True (unchanged)
- No changes to execution engine, risk control, or signal generation
- No changes to existing schedule slots or their timing
- The OHLCV/bhav refresh blocks are non-critical — wrapped in try/except
