# Transition Guide — C15 M1 Integration Lifecycle

Each `IntegrationLifecycle` method corresponds to one named transition.
All transitions are validated against `VALID_TRANSITIONS` before execution.

---

## Transition Methods

### `create_session(workflow_id, *, metadata, session_id) → IntegrationSession`

Creates a new session in **CREATED** state.  Registers it in the registry and
emits `INTEGRATION_CREATED`.

---

### `initialize(session_id, *, actor, reason) → IntegrationTransition`

`CREATED → INITIALIZING`

Call after `create_session`.  Signals the session is beginning its setup sequence.

---

### `discover(session_id, *, actor, reason) → IntegrationTransition`

`INITIALIZING → DISCOVERING`

Signals that capability/endpoint discovery is in progress.

---

### `configure(session_id, *, actor, reason) → IntegrationTransition`

`DISCOVERING → CONFIGURING`

Signals that configuration is being applied.

---

### `validate_session(session_id, *, actor, reason) → IntegrationTransition`

`CONFIGURING → VALIDATING`

Signals that pre-connect validation is running.

---

### `mark_ready(session_id, *, actor, reason) → IntegrationTransition`

`VALIDATING → READY`

Signals that the session passed all validation checks and is ready to connect.

---

### `connect(session_id, *, actor, reason) → IntegrationTransition`

`READY → CONNECTING`

Signals that a connection attempt is in progress.

---

### `activate(session_id, *, actor, reason) → IntegrationTransition`

`CONNECTING → ACTIVE`

Signals that the session is now fully connected and operational.

---

### `pause(session_id, *, actor, reason) → IntegrationTransition`

`ACTIVE → PAUSED`

Signals that the session has been suspended (e.g. rate limit, maintenance).

---

### `resume(session_id, *, actor, reason) → IntegrationTransition`

`PAUSED → RESUMING`

Signals that a resume is in progress.

---

### `mark_resumed(session_id, *, actor, reason) → IntegrationTransition`

`RESUMING → ACTIVE`

Signals that the session has fully resumed to ACTIVE state.

---

### `complete(session_id, *, actor, reason) → IntegrationTransition`

`ACTIVE → COMPLETED`

Signals that the session has finished its work successfully.

---

### `fail(session_id, *, actor, reason) → IntegrationTransition`

`(any active state) → FAILED`

Signals that an unrecoverable error occurred.  FAILED sessions may be retried or archived.

---

### `retry(session_id, *, actor, reason) → IntegrationTransition`

`FAILED → INITIALIZING`

Re-enters the lifecycle from INITIALIZING.  Valid only from FAILED.

---

### `archive(session_id, *, actor, reason) → IntegrationTransition`

`COMPLETED | FAILED | READY | PAUSED → ARCHIVED`

Finalises and seals the session.  No further transitions are possible.

---

## Invalid Transition Behaviour

If a transition is not in `VALID_TRANSITIONS`, `session.transition_to()` raises
`IntegrationInvalidTransitionError` (ILC-002).

If the session is already ARCHIVED, it raises `IntegrationSessionTerminatedError` (ILC-003).
