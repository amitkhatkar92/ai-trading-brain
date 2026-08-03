# Scientific Hypothesis Registry
## ARS Phase 1.2 — Permanent Scientific Memory of IIOS

**Status:** IMPLEMENTED ✅  
**Module:** `autonomous_research/hypothesis_registry.py`  
**Storage:** `data/ars_hypothesis_registry.json`  
**Tests:** 40/40 pass  

---

## What This Module Is

The Scientific Hypothesis Registry is the **permanent scientific memory** of the
Intelligent IIOS Orchestration System. It stores every research hypothesis, its
supporting evidence, lifecycle state, validation history, and final outcome.

It exists so that:
- Every scientific claim about market behaviour is explicitly recorded
- Every decision about a hypothesis is auditable and reproducible
- The Scientific Director can depend on a single source of truth for open and
  resolved hypotheses
- Knowledge gaps never disappear silently — they either get confirmed, rejected,
  or remain open

---

## What This Module Is NOT

The registry has **zero reasoning responsibility**. It explicitly does not:

| Prohibited behaviour | Why |
|---|---|
| Generate hypotheses | That is the Scientific Director's job |
| Prioritise or rank hypotheses | Scientific Director applies scoring |
| Execute research studies | Replay infrastructure handles that |
| Schedule work | Orchestrator owns the schedule |
| Modify strategies | Trading engine only |
| Modify the AI system | Governance layer only |
| Write to any KnowledgeProvider store | KP is read-only from registry's POV |

Violation of any of these boundaries would corrupt the scientific workflow.

---

## Architecture Position

```
Layer above (consumer):
    ScientificDirector
        ↓ creates, updates, queries hypotheses
    HypothesisRegistry  ← THIS MODULE
        ↓ validates evidence references against
    KnowledgeProvider  (read-only)
        ↓ reads from
    SQLite/JSON data stores (read-only from ARS)
```

The registry sits between the Scientific Director's reasoning layer and the raw
knowledge stores. It never reads raw data stores directly — all knowledge access
goes through `KnowledgeProvider`.

---

## Lifecycle State Machine

Every hypothesis travels through a defined lifecycle. Transitions are enforced
at the registry level — invalid moves raise `InvalidTransitionError`.

```
                  ┌─────────────────────────────────────┐
                  ↓                                     │
             PROPOSED ──────────────────────────→ ARCHIVED
                  │                                     ↑
                  ↓                                     │
           UNDER_REVIEW ──→ REJECTED ──────────────────┤
                  │              │                      │
                  │ PROPOSED ←───┘  (revival path)      │
                  ↓                                     │
             APPROVED ──────────────────────────→ ARCHIVED
                  │
                  ↓
             PLANNED ───────────────────────────→ ARCHIVED
                  │
                  ↓
             RUNNING
                  │
           ┌──────┴──────┐
           ↓             ↓
       VALIDATED      REJECTED ──────────────────→ ARCHIVED
           │
    ┌──────┴──────┐
    ↓             ↓
CONFIRMED     REJECTED
    │
    ↓
 ARCHIVED  (terminal)
```

### Valid transitions table

| From | To (allowed) |
|---|---|
| PROPOSED | UNDER_REVIEW, ARCHIVED |
| UNDER_REVIEW | APPROVED, REJECTED, PROPOSED |
| APPROVED | PLANNED, ARCHIVED |
| PLANNED | RUNNING, ARCHIVED |
| RUNNING | VALIDATED, REJECTED |
| VALIDATED | CONFIRMED, REJECTED |
| CONFIRMED | ARCHIVED |
| REJECTED | ARCHIVED, PROPOSED |
| ARCHIVED | *(terminal — no further transitions)* |

---

## Hypothesis Identity

Each hypothesis is assigned a unique ID on creation:

```
Format: H{YYYY}-{MM}-{NNN:03d}
Example: H2026-08-001
```

IDs are sequential within the month and monotonically increasing. They are
generated inside the thread lock to prevent ID collision under concurrent access.

---

## Evidence Chain

Every hypothesis must be traceable to evidence. The registry enforces this by:

1. Accepting evidence references at creation time and via `add_evidence()`
2. Validating each reference against `KnowledgeProvider` before acceptance
3. Maintaining the full chain in `supporting_evidence` for every hypothesis

**Evidence types:**

| Type | Validated against |
|---|---|
| STUDY | `KnowledgeProvider.get_study(id)` |
| FINDING | `KnowledgeProvider.list_findings()` |
| EDGE | `KnowledgeProvider.list_edges()` |
| CERTIFICATION | `KnowledgeProvider.list_certifications()` |
| STRATEGY | `KnowledgeProvider.list_strategies()` |
| METRIC | Non-empty ID only (metrics are dynamic) |
| EXTERNAL | Accepted without validation (academic papers, etc.) |

Evidence references are **idempotent** — adding the same `evidence_id` twice is
a no-op (skipped with a warning).

---

## Decision Audit Trail

Every state change, evidence addition, confidence update, and validation result
is recorded as a `DecisionEvent` in `decision_history`. The history is:

- **Append-only** — no event is ever deleted or modified
- **Immutable copies** — `get_decision_history()` returns a copy, not a reference
- **Fully serialised** — the complete history survives every reload cycle

A `DecisionEvent` captures:
```
event_id        — 8-char UUID fragment
timestamp       — ISO datetime
actor           — who made the decision
action          — what was done
reason          — why it was done
previous_status — status before
new_status      — status after
metadata        — arbitrary key/value context
```

---

## Persistence Design

### Storage format

```json
{
  "version": "1.0",
  "created_at": "2026-08-01T09:00:00",
  "last_updated": "2026-08-14T11:23:45",
  "hypothesis_count": 12,
  "hypotheses": {
    "H2026-08-001": { ... }
  }
}
```

### Atomic write protocol

Every save follows three steps:
1. Serialise to `ars_hypothesis_registry.json.tmp`
2. Copy existing `ars_hypothesis_registry.json` → `ars_hypothesis_registry.json.bak`
3. `os.replace(tmp, final)` — atomic on POSIX and Windows

The backup means the last-good version is always available if a write is
interrupted. The `os.replace()` call ensures no partially-written file is ever
visible to a concurrent reader.

### Thread safety

A `threading.Lock()` wraps all writes. Reads (`get`, `list_*`, `search`,
`statistics`) are not locked — they operate on the in-memory `_store` dict
which Python's GIL protects at the dict-read level. The lock is held during the
`_generate_id() → store → persist` sequence, preventing ID collisions under any
number of concurrent writers.

---

## Four Scientific Accountability Questions

**Q1: Can every hypothesis be traced back to evidence?**

YES. `EvidenceReference` objects are mandatory at creation (via
`supporting_evidence`) and validated against `KnowledgeProvider`. Additional
evidence can be added at any lifecycle stage via `add_evidence()`. The full
chain is always accessible via `get_evidence_chain()`.

**Q2: Can every decision be audited?**

YES. `DecisionEvent` records are written for every state change, evidence
addition, confidence update, and validation result. The `decision_history` list
is append-only and fully persisted. `get_decision_history()` returns a copy
that cannot corrupt the original.

**Q3: Can every lifecycle transition be reproduced?**

YES. `VALID_TRANSITIONS` is the single authoritative state machine. It is
consulted on every `update_status()` call. The entry and exit state are both
recorded in the decision event. Given the history, any audit can replay every
transition in exact sequence.

**Q4: Can the Scientific Director safely depend on this registry?**

YES. The registry provides:
- Thread-safe concurrent writes (lock wraps all mutation)
- Atomic persistence (no partial writes visible)
- Automatic backup before every overwrite
- Lazy load on first access (no stale cache risk)
- Strict evidence validation (KP-backed)
- Hard lifecycle enforcement (`InvalidTransitionError` on illegal moves)
- Immutable decision history (append-only, copy-on-read)
- Versioned JSON format (forward-compatible parsing)

---

## Error Taxonomy

| Exception | When raised |
|---|---|
| `RegistryError` | Base — not raised directly |
| `HypothesisNotFoundError` | `get_or_raise()`, `update_status()` on unknown ID |
| `DuplicateHypothesisError` | Internal collision guard (should never fire in production) |
| `InvalidTransitionError` | `update_status()` with a forbidden state machine move |
| `InvalidEvidenceError` | `add_evidence()` when evidence_id not found in KP |
| `RegistryValidationError` | Required fields empty, confidence out of range, wrong status for `set_validation_result()` |

---

## Data Retention

Hypotheses are never deleted. The final states are:
- `CONFIRMED` → archived when superseded
- `REJECTED` → archived or revived to `PROPOSED`
- `ARCHIVED` → terminal (no further transitions)

The full history of all hypotheses, including rejected and archived ones, is
retained in the JSON file and available to future analysis.
