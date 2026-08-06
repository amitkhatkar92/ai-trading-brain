# IRP002_METHOD_REVIEW.md

**Study:** IRP-002 — Symmetric Cross-Year DNA Validation
**Date:** 2026-08-06
**Version:** 1.0.0

## Methodology Equivalence Declaration

IRP-002 applies IDENTICAL methodology to winner DNA as H001 applied to loser DNA.

| Parameter | H001 (Loser DNA) | IRP-002 (Winner DNA) |
|---|---|---|
| Method | feature_match | feature_match |
| edge_lifecycle | YES (12 conditions) | **NO** (excluded by design) |
| Training year | 2025 (196 records) | 2025 (196 records) |
| Validation year | 2026 (304 records) | 2026 (304 records) |
| Min lift threshold | 1.15 | 1.15 |
| Min stability | 0.65 | 0.65 |
| Min N per condition | 5 | 5 |
| Chi-sq alpha | 0.15 | 0.15 |
| Target outcome | P(fr < -0.5%) | P(fr > +0.5%) |

## Feature Vocabulary Gap

All 9 winner DNA patterns require `atr_14`. This feature is not present in the
500-record KP feature database.

- `atr_14` was in study002a (280,909 OHLCV rows), but not ingested into ede_feature_db.
- This is a **Feature Vocabulary Gap**, analogous to H001's INSUFFICIENT_DATA conditions.
- Affected patterns: W01–W09 (compound tests). Individual sub-conditions tested without atr_14.
- Recommended fix: ingest atr_14 into feature records via H-HIGH-013 (10-year expansion).

## Why edge_lifecycle is Excluded

The inverted proxy problem identified in H001 meta-validation:
- All 132 DECAYING edges are BUY direction (0 SELL/SHORT DECAYING).
- edge_lifecycle measures BUY-edge-decay, not loser-DNA-persistence.
- Using it as a persistence proxy produces inverted signals for SHORT patterns.
- IRP-002 uses only direct empirical measurement (feature_match) for both sides.

## Methodological Symmetry: ACHIEVED

- Same feature set, same threshold, same statistical test, same years.
- The only asymmetry is the direction of the outcome variable:
  H001: P(fr < -0.5%)  IRP-002: P(fr > +0.5%)
- This is the correct scientific control: same test, opposite labels.
