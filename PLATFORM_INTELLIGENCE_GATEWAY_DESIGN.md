# Platform Intelligence Gateway — Design
## R-001 Phase 1: Architecture, Responsibilities, and Integration

**Date:** 2026-08-04  
**Phase:** R-001 Phase 1  
**Status:** IMPLEMENTED — 90/90 tests pass

---

## 1. Purpose

The Platform Intelligence Gateway (PIG) is the **ONLY public entry point**
between the Trading Platform and the institutional intelligence stack.

It exists so that:
- No trading module ever calls PMCIEngine, CDSEngine, MCIEngine, or IDRRepository directly
- Institutional intelligence is consumed through a single, stable, explainable interface
- Every score returned can be audited by the consumer

---

## 2. What PIG Is Not

| What PIG does NOT do | Why |
|---|---|
| Discover DNA | Phase 3 — DNADiscoveryEngine |
| Build DNA consensus | Phase 4 — DNAConsensusEngine |
| Compute raw PMCI | Phase 5 — PMCIEngine (PIG delegates to it) |
| Evaluate market context | Phase 5A — MCIEngine (PIG delegates to it) |
| Score DNA against context | Phase 5A.1 — CDSEngine (PIG delegates to it) |
| Adjust PMCI for context | Phase 5B — CAPMCIEngine (PIG delegates to it) |
| Execute trades | Never |
| Recommend trades | Never |
| Modify any persistent store | Never |

---

## 3. Architecture

```
Trading Platform
        |
        | (Phase 2: integration not yet wired)
        v
+--------------------------------------------+
|  PlatformIntelligenceGateway               |
|  (market_learning/pig_gateway.py)          |
|                                            |
|  evaluate_symbol()  evaluate_universe()    |
|  get_context()      get_pmci()  get_cds()  |
|  statistics()                              |
|                                            |
|  Delegates to:                             |
+--------------------------------------------+
    |         |         |         |        |
    v         v         v         v        v
 PMCIEngine  MCIEngine  CDSEngine  CA-PMCI  IDRRepository
 (Phase 5)  (Phase 5A) (Phase 5A.1)(Phase 5B) (R-013)
```

---

## 4. File Layout

| File | Purpose |
|---|---|
| `market_learning/pig_gateway.py` | PlatformIntelligenceGateway class |
| `market_learning/pig_models.py` | All PIG output models (pure data) |
| `market_learning/mls_config.py` | PIG config fields (pig_* prefix) |
| `market_learning/__init__.py` | Package exports |
| `test_pig_gateway.py` | 90-test suite |

---

## 5. Data Models

| Model | Purpose |
|---|---|
| `PlatformIntelligence` | Primary output per symbol — all 10 required fields |
| `PlatformEvidence` | Traces one output score to its source engine |
| `PlatformConfidence` | Confidence breakdown by source |
| `PlatformRecommendationContext` | Simplified context for trading modules |
| `PlatformGatewayStatistics` | Aggregate stats over a universe evaluation |

---

## 6. Output Fields (R-001 Spec)

| Field | Source | Notes |
|---|---|---|
| `raw_pmci` | PMCIEngine | PMCIResult.pmci_score [0,1] |
| `ca_pmci` | CAPMCIEngine | CAPMCIResult.ca_pmci [0,1] |
| `cds_score` | CDSEngine | CDSLibraryResult.statistics.avg_cds [0,1] |
| `winner_dna_match` | PMCIEngine | "winner_match" component [0,1] |
| `loser_dna_match` | PMCIEngine | "loser_match" component [0,1] |
| `evidence_count` | PMCIEngine | len(breakdown.matched_dna) |
| `confidence` | All engines | Blended: 0.40×PMCI + 0.35×CA-PMCI + 0.15×MCIE + 0.10×IDR |
| `dna_freshness` | PMCIEngine | "dna_freshness" component [0,1] |
| `dna_drift` | CAPMCIEngine | 1 - dna_context_stability [0,1] |
| `institutional_confidence` | IDRRepository | statistics().avg_confidence [0,1] |

---

## 7. Explainability

Every `PlatformIntelligence` result includes a `List[PlatformEvidence]` that
contains one item per required output field. Each `PlatformEvidence` provides:

- `source`: which engine produced this value ("PMCI", "CA-PMCI", "CDS", "IDR", "MCIE")
- `component`: which specific component within that engine
- `value`: the exact score
- `explanation`: one-line human-readable description
- `raw`: the original input values from the source engine

This means any downstream consumer can audit any score without needing to
re-run the engine.

---

## 8. Confidence Formula

```
confidence = 0.40 * PMCI.confidence
           + 0.35 * CA-PMCI.confidence
           + 0.15 * MarketContext.confidence
           + 0.10 * IDR.avg_confidence
```

Clamped to [0, 1].

---

## 9. Intelligence Quality Classification

`PlatformRecommendationContext.intelligence_quality`:

| Label | Condition |
|---|---|
| `HIGH` | ca_pmci >= 0.70 AND confidence >= 0.60 |
| `MEDIUM` | ca_pmci >= 0.45 AND confidence >= 0.40 |
| `LOW` | ca_pmci > 0.30 |
| `INSUFFICIENT` | ca_pmci <= 0.30 |

`winner_alignment`:

| Label | Condition |
|---|---|
| `HIGH` | ca_pmci >= 0.70 |
| `MEDIUM` | ca_pmci >= 0.45 |
| `LOW` | ca_pmci < 0.45 |

`context_support`:

| Label | Condition |
|---|---|
| `STRONG` | context_score >= 0.65 |
| `MODERATE` | context_score >= 0.35 |
| `WEAK` | context_score < 0.35 |

---

## 10. Engine Injection

PIG supports injecting pre-warmed engines at construction time:

```python
mci  = MCIEngine(config)
pmci = PMCIEngine(config)
cds  = CDSEngine(config)
cap  = CAPMCIEngine(config)

gw = PlatformIntelligenceGateway(
    config=config,
    mci_engine=mci,
    pmci_engine=pmci,
    cds_engine=cds,
    ca_pmci_engine=cap,
)
```

This allows the orchestrator to share pre-warmed engines across calls,
preserving engine history (MCIEngine, CDSEngine) across evaluations.

---

## 11. Universe Batch Efficiency

When `evaluate_universe()` is called, the market context and CDS are
computed **ONCE** and shared across all symbols:

```
evaluate_universe(daily_snapshot, library, market_snapshot, repo)
    |
    +--> MCIEngine.evaluate(market_snapshot)     -- ONCE
    +--> CDSEngine.evaluate_library(...)         -- ONCE
    +--> IDRRepository.statistics()              -- ONCE
    |
    For each symbol:
    +--> PMCIEngine.evaluate(obs, library)
    +--> CAPMCIEngine.evaluate_with_context(obs, library, market_snapshot)
    +--> _build_intelligence(...)
```

---

## 12. Backward Compatibility

- No existing trading module is modified
- No existing MLS engine interface is changed
- All existing tests continue to pass
- PIG is additive: new files only (pig_models.py, pig_gateway.py)
- `mls_config.py` and `__init__.py` receive only additive changes

---

## 13. Phase 2 Integration

Phase 2 will:
1. Wire `PlatformIntelligenceGateway` into `MasterOrchestrator`
2. Have strategy modules consume `PlatformRecommendationContext`
3. Replace direct PMCIEngine/CDSEngine calls in trading modules with PIG calls

No trading module changes in Phase 1.
