# SYSTEM UTILIZATION & DECISION-LINEAGE AUDIT — V3
## "What the system knows" vs "What the system uses" — definitive matrix

**Date:** 2026-09-10
**Type:** READ-ONLY audit. Builds on V1 (`SYSTEM_ARCHITECTURE_DATA_LINEAGE_AUDIT_V1.md`) and V2
(`SYSTEM_TRUTH_MAP_V2.md`) — read both first. No code, wiring, or data was changed.

**The test applied in this document, per your stated objective:**
> Nothing important should be collected without a defined consumer, and nothing validated as
> useful should remain permanently outside the decision process without a **documented reason**.

**Standard for "documented reason" used here (stricter than the raw research pass):**
A reason only counts if it existed **before and independent of this audit series** — e.g. a
module's own design docstring, or a pre-existing report like `ARCH_006_FINAL_REPORT.md`
(dated 2026-08-22, predates this session). V1 or V2 *noticing* that something is disconnected
does **not** count as a documented reason for it to stay that way — that would be the audit
grading its own homework. This distinction turned out to matter: several items the raw research
pass marked "YES, documented" are downgraded below because the only citation was V1/V2 itself.

---

## 1. The definitive matrix

Three columns only, because that is the whole point of this phase:

- **CONNECTED** — reaches a live decision today (carried forward from V1/V2, re-verified)
- **DOCUMENTED-INTENTIONAL-GAP** — genuinely, independently documented as deliberately kept out
- **UNDOCUMENTED GAP** — no genuine prior reason found; requires an actual decision

| # | Item | Verdict | Basis |
|---|---|---|---|
| 1 | `autonomous_research.ResearchCoordinator` | DOCUMENTED-INTENTIONAL-GAP | `ARCH_006_FINAL_REPORT.md` (2026-08-22): *"KEEP_RESEARCH — not wired into production (intentional)"* — predates this session |
| 2 | `autonomous_research.scientific_director` | DOCUMENTED-INTENTIONAL-GAP | Grouped with #1 in same ARCH_006 disposition table |
| 3 | `knowledge_system/options_research_pipeline.py` (KS_VALIDATED state) | **UNDOCUMENTED GAP** | No prior doc states options gates should ignore knowledge state — V1 simply misclassified it as live; V2 corrected the *fact*, but nobody ever decided *whether it should gate*. Real open question. |
| 4 | `oios/phase_f/outcome_tracker.py` | DOCUMENTED-INTENTIONAL-GAP *(upgraded from V2)* | `oios/phase_f/outcome_tracker.py`'s own header contains an explicit **"ISOLATION CONTRACT"**: *"Reads: ohlcv_daily, market_leaders_daily, market_research_controls. Writes: market_leader_outcomes, market_research_controls. No writes to any A–E table."* — this is genuine, original design intent, not this audit's finding. |
| 5 | `scripts/knowledge_system/` phases 3-6 (RQ generation/prioritization/proposals) | DOCUMENTED-INTENTIONAL-GAP (derivative) | Disconnected only because their sole intended executor (#1) is intentionally deferred — same ARCH_006 basis |
| 6 | `production_readiness/prr_runner.py` (9 gates) | **UNDOCUMENTED GAP** | No prior doc states the 9 gates are meant to be report-only forever. Worth a real decision: should `certification_status == RED` actually halt trading? Currently nothing checks it. |
| 7 | `growth_validator/gva_runner.py` | DOCUMENTED-INTENTIONAL-GAP | `ARCHITECTURE_GAP_REGISTER.md`: *"schedule only when a specific research question has sufficient data and operator has reviewed it. Manual invocation pattern is correct for now."* |
| 8 | `decision_tracer/` | DOCUMENTED-INTENTIONAL-GAP | Built as a CLI tool (`python -m decision_tracer SYMBOL`) by construction — not an omission |
| 9 | `hkap/` | DOCUMENTED-INTENTIONAL-GAP | `HKAP_DESIGN.md`: standalone historical-replay research tool, no production wiring implied anywhere |
| 10 | `ikn/` | DOCUMENTED-INTENTIONAL-GAP | `ARS_GAP_ANALYSIS.md`: explicitly listed as disconnected research utility |
| 11 | `data/discovered_edges.json` vs `evolved_strategies.json` | DOCUMENTED-INTENTIONAL-GAP (weak but real) | `LEARNING_PIPELINE_INVESTIGATION_2026-08-11.md` describes `discovered_edges.json` as the exploration/audit trail, separate from the promoted live file — thin but genuine, predates this session |
| 12 | `data/scanner_memory.json` | **UNDOCUMENTED GAP** | No prior doc states why this stays observational-only; `candidate_store.py`'s comment describes *what* it does, not *why* nothing else reads it |
| 13 | `data/odm_state.json` | **UNDOCUMENTED GAP** | Confirmed by direct research: no doc anywhere explains why it's restore-only |
| 14 | `data/knowledge_pipeline_health.json` | **UNDOCUMENTED GAP — actually a flagged DEFECT, not a decision** | `DTA_LIVE_001_AUDIT_REPORT.md` says it was *"3 days stale... this is an observability gap"* — that is a **bug report**, not a reason to accept the status quo. Misclassified as "documented" by the raw research pass; corrected here. |
| 15 | `data/ars_hypothesis_registry.json` | DOCUMENTED-INTENTIONAL-GAP (derivative) | Same basis as #1 — its only consumer is intentionally deferred |
| 16 | `data/champion_challenger_registry.jsonl` | **UNDOCUMENTED GAP** (weak evidence either way) | Only evidence is the script's own inline comment *"NOT wired into any live/paper trading path"* — states current fact, not a reason it should stay that way |
| 17 | `data/fingerprint_discovery_daily.jsonl` | DOCUMENTED-INTENTIONAL-GAP | Own docstring: *"standalone, manually invoked"* — genuine, predates this session |
| 18 | `data/ml_performance_dataset.json` | DOCUMENTED-INTENTIONAL-GAP (by circumstance) | Multiple pre-existing reports (`KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001_2026-08-14.md`, `STUDY_002_KNOWLEDGE_SUMMARY.md`) independently confirm: empty because live trades haven't produced enough closed outcomes yet — a real, external constraint, not a decision to ignore it |
| 19 | `analysis/rejection_tracker.py` → `rejection_audit.db` | **UNDOCUMENTED GAP — accidental reversal** | `ARCH_006_FINAL_REPORT.md` explicitly said *"DEPRECATE — redundant"* (2026-08-22). This session found `knowledge_fusion_engine.py` now reads it, and this session's own new code (`market_opportunity_benchmark.py`) writes to it too. **Nobody decided to revive this — it happened as an uncoordinated side effect.** This is precisely the kind of gap your objective is designed to catch. |
| 20 | `cle_learning_executor/` (writes IDRRepository) | **UNDOCUMENTED GAP** | Confirmed: writes real data, no reader found anywhere, no doc explains why |

### 1.1 Score

- **10 of 20** items have a genuine, pre-existing, independent documented reason for being
  outside the live decision path — correctly classified as intentional research/audit
  infrastructure, not oversights.
- **7 of 20** are real **undocumented gaps** — nobody has ever written down a decision about
  them. Per your stated principle, these are the ones that need attention (not necessarily
  fixing — a documented "we choose to leave this as-is because X" is equally valid closure).
- **1 of 20** (`knowledge_pipeline_health.json`) was mis-graded "documented" by the raw research
  pass — it is actually a previously-flagged bug that was never fixed, which is worse than an
  undocumented gap: it's a **known, written-down defect that has been sitting unresolved.**
- **1 of 20** (`rejection_audit.db`) is the most interesting case: it moved from "intentionally
  deprecated" to "actually in active use" **without anyone deciding that** — a live example of
  drift happening silently, exactly the failure mode this whole audit phase exists to catch.

---

## 2. The two remaining V2 residual unknowns — now resolved

### 2.1 Is OIOS Phase F meant to eventually feed KDA?

**No — resolved definitively.** `oios/phase_f/outcome_tracker.py`'s own header states an explicit
**ISOLATION CONTRACT**: it reads only `ohlcv_daily`, `market_leaders_daily`,
`market_research_controls`, writes only `market_leader_outcomes`/`market_research_controls`, and
states *"No writes to any A–E table."* `oios/__init__.py` independently describes OIOS as
*"Phase A0 — Core data model only. No scanners, no market data, no RE computation, no AI."*
Neither `OIOS_DEPLOYMENT_CERTIFICATION.md` nor `OIOS_WIRING_CERTIFICATION.md` mentions KDA
integration anywhere. **This reclassifies item #4 above from "undocumented" (as V2 left it) to
"genuinely, originally documented-intentional."**

### 2.2 Does `production_readiness/ph1_edge_gate.py` duplicate `edge_ranking_engine.py`'s decay logic?

**No — it is a correctly-built pass-through gate, not duplicate computation**, but it gates a
**dead branch**. Verified by direct read:
- `edge_ranking_engine.py` is the **only** place that computes decay (Sharpe drift < 0.70,
  age > 90 days, backtest failure, active-edge pruning) — 4 distinct mutation sites, each
  setting `rec.status = "DECAYING"`.
- `ph1_edge_gate.py` only **reads** the `status` field already set by the above and filters on
  it — confirmed no threshold/age/Sharpe constants exist in `ph1_edge_gate.py` at all.
- **However**, `ph1_edge_gate.py`'s `patch_knowledge_provider()` monkey-patches
  `autonomous_research.knowledge_provider.KnowledgeProvider.list_edges()` — and every other
  caller of `.list_edges()` found in the codebase (`cross_study_synthesizer.py`,
  `data_quality_assessor.py`, `evidence_validator.py`, `gap_detector.py`,
  `hypothesis_registry.py`, `methodology_auditor.py`, `research_coordinator.py`) is itself part
  of the disconnected `autonomous_research/` ecosystem (item #1/#2 above). `evolved_strategies.json`
  — what `MetaStrategyController` actually reads — is untouched by this patch.
- **Precise verdict:** the edge-decay gate mechanism is correctly engineered and well-tested
  (`LIVE_PRE_FLIGHT_AUDIT.md` confirms it worked: *"132/259 DECAYING edges blocked... 0 DECAYING
  passed"*) — but it is **a correctly-built bridge to a destination that is itself
  disconnected.** Fixing this gate wouldn't change live trading at all today, because nothing
  live reads `KnowledgeProvider.list_edges()` in the first place.

---

## 3. Direct answer to your stated objective

> "Nothing important should be collected without a defined consumer, and nothing validated as
> useful should remain permanently outside the decision process without a documented reason."

**Collected-without-a-consumer:** none found across two audit rounds — every data store traced
(~23 significant files/DBs in V1 §6, ~96 files in V2 §1) has at least one reader. The failure
mode in this codebase is not "orphaned data," it's **"has a reader, but the reader itself is
disconnected from decisions"** — a subtler, two-hop version of the same problem.

**Validated-but-undocumented-exclusion — the real, actionable list from this audit:**
1. `options_research_pipeline`'s KS state — never gated, never decided whether it should be (#3)
2. `production_readiness`'s 9 certification gates — never enforced, never decided whether they should be (#6)
3. `scanner_memory.json`, `odm_state.json` — harmless, but genuinely never reviewed (#12, #13)
4. `champion_challenger_registry.jsonl` — thin, never reviewed (#16)
5. `knowledge_pipeline_health.json` — a previously flagged, still-unresolved bug, not a decision (#14)
6. `rejection_audit.db` — silently reversed from "deprecate" to "active" with no one deciding that (#19)
7. `cle_learning_executor` — writes real output with no reader and no explanation (#20)

These 7 are the complete, definitive list of items that violate your stated principle today.
Everything else in the knowledge/research ecosystem — including large, sophisticated blocks like
`autonomous_research/`'s 28 files and OIOS's 69 files — is **intentionally** outside the decision
path, for reasons that were written down independently of this audit, before this session began.

---

## 4. What this phase deliberately does not do

Per your own sequencing (Audit → Map → Understand → Classify → Identify gaps → **Decide** → Only
then modify), this document stops at "Identify gaps." It does not recommend which of the 7
undocumented gaps should be connected, formally documented-and-kept, or retired — that is the
next, separate, explicitly-authorized decision. What it does provide is a clean, minimal punch
list to make that decision from, instead of the ~270 scattered reports this system had
accumulated before V1.
