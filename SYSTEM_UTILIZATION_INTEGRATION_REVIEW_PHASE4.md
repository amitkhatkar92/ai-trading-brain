# SYSTEM UTILIZATION & INTEGRATION REVIEW — PHASE 4
## The 7-item punch list — Why / Where / Should-it-decide, classified

**Date:** 2026-09-10
**Type:** READ-ONLY review. No code, wiring, or trading logic changed. This is a classification
exercise only, per explicit instruction: "That is much more valuable than simply fixing
disconnected files."
**Builds on:** V1 (`SYSTEM_ARCHITECTURE_DATA_LINEAGE_AUDIT_V1.md`), V2 (`SYSTEM_TRUTH_MAP_V2.md`),
V3 (`SYSTEM_UTILIZATION_DECISION_LINEAGE_AUDIT_V3.md`) — read all three first.

**Standard applied:** the KDA loop (`Market → Observation → Analysis → Knowledge → Validation →
Decision → Trade/No Trade → Outcome → Learning → Future Decision`) is the reference architecture.
Each item below is judged against how close it is to that loop, and whether closing the gap is
warranted, premature, or unnecessary.

---

## Two corrections found while completing this review

Continuing the pattern from V1→V2→V3 (each round corrected the previous one), completing this
review's due diligence produced two more corrections. Recorded honestly rather than silently
folded in.

**Correction 1 — `data/rejection_audit.db` is more connected than V1/V3 stated.**
V3 described it only as "has a reader (`knowledge_fusion_engine.py`)". Direct trace this round
found the full chain: `knowledge_fusion_engine.py::load_fusion_records()` loads rejection records
→ `_source_quality_angle()` scores them (weight 1.0 for `REJECTION_AUDIT` source type) →
produces a `MultiAngleView` (`angle_view`) → passed directly into
`knowledge_decision_pipeline.py:436-458`, which feeds `knowledge_decision_authority.py`'s
per-signal decision computation — confirmed called every cycle, every signal, via KDA
(`knowledge_authority/knowledge_decision_pipeline.py:726-736`, `_reload_kfe()`). **This is not
just "an evidence pool member" — rejection data genuinely reaches a live decision today.**

**Correction 2 — `data/champion_challenger_registry.jsonl` is properly documented, not an
undocumented gap.** V3 graded this "UNDOCUMENTED GAP (weak evidence either way)" based on a thin
inline comment. Reading the module's full header this round found an explicit, rich statement:
*"SCOPE (explicitly confirmed with the user before implementation): Promotion in this phase is a
REGISTRY/STATUS LABEL CHANGE ONLY... Reaching CHALLENGER_ELIGIBLE status does NOT feed KDA,
DecisionEngine, or any paper/live trading path — that would be a separate, later phase requiring
its own explicit approval, per the standing rule that a discovered characteristic must not
influence live selection until it clears the full validation gate AND a further, dedicated
go-ahead."* This is a genuine, deliberate, pre-approved governance decision — reclassified below.

---

## The 7 items — Why / Where / Should-it-decide / Classification

### 1. `knowledge_system/options_research_pipeline.py` — KS_VALIDATED state

| Question | Answer |
|---|---|
| **Why does this exist?** | A statistically rigorous options-hypothesis validation ladder — `KS_VALIDATED` requires ≥20 outcomes + OOS win-rate ≥50% + p<0.10; `KS_AUTHENTICATED` requires ≥40 outcomes + walk-forward Sharpe>0 (`options_knowledge_store.py:41-42`). This is genuine research-grade rigor, not a toy metric. |
| **Where does output go today?** | Persisted internally as state labels (VALIDATED/AUTHENTICATED/DEGRADED). `options_risk_engine.py`'s 4 live gates (capital, per-trade loss, VIX, loss-streak) never read it — confirmed by direct grep (V2 §0). Dead end at KNOWLEDGE stage. |
| **Should it influence a decision?** | **CONDITIONAL — yes, and the mechanism is already designed.** The module's own header states its intended integration: *"VALIDATED → BOUNDED influence: max ±5% confidence adjustment"* (`options_knowledge_store.py:34`). This is the exact same bounded-influence pattern KDA already uses successfully elsewhere in this system. The design work is done; only the wiring step (reading `KS_VALIDATED` state into wherever options confidence is set, capped at ±5%) was never completed. |

**Classification: 🔵 Keep but connect to decision.** Of all 7 items, this is the strongest
candidate for actually wiring in — the bounded, capped mechanism was already specified by the
original author, reducing the risk of "connect it and see what happens."

---

### 2. `production_readiness/prr_runner.py` — 9 certification gates

| Question | Answer |
|---|---|
| **Why does this exist?** | Daily automated readiness dashboard across 9 dimensions (edge decay, SHORT DNA audit, signal freshness, universe coverage, daily pipeline health, knowledge validity, missed opportunities, learning impact, final GREEN/YELLOW/RED certification) — built during the ARCH-006 pre-live pilot certification effort. |
| **Where does output go today?** | 9 markdown reports + a `certification_status` verdict, written daily at EOD. Confirmed by grep: zero references to `certification_status` in `risk_guardian.py`, `decision_engine.py`, or `order_manager.py`. |
| **Should it influence a decision?** | **CONDITIONAL.** The verdict is exactly the kind of macro "should the system even be trading today" signal that could sensibly gate new-signal generation on a RED day — conceptually similar to RiskGuardian's kill-switch, but operating on system-health signals rather than market signals. However, wiring 9 heterogeneous audit gates directly into a trading halt is materially riskier than item #1 (false-positive halt risk from any one of 9 gates is real and untested against live trading impact). |

**Classification: 🟡 Needs redesign/clarification.** The underlying question ("should a RED day
pause trading") is worth a real decision, but connecting `prr_runner.py` as-is would be premature.
Needs a scoped follow-up: which of the 9 gates (if any) are trustworthy/low-noise enough to gate
trading vs. remain advisory-only.

---

### 3. `data/scanner_memory.json`

| Question | Answer |
|---|---|
| **Why does this exist?** | Tracks candidate/concentration history over a rolling `SCANNER_MEMORY_RETENTION_DAYS` window, to support retrospective premarket reporting of scanner behavior. |
| **Where does output go today?** | Written by `candidate_store.py`; read only by a premarket report generator. |
| **Should it influence a decision?** | **NO.** This is inherently a retrospective/diagnostic artifact (what the scanner has recently concentrated on), not a forward-looking signal. There is no natural decision it should gate. |

**Classification: 🟢 Keep as-is.** The V3 "gap" here was really just that nobody had formally
written down "this is fine as observability-only" — now done.

---

### 4. `data/odm_state.json`

| Question | Answer |
|---|---|
| **Why does this exist?** | Persists `OpportunityDensityMonitor`'s scan-mode (NORMAL/AGGRESSIVE/CONSERVATIVE) across container restarts. |
| **Where does output go today?** | Restored once at startup; ODM itself is already live and directly drives scanner behavior every cycle (confirmed V1, `run_full_cycle():1038`). |
| **Should it influence a decision?** | **Already does — via the live ODM component, not via this file.** The JSON's only job is surviving a restart. |

**Classification: 🟢 Keep as-is.** Correcting V3's framing: this was never really an information
gap — it's a persistence detail for a component that is already fully wired into live decisions.

---

### 5. `data/champion_challenger_registry.jsonl`

| Question | Answer |
|---|---|
| **Why does this exist?** | A deliberately staged promotion registry for discovered fingerprints — explicitly scoped in its own header as a "REGISTRY/STATUS LABEL CHANGE ONLY" step, per an explicit prior agreement with the user before implementation (see corrections above). |
| **Where does output go today?** | Its own registry file; genuinely consumed daily by Phase 6 (`shadow_challenger_tracker_001.py`) to decide which fingerprints to shadow-track next — a real, if non-live-decision, consumer. |
| **Should it influence a decision?** | **NO, not yet — by explicit, pre-approved design.** The module's own documentation states reaching its terminal status "does NOT feed KDA, DecisionEngine, or any paper/live trading path... that would be a separate, later phase requiring its own explicit approval." |

**Classification: 🟢 Keep as-is.** Correcting V3 downward from "undocumented gap" to properly
documented, deliberately staged governance — exactly the kind of caution ("don't blindly activate
everything without controlled evidence") that has been the standing rule throughout this session.

---

### 6. `data/knowledge_pipeline_health.json`

| Question | Answer |
|---|---|
| **Why does this exist?** | Observability file reporting the EOD knowledge-feedback-loop's health, meant to catch silent pipeline failures. |
| **Where does output go today?** | Read by a startup/readiness health-check script only — appropriate for a monitoring file, not a decision gate. |
| **Should it influence a decision?** | **NO** — monitoring files shouldn't gate decisions directly. But the *original* staleness complaint (`DTA_LIVE_001_AUDIT_REPORT.md`, ~2026-08-21: *"3 days stale... observability gap"*) is a genuine open question. The writer (`write_health_file()` in `knowledge_feedback_loop_001.py`) is properly built and tested (idempotency + tmp-file-cleanup tests exist in `test_knowledge_pipeline_flow.py`), and is called from the EOD-wired pipeline — so the bug **may already be fixed** by later work, or may still be silently failing. This audit found no way to confirm from static code alone; it requires a runtime check (actual file mtime in production). |

**Classification: ⚪ Monitor only** — with one flagged follow-up: verify the staleness bug is
actually resolved (a quick, low-risk, separate check against the live file's mtime), since a
health-check file that nobody re-verified as fixed is worse than one nobody built at all.

---

### 7. `analysis/rejection_tracker.py` → `data/rejection_audit.db`

| Question | Answer |
|---|---|
| **Why does this exist?** | Central rejection-attribution database, recording *why* every candidate was rejected at every gate (CapitalRiskEngine, RiskManagerAI, RiskGuardian, and — as of this session — `market_opportunity_benchmark.py`). |
| **Where does output go today?** | **Confirmed this round (Correction 1 above): reaches a live decision.** `knowledge_fusion_engine.py` → `angle_view` → `knowledge_decision_pipeline.py` (KDA) → per-signal decision, every cycle. |
| **Should it influence a decision?** | **YES — and it already does.** |

**Classification: 🟢 Keep as-is, functionally** — but with a mandatory documentation-hygiene
action: `ARCH_006_FINAL_REPORT.md` (2026-08-22) formally recorded a decision to **DEPRECATE** this
file as "redundant." That decision was silently reversed by later, uncoordinated work (KFE's
adoption of it, plus this session's own new writer) with nobody updating the record. This is not
a code change — it is a one-line correction to ARCH_006's disposition table (or a superseding
note) so a future audit doesn't get misled by a stale, contradicted decision the way this one
briefly was.

---

## Summary table

| # | Item | Classification | Action implied |
|---|---|---|---|
| 1 | `options_research_pipeline` KS_VALIDATED | 🔵 Keep but connect to decision | Wire the already-designed ±5% bounded confidence adjustment — separate, explicitly authorized session |
| 2 | `prr_runner.py` 9 gates | 🟡 Needs redesign/clarification | Decide which (if any) of 9 gates should halt trading vs. stay advisory |
| 3 | `scanner_memory.json` | 🟢 Keep as-is | None — now formally documented as observability-only |
| 4 | `odm_state.json` | 🟢 Keep as-is | None — was never actually a gap |
| 5 | `champion_challenger_registry.jsonl` | 🟢 Keep as-is | None — properly documented, deliberately staged governance |
| 6 | `knowledge_pipeline_health.json` | ⚪ Monitor only | Verify staleness bug status against production (read-only check, not a fix) |
| 7 | `rejection_audit.db` | 🟢 Keep as-is (functionally) | Correct `ARCH_006`'s stale "DEPRECATE" disposition table entry — documentation only |

**Net result: of the original 7 "undocumented gaps," 4 turn out to be fine as-is once properly
understood (3, 4, 5, 7), 1 is a genuine, well-specified connection opportunity worth a future
session (1), 1 needs a scoped design decision before any wiring (2), and 1 needs a read-only
production verification, not code (6). Zero of the 7 require immediate code changes.**

---

## What this confirms about the KDA loop as the reference standard

Two of the four "actually fine" items (4, 5) turned out to be fine specifically *because* they
already follow the KDA-loop discipline correctly: #4 (`odm_state.json`) is a persistence detail
for a component that already closes the full loop; #5 (`champion_challenger_registry.jsonl`) is
explicitly staged *to avoid* prematurely joining the loop without validation. The one item most
worth connecting (#1, options research) is worth connecting precisely *because* its author
already designed a bounded, capped mechanism — the same caution KDA itself uses. This is
consistent evidence that the system's best-built parts already share one discipline; the audit's
job across all four documents has been finding where that discipline was applied only partially,
or not reviewed since being built.

---

## Explicit non-scope of this document

No code was changed. No item was wired, disconnected, or retired. Item #1's "connect it" and
item #2's "decide the gate policy" are recommendations for a future, separately-authorized
session — consistent with the standing rule established across all four audit documents: Audit →
Map → Understand → Classify → Identify gaps → **Decide** → Only then modify. This document
completes "Classify." "Decide" and "modify" remain deliberately out of scope here.
