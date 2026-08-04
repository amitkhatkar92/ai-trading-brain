# Platform Intelligence Integration — R-001 Phase 2

**Status:** COMPLETE  
**Commit:** pending  
**Tests:** 115/115

---

## Overview

R-001 Phase 2 wires the Platform Intelligence Gateway (PIG) into the live
trading pipeline at two injection points:

| Injection Point | Layer | What changes |
|---|---|---|
| Opportunity Engine | Layer 3 | `TradeSignal.confidence` enriched by CA-PMCI for ranking |
| Decision Engine | Layer 10 | `InstitutionalDNAAI` vote added with weight 0.08 |

PIG is **additional evidence only** — it does not generate signals, change
signal direction, or override the Decision Engine.

---

## Architecture

```
MarketObserver (daily)
  └─► DNAConsensusEngine  →  ConsensusLibrary (disk)
  └─► IDRRepository       →  InstitutionalDNA (SQLite)

Live trading cycle:
  EquityScannerAI.scan()
       │
       ▼
  PIGTradingAdapter.query(symbol, signal, snapshot)
       │   ├─► build MinimalMarketObservation from signal features
       │   ├─► PlatformIntelligenceGateway.evaluate_symbol()
       │   └─► returns PlatformIntelligence | None (fallback)
       │
       ├─ Part 1: pig_enrich_signals()
       │   └─► signal.confidence += min(max_boost, ca_pmci * max_boost)
       │
       └─ Part 2: pig_build_vote() → DebateVote("InstitutionalDNAAI")
               └─► added to votes list before DecisionEngine.decide()
```

---

## Files Changed

| File | Change | Type |
|---|---|---|
| `market_learning/pig_integration.py` | NEW — core integration module | New |
| `market_learning/mls_config.py` | Phase 2 influence policy fields | Modified |
| `market_learning/__init__.py` | Phase 2 symbol exports | Modified |
| `decision_ai/decision_engine.py` | `AGENT_WEIGHTS["InstitutionalDNAAI"] = 0.08` | Modified |
| `orchestrator/master_orchestrator.py` | PIGTradingAdapter wiring | Modified |
| `test_pig_integration.py` | 115-test suite | New |

---

## Part 1 — Opportunity Engine Enrichment

**When:** after `EquityScannerAI.scan()` returns, before events are published.

**How:** `pig_enrich_signals(equity_signals, pig_adapter, snapshot, policy)`

**Formula:** `new_confidence = min(10.0, old + min(max_boost, ca_pmci * max_boost))`  
Default `max_boost = 1.0` → max 1.0 point on 0-10 confidence scale.

**Fallback:** if `pig_adapter.query()` returns None, signal is unchanged.

**No trading signals changed** — only `confidence` (ranking score) is adjusted.
Signal direction, entry, stop-loss, and target are never touched.

---

## Part 2 — Decision Engine Vote

**When:** after `MultiAgentDebate.run()`, before `DecisionEngine.decide()`.

**How:**
```python
pi = pig_adapter.query(signal.symbol, signal, snapshot)
if pi and pi.ca_pmci >= min_ca_pmci_for_vote:
    votes.append(DebateVote("InstitutionalDNAAI", "approve", ca_pmci*10, ...))
```

**Score mapping:** `score = min(10.0, ca_pmci * 10.0)`

**Silence:** CA-PMCI < 0.30 → no vote added → existing 5-agent arithmetic unchanged.

**Weight:** `AGENT_WEIGHTS["InstitutionalDNAAI"] = 0.08` — less than the
weakest existing agent (RegimeDebateAI = 0.10).

---

## Part 3 — Explainability

Every decision where a PIG vote is cast emits:

```
[PIGExplainability] symbol=X raw_pmci=0.550 ca_pmci=0.650 
  cds=0.500 inst_confidence=0.550 evidence=12 
  dna_match=0.650 ctx_match=0.600 vote_score=6.50
```

The `InstitutionalDNAAI` vote reasoning string records all 7 fields:
```
[InstitutionalDNA] raw_pmci=0.550 ca_pmci=0.650 cds=0.500 
  inst_confidence=0.550 evidence=12 dna_match=0.650 ctx_match=0.600
```

---

## Part 6 — Fallback Behaviour

| Condition | Result |
|---|---|
| MLS infrastructure not loaded | `_init_failed=True` → all queries return None instantly |
| ConsensusLibrary empty (no DNA yet) | query returns None |
| `evaluate_symbol()` raises | exception caught → None |
| PIG unavailable | 5-agent arithmetic unchanged — identical to pre-Phase-2 |

The pipeline **never blocks, delays, or crashes** due to PIG.

---

## Part 7 — Backward Compatibility

- Without a PIG vote in the list: `total_weight = 1.0` exactly → scores identical.
- `DecisionEngine.decide()` signature unchanged.
- `EquityScannerAI.scan()` signature unchanged.
- `MasterOrchestrator._run_debate_and_decide()` still returns `dict | None`.
- All existing tests continue to pass (AGENT_WEIGHTS extended, not modified).

---

## Knowledge Flow — Architecture Review Gate

| Criterion | Before | After |
|---|---|---|
| Institutional knowledge in trading decisions | FAIL | **PASS** |
| Decision Engine final authority | PASS | **PASS** |
| Explainability of institutional evidence | FAIL | **PASS** |
| Graceful fallback when data unavailable | N/A | **PASS** |
| Backward compatibility | PASS | **PASS** |
