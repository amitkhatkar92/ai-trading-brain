# Coordinator Readiness
## AR-001 Part 10: Readiness for MarketLearningCoordinator, ResearchCoordinator, and ScientificDirector

**Date:** 2026-08-04

---

## 1. Background

The platform is currently orchestrated by a single `MasterOrchestrator` (5,900+ LOC).
The next architectural evolution introduces three specialised coordinators:

| Coordinator | Responsibility |
|---|---|
| `MarketLearningCoordinator` | Orchestrates MLS phases 1–5B + CDS lifecycle |
| `ResearchCoordinator` | Orchestrates ARS, EdgeDiscovery, and knowledge synthesis |
| `ScientificDirector` | Governs research quality, statistical integrity, publication |

This document assesses whether the platform is ready for each to be implemented.

---

## 2. MarketLearningCoordinator

### Purpose
Manage the full MLS lifecycle: daily observation → classification → discovery →
consensus → context evaluation → DNA scoring. Deliver `CDSLibraryResult` and
`MarketContext` to the trading platform each session.

### Readiness Checklist

| Requirement | Status | Evidence |
|---|---|---|
| Phase 1 MarketObserver implemented | ✅ | `market_observer.py` complete |
| Phase 2 PopulationClassifier implemented | ✅ | `population_classifier.py` complete |
| Phase 3 DNADiscoveryEngine implemented | ✅ | 83/83 tests pass |
| Phase 4 DNAConsensusEngine implemented | ✅ | 90/90 tests pass |
| Phase 5 PMCIEngine implemented | ✅ | 90/90 tests pass |
| Phase 5A MCIEngine implemented | ✅ | 90/90 tests pass |
| Phase 5A.1 CDSEngine implemented | ✅ | 90/90 tests pass |
| Phase 5B CAPMCIEngine implemented | ✅ | 90/90 tests pass |
| Each phase has stable API | ✅ | All phases have documented dataclasses |
| Phase interfaces are composable | ✅ | Output of each phase is input-compatible with next |
| Configuration is centralised | ✅ | `mls_config.py` with all thresholds |
| DNA persistence mechanism | ⚠️ | DNA stored in-memory in `DNAConsensusEngine`; no persistent DNA store |
| Scheduler slot available | ⚠️ | No MLS jobs in SCHEDULE dict |
| Integration points with trading | ❌ | Not wired (see PMCI_INTEGRATION_REVIEW.md) |

### What is needed before MarketLearningCoordinator can be implemented

1. **DNA persistence store** — `ConsensusLibrary` must be serialisable to
   `data/dna_library.json` or a SQLite table. Currently exists only in-memory.

2. **Scheduler entry** — Add `"mls_overnight": "20:00"` or `"mls_daily": "16:00"`
   to `config.py SCHEDULE` for phases 1–4.

3. **MCIEngine context endpoint** — The coordinator must produce a `MarketContext`
   that can be fetched by the trading platform at 09:05.

4. **Integration bridge** — Three integration points in `master_orchestrator.py`
   (see PMCI_INTEGRATION_REVIEW.md sections 2.1–2.4).

### Readiness Score: 7/10 — Implementation can begin; 3 prerequisites needed.

---

## 3. ResearchCoordinator

### Purpose
Orchestrate the Autonomous Research System (ARS): schedule studies,
register hypotheses, validate evidence, synthesise knowledge, detect gaps,
and feed insights to the trading platform.

### Readiness Checklist

| Requirement | Status | Evidence |
|---|---|---|
| RoadmapManager implemented | ✅ | `autonomous_research/roadmap_manager.py` |
| StudyPlanner implemented | ✅ | `autonomous_research/study_planner.py` |
| HypothesisRegistry implemented | ✅ | `autonomous_research/hypothesis_registry.py` |
| EvidenceValidator implemented | ✅ | `autonomous_research/evidence_validator.py` |
| GapDetector implemented | ✅ | `autonomous_research/gap_detector.py` |
| KnowledgeProvider implemented | ✅ | `autonomous_research/knowledge_provider.py` |
| EdgeDiscoveryEngine implemented | ✅ | `edge_discovery/edge_discovery_engine.py` |
| AR components are inter-connected | ❌ | Not verified — components may be standalone |
| AR outputs feed LearningSystem | ❌ | No connection to `learning_system/` |
| AR outputs feed StrategyLab | ❌ | No connection to `strategy_lab/` |
| Scheduler entries for AR studies | ❌ | No AR jobs in SCHEDULE dict |
| Study history persisted | ⚠️ | `data/study002_results.json` (one-off files) |

### What is needed before ResearchCoordinator can be implemented

1. **Inter-AR connectivity** — Verify that ARS components call each other
   in a coherent pipeline (RoadmapManager → StudyPlanner → EvidenceValidator
   → KnowledgeProvider).

2. **ARS → LearningSystem bridge** — `KnowledgeProvider` output needs a
   defined interface that `LearningEngine` or `StrategyLab` can consume.

3. **ARS → EdgeDiscovery bridge** — `GapDetector` findings should trigger
   `EdgeDiscoveryEngine.discover()` to fill the gap.

4. **Scheduler entry** — Weekend intelligence (`saturday_intelligence`)
   is the natural slot for AR studies.

5. **Persistent study registry** — Replace one-off result files with a
   proper `research_brain.db` table.

### Readiness Score: 4/10 — Components exist but pipeline is unverified and not integrated.

---

## 4. ScientificDirector

### Purpose
Govern research quality across the entire platform: enforce temporal contracts,
approve DNA promotion, certify validation reports, prevent overfitting, approve
hypothesis tests, ensure reproducibility.

### Readiness Checklist

| Requirement | Status | Evidence |
|---|---|---|
| Validation pipeline exists | ✅ | 6-stage ValidationEngine |
| Promotion gates defined | ✅ | ResearchLab (WR ≥50%, Sharpe >0.8, DD <15%) |
| Temporal contract enforced | ✅ | MarketObserver 09:15 cutoff |
| Reproducibility via IDs | ✅ | PMCIResult, CDSEngine use deterministic SHA-256 IDs |
| Statistical significance checking | ⚠️ | WFT but no formal p-value check |
| Overfitting guard | ⚠️ | WFT OOS ratio 70/30, no additional bootstrap |
| Research governance framework | ❌ | `decision_governance/` exists in IIOS but not used |
| Hypothesis approval workflow | ❌ | No approval gate before experiments run |
| Publication/certification workflow | ❌ | Not implemented |
| ScientificDirector class exists | ❌ | Not yet implemented |
| DNA lifecycle governance | ✅ | Deprecation via `DNARelevance.DEPRECATED` |

### What is needed before ScientificDirector can be implemented

1. **ResearchCoordinator must be operational** — ScientificDirector governs
   what ResearchCoordinator produces. It cannot function without an AR pipeline.

2. **Hypothesis approval gate** — Before any study runs, ScientificDirector
   must approve the hypothesis and the experimental protocol.

3. **Statistical governance rules** — Formalise minimum sample sizes,
   significance thresholds, and bootstrap requirements.

4. **`decision_governance/` activation** — The IIOS decision governance
   framework already contains approval/audit/certification stubs.
   These should be the foundation of ScientificDirector.

5. **Publication standard** — Define what constitutes a "published" finding:
   DNA promoted to consensus, strategy promoted to lab, edge promoted to
   evolution candidate.

### Readiness Score: 2/10 — Prerequisites (ResearchCoordinator) not yet met.

---

## 5. Implementation Order

```
Step 1: DNA persistence store (3 days)
Step 2: MLS scheduler integration (2 days)
Step 3: MCIEngine → MarketContext endpoint (1 day)
Step 4: CDS → OpportunityEngine scoring bridge (2 days)
Step 5: MarketLearningCoordinator class (4 days)
        [Readiness: 10/10]

Step 6: ARS pipeline connectivity verification (2 days)
Step 7: ARS → LearningSystem bridge (3 days)
Step 8: ResearchCoordinator class (5 days)
        [Readiness: 10/10]

Step 9: Statistical governance rules (2 days)
Step 10: Hypothesis approval gate (2 days)
Step 11: ScientificDirector class (5 days)
         [Readiness: 10/10]
```

Total estimated implementation: ~31 days across 3 sequential milestones.
