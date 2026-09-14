# Execution Risk Lifecycle — State Diagram

**IIOS C6 Execution Intelligence — Phase 4, Module 1**

---

## State Transition Diagram

```
                    ┌─────────────────────────────────────────┐
                    │              CREATED                     │
                    └────────────┬────────────────┬───────────┘
                                 │                │
                    PENDING_EVA  │         FAILED │  EXPIRED
                                 ▼                ▼
                    ┌────────────────┐   ┌───────┐  ┌─────────┐
                    │PENDING_EVALUAT.│   │FAILED │  │ EXPIRED │
                    └────────┬───────┘   └───┬───┘  └────┬────┘
                             │               │            │
                  EVALUATING │      FAILED   │    EXPIRED │    ARCHIVED
                             │           ◄───┘            │
                             ▼                            ▼
                    ┌────────────────┐           ┌───────────────┐
                    │   EVALUATING   │           │   ARCHIVED    │◄─────┐
                    └──┬──┬──┬──┬───┘           │  (TERMINAL)   │      │
                       │  │  │  │               └───────────────┘      │
               PASSED  │  │  │  │  BLOCKED                             │
                       │  │  │  │                                      │
              WARNING  │  │  │  └──► BLOCKED ──► OVERRIDDEN ──────────►│
                       │  │  │           │           │                  │
               PASSED ◄┘  │  └──► FAILED│    ARCHIVED◄────────────────►│
                           │            ▼            │                  │
                     WARN ◄┘        ARCHIVED ◄───────┘                  │
                                                                        │
         ┌──────────┐    ┌─────────┐    ┌───────────┐                  │
         │  PASSED  │    │ WARNING │    │ OVERRIDDEN│                  │
         └──┬───┬───┘    └───┬─┬───┘    └────┬──────┘                  │
            │   │            │ │              │                         │
  OVERRIDE  │   │ ARCHIVED   │ │ BLOCKED      │ ARCHIVED / EXPIRED      │
            │   │            │ │              ▼                         │
            ▼   ▼            ▼ ▼          ARCHIVED ──────────────────►──┘
        OVERRIDE ARCHIVE  BLOCK ARCHIVE
```

---

## Simplified Linear View

```
CREATED
  │
  ├──► PENDING_EVALUATION
  │         │
  │         ├──► EVALUATING
  │         │         │
  │         │         ├──► PASSED ──────────────────────┐
  │         │         ├──► WARNING ──────────────────────┤──► OVERRIDDEN ──┐
  │         │         ├──► BLOCKED ──────────────────────┘                 │
  │         │         ├──► EXPIRED ──────────────────────────────────────┐ │
  │         │         └──► FAILED ───────────────────────────────────────┤ │
  │         ├──► EXPIRED ─────────────────────────────────────────────── ┤ │
  │         └──► FAILED ──────────────────────────────────────────────── ┤ │
  ├──► EXPIRED ───────────────────────────────────────────────────────── ┤ │
  └──► FAILED ────────────────────────────────────────────────────────── ┤ │
                                                                          │ │
                                                                          ▼ ▼
                                                                       ARCHIVED
                                                                      (TERMINAL)
```

---

## Valid Transitions Table

| From State         | To State(s)                                       |
|--------------------|---------------------------------------------------|
| CREATED            | PENDING_EVALUATION, EXPIRED, FAILED               |
| PENDING_EVALUATION | EVALUATING, EXPIRED, FAILED                       |
| EVALUATING         | PASSED, WARNING, BLOCKED, EXPIRED, FAILED         |
| PASSED             | OVERRIDDEN, EXPIRED, ARCHIVED                     |
| WARNING            | OVERRIDDEN, BLOCKED, EXPIRED, ARCHIVED            |
| BLOCKED            | OVERRIDDEN, EXPIRED, ARCHIVED                     |
| OVERRIDDEN         | EXPIRED, ARCHIVED                                 |
| EXPIRED            | ARCHIVED                                          |
| FAILED             | ARCHIVED                                          |
| ARCHIVED           | *(terminal — no transitions)*                     |

---

## State Groups

| Group             | States                                              |
|-------------------|-----------------------------------------------------|
| ACTIVE_STATES     | PENDING_EVALUATION, EVALUATING                      |
| PASS_STATES       | PASSED, WARNING, OVERRIDDEN                         |
| BLOCKING_STATES   | BLOCKED                                             |
| OUTCOME_STATES    | PASSED, WARNING, BLOCKED, OVERRIDDEN                |
| ENDED_STATES      | EXPIRED, FAILED, ARCHIVED                           |
| TERMINAL_STATES   | ARCHIVED                                            |
