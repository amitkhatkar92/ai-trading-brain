# KVA-001 Executive Summary

**Issue:** KVA-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  


## Certification: `PASS WITH OBSERVATIONS`

**Certificate ID:** `KVA-6E76E78105`  
**Start:** 2026-08-05T15:58:19.968  
**Finish:** 2026-08-05T15:58:20.424  

## Knowledge Scorecard

| Dimension | Score | Status |
|-----------|-------|--------|
| Institutional Knowledge Score | 54.3 | **PASS WITH OBSERVATIONS** |
| DNA Quality Score | 85.7 | **PASS** |
| Scientific Confidence | 70.2 | **PASS** |
| Research Coverage | 30.0 | **FAIL** |
| Knowledge Completeness | 64.2 | **PASS WITH OBSERVATIONS** |
| Knowledge Explainability | 85.3 | **PASS** |
| Reasoning Quality | 66.6 | **PASS WITH OBSERVATIONS** |
| **Overall Rating** | 64.6 | **PASS WITH OBSERVATIONS** |

## Category Results

| Category | Score | Status | Key Finding |
|----------|-------|--------|-------------|
| C1 Winner Knowledge | 68.0 | **PASS WITH OBSERVATIONS** | 7 distinct features found in winner conditions. Top: sect_conviction(conf=0.67,c... |
| C2 Loser Knowledge | 36.3 | **FAIL** | Loser conditions identified: avg_conviction(n=3), atr_14(n=2)... |
| C3 DNA Knowledge | 58.6 | **PASS WITH OBSERVATIONS** | 85 edges have WF consistency ≥ 0.8 and OOS win rate ≥ 60%. Top regime-survivors:... |
| C4 Market Behaviour | 71.6 | **PASS WITH OBSERVATIONS** | Year-by-year regime: 2026: dominant=range_market(62%)... |
| C5 Sector Intelligence | 59.6 | **PASS WITH OBSERVATIONS** | Top sectors: METALS(avg=0.0002,n=141), IT(avg=0.0000,n=359). Weakest: METALS(avg... |
| C6 Feature Intelligence | 68.0 | **PASS WITH OBSERVATIONS** | Feature-return correlations computed on 500 samples. Most predictive: cons_up_da... |
| C7 Discovery Knowledge | 68.7 | **PASS WITH OBSERVATIONS** | Top OOS win rate: EDG_VOLATI_91_EE0004(100.00%) — IF pcr > 0.400 AND bb_position... |
| C8 Failure Knowledge | 62.7 | **PASS WITH OBSERVATIONS** | IDR: 0 retired DNA records. HypothesisRegistry: 0 hypotheses (0 rejected yet — s... |
| C9 Reasoning Assessment | 66.6 | **PASS WITH OBSERVATIONS** | Current regime (as of 2026-04-02): range_market (confidence=0.18). Historical an... |
| C10 Scientific Integrity | 73.7 | **PASS WITH OBSERVATIONS** | 259/259 edges (100%) have traceable entry conditions. All winner DNA (9 records)... |
| C11 Emergent Intelligence | 72.8 | **PASS WITH OBSERVATIONS** | Most statistically surprising edge: EDG_MOMENT_100_EE0005 — "IF mom_5d > 0.006 A... |

## Knowledge Inputs

- Studies: 3
- Findings: 24 (9 winner DNA, 1 loser DNA)
- Edges: 259
- Feature Records: 500
- Regime History: 500 records
- IDR DNA: 0
- IKN Nodes: 20
- Hypotheses: 0

## Top Gaps

- [HIGH] HypothesisRegistry: No hypotheses registered — SD needs to generate hypotheses from current knowledge
- [HIGH] IDR: IDR has 0 DNA records — run full AMLS pipeline to populate
- [HIGH] Loser Knowledge: Loser DNA corpus critically small (1 record) — systematic loser analysis needed
- [HIGH] Loser Knowledge: No cross-year loser validation possible with current data
- [HIGH] Loser Knowledge: Only 1 loser DNA records — loser study required
- [MEDIUM] DNA Knowledge: DNA contradiction mapping needs systematic IKN population
- [MEDIUM] Discovery Knowledge: 17 promising edges need more support (n<20)
- [MEDIUM] Failure Knowledge: Systematic post-mortem analysis framework not yet implemented

## Final Questions


**Q1:** Highest confidence knowledge: 101 edges with OOS win rate ≥80%. Top: EDG_VOLATI_91_EE0004(oos=100.00%) — IF pcr > 0.400 AND bb_position > 0.397 AND mom_1d > 0.005 THEN bullish with 92% 

**Q2:** IIOS does not yet know: (a) loser DNA (only 1 record), (b) IDR institutional DNA (0 records), (c) multi-decade regime patterns (only 3 studies), (d) sector rotation cycles, (e) hypothesis validation outcomes

**Q3:** Strongest discoveries: EDG_MOMENT_86_EE0002, EDG_COMPOS_73_EE0001, EDG_MOMENT_93_EE0000

**Q4:** 17 high-confidence edges with support < 20 need more evidence

**Q5:** Knowledge that changed through time: 133 edges show DECAYING status — their predictive power weakened. Regime confidence trends suggest market was predominantly RANGE_MARKET in recent period.

**Q6:** IIOS can explain 259/259 edges with human-readable descriptions. Winner DNA explained via feature conditions and lift. Scientific integrity score: 85/100.

**Q7:** 259/259 edges traced to raw entry conditions. All 9 winner DNA traced to study002a.

**Q8:** IIOS has developed PARTIAL institutional knowledge. Evidence: 259 validated edges, 9 winner DNA, 3 scientific studies, 500 labelled feature records, 30-day live replay.

**Q9:** IIOS is READY for knowledge-driven decision making. Score: 64.6/100. Primary blockers: (1) IDR empty, (2) loser DNA minimal.

**Q10:** ScientificDirector should study next: (1) Systematic loser DNA discovery (5-year underperformers), (2) Full HKAP 2015-2026 run, (3) Regime-conditional DNA validation, (4) Sector rotation cycle mapping, (5) Feature interaction mining (2+ feature combinations).