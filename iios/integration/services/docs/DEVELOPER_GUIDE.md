# Developer Guide

## Retry Strategies

```python
from iios.integration.services import RetryEngine, RetryConfig, RetryStrategy

engine = RetryEngine(RetryConfig(
    max_attempts = 5,
    strategy     = RetryStrategy.EXPONENTIAL_BACKOFF,
    delay_ms     = 200,
))

result = engine.execute(lambda: my_flaky_call())
if result.success:
    print(result.result)
else:
    print(f"Failed after {result.total_attempts} attempts: {result.error}")
```

## Failover

```python
from iios.integration.services import FailoverEngine

failover = FailoverEngine(failure_threshold=3)
failover.add_endpoint("primary",   "https://api1.example.com", priority=0)
failover.add_endpoint("secondary", "https://api2.example.com", priority=1)
failover.add_endpoint("tertiary",  "https://api3.example.com", priority=2)

result = failover.execute(lambda addr: call_api(addr))
print(f"Used: {result.endpoint_used}, attempts: {result.attempts}")
```

## Rate Limiting

```python
from iios.integration.services import RateLimitEngine, RateLimitConfig

limiter = RateLimitEngine()
limiter.configure("kafka", RateLimitConfig(rps=50, burst=20))

result = limiter.acquire("kafka")
if result.allowed:
    engine.execute(request)
```

## Timeout

```python
from iios.integration.services import TimeoutEngine

timeout_engine = TimeoutEngine(default_timeout_ms=5_000)
result = timeout_engine.execute(lambda: slow_call(), timeout_ms=2_000)
if result.timed_out:
    print("Call timed out!")
```

## Connection Pool

```python
from iios.integration.services import ConnectionPool

pool = ConnectionPool(pool_name="rest-pool", min_size=5, max_size=20)
slot = pool.acquire(timeout_ms=1_000)
try:
    # use slot.slot_id to track active connection
    ...
finally:
    pool.release(slot)

stats = pool.stats()
print(f"Available: {stats.available}, In Use: {stats.in_use}")
```

## Webhook

```python
from iios.integration.services import WebhookEngine

wh = WebhookEngine()
ep = wh.register(
    url    = "https://hooks.example.com/trading",
    secret = "my-signing-secret",
    topics = ["trade.executed", "position.closed"],
)
records = wh.dispatch("trade.executed", {"symbol": "NIFTY", "qty": 50})
print(f"Delivered to {len(records)} endpoints")
```

## Validation Report

```python
from iios.integration.services import IntegrationServicesValidator

validator = IntegrationServicesValidator()
report = validator.validate(request)
if not report.passed:
    for issue in report.errors:
        print(f"[{issue.check.value}] {issue.message}")
```

## Security Policy Notes

- Private keys and secrets are **never** logged. `CredentialEntry.safe_repr()` redacts them.
- `SecretManager` stores secrets in-memory only. Use Vault/AWS SM in production.
- `CertificateManager` stores certificates in-memory only. Use HSM in production.
- `AuthenticationEngine` validates credentials structurally. Wire to a real IdP in production.
