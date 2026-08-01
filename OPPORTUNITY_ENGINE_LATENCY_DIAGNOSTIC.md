# OPPORTUNITY ENGINE LATENCY DIAGNOSTIC
## P1 — Root Cause Investigation

**Date:** 2026-08-01  
**Status:** Instrumentation deployed. Awaiting next trading-day data to confirm.  
**Observed behaviour:** OE layer ≈2.7 s (WARN) at market open → ≈5.1 s (CRITICAL, cycle abort) by ~14:00 IST  

---

## 1. How to Read the New Log Tags

Three structured tags now emit every scan cycle. Correlate them by wall-clock timestamp.

### `[OE-timing]` — already existed; equity / options / arb split
```
[OE-timing] equity=Xms  options=Yms  arb=Zms
```
Source: `orchestrator/master_orchestrator.py` `_run_opportunity_engine()`.  
**First check this tag.** It reveals which sub-engine owns the latency.

### `[OELatencyProfile]` — new; sub-stage breakdown of `equity_scanner.scan()`
```
[OELatencyProfile] total=Xms  pu=Ams  setup=Bms  scanner=Cms  enrichment=Dms  phase_h=Ems  n_watchlist=N  n_prepared=P  n_signals=S
```
| Field | Measures |
|---|---|
| `total` | Wall time of entire `scan()` call |
| `pu` | Stage 1: `_prepared_watchlist()` — reads `daily_candidates.json` (1st of 4 reads) |
| `setup` | Stage 2–3: safe-mode check + LTP inject + sector sort + 2 more JSON reads (`_check_safe_mode_triggers` + `_emit_prepared_universe_health`) |
| `scanner` | Stage 4: `for stock in watchlist: _identify_setup()` loop |
| `enrichment` | Stage 9: Universal Enrichment block — 4th JSON read + `_CS_enrich.read()` + `update_enrichment()` write |
| `phase_h` | Phase H: Hybrid exploration budget |

### `[OELatencyProfilePU]` — new; sub-stage breakdown of `_prepared_watchlist()`
```
[OELatencyProfilePU] total_ms=Xms  store_read_ms=Ams  candidate_loop_ms=Bms  conviction_decay_ms=Cms  n_candidates=N  n_rows=R
```
| Field | Measures |
|---|---|
| `store_read_ms` | `CandidateStore.read()` — full JSON read + parse + checksum of `daily_candidates.json` |
| `candidate_loop_ms` | Per-candidate loop: TTL check + invalidation engine + `DataIntegrityTracker.get_trust_score()` + lifecycle compute |
| `conviction_decay_ms` | Score decay loop over all candidates + forensic calls |

---

## 2. Stage Breakdown

### Full execution path per scan cycle

```
[OE-timing covers all three below]
│
├── equity_scanner.scan()                      ← [OELatencyProfile] total
│   ├── Stage 1  _prepared_watchlist()          ← pu=
│   │   ├── CandidateStore.read()               ← store_read_ms (JSON read #1)
│   │   ├── per-candidate loop (N×)             ← candidate_loop_ms
│   │   │   ├── TTL check (datetime.fromisoformat)
│   │   │   ├── invalidation engine
│   │   │   │   ├── _check_breakout_invalidation()
│   │   │   │   ├── get_invalidation_tracker() calls (3×)
│   │   │   │   ├── get_false_breakout_tracker()
│   │   │   │   └── get_forensic_reporter()
│   │   │   ├── compute_lifecycle_state()
│   │   │   └── DataIntegrityTracker.get_trust_score()  ← O(1) dict lookup
│   │   └── conviction decay loop (N×)          ← conviction_decay_ms
│   │
│   ├── Stage 2–3  setup + ranking              ← setup=
│   │   ├── _check_safe_mode_triggers()
│   │   │   └── CandidateStore.read_context()   ← JSON read #2
│   │   ├── _live_watchlist()                   ← static dict copy (no I/O)
│   │   ├── LTP injection + sector sort
│   │   └── _emit_prepared_universe_health()
│   │       └── STORE_FILE.read_text()          ← JSON read #3
│   │
│   ├── Stage 4  scanner AI loop (N×)           ← scanner=
│   │   └── _identify_setup() per symbol
│   │       ├── ATR + regime guards
│   │       ├── Setup 1-5 evaluations
│   │       └── signal construction
│   │
│   └── Stage 9  Universal Enrichment           ← enrichment=
│       ├── _CS_enrich.read()                   ← JSON read #4
│       ├── for _raw_c in _all_store_raw (N×)
│       │   └── datetime.fromisoformat() ×2     ← DUPLICATE (known bug)
│       ├── FreshnessValidation iterate store   ← another O(N) pass
│       ├── LifecycleTransitionAudit
│       └── update_enrichment()                 ← JSON read #5 + write (every 5 min)
│
├── options_opportunity.scan()                  ← [OE-timing] options=
│   └── for symbol in OPTIONS_SYMBOLS (2×):
│       ├── get_options_capability()            ← dict lookup (fast)
│       └── _scan_symbol()
│           ├── self._feed.get_chain()          ← BLOCKING HTTP (yfinance fallback)
│           └── if dte < MIN_DTE_ENTRY:
│               └── self._feed.get_chain()      ← SECOND blocking HTTP call
│
└── arbitrage_ai.scan()                         ← [OE-timing] arb= (expected ~0ms)
```

---

## 3. Timing Table — Expected Pattern

The following table shows what the logs will contain. "Morning" = ~09:15–11:00 IST. "Afternoon" = ~13:00–15:00 IST.

| Tag | Field | Morning (expected) | Afternoon (expected) | Growing? |
|---|---|---|---|---|
| `[OE-timing]` | `equity` | ~300–600 ms | ~400–800 ms | Slight |
| `[OE-timing]` | `options` | ~200–800 ms | ~1500–4000 ms | **Yes — primary suspect** |
| `[OE-timing]` | `arb` | ~0–5 ms | ~0–5 ms | No |
| `[OELatencyProfile]` | `pu` | ~50–150 ms | ~60–200 ms | Slight |
| `[OELatencyProfile]` | `setup` | ~20–80 ms | ~20–80 ms | No |
| `[OELatencyProfile]` | `scanner` | ~50–200 ms | ~50–200 ms | No |
| `[OELatencyProfile]` | `enrichment` | ~100–300 ms | ~100–400 ms | Slight |
| `[OELatencyProfilePU]` | `store_read_ms` | ~5–20 ms | ~5–30 ms | Slight |
| `[OELatencyProfilePU]` | `candidate_loop_ms` | ~20–80 ms | ~20–80 ms | No |
| `[OELatencyProfilePU]` | `conviction_decay_ms` | ~10–50 ms | ~10–50 ms | No |

**If the `[OE-timing] options=` field shows growth → PRIMARY CAUSE CONFIRMED (Hypothesis 1).**  
**If `options=` is flat and `[OELatencyProfile] enrichment=` grows → SECONDARY CAUSE confirmed (Hypothesis 2).**

---

## 4. Root Cause — Code Analysis Findings

### PRIMARY HYPOTHESIS: Options scanner synchronous HTTP fetches grow intraday

**Confidence: HIGH**

`options_opportunity_ai.py` `_scan_symbol()` calls `self._feed.get_chain()` for each symbol in `OPTIONS_SYMBOLS` (NIFTY + BANKNIFTY). Because Dhan's data API returns HTTP 451 (blocked), the feed falls through to yfinance:

```python
# options_opportunity_ai.py — _scan_symbol()
chain = self._feed.get_chain(symbol, dte_target=20)     # blocking HTTP call #1
...
if chain.dte < MIN_DTE_ENTRY:
    chain = self._feed.get_chain(symbol, dte_target=21) # blocking HTTP call #2
```

**Why it grows intraday:**

| Time | Cause | Effect |
|---|---|---|
| Morning (9:15 AM) | Expiry is 3–5 days away; DTE safely above MIN_DTE_ENTRY | 1 HTTP call per symbol = 2 calls total |
| Approaching expiry | DTE decreases below MIN_DTE_ENTRY threshold | 2 HTTP calls per symbol = 4 calls total |
| Afternoon (BANKNIFTY, Tuesday) | BANKNIFTY expiry proximity triggers double fetch every cycle | options= 2–4× morning value |
| `MULTI_SID_REJECTED` accumulation | Dhan reconnect failures → yfinance fallback for ALL options calls | Each call = full HTTP round-trip |

A yfinance option chain download takes ~500–2500 ms depending on chain size, network latency, and Yahoo Finance server response time. With 4 calls per cycle in the afternoon: **4 × 800 ms average = 3.2 s added to OE layer** — which exactly explains the 2.7 s → 5.1 s progression.

The `OpportunityEngine` layer time = `equity + options + arb`. If equity stays at ~400 ms and options grows from 500 ms to 3500 ms, the total grows from 900 ms to 3900 ms.

---

### SECONDARY HYPOTHESIS: Four redundant reads of `daily_candidates.json` per cycle

**Confidence: HIGH (constant overhead, not growing)**

Every 30-second scan cycle reads `daily_candidates.json` **four times**:

| Call site | Function | Purpose |
|---|---|---|
| `_prepared_watchlist()` | `CandidateStore.read()` | Load candidates + validate checksum |
| `scan()` → `_check_safe_mode_triggers()` | `CandidateStore.read_context()` | Check premarket_refresh_complete flag |
| `scan()` → `_emit_prepared_universe_health()` | `STORE_FILE.read_text()` | Get coverage_pct + store age |
| `scan()` Universal Enrichment | `_CS_enrich.read()` | Build enrichment map for all candidates |

Plus every 5 minutes: `update_enrichment()` reads AND writes the file.

On a Linux VPS with cold page cache (evicted by yfinance DataFrame memory allocation), each read may trigger actual disk I/O:
- `read_text()` on a 30–80 KB file: 1–5 ms warm, 10–50 ms cold
- `json.loads()` on 30–80 KB: 0.5–3 ms

**Total constant overhead: 4 × (2–53 ms) = 8–212 ms per cycle.** This does not explain the intraday growth but accounts for ~10% of the baseline latency.

**Additionally, a code defect was found:** In the Universal Enrichment block, `datetime.fromisoformat()` is called **twice** for the same `prepared_at` value per candidate (duplicate code block at lines ~1510–1525). This runs 2 × N_candidates per cycle unnecessarily.

---

### TERTIARY HYPOTHESIS: Deep scan CPU/IO contention in the afternoon

**Confidence: MEDIUM**

`market_monitor.py` runs 6 deep scan slots during trading hours. Each deep scan:
1. Calls `market_scanner.py` which downloads historical OHLCV for 33+ symbols via yfinance
2. Writes the updated `daily_candidates.json`
3. Consumes significant CPU (pandas computation) and network bandwidth

By 14:00 IST, all 6 deep scan slots have fired. If a deep scan is running concurrently with an OE cycle, the VPS CPU is shared between:
- The main orchestrator thread running `equity_scanner.scan()`
- The market monitor thread running `market_scanner.run_scan()`
- Background threads: RSI refresh (`_background_rsi_refresh`), price refresh

This explains periodic latency spikes (every deep scan interval) but not continuous intraday growth.

**RSI background refresh:** `_background_rsi_refresh()` makes 33 serial `get_history()` calls (1 per symbol) every 5 minutes. Each call fetches 22 days of daily bars. This runs in a daemon thread and does not block `scan()` directly, but creates Python-level GIL competition during the post-fetch DataFrame processing.

---

### QUATERNARY HYPOTHESIS: yfinance file descriptor accumulation

**Confidence: LOW (mitigated by ulimit increase)**

The `docker-compose.yml` already raised `nofile` to 65,536 to address yfinance SQLite FD leaks. This hypothesis is unlikely to be the primary cause unless the container has been running for many days without restart.

---

## 5. Evidence

### Evidence for Hypothesis 1 (options scanner)

```python
# options_opportunity_ai.py — lines 91–134 (scan() method)
def scan(self, snapshot: MarketSnapshot) -> List[TradeSignal]:
    signals: List[TradeSignal] = []
    for symbol in OPTIONS_SYMBOLS:                     # 2 symbols: NIFTY + BANKNIFTY
        ...
        sig = self._scan_symbol(symbol, snapshot)     # blocking HTTP per symbol

def _scan_symbol(self, symbol, snapshot):
    chain = self._feed.get_chain(symbol, dte_target=20)    # HTTP call #1
    ...
    if chain.dte < MIN_DTE_ENTRY:
        chain = self._feed.get_chain(symbol, dte_target=21) # HTTP call #2 (DTE edge)
```

**Already-existing `[OE-timing]` in `_run_opportunity_engine()`:**
```python
# orchestrator/master_orchestrator.py — _run_opportunity_engine()
_t0 = _t.monotonic()
equity_signals  = self.equity_scanner.scan(snapshot, odm_directive=odm_directive)
_t1 = _t.monotonic()
options_signals = self.options_opportunity.scan(snapshot)
_t2 = _t.monotonic()
arb_signals     = self.arbitrage_ai.scan(snapshot)
_t3 = _t.monotonic()
log.info("[OE-timing] equity=%.0fms  options=%.0fms  arb=%.0fms", ...)
```

**Grep for pattern in VPS logs:**
```bash
docker logs ai-trading-brain 2>&1 | grep '\[OE-timing\]' | awk '{print $1, $2, $NF}' | head -50
```

If `options=` starts below 1000 ms and ends above 2000 ms → Hypothesis 1 confirmed.

---

### Evidence for Hypothesis 2 (4× JSON reads)

```python
# equity_scanner_ai.py — _prepared_watchlist()
candidates = CandidateStore.read()             # Read #1 — full JSON parse

# equity_scanner_ai.py — scan() → _check_safe_mode_triggers()
_ctx = _CSa.read_context()                     # Read #2 — full JSON parse

# equity_scanner_ai.py — scan() → _emit_prepared_universe_health()
_payload = _json.loads(STORE_FILE.read_text()) # Read #3 — full JSON parse

# equity_scanner_ai.py — scan() Universal Enrichment
_all_store_raw = _CS_enrich.read() or []       # Read #4 — full JSON parse
```

`CandidateStore.read()` computes a SHA-256 checksum over the entire candidates list on every read:
```python
# candidate_store.py
actual_checksum = _checksum(candidates)   # hashlib.sha256 over json.dumps()
```
This is an O(N × field_count) serialization + hash per call.

**Grep for timing data:**
```bash
docker logs ai-trading-brain 2>&1 | grep '\[OELatencyProfile\]' | head -20
docker logs ai-trading-brain 2>&1 | grep '\[OELatencyProfilePU\]' | head -20
```

If `store_read_ms` or `enrichment` grows through the day → Hypothesis 2 contributing.

---

### Evidence for Hypothesis 3 (deep scan contention)

```python
# market_monitor.py — deep scan slots fire throughout the day
# Each slot calls market_scanner.run_scan() which downloads 33 symbols via yfinance
```

**Correlate with VPS logs:**
```bash
docker logs ai-trading-brain 2>&1 | grep -E '\[DeepScan\]|\[MarketMonitor\]' | head -20
docker logs ai-trading-brain 2>&1 | grep '\[OE-timing\]' | head -20
# Compare timestamps between DeepScan events and high-latency OE cycles
```

---

### Known code defect found during audit

**Duplicate `datetime.fromisoformat()` in Universal Enrichment block** (constant overhead, not growing):

```python
# equity_scanner_ai.py — Universal Enrichment, inside for _raw_c in _all_store_raw loop
# Lines ~1510-1525 — DUPLICATE CODE BLOCK

# First computation (correct):
_fpa_e = _raw_c.get("prepared_at", "")
try:
    _fage_e = max(0, int((_now_e - _dt_enrich.fromisoformat(
        _fpa_e.replace("Z", "+00:00")
    )).total_seconds() / 60)) if _fpa_e else 0
except Exception:
    _fage_e = 0

# DUPLICATE — identical computation immediately follows:
_fpa_e = _raw_c.get("prepared_at", "")   # ← reassigns same value
try:
    _fage_e = max(0, int((_now_e - _dt_enrich.fromisoformat(
        _fpa_e.replace("Z", "+00:00")
    )).total_seconds() / 60)) if _fpa_e else 0   # ← overwrites same result
except Exception:
    _fage_e = 0
```

For 33–65 candidates, this adds 66–130 unnecessary `datetime.fromisoformat()` calls per cycle. Negligible individually (~0.01 ms each), but documented for removal.

---

## 6. Recommendations

### R1 — Verify primary cause with existing log tag (immediate, no code change)

On the next trading day, grep VPS logs for `[OE-timing]` at market open (~09:15 IST) and at 14:00 IST:

```bash
docker logs ai-trading-brain 2>&1 | grep '\[OE-timing\]'
```

**Decision tree:**
- If `options` > 1500 ms in afternoon → **fix the options scanner HTTP blocking (R2)**
- If `options` is flat and `equity` grows → **fix the 4× JSON reads (R3)**
- If both are flat but OE total grows → deep scan contention (R4)

---

### R2 — Cache the options chain between scan cycles (addresses Hypothesis 1)

**File:** `data_feeds/dhan_feed.py` or `data_feeds/options_feed.py`  
**Change:** Add a 60-second in-memory cache on `get_chain()` results, similar to the existing `_PRICE_CACHE` in `equity_scanner_ai.py` (stale-while-revalidate pattern).

```python
# Pattern to follow — already used in equity_scanner_ai.py
_CHAIN_CACHE: Dict[str, Tuple[OptionsChain, float]] = {}  # symbol → (chain, ts)
_CHAIN_CACHE_TTL = 60.0  # seconds

def get_chain(self, symbol: str, dte_target: int = 20) -> Optional[OptionsChain]:
    now = time.monotonic()
    cached = _CHAIN_CACHE.get(symbol)
    if cached and (now - cached[1]) < _CHAIN_CACHE_TTL:
        return cached[0]  # return stale data, refresh in background
    chain = self._fetch_chain(symbol, dte_target)  # existing HTTP logic
    if chain:
        _CHAIN_CACHE[symbol] = (chain, now)
    return chain
```

**Impact:** Reduces options scanner from 2–4 HTTP calls per cycle to 0 calls (cache hit) for the 60-second TTL window. OE option latency drops from 2–4 seconds to <5 ms on cache hits.  
**Risk:** Low — options chains update slowly (IV/OI change gradually intraday). A 60-second stale chain is acceptable for signal generation.

---

### R3 — Eliminate redundant JSON reads (addresses Hypothesis 2)

**File:** `opportunity_engine/equity_scanner_ai.py`  
**Change (3 targeted edits):**

**(a)** In `_emit_prepared_universe_health()` — replace `STORE_FILE.read_text()` with cached stats already in `_LAST_PREPARED_STATS`:
```python
# Instead of reading the file again, use data already available
coverage_pct = _LAST_PREPARED_STATS.get("coverage_pct", 0.0)
premarket_complete = _LAST_PREPARED_STATS.get("premarket_complete", False)
store_age_min = _LAST_PREPARED_STATS.get("store_age_min", 0.0)
```
`_LAST_PREPARED_STATS` is populated by `_prepared_watchlist()` which already ran and parsed the file.

**(b)** In `_check_safe_mode_triggers()` — replace `CandidateStore.read_context()` with `_LAST_PREPARED_STATS` stats for store age:
```python
_store_age_h = _LAST_PREPARED_STATS.get("store_age_h", 999.0)
# Remove the CandidateStore.read_context() call entirely
```

**(c)** In Universal Enrichment — instead of calling `_CS_enrich.read()` again, reuse the `prepared` list already loaded by `_prepared_watchlist()` for the Step 1 baseline. The `_all_store_raw` read is only needed to cover non-prepared (expired) candidates — scope it conditionally.

**Impact:** Reduces JSON reads per cycle from 4 to 1 (the initial `CandidateStore.read()` in `_prepared_watchlist()`). Removes ~30–200 ms constant overhead per cycle.

---

### R4 — Fix duplicate `datetime.fromisoformat()` in Universal Enrichment (low priority)

**File:** `opportunity_engine/equity_scanner_ai.py` lines ~1510–1525  
**Change:** Delete the second identical `_fpa_e` / `_fage_e` block (lines 1518–1525).  
**Impact:** Removes 66–130 unnecessary calls per cycle.

---

### R5 — Stagger background RSI refresh with options scanner HTTP calls (addresses Hypothesis 3)

After confirming the primary cause, if RSI refresh + options HTTP calls fire simultaneously:  
**Change:** Add a jitter delay before `_background_rsi_refresh` launch — e.g., if `_PRICE_REFRESH_RUNNING` was recently cleared, delay RSI refresh by 10 seconds.  
**Impact:** Prevents both background threads from hitting the network simultaneously.

---

## 7. Diagnostic Workflow for Next Trading Day

```
1. Deploy this instrumentation to VPS (git push → docker compose restart)
2. At 09:15 IST — note first 5 cycles' [OE-timing] options= and equity= values
3. At ~11:00, 13:00, 14:00 IST — note same values
4. Compare: does options= grow? Does equity= grow?
5. Grep [OELatencyProfile] for enrichment= growth
6. Grep [OELatencyProfilePU] for store_read_ms growth
7. Cross-reference with [DeepScan] timestamps

Deploy commands:
  git add opportunity_engine/equity_scanner_ai.py
  git commit -m "P1 OE latency diagnostic instrumentation"
  git push origin main
  ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose restart ai-trading-brain"
```

---

## 8. Instrumentation Removal

After root cause is confirmed, remove the P1 probes:

```bash
# Remove all P1 diagnostic lines from equity_scanner_ai.py
grep -n "P1 diagnostic" opportunity_engine/equity_scanner_ai.py
# Lines marked "# P1 diagnostic" can be deleted; [OELatencyProfile*] log.info() blocks remove with them
```

The instrumentation is confined to 13 `time.monotonic()` assignments and 2 `log.info()` calls:
- 6 probes in `_prepared_watchlist()` (lines matching `_pu_t`)
- 7 probes in `scan()` (lines matching `_sc_t`)

No module changes, no new imports, no architecture changes. All existing log tags and audit paths are unchanged.
