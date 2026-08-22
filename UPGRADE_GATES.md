# UPGRADE GATES

**Principle: Evidence authorizes upgrades. Not time. Not opinion. Not code volume.**

---

## Phase C Authorization

Run: `python check_phase_c_ready.py`

| Gate | Criterion | Status |
|------|-----------|--------|
| C-Ready-1 | signal_births >= 100 | [ ] |
| C-Ready-2 | >= 30 FULL rows per sector in sector_conviction_daily | [ ] |
| C-Ready-3 | theme_phase_history >= 5 transitions | [ ] |
| C-Ready-4 | all archetypes firing within expected frequency bounds | [ ] |
| C-Ready-5 | opportunity lifecycle: >= 2 states, no state > 90% | [ ] |

**STATUS: NOT AUTHORIZED**

When all 5 gates pass, update STATUS to `AUTHORIZED — [date]`.

---

## Phase D Authorization

Run: `python check_phase_d_ready.py`

| Gate | Criterion | Status |
|------|-----------|--------|
| D-Ready-1 | >= 100 ACTIVE->WATCHING/INVALID transitions | [ ] |
| D-Ready-2 | >= 60 calendar days of RE trajectory data | [ ] |
| D-Ready-3 | >= 30 completed opportunities (terminal state reached) | [ ] |
| D-Ready-4 | >= 3 distinct invalidation reasons represented | [ ] |
| D-Ready-5 | no single state > 80% for 30 consecutive days | [ ] |

**STATUS: NOT AUTHORIZED** *(Phase C not yet authorized)*

When all 5 gates pass, update STATUS to `AUTHORIZED — [date]`.

---

## What each gate is protecting against

| Gate | Failure it prevents |
|------|---------------------|
| C-Ready-1 | Building ELE on a signal population that doesn't exist yet |
| C-Ready-2 | Sector conviction logic that silently fails upstream |
| C-Ready-3 | Theme Phase Engine activating before the 30-day guard has meaning |
| C-Ready-4 | One archetype dominating all signal generation |
| C-Ready-5 | Lifecycle degeneracy — ELE managing a stuck population |
| D-Ready-1 | Phase D learning from transitions that never happened |
| D-Ready-2 | RE velocity attribution without enough regime variation |
| D-Ready-3 | Outcome distribution tables built on < 30 resolved cases |
| D-Ready-4 | Phase D learning to classify one invalidation reason as all reasons |
| D-Ready-5 | Transition probabilities trained on a non-stationary, concentrated state |

---

## Rule

Never ask: *"Are we ready?"*

Ask: **"Which gate is failing?"**

Those are different questions. The first is subjective. The second has an answer.
