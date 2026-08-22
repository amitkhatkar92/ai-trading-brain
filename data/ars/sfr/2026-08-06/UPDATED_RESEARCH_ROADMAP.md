# UPDATED_RESEARCH_ROADMAP.md

**SFR ID:** sfr-20260806-6861bc74
**Date:** 2026-08-06
**Generated:** 2026-08-06T11:41:38

## Prioritisation Method

Hypotheses are prioritised using Expected Information Gain (EIG):

```
EIG = P(uncertainty) × P(resolution) × I(value)

P(uncertainty)  = gap severity weight (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5)
P(resolution)   = estimated_knowledge_gain × 1.2
I(value)        = estimated_knowledge_gain (from RoadmapManager)
```

Secondary factors: Scientific Impact, Knowledge Gap Severity,
Evidence Strength, Research Cost, Strategic Importance.

## Generated Research Hypotheses

| Rank | Title | Priority | EIG | Study Type | Origin Gap |
|---|---|---|---|---|---|

## Data Quality Constraints

DQA Score: **5.8/100** (INSUFFICIENT)

Identified weaknesses that affect research quality:
- No feature records.
- Records with atr_14: 0/0 (N/A)
- Coverage: N/A (0 years)
- Fewer than 2 dated records.
- Distinct sectors with evidence: 0
- Distinct regimes: 0 ()
- Edges: BUY=0, SELL=0 (0.0% SELL)
- Compound DNA testable: 0 records with atr_14
- Missing DNA features: ['atr_14', 'intra_range', 'mom_5d', 'close_pos', 'sect_conviction', 'sect_part5d', 'avg_conviction', 'mom_1d', 'mom_10d', 'mom_20d', 'vol_ratio', 'cons_up_days', 'breadth', 'sector_flow_count', 'sector_strength', 'volume_spike', 'pcr']
- Total feature records: 0 (need ≥2,000)

Infrastructure recommendations:
- Run Phase 2 feature expansion.
- Run rii001.py Phase 2 to backfill atr_14 from replay.db.
- Expand historical data to cover 4+ years using replay.db.
- Add more feature records.
- Add symbols from 5 more sectors to the universe.
- Ensure feature records span multiple market regimes (TRENDING, SIDEWAYS, VOLATILE).
- Initiate SELL-side DNA Discovery program (H-SELL-001).
- Backfill atr_14 using replay.db OHLCV data (see rii001.py).
- Add ['atr_14', 'intra_range', 'mom_5d', 'close_pos', 'sect_conviction', 'sect_part5d', 'avg_conviction', 'mom_1d', 'mom_10d', 'mom_20d', 'vol_ratio', 'cons_up_days', 'breadth', 'sector_flow_count', 'sector_strength', 'volume_spike', 'pcr'] to feature computation pipeline.
- Increase replication studies to raise confidence above 0.60.
- Expand historical feature records using replay.db.

## Governance Principle

No human ordering of research. Evidence determines the next program.
The next study is selected by highest EIG from the open gap universe.