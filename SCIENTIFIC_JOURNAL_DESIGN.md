# Scientific Journal — Design Reference

**Phase 3C | IIOS Research Infrastructure**

---

## Purpose

The Scientific Journal is the **long-term structured scientific memory** of the
IIOS platform. It stores every scientific decision, review, and observation in a
structured, queryable, append-only record.

Every SD decision can be fully reconstructed from journal history alone.

---

## Design Principles

### Append-only
Entries are never modified or deleted during a session. The journal only evicts
the oldest entries when `max_entries` is exceeded (FIFO).

### Structured
Every entry is a `JournalEntry` dataclass with named fields. No free-text blobs.
Every entry captures *observation*, *reasoning*, and *decision* separately.

### Queryable
- `history(limit, entry_type)` — recency-filtered list
- `search(keyword)` — full-text search across all text fields
- `pending_followups()` — overdue entries by date

### Persistent
Entries are written to a JSON file on every append (unless `dry_run=True`).
On reload, entries are deserialised using `JournalEntry.from_dict()`.

### Thread-safe
All reads and writes are protected by a `threading.Lock()`.

---

## Entry Types

| Type | When created |
|---|---|
| `REVIEW` | At the end of every `daily_review / weekly_review / monthly_review / evaluate_platform` |
| `DECISION` | For every `ScientificDecision` that does NOT require human approval |
| `ESCALATION` | For every `ScientificDecision` that DOES require human approval |
| `OBSERVATION` | For standalone observations recorded via `record_observation()` |

---

## `JournalEntry` Fields

| Field | Type | Description |
|---|---|---|
| `entry_id` | str | Unique ID, derived from parent review or decision ID |
| `entry_type` | str | "REVIEW" / "DECISION" / "ESCALATION" / "OBSERVATION" |
| `date` | str | ISO date "YYYY-MM-DD" |
| `observation` | str | What the SD observed (structured description) |
| `reasoning` | str | How the SD reasoned about it |
| `decision` | str | What the SD decided |
| `confidence` | float | 0.0–1.0 |
| `expected_followup` | str | What should happen next |
| `follow_up_date` | Optional[str] | ISO date when follow-up is expected |
| `review_id` | Optional[str] | Parent review ID if applicable |
| `review_type` | Optional[str] | Parent review type if applicable |
| `version` | int | Schema version (currently 1) |

---

## Eviction Policy

When `len(entries) > max_entries`, the **oldest** entries are evicted first
(FIFO). The default `max_entries=365` means approximately one year of daily
reviews can be retained indefinitely.

---

## Usage

```python
from autonomous_research import ScientificJournal, SDConfig

journal = ScientificJournal(
    journal_path="data/ars/sd/journal.json",
    max_entries=365,
    dry_run=False,
)

# After a review
entry = journal.record_review(review)

# After a decision
entry = journal.record_decision(decision, review_id=review.review_id)

# Manual observation
entry = journal.record_observation(
    component="KnowledgeProvider",
    metric="completeness_drop",
    value=0.21,
    interpretation="Knowledge completeness dropped 15% since last week.",
    confidence=0.85,
    review_id=review.review_id,
)

# Query
recent = journal.history(limit=30)
reviews_only = journal.history(limit=10, entry_type="REVIEW")
escalations = journal.history(limit=10, entry_type="ESCALATION")

# Search
hits = journal.search("critical gap")

# Follow-ups
overdue = journal.pending_followups()

# Statistics
stats = journal.statistics()
# {
#     "total_entries": 47,
#     "by_type": {"REVIEW": 10, "DECISION": 30, "ESCALATION": 7},
#     "escalations": 7,
#     "pending_followups": 0
# }
```

---

## JSON Schema (version 1)

```json
[
  {
    "entry_id": "je-sd-review-2025-01-15-a1b2c3d4",
    "entry_type": "REVIEW",
    "date": "2025-01-15",
    "observation": "DAILY review: 5 observations, 2 decisions. Health=HEALTHY.",
    "reasoning": "DAILY review completed in 38ms. ...",
    "decision": "Review completed. Decisions: CREATE_HYPOTHESIS; APPROVE_STUDY_CLASS_A",
    "confidence": 0.9,
    "expected_followup": "Monitor decisions delegated in this review. Next review: daily",
    "follow_up_date": null,
    "review_id": "sd-review-2025-01-15-a1b2c3d4",
    "review_type": "DAILY",
    "version": 1
  }
]
```

---

## Storage Location

Default: `data/ars/sd/journal.json`

The parent directory is created automatically on first write.

For VPS deployment, this file lives inside the `./data:/app/data` Docker volume
and survives container restarts.

---

## Audit Capability

The full scientific record of any IIOS session can be reconstructed using:

```python
# All reviews in order
reviews = journal.history(limit=365, entry_type="REVIEW")

# All decisions ever escalated to human
escalations = journal.history(limit=365, entry_type="ESCALATION")

# Everything mentioning a specific hypothesis
hits = journal.search("Research gap: Coverage gap X")
```
