# SVP Performance Report

**Issue:** SVP-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  

## Performance Measurements

| Metric | Value |
|--------|-------|
| pmci_50_symbols_ms | 0.52 |
| pmci_per_symbol_ms | 0.01 |
| ikn_100_nodes_stats_10x_ms | 1.65 |
| ikn_shortest_path_ms | 0.18 |
| decision_engine_100x_ms | 77.92 |
| decision_engine_per_call_ms | 0.779 |
| pmci_peak_memory_kb | 5.0 |

## Module Execution Times

| Module | Execution Time (ms) | Status |
|--------|---------------------|--------|
| MasterOrchestrator | 124 | ✔ PASS |
| FeatureExtractor | 87 | ✔ PASS |
| PlatformIntelligenceGateway | 50 | ✔ PASS |
| KnowledgeProvider | 49 | ✔ PASS |
| AutonomousMarketLearningScheduler | 30 | ✔ PASS |
| IDRRepository | 25 | ✔ PASS |
| DNAReinforcementEngine | 19 | ✔ PASS |
| KDEEngine | 14 | ✔ PASS |
| OpportunityEngine | 13 | ✔ PASS |
| HKAPEngine | 12 | ✔ PASS |
| IKNNetwork | 9 | ✔ PASS |
| MarketLearningCoordinator | 9 | ✔ PASS |
| DecisionEngine | 8 | ✔ PASS |
| HistoricalReplay | 5 | ✔ PASS |
| ScientificDirector | 2 | ✔ PASS |
| MLS (MarketObserver + PopulationClassifier) | 1 | ✔ PASS |
| ResearchCoordinator | 1 | ✔ PASS |
| HypothesisRegistry | 1 | ✔ PASS |
| RoadmapManager | 1 | ✔ PASS |
| StudyPlanner | 1 | ✔ PASS |
| PTUE | 0 | ✔ PASS |
| PMCIEngine | 0 | ✔ PASS |
| CAPMCIEngine | 0 | ✔ PASS |
| CrossStudySynthesizer | 0 | ✔ PASS |
| GapDetector | 0 | ✔ PASS |
| InstitutionalDNAAI | 0 | ✔ PASS |
| MCIEngine (Market Context Intelligence) | 0 | ✔ PASS |
| EvidenceValidator | 0 | ✔ PASS |
| CDSEngine | 0 | ✔ PASS |

## Performance Thresholds
- Import threshold: 5000ms
- Instantiation threshold: 2000ms
- Execution threshold: 10000ms