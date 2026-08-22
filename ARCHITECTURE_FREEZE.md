# ARCHITECTURE FREEZE
## Opportunity Intelligence Operating System (OIOS)

**Freeze Date:** 2026-06-16  
**Authoritative Specification:** MAS_v1.2.md  
**Freeze Status:** ACTIVE

---

## What Is Frozen

The following are frozen and may not change without a formal finding:

- All table schemas defined in MAS_v1.2.md Section 4
- All layer definitions in MAS_v1.2.md Section 5
- The three-engine architecture (Discovery / Lifecycle / Learning)
- The opportunity state machine (DISCOVERED / ACTIVE / WATCHING / INVALID)
- The Opportunity entity as the root tradable object
- The build sequence (A0 / A / B / C / D / E0 / E1)
- The execution system interface contract (Section 6)
- The RE formula structure and OS formula structure

## What Is NOT Frozen

The following may change without a formal finding:

- Parameter values (TTL numbers, half-life values, evidence weights, thresholds)
- Archetype detection rules, subject to Layer 6 guardrails
- Trading calendar entries
- stock_sector_map sector_purity_score values
- Bug fixes that do not change table schemas or state machine transitions
- Performance optimizations that do not change observable behavior

## Change Process

Any change to frozen components requires:

1. A written finding describing the specific gap, failure mode, or observed defect
2. Classification as SERIOUS or FATAL
3. A proposed fix that is the minimum change resolving the finding
4. Review confirming the fix does not introduce new circular dependencies
5. Update to MAS_v1.2.md before any code changes

Changes driven by implementation convenience, aesthetic preference, or speculative
improvement are not permitted. The architecture has been through three forensic audits.
Further redesign has diminishing returns and increasing integration risk.

## Why This Document Exists

Most systems with sophisticated architectures fail not because the design was wrong,
but because the design kept changing after coding began. Each change requires
re-testing, re-integrating, and re-validating previously working components. The
cumulative cost exceeds the value of the improvements.

The OIOS architecture reached Round-3 audit status of:

- FATAL findings: 0
- SERIOUS findings: 3 (all resolved in MAS_v1.2)
- GAP findings: 1 (resolved in MAS_v1.2)

This is the correct point to stop designing and start building.

## Authorized Work

**Phase A0 coding is authorized.**

Scope: data/market_behavior.db schema creation, repository layer (CRUD only),
domain models, state machine implementation, and acceptance tests.

No scanner logic. No DNA detection. No RE computation. No market data calls.
No sector engine. No AI components.

The Phase A0 acceptance tests defined in MAS_v1.2.md Section 7 are the
exit condition for Phase A0. All tests must pass before Phase A begins.

## Implementation Audit Gate

After Phase A0 code is written, a forensic implementation audit is required
before Phase A begins. The audit asks:

- Does every state transition write to signal_state_transitions?
- Can full transition history be reconstructed for any opportunity?
- Can a signal_births record exist without an opportunity_id?
- Can an opportunity exist with zero rows in opportunity_signals?
- Can INVALID state transition to any other state?
- Can duplicate opportunities be created for the same (symbol, direction) within merge window?
- Can orphan records exist in opportunity_signals (referencing non-existent opportunity)?
- Does the THESIS_INVALIDATED_WITH_POSITION event emit before the INVALID transition is committed?

These are code correctness questions, not design questions.
The implementation audit is a code review, not an architecture review.
