# Knowledge Lifecycle Guide

## Overview

The Knowledge Lifecycle subsystem (`iios.knowledge.lifecycle`) tracks the
full institutional lifecycle of a knowledge artifact — from the moment it is
submitted to the platform through publication and eventual archival.

## Lifecycle States

| State | Meaning |
|---|---|
| `CREATED` | Session instantiated; no processing started |
| `INITIALIZING` | Session is being set up |
| `COLLECTING` | Raw knowledge data is being gathered |
| `VALIDATING` | Content is being validated for correctness |
| `READY` | Validated; ready for capture |
| `CAPTURING` | Knowledge is being captured / extracted |
| `INDEXING_PENDING` | Capture complete; awaiting index pipeline |
| `PUBLISHED` | Knowledge is live and accessible |
| `PAUSED` | Processing temporarily suspended |
| `RESUMING` | Transitioning back from PAUSED |
| `COMPLETED` | Successfully completed; no longer active |
| `FAILED` | An error occurred; captured in `failure_reason` |
| `ARCHIVED` | Terminal state; immutable |

## Happy-Path Flow

```
CREATED → INITIALIZING → COLLECTING → VALIDATING → READY
        → CAPTURING → INDEXING_PENDING → PUBLISHED
        → COMPLETED → ARCHIVED
```

## Pause / Resume Flow

```
READY | PUBLISHED → PAUSED → RESUMING → CAPTURING | READY
```

## Failure Flow

```
any non-terminal state → FAILED → ARCHIVED
```

## Statistics

The subsystem tracks 6 statistics counters:

| Counter | Description |
|---|---|
| `knowledge_sessions_created` | Total sessions created |
| `knowledge_sessions_completed` | Sessions that reached COMPLETED |
| `knowledge_sessions_failed` | Sessions that entered FAILED |
| `knowledge_sessions_archived` | Sessions that have been archived |
| `transition_count` | Total state transitions recorded |
| `average_session_duration_seconds` | Mean duration for archived sessions |

## Events

10 domain events are emitted:

| Event | Trigger |
|---|---|
| `knowledge.created` | Session created |
| `knowledge.initialized` | Entered INITIALIZING |
| `knowledge.validated` | Entered READY (post-validation) |
| `knowledge.capture_started` | Entered CAPTURING |
| `knowledge.published` | Entered PUBLISHED |
| `knowledge.paused` | Entered PAUSED |
| `knowledge.resumed` | Entered RESUMING |
| `knowledge.completed` | Entered COMPLETED |
| `knowledge.failed` | Entered FAILED |
| `knowledge.archived` | Entered ARCHIVED |
