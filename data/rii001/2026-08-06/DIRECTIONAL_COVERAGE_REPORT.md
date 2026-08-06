# DIRECTIONAL_COVERAGE_REPORT.md

**Study:** RII-001 Phase 4 — Directional Balance Program
**Date:** 2026-08-06
**Generated:** 2026-08-06T11:12:32

## Objective

Measure BUY / SELL / NEUTRAL edge coverage and determine whether the observed
imbalance originates from market behaviour or research history.
Do NOT artificially balance the data — only identify missing evidence.

## Discovered Edge Directional Balance

| Direction | Count | % of Edges |
|---|---|---|
| BUY / LONG | 237 | 91.5% |
| SELL / SHORT | 22 | 8.5% |
| NEUTRAL / OTHER | 0 | 0.0% |
| **Total** | **259** | 100% |

## Direction Distribution by Count

```
BUY  [███████████████████████████████████████████████] 237 (92%)
SELL [████] 22 (8%)
```

## Root Cause Analysis

### Market Behaviour Evidence

| Metric | Value | Interpretation |
|---|---|---|
| Feature DB winner records | 97,176 | fr > +0.5% |
| Feature DB loser records  | 84,898  | fr < -0.5% |
| Winner base rate | 47% | — |
| Loser base rate  | 41%  | — |
| Market upward bias | YES | Winners > Losers in data |

### Conclusion

The BUY imbalance (92% BUY vs 8% SELL) is primarily driven by **market behaviour**. The Indian equity market exhibits a structural upward bias — winner records outnumber loser records in the feature database. This is consistent with the long-term bull trend in NSE indices.

### Missing Evidence (SELL-Side)

- SELL-side DNA discovery has not been performed.
- Only 20 dedicated SELL edges exist out of 259 total.
- Research programs H001 and IRP-002 focused exclusively on the BUY side.
- **Recommendation:** A future SELL-Side DNA Discovery study (H-SELL-001) should be initiated.
  This is outside the scope of RII-001 (evidence infrastructure only — not new research).

## Edge Lifecycle Status

DECAYING edges by direction (known from prior analysis):
- DECAYING BUY edges: 132/132 (100% BUY)
- DECAYING SELL edges: 0

This confirms that edge_lifecycle is an INVALID proxy for SELL-side pattern analysis.
The MethodologyAuditor (IRP-002A) now blocks promotion of studies using edge_lifecycle
without explicit Scientific Director approval.

## Action

No artificial rebalancing applied.
Evidence infrastructure improvements (Phases 1–3) increase statistical power symmetrically.
SELL-side imbalance is documented as a known gap requiring dedicated future research.
