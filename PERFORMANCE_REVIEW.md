# Performance Review
## AR-001 Part 7: CPU, Memory, Disk, and Scalability Analysis

**Date:** 2026-08-04

---

## 1. Known Performance Baselines

From system_monitor telemetry (as reported in ARCHITECTURE.md):

| Layer | Current Latency | Threshold WARN | Threshold CRIT | Status |
|---|---|---|---|---|
| GlobalIntelligence | 17ms | 5,000ms | 12,000ms | ✅ Excellent |
| MarketIntelligence | 19ms | 2,000ms | 5,000ms | ✅ Excellent |
| Full cycle | 172ms | — | — | ✅ HEALTHY |

The 5-minute cache on `GlobalDataAI` and background pre-warm thread are
responsible for the 17ms achievement. This design is exemplary.

---

## 2. Scalability Bottlenecks

### PERF-001: Sequential NIFTY500 scan (HIGH)

**Location:** `opportunity_engine/equity_scanner_ai.py`  
**Description:** The scanner iterates 500 symbols sequentially, fetching
quotes one at a time from `DataFeedManager`. At 8ms per quote (best case),
500 symbols = 4 seconds minimum. With yfinance fallback and rate limiting,
real-world scan time can reach 30–60 seconds.

**Evidence:** `post_market_scan` at 16:45 does "full NIFTY500 scan" —
this is the most expensive job in the scheduler.

**Impact for scale:**
- Current: 500 symbols (NIFTY500) — marginal
- Future: 2,000+ symbols (multi-cap) — fails latency budget
- Future: Multi-country (500 India + 500 US) — definitely fails

**Recommendation:**
- Use `DataFeedManager.get_multiple_quotes()` (batch fetch) if implemented
- Add `asyncio.gather()` for concurrent fetches
- Or use `yfinance.download(tickers, period, threads=True)` for batch downloads

---

### PERF-002: `master_orchestrator.py` single-threaded coordination (MEDIUM)

**Location:** `orchestrator/master_orchestrator.py` (5,900+ LOC)  
**Description:** All 17 layers are invoked sequentially from the single
orchestrator thread. Layers that could run in parallel (e.g., GlobalIntelligence
and MarketIntelligence, both I/O-bound) are serialised.

**Impact:** The 172ms full cycle relies on pre-warmed caches. Without
pre-warming (e.g., after restart), GlobalIntelligence could take 2–5 seconds,
making the full cycle approach the 5,000ms CRIT threshold.

**Recommendation:** Layers 1 and 2 could run concurrently (both I/O bound,
no shared write state). Use `concurrent.futures.ThreadPoolExecutor`.

---

### PERF-003: 14 SQLite databases — connection overhead (MEDIUM)

**Location:** `database/db_manager.py` and multiple SQLite owners  
**Description:** Each of the 14 SQLite databases requires a separate connection.
In a time-sensitive trading cycle, connection acquisition adds latency.
SQLite in WAL mode mitigates write contention but does not eliminate it.

**Recommendation:** 
- Consolidate to 4 databases (see KNOWLEDGE_STORE_AUDIT.md R-005)
- Use connection pooling (persistent `check_same_thread=False` connections)
- Ensure WAL mode is enabled: `PRAGMA journal_mode=WAL`

---

### PERF-004: MLS phases run only on manual/weekend trigger (LOW for now)

**Location:** `market_learning/` package  
**Description:** The 8-phase MLS pipeline has no production scheduler entry.
When integrated (per R-001), phases 1–4 (observation, classification, discovery,
consensus) will need to run overnight. Phase 5+ (PMCI, CDS) can run on-demand.

**Estimated overhead when integrated:**
- Phases 1–3 (observation → DNA discovery): ~500ms–2,000ms for 500 symbols
- Phase 4 (consensus): ~100ms
- Phase 5A (MCI): ~50ms per evaluation call
- Phase 5A.1 (CDS): ~10ms per library evaluation

**Recommendation:** Add MLS pipeline to `eod_learning` scheduler slot (15:35)
or to `saturday_intelligence` (08:00) for weekly DNA refresh.

---

### PERF-005: 5-agent debate overhead (LOW)

**Location:** `debate_system/multi_agent_debate.py`  
**Description:** 5 agents each produce a conviction score 0–10.
If any agent calls external data (quotes, news) during debate, latency increases.
If all 5 use in-memory data, debate overhead should be negligible (<10ms).

**Recommendation:** Verify that all debate agents use pre-fetched context,
not live data fetches during the 09:45 trade decision window.

---

## 3. Memory Profile

### In-memory singletons: estimate

| Singleton | Estimated size |
|---|---|
| `CandidateStore` (500 candidates) | ~2–5 MB |
| `RegimeStrategyMap` | <1 MB |
| `CDSEngine._context_history` (200 entries) | ~2 MB |
| `GlobalSnapshot` (prices, rates) | <1 MB |
| `AgentMemory` (message store) | ~5–20 MB (unbounded?) |
| Total singletons | ~15–35 MB |

**Issue PERF-006: `AgentMemory` may be unbounded.**
`communication/agent_memory.py` stores agent memory entries. If entries
are never evicted, memory will grow indefinitely over a multi-day run.
**Recommend:** Add `maxlen` to the underlying deque or TTL eviction.

---

## 4. Disk I/O Profile

### Write-heavy paths

| Path | Frequency | Write size |
|---|---|---|
| `data/paper_trades.csv` | Per paper trade | ~100 bytes/row |
| `control_tower.db` | Every cycle | ~500 bytes/event |
| `logs/*.log` | Continuous | ~10 KB/hour |
| `simulation_logs/` | Per simulation | ~50 KB/run |
| `data/candidates.json` | Every scan | ~50–200 KB |

### Concern: `candidates.json` full-rewrite on every scan

`CandidateStore.persist()` serialises the entire candidate list to JSON
on every scan cycle (every 30s for continuous scan). At 200 KB per write,
this is ~400 KB/minute of unnecessary I/O.

**Recommendation:** Use incremental JSON updates or SQLite table for
candidates rather than full-rewrite every 30 seconds.

---

## 5. Scalability Trajectory

| Scenario | Current capacity | Future requirement | Gap |
|---|---|---|---|
| Symbols scanned | 500 (sequential) | 2,000+ | PERF-001 |
| Concurrent users | 1 (single-instance PID lock) | 1 (by design) | None |
| Trading strategies | ~10 evolved | Target 50+ evolved | WFT compute time scales linearly |
| Data feeds | 4 (Dhan, Yahoo, AngelOne, NSE) | + US feed, crypto | Feed abstraction supports this |
| Agents | 62 | ~100 with ARS+Coordinators | Memory/CPU manageable |
| MLS phases | 8 | Stable (no new phases planned) | PERF-004 |

---

## 6. Performance Summary

| ID | Issue | Severity | Effort |
|---|---|---|---|
| PERF-001 | Sequential NIFTY500 scan | High | Medium |
| PERF-002 | Sequential orchestrator layers | Medium | Medium |
| PERF-003 | 14 SQLite connections | Medium | High |
| PERF-004 | MLS scheduling overhead (future) | Low | Low |
| PERF-005 | Debate agent data fetches | Low | Low |
| PERF-006 | AgentMemory unbounded growth | Medium | Low |
| PERF-007 | candidates.json full-rewrite 30s | Medium | Low |
