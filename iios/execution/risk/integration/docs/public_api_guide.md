# Public API Reference — Execution Risk Integration

## `ExecutionRiskIntegrationManager`

Primary entry point.  Facade over `ExecutionRiskIntegrationEngine`.

```python
class ExecutionRiskIntegrationManager(LifecycleAwareMixin):
    def start() → None
    def stop()  → None

    @property
    def is_running() → bool

    # Rule management
    def register_rule(rule: Any)        → None
    def deregister_rule(rule_name: str) → None
    def registered_rules()              → List[str]

    # Evaluation
    def evaluate(request: ExecutionRiskRequest) → ExecutionRiskResponse
    def validate(request: ExecutionRiskRequest) → ValidationReport

    # Observability
    def health()     → SubsystemHealth
    def status()     → SubsystemStatus
    def statistics() → IntegrationStatistics
    def snapshot()   → ExecutionRiskIntegrationSnapshot
    def history(n: int = 50) → List[ExecutionRiskResponse]
    def query(**filters)     → List[ExecutionRiskResponse]
    def events()             → List[IntegrationEvent]

    # Convenience factory
    def create_context(execution_id, order_id, **kw) → ExecutionContext
    def create_request(context, **kw)                → ExecutionRiskRequest
```

## `IntegrationRequestFactory`

All static methods.  Preferred way to create requests.

```python
IntegrationRequestFactory.create_context(execution_id, order_id, **kw)
IntegrationRequestFactory.create_equity_context(execution_id, order_id, symbol, side, qty, price, **kw)
IntegrationRequestFactory.create_option_context(execution_id, order_id, symbol, side, qty, price, **kw)
IntegrationRequestFactory.create_request(context, **kw)
IntegrationRequestFactory.create_minimal_request(execution_id, order_id, **kw)
IntegrationRequestFactory.create_strict_request(context, **kw)
IntegrationRequestFactory.create_emergency_request(context, **kw)
```

## `ExecutionRiskRequest` (frozen dataclass)

Key fields: `request_id`, `execution_context`, `evaluation_mode`,
`timeout_ms`, `risk_category`, `requested_at`, `correlation_id`.

Properties: `execution_id`, `order_id`, `portfolio_id`, `strategy_id`,
`age_ms`, `is_expired`, `effective_correlation_id`.

## `ExecutionRiskResponse` (frozen dataclass)

Key fields: `response_id`, `request_id`, `execution_id`, `order_id`,
`approved`, `action`, `risk_state`, `snapshot`, `elapsed_ms`, `error_message`.

Properties: `is_blocked`, `is_error`, `is_emergency`, `was_overridden`, `has_warnings`.

Methods: `to_dict()`, `to_json()`.

## `ExecutionContext` (frozen dataclass)

Key fields: `execution_id`, `order_id`, `portfolio_id`, `strategy_id`,
`symbol`, `side`, `quantity`, `price`, `asset_class`, `correlation_id`,
`execution_snapshot`, `position_snapshot`, `risk_limits`, `metadata`.

Properties: `has_execution_snapshot`, `has_position_snapshot`, `has_risk_limits`, `age_ms`.

## `ValidationReport` (frozen dataclass)

Fields: `is_valid`, `errors` (Tuple), `warnings` (Tuple), `validated_at`.

`bool(report)` → True if valid.  `raise_if_invalid()` → raises `RequestValidationError`.

## Exceptions

| Exception | Code | When |
|---|---|---|
| `ExecutionRiskIntegrationError` | ERI-000 | Base |
| `IntegrationNotRunningError`    | ERI-001 | evaluate() before start() |
| `RequestValidationError`        | ERI-002 | validate_request_and_raise() |
| `EvaluationFailedError`         | ERI-003 | M2 failure propagated (unused internally) |
| `ComponentNotHealthyError`      | ERI-004 | require() on missing component |
| `IntegrationTimeoutError`       | ERI-005 | future timeout enforcement |
| `ComponentRegistrationError`    | ERI-006 | ComponentRegistry.require() |
| `ContextValidationError`        | ERI-007 | context-level validation |
| `IntegrationHistoryError`       | ERI-008 | history operation failure |
