# Architecture Recommendations
## AR-001 Part 13: All Recommendations with Architectural Evidence

**Date:** 2026-08-04

---

## Recommendation Priority Legend

| Priority | Description |
|---|---|
| **P0 — Critical** | Blocks correct operation or scientific validity |
| **P1 — High** | Significant improvement to integration or reliability |
| **P2 — Medium** | Technical debt, performance, or design quality |
| **P3 — Low** | Long-term quality improvements |

---

## R-001 — Wire PMCI and CDS into OpportunityEngine and CapitalRiskEngine (P0)

**Evidence:** KNOWLEDGE_FLOW_REVIEW.md GAP-001, PMCI_INTEGRATION_REVIEW.md  
**Source files:** `orchestrator/master_orchestrator.py`, `opportunity_engine/equity_scanner_ai.py`,
`capital_risk_engine/capital_risk_engine.py`

**Problem:** 8 phases of MLS work (PMCIEngine, CDSEngine, CAPMCIEngine)
produce analytically valid output that is never consumed by the trading platform.
Every trade decision is made without PMCI context.

**Recommendation:**
1. Add `MCIEngine.compute()` call at the start of each trading cycle (09:05)
2. Add `CDSEngine.evaluate_library()` call once per session (09:10 warm-up)
3. Enrich candidate scores with PMCI: `candidate.pmci_score = pmci_engine.compute(dna, context).pmci_score`
4. Scale position size by CDS relevance: `size_factor = 1.0 + (cds_score - 0.55) * 0.4`
   (HIGHLY_RELEVANT DNA: up to 18% larger position; WEAK DNA: reduce position)
5. Pass PMCI/CDS summary to `MultiAgentDebate` as one of the 5 agent inputs

**Minimal viable integration (3 days):**
- Wire `MCIEngine` at 09:05 (1 day)
- Wire `CDSEngine` session evaluation at 09:10 (1 day)
- Pass CDS `DNARelevance` to `EquityScannerAI` as priority signal (1 day)

---

## R-002 — Decompose `master_orchestrator.py` into Coordinators (P1)

**Evidence:** DEPENDENCY_ANALYSIS.md section 3.1, TECHNICAL_DEBT_REGISTER.md TD-002  
**Source files:** `orchestrator/master_orchestrator.py` (5,900+ LOC)

**Problem:** Single 5,900-line file coordinates all 17 layers. Untestable in
isolation. Any layer API change risks breaking the orchestrator.

**Recommendation:**
1. Extract `MarketCoordinator` — layers 1–4 (global → opportunity)
2. Extract `TradingCoordinator` — layers 5–11 (strategy → execution)
3. Extract `LearningCoordinator` — layers 12–17 (monitoring → validation)
4. `MasterOrchestrator` becomes a thin scheduler that calls the three coordinators

**Interface constraint:** `MasterOrchestrator.run_full_cycle()` and
`start_scheduler()` signatures must remain unchanged (protected interfaces).

**Estimated effort:** High (10–15 days). Recommended for next major version.

---

## R-003 — Merge CorrelationEngine into single shared service (P2)

**Evidence:** INTELLIGENCE_DUPLICATION_AUDIT.md section 1, DEPENDENCY_ANALYSIS.md 2.1  
**Source files:** `global_intelligence/correlation_engine.py`,
`capital_risk_engine/correlation_engine.py`, `risk_control/correlation_engine.py`

**Problem:** Three independently maintained CorrelationEngine implementations.
Divergent formulae risk numerical inconsistency between portfolio risk
and capital sizing.

**Recommendation:**
1. Create `analytics/correlation_engine.py` with unified implementation
2. Accept `CorrelationContext` enum (MACRO, PORTFOLIO, RISK)
3. Replace three implementations with thin wrappers importing from `analytics/`

**Effort:** Medium (2 days)

---

## R-004 — Add async parallelism to NIFTY500 scan (P2)

**Evidence:** PERFORMANCE_REVIEW.md PERF-001  
**Source files:** `opportunity_engine/equity_scanner_ai.py`, `data_feeds/data_feed_manager.py`

**Problem:** 500 symbols scanned sequentially. At 8ms/quote minimum,
post_market_scan takes 4+ seconds. With real feed latency, 30–60 seconds.

**Recommendation:**
1. Use `DataFeedManager.get_multiple_quotes(symbols)` — batch fetch if available
2. If batch fetch not available, use `asyncio.gather()` with 20-symbol batches
3. Target: 500 symbols in < 5 seconds using parallelism

**Effort:** Medium (2–3 days)

---

## R-005 — Consolidate SQLite databases from 14 to 4 (P2)

**Evidence:** KNOWLEDGE_STORE_AUDIT.md section 6, PERFORMANCE_REVIEW.md PERF-003

**Problem:** 14 separate SQLite files. No cross-DB transaction atomicity.
Connection overhead. Historical/obsolete DBs not clearly marked.

**Recommendation:**

| New DB | Absorbs |
|---|---|
| `trading_brain.db` | trades, positions, signals, orders, trade_quality, rejections |
| `learning_brain.db` | strategy_performance (legacy), eod_eval, options_audit |
| `control_tower.db` | events, layer_timings, health, news, recommendations |
| `research_brain.db` | iios, live_observations, discovered_edges, replay |

**Archive:** `study002_replay.db`, `re001_replay.db` → `data/archive/`

**Effort:** High (5–7 days). Do after R-001 and R-003 are stable.

---

## R-006 — Add point-in-time NIFTY500 universe for backtests (P0)

**Evidence:** SCIENTIFIC_INTEGRITY_REVIEW.md section 3.1

**Problem:** `data/nifty500_universe.json` is a static snapshot. Historical
backtests exhibit survivorship bias — the universe includes today's winners,
not the composition at the backtest start date.

**Recommendation:**
1. Create `data/universes/nifty500_{YYYY_MM}.json` monthly snapshots
2. `BacktestingAI` accepts `universe_at_date(date)` method
3. `MarketObserver` uses universe valid at observation date

**Effort:** Medium (2 days for data collection, 1 day for integration)

---

## R-007 — Add `evolution_seed` and `simulation_seed` to config (P3)

**Evidence:** SCIENTIFIC_INTEGRITY_REVIEW.md sections 4.2 and 4.3

**Recommendation:**
```python
# config.py additions
EVOLUTION_SEED: Optional[int] = None  # None = random
SIMULATION_SEED: Optional[int] = None  # None = random
```

Log seeds with every evolution run and simulation result for reproducibility.

**Effort:** Low (0.5 days)

---

## R-008 — Add WFT split utility function (P3)

**Evidence:** DEPENDENCY_ANALYSIS.md section 2.3, TECHNICAL_DEBT_REGISTER.md TD-006

**Recommendation:**
```python
# utils/walk_forward_split.py
def split_oos(prices: pd.DataFrame, is_ratio: float = 0.70) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (in_sample, out_of_sample) DataFrames."""
```

All three WFT implementations should use this shared function.

**Effort:** Low (0.5 days)

---

## R-009 — Add minimum sample size enforcement in StrategyPerformanceTracker (P2)

**Evidence:** SCIENTIFIC_INTEGRITY_REVIEW.md section 5.3

**Recommendation:**
- `MIN_TRADES_FOR_STATS = 30` in `config.py` (currently may be lower)
- Win rate and Sharpe are marked `UNRELIABLE` when below minimum
- `StrategyHealthMonitor` flags strategies as `INSUFFICIENT_SAMPLE`

**Effort:** Low (1 day)

---

## R-010 — Fix L-001: reverse meta_learning dependency in market_intelligence (P1)

**Evidence:** PLATFORM_LAYER_REVIEW.md issue L-001

**Problem:** `market_intelligence/regime_probability_model.py` imports from
`meta_learning/`. This creates an L2 → L3 upward dependency.

**Recommendation:**
- `RegimeProbabilityModel` should only use `market_regime_ai.py` output
- The k-NN probability enhancement belongs in meta_learning, not market_intelligence
- Decouple by passing `RegimeProbabilities` as a parameter to meta_learning,
  not by importing meta_learning from within market_intelligence

**Effort:** Medium (1–2 days)

---

## R-011 — Move candidates to SQLite UPSERT pattern (P2)

**Evidence:** TECHNICAL_DEBT_REGISTER.md TD-010, PERFORMANCE_REVIEW.md PERF-007

**Recommendation:**
- Add `candidates` table to `trading_brain.db`
- `CandidateStore.persist()` becomes `UPSERT` instead of full JSON rewrite
- Remove full-rewrite on every 30s scan cycle

**Effort:** Low (1 day)

---

## R-012 — Secure `api_tokens.json` credentials (P1)

**Evidence:** TECHNICAL_DEBT_REGISTER.md TD-013

**Recommendation:**
1. Move credentials to environment variables (`.env` file loaded via `python-dotenv`)
2. `config.py` reads `os.getenv("DHAN_CLIENT_ID")` with fallback
3. `.env` is in `.gitignore`; `config/api_tokens.json` becomes optional fallback only

**Effort:** Low (0.5 days)

---

## R-013 — DNA persistence store (P0)

**Evidence:** COORDINATOR_READINESS.md section 2

**Problem:** `DNAConsensusEngine` builds a `ConsensusLibrary` in memory.
There is no persistent storage of the DNA library. Every restart loses all
accumulated DNA.

**Recommendation:**
- `data/dna_library.json` — serialised `ConsensusLibrary`
- `DNAConsensusEngine.save()` / `DNAConsensusEngine.load()`
- CDSEngine loads the library at startup

**Effort:** Low (1 day)

---

## Summary by Priority

| Priority | Recommendations | Total effort |
|---|---|---|
| P0 (Critical) | R-001, R-006, R-013 | ~6 days |
| P1 (High) | R-002, R-010, R-012 | ~13 days |
| P2 (Medium) | R-003, R-004, R-005, R-009, R-011 | ~13 days |
| P3 (Low) | R-007, R-008 | ~1 day |

**Recommended first sprint (P0 + P1 quick wins):**
R-013 → R-001 → R-006 → R-012 → R-010
(~9 days, highest scientific and integration value)
