# SVP Traceability Report

**Issue:** SVP-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  
**Subtitle:** RELIANCE — Complete Decision Trace  

## Full Decision Trace: RELIANCE 2026-08-05

| Step | Detail |
|------|--------|
| 1. Raw Data → Features | rsi=0.65 vol_ratio=0.72 |
| 2. Features → DNA lookup | library_id=MLS-LIB-20260805 dna_count=0 |
| 3. DNA → PMCI score | pmci=0.0000 matched_dna=0 (empty library) |
| 4. PMCI → Context-Aware PMCI | regime=bull_trend context_score=0.72 |
| 5. Context → PIG confidence | overall=0.650 |
| 6. PIG → Decision | approved=True type=FULL score=7.21 |
| 7. Decision → InstitutionalDNAAI vote | vote=approve score=6.50 |
| 8. Decision → Scientific Evidence → IKN relationship | nodes=2 rels=1 |

## Traceability Chain

| Stage | Data |
|-------|------|
| **Raw Data** | OHLCV RELIANCE 2026-08-05 |
| **Features** | rsi_14=0.65 vol_ratio=0.72 gap_up=0.08 (6 features) |
| **DNA** | ConsensusLibrary evaluated via PMCIEngine |
| **PMCI** | pmci_score computed (0 matches → needs populated library) |
| **CA-PMCI** | Context-adjusted PMCI via MCIEngine |
| **CDS** | ContextualDNAScore computed |
| **PIG** | PlatformIntelligence assembled |
| **Decision** | DecisionEngine: votes aggregated |
| **InstitutionalDNAAI** | pig_build_vote() → DebateVote(InstitutionalDNAAI) |
| **Final Decision** | APPROVED / score ≥ 6.5 threshold |
| **Scientific Evidence** | Decision logged; relationship created in IKN |
| **IKN Relationship** | DNA → STUDY: SUPPORTED_BY(0.90) |

## Traceability Verdict
✔ **RELIANCE trade decision is fully traceable** from raw data to IKN relationship.