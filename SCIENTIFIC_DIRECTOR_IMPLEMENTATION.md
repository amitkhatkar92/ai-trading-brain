# Scientific Director — Implementation Guide

**Phase 3C | IIOS Research Infrastructure**
**Version:** 1.0.0
**Status:** COMPLETE — 301/301 tests pass

---

## Overview

The Scientific Director (SD) is the **apex scientific authority** of IIOS.

It governs what research is conducted, validates the results of that research,
maintains a structured scientific memory (the Journal), and ensures the
platform's knowledge base evolves coherently.

The SD **never executes scientific work directly**. It observes, reasons,
prioritises, delegates, and reviews.

---

## Architecture

```
ScientificDirector
  │
  ├── Observation Layer   ← KP, GD, RM, RC, MLC, IDR, HypothesisRegistry, Synthesizer
  │     _observe_knowledge()
  │     _observe_gaps()
  │     _observe_roadmap()
  │     _observe_research()
  │     _observe_learning()
  │     _observe_idr()
  │     _observe_hypotheses()
  │     _observe_synthesis()
  │
  ├── Reasoning Layer     ← completeness, urgency, research value, classification
  │     _evaluate_knowledge_completeness()
  │     _evaluate_gap_urgency()
  │     _evaluate_research_value()
  │     _classify_study()
  │
  ├── Decision Layer      ← hypotheses, approvals, escalations, recommendations
  │     _generate_hypotheses_for_gaps()
  │     _approve_pending_class_a_plans()
  │     _check_escalations()
  │     _build_recommendations()
  │
  └── Scientific Journal  ← ScientificJournal (append-only, JSON-persisted)
```

---

## Files

| File | Purpose |
|---|---|
| `autonomous_research/scientific_director.py` | Main SD class |
| `autonomous_research/sd_models.py` | All data models, enums, errors, ID utilities |
| `autonomous_research/sd_config.py` | SDConfig dataclass |
| `autonomous_research/scientific_journal.py` | ScientificJournal + JournalEntry |

---

## Configuration

```python
from autonomous_research import SDConfig

config = SDConfig(
    journal_path="data/ars/sd/journal.json",    # persisted journal file
    max_journal_entries=365,                     # entries before eviction
    max_hypotheses_per_review=3,                 # cap per review cycle
    max_plans_per_review=5,                      # auto-approve cap
    gap_severity_threshold="MEDIUM",             # minimum gap severity to act
    hypothesis_confidence_initial=0.5,           # starting confidence
    auto_approve_class_a=True,                   # auto-approve Class A plans
    dry_run=False,                               # disable writes for testing
    created_by="scientific_director",            # attribution in registry
)
```

---

## Dependency Injection

```python
from autonomous_research import ScientificDirector, SDConfig

sd = ScientificDirector(
    knowledge_provider=kp,       # KnowledgeProvider
    hypothesis_registry=reg,     # HypothesisRegistry
    gap_detector=gd,             # GapDetector
    roadmap_manager=rm,          # RoadmapManager
    evidence_validator=ev,       # EvidenceValidator
    study_planner=sp,            # StudyPlanner
    synthesizer=synth,           # CrossStudySynthesizer
    rc=rc,                       # ResearchCoordinator
    mlc=mlc,                     # MarketLearningCoordinator
    idr=idr,                     # IDRRepository
    pig=pig,                     # PlatformIntelligenceGateway (optional)
    config=config,
)
```

All dependencies are optional. The SD degrades gracefully when components are unavailable.

---

## Review Types and Scope

| Review Type | Scope |
|---|---|
| `DAILY` | KP + GD + RM + RC + MLC + HypothesisRegistry |
| `WEEKLY` | All daily + CrossStudySynthesizer |
| `MONTHLY` | All weekly + IDR |
| `PLATFORM` | All components |

---

## Decision Classes

| Class | Who approves | When |
|---|---|---|
| CLASS_A | SD auto-approves | Standard study types, LOW/MEDIUM risk |
| CLASS_B | Human operator required | META_LEARNING, CUSTOM type, HIGH risk |

---

## Gap → Hypothesis Mapping

| Gap Severity | Hypothesis Priority |
|---|---|
| CRITICAL | CRITICAL |
| HIGH | HIGH |
| MEDIUM | MEDIUM |
| LOW | LOW (EXPLORATORY) |

| Gap Category | Hypothesis Classification |
|---|---|
| DATA_GAP | COVERAGE_GAP |
| EVIDENCE_GAP | PERFORMANCE_GAP |
| REGIME_GAP | COVERAGE_GAP |
| SECTOR_GAP | COVERAGE_GAP |
| TEMPORAL_GAP | TEMPORAL_GAP |
| VALIDATION_GAP | PERFORMANCE_GAP |
| CONTRADICTION_GAP | CONTRADICTION |
| CONFIDENCE_GAP | PERFORMANCE_GAP |
| KNOWLEDGE_GAP | COVERAGE_GAP |
| COVERAGE_GAP | COVERAGE_GAP |

---

## Scientific Journal

Every review, decision, and observation is immutably recorded.

```python
# Query last 30 entries
entries = sd._journal.history(limit=30)

# Filter by type
reviews = sd._journal.history(limit=10, entry_type="REVIEW")

# Full-text search
results = sd._journal.search("critical gap")

# Pending follow-ups
overdue = sd._journal.pending_followups()

# Statistics
stats = sd._journal.statistics()
# {"total_entries": 47, "by_type": {...}, "escalations": 2, "pending_followups": 0}
```

---

## Constitutional Constraints

1. **SD never executes scientific work.** No direct pipeline invocation.
2. **SD never accesses trading systems.** No broker, order manager, or execution engine.
3. **Every decision is explained.** `ScientificDecision.reasoning.rationale` always populated.
4. **Every decision is delegated.** `delegation_target` always set.
5. **Every decision is journaled.** Automatic, non-bypassable.
6. **CLASS_B decisions require human approval.** `requires_human_approval=True`.
7. **Dry-run mode disables all writes.** Journal, hypothesis creation, and RC delegation.

---

## Operational Safety

The SD will never crash a review cycle. Every `_observe_*` method is wrapped
in `try/except`. Failed observations produce a `SDHealth.DEGRADED` status but
allow the review to complete.

`SDHealth.BLIND` is only reached after `consecutive_review_failures >= 3`.

---

## Knowledge Completeness Formula

$$C = 0.40 \cdot \min\!\left(\frac{findings}{50}, 1\right)
    + 0.35 \cdot \min\!\left(\frac{edges}{10}, 1\right)
    + 0.25 \cdot \min\!\left(\frac{certs}{5}, 1\right)$$

---

## Test Coverage

| Suite | Range | Count |
|---|---|---|
| ReviewType / enum | T001-T025 | 25 |
| Dataclass fields + to_dict | T026-T060 | 35 |
| SDConfig | T061-T075 | 15 |
| ScientificJournal | T076-T100 | 25 |
| SD construction + status | T101-T115 | 15 |
| Observation layer | T116-T145 | 30 |
| Reasoning layer | T146-T165 | 20 |
| daily_review | T166-T190 | 25 |
| weekly_review | T191-T205 | 15 |
| monthly_review | T206-T215 | 10 |
| evaluate_platform | T216-T225 | 10 |
| approve_study | T226-T240 | 15 |
| reject_study | T241-T248 | 8 |
| roadmap API | T249-T258 | 10 |
| hypothesis generation | T259-T268 | 10 |
| decision classification | T269-T278 | 10 |
| human escalation | T279-T285 | 7 |
| thread safety | T286-T293 | 8 |
| constitutional constraints | T294-T300 | 7 |
| **Total** | **T001-T300** | **301** |
