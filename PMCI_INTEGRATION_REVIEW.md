# PMCI Integration Review
## AR-001 Part 9: Where PMCI and CDS Should Integrate Across the Platform

**Date:** 2026-08-04

---

## 1. Current Integration State

As of the AR-001 review date (post Phase 5A.1 completion):

| Component | Exists | Scheduled | Wired to trading |
|---|---|---|---|
| `MCIEngine` (5A) | ✅ | ❌ | ❌ |
| `PMCIEngine` (5) | ✅ | ❌ | ❌ |
| `CAPMCIEngine` (5B) | ✅ | ❌ | ❌ |
| `CDSEngine` (5A.1) | ✅ | ❌ | ❌ |
| `DNAConsensusEngine` (4) | ✅ | ❌ | ❌ |

**Status: Complete isolation.** MLS produces analytically valid output
but contributes nothing to the live trading decision.

---

## 2. Architectural Integration Design

The following describes the target integration. This document defines the
design — implementation is a separate task (not part of AR-001).

### 2.1 Where MCIEngine fits

`MCIEngine` computes a `MarketContext` from:
- RegimeLabel, VIX, breadth, FII, sector scores, global sentiment

This context is already available in `master_orchestrator.py` from
Layers 1 and 2. The integration point is the start of each trading cycle.

```python
# In master_orchestrator.py:_do_monitor()

regime_snapshot = market_intelligence.get_regime()
market_context = mci_engine.compute(regime_snapshot, global_snapshot)
# market_context is now available for PMCI and CDS
```

**Integration layer:** Between Layer 2 (MarketIntelligence) and Layer 4
(OpportunityEngine).

---

### 2.2 Where PMCIEngine fits

`PMCIEngine.compute(dna, context)` takes a candidate DNA pattern and
the current `MarketContext`. It produces a probability that the pattern
precedes a significant price move in the current context.

**Integration point:** `EquityScannerAI.score_candidate()` or a post-scan
enrichment step before candidates enter `CandidateStore`.

```python
# Conceptual integration:
for candidate in raw_candidates:
    dna = dna_store.lookup(candidate.symbol)
    if dna is not None:
        pmci_result = pmci_engine.compute(dna, market_context)
        candidate.pmci_score = pmci_result.pmci_score
        candidate.pmci_confidence = pmci_result.confidence

# CandidateStore sorts by composite score including pmci_score
```

**Effect:** Candidates with high PMCI (DNA is likely to precede movement
in the current market context) are ranked higher.

---

### 2.3 Where CDSEngine fits

`CDSEngine.evaluate_library(library, context)` evaluates an entire DNA
library and returns `CDSLibraryResult` with a `ContextualDNAScore` per DNA.

**Integration point:** Pre-scan warm-up (before 09:10 scan) or during
the `strategy_evaluation` slot (09:20).

```python
# Conceptual integration:
library = dna_consensus_engine.get_library()
cds_result = cds_engine.evaluate_library(library, market_context)
top_dna = cds_engine.top_supported_dna(cds_result.scores, n=20)

# EquityScannerAI receives top_dna as a priority set
# Candidates matching top_dna symbols get a CDS relevance boost
```

**Effect:** The scanner focuses on candidates whose underlying DNA has
high contextual relevance to today's market. DNA that is IRRELEVANT or
DEPRECATED in the current context is deprioritised.

---

### 2.4 Where CAPMCIEngine fits

`CAPMCIEngine.compute(dna, context)` returns a context-adjusted PMCI score.
This is the most refined signal: it adjusts the raw PMCI probability by
the quality of the DNA's contextual alignment (CDS score).

**Integration point:** Final candidate scoring before `CapitalRiskEngine`.

```python
# Conceptual integration:
for candidate in prioritised_candidates:
    dna = dna_store.lookup(candidate.symbol)
    ca_pmci = ca_pmci_engine.compute(dna, market_context)
    candidate.ca_pmci_score = ca_pmci.ca_pmci

# CapitalRiskEngine uses ca_pmci_score to scale position size
# High ca_pmci → larger position within budget
# Low ca_pmci → minimum size or skip
```

---

## 3. PMCI as a Platform Service

Currently `PMCIEngine` is a standalone engine in `market_learning/`.
It could be promoted to a platform service accessible to all layers.

**Service interface (proposed):**

```python
class PMCIService:
    """Platform-level service wrapping PMCIEngine, MCIEngine, and CDSEngine."""

    def get_market_context(self) -> MarketContext:
        """Returns the current MCIEngine context (cached, refreshed each cycle)."""

    def score_candidate(self, symbol: str) -> PMCICandidateScore:
        """Returns PMCI + CDS scores for a candidate symbol."""

    def get_top_dna(self, n: int = 20) -> List[ContextualDNAScore]:
        """Returns top N contextually relevant DNA."""

    def get_session_stability(self) -> ContextStabilityLabel:
        """Returns current session context stability."""
```

**Consumers:**
- `EquityScannerAI` — uses `get_top_dna()` for scan prioritisation
- `CapitalRiskEngine` — uses `score_candidate()` for sizing
- `DecisionEngine` — uses `PMCICandidateScore` in debate context
- `TelegramBot` — uses `get_session_stability()` for `/market` command

---

## 4. CDS as a Platform Service

`CDSEngine` computes contextual relevance of DNA patterns. As a platform
service it would:

1. Run at market open (09:05) — evaluate the day's DNA library
2. Cache results for the session
3. Be queryable by any component needing DNA relevance

**Service interface (proposed):**

```python
class CDSService:
    """Platform-level service wrapping CDSEngine."""

    def get_session_scores(self) -> CDSLibraryResult:
        """Returns today's full library evaluation."""

    def get_relevance(self, dna_id: str) -> DNARelevance:
        """Returns relevance tier for a specific DNA pattern."""

    def is_highly_relevant(self, dna_id: str) -> bool:
        """True if CDS >= 0.75."""

    def top_n(self, n: int = 10) -> List[ContextualDNAScore]:
        """Returns top N contextually supported DNA."""
```

---

## 5. Integration Readiness Assessment

| Component | API stability | Test coverage | Integration effort |
|---|---|---|---|
| `MCIEngine` | ✅ Stable | 90/90 | Low |
| `PMCIEngine` | ✅ Stable | 90/90 | Low |
| `CDSEngine` | ✅ Stable | 90/90 | Low |
| `CAPMCIEngine` | ✅ Stable | 90/90 | Low |
| `DNAConsensusEngine` | ✅ Stable | 90/90 | Medium (need DNA store) |

**The components are ready.** What is needed is:
1. A DNA store that maps symbol → ConsensusDNA (currently in-memory)
2. A scheduler slot for overnight MLS pipeline (phases 1–4)
3. Orchestrator integration at the 3 points described above

---

## 6. Integration Priority Order

1. **First:** Wire `MCIEngine` into the daily cycle (09:05) — this provides
   `MarketContext` for all downstream MLS services.

2. **Second:** Run `CDSEngine.evaluate_library()` once at open (09:05–09:10)
   and cache the result. This is the cheapest integration with the highest value.

3. **Third:** Wire `PMCIEngine.compute()` into `EquityScannerAI` candidate scoring.

4. **Fourth:** Wire `CAPMCIEngine.compute()` into `CapitalRiskEngine` sizing factor.

5. **Fifth:** Add `MarketObserver` and MLS phases 1–4 to the EOD learning slot
   to rebuild DNA nightly.
