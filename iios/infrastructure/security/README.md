# IIOS Security Framework

The Security Framework is the mandatory security infrastructure layer for every IIOS module. It provides authentication, authorisation, encryption, secrets management, integrity verification, and audit logging under a single façade.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Quick Start](#quick-start)
3. [Authentication Guide](#authentication-guide)
4. [Authorization Guide](#authorization-guide)
5. [Encryption Guide](#encryption-guide)
6. [Secrets Management Guide](#secrets-management-guide)
7. [Integrity & Tamper Detection](#integrity--tamper-detection)
8. [Audit Logging](#audit-logging)
9. [Developer Guide](#developer-guide)
10. [Module Index](#module-index)

---

## Architecture

```
iios/infrastructure/security/
│
├── Core
│   ├── security_constants.py     ← All enums, numeric and string constants
│   ├── security_exceptions.py    ← Full exception hierarchy
│   ├── security_models.py        ← Dataclass models (records, results, events)
│   └── security_context.py       ← Thread-local security context (principal, session)
│
├── Identity
│   ├── principal.py              ← Abstract Principal, AnonymousPrincipal
│   ├── user_identity.py          ← UserIdentity (human users)
│   ├── service_identity.py       ← ServiceIdentity (microservices, agents)
│   ├── system_identity.py        ← SystemIdentity singleton (all-permit)
│   ├── identity_provider.py      ← IdentityProvider ABC + InMemoryIdentityProvider
│   └── identity_manager.py       ← Registry of all principals
│
├── Authentication
│   ├── credential_manager.py     ← Password hashing, API key generation
│   ├── session_manager.py        ← Session lifecycle, TTL, idle timeout
│   ├── token_manager_new.py      ← HMAC-SHA256 signed tokens (JWT-like)
│   ├── authentication_provider.py← Password / API key / token / system providers
│   └── authentication_manager.py ← Orchestrates all providers + lockout policy
│
├── Authorisation
│   ├── permission_manager.py     ← Permission registry with fnmatch wildcard matching
│   ├── role_manager.py           ← Role hierarchy with permission inheritance
│   ├── policy_manager.py         ← ABAC policy evaluation (DENY overrides ALLOW)
│   ├── access_controller.py      ← RBAC + ABAC decision engine
│   └── authorization_manager.py  ← High-level façade (grant/revoke roles, check/require)
│
├── Encryption
│   ├── crypto_provider.py        ← CryptoProvider ABC; Fernet + stdlib implementations
│   ├── key_manager.py            ← Symmetric key lifecycle (generate, rotate, revoke)
│   ├── certificate_manager.py    ← X.509 certificate store (self-signed, PEM import)
│   └── encryption_manager.py     ← Encrypt/decrypt, hash, sign, verify, API keys
│
├── Secrets
│   ├── secret_store.py           ← Encrypted in-memory versioned store
│   ├── vault_provider.py         ← VaultProvider ABC; InMemory + Environment backends
│   └── secret_manager.py         ← Unified secret lifecycle with vault fallback
│
├── Integrity & Audit
│   ├── tamper_detector.py        ← HMAC-SHA256 tamper detection
│   ├── audit_recorder.py         ← Tamper-evident audit ring buffer
│   ├── audit_manager.py          ← High-level audit event helpers
│   └── integrity_manager.py      ← Checksums, file hashes, signed payloads
│
├── Registry & Façade
│   ├── security_registry.py      ← Central component registry (lazy resolution)
│   └── security_manager.py       ← Master façade — single entry point
│
└── __init__.py                   ← All public symbols exported
```

### Decision flow (authorisation)

```
check(principal_id, action, resource)
    │
    ├─ Is SystemIdentity? → PERMIT immediately
    │
    ├─ RBAC: does any role have permission?
    │   ├─ YES → PERMIT (unless policy DENY overrides)
    │   └─ NO  → continue to ABAC
    │
    ├─ ABAC: evaluate attached policies
    │   ├─ DENY statement matched → DENY
    │   ├─ ALLOW statement matched → PERMIT
    │   └─ NOT_APPLICABLE → use deny_by_default flag
    │
    └─ DENY (deny_by_default=True, the production default)
```

---

## Quick Start

```python
from iios.infrastructure.security import get_security_manager

sec = get_security_manager()

# 1. Create a user
user = sec.create_user("alice", email="alice@example.com", roles=["trader"])
sec.set_password(user.principal_id, "SecurePass123!")

# 2. Authenticate
result = sec.login(user.principal_id, password="SecurePass123!")
assert result.is_success

# 3. Authorise
sec.grant_role(user.principal_id, "trader")
assert sec.is_permitted(user.principal_id, "trade:execute", "RELIANCE")

# 4. Encrypt secrets
ct = sec.encrypt(b"broker_api_key_value")
pt = sec.decrypt(ct)

# 5. Manage secrets
sec.set_secret("broker/dhan/api_key", b"sk-abc123")
key = sec.get_secret("broker/dhan/api_key")

# 6. Issue tokens
token_str = sec.issue_token(user.principal_id)
claims = sec.validate_token(token_str)   # raises if invalid/expired
```

---

## Authentication Guide

### Password authentication

```python
from iios.infrastructure.security import (
    get_credential_manager, get_authentication_manager,
)

cm = get_credential_manager()
am = get_authentication_manager()

# Register credentials
cm.set_password("user:alice", "StrongPassword123!")

# Authenticate (returns AuthResult)
result = am.authenticate(
    {"principal_id": "user:alice", "password": "StrongPassword123!"},
    issue_session=True,
    issue_token=True,
    ip_address="192.168.1.1",
)

if result.is_success:
    session_id = result.session_id   # Optional[str]
    token = result.token             # Optional[str] signed token
```

### API key authentication

```python
raw_key = cm.generate_api_key("service:bot")
# Store raw_key somewhere safe — it won't be retrievable again.

result = am.authenticate({"api_key": raw_key})
```

### Token authentication

```python
from iios.infrastructure.security import get_token_manager

tm = get_token_manager()
token_str = tm.issue("user:alice", scopes=["trade:read"])

# Later:
claims = tm.validate_raw(token_str)   # raises TokenError if invalid
tm.revoke(claims["jti"])              # explicit revocation
```

### Session management

```python
from iios.infrastructure.security import get_session_manager

sm = get_session_manager()
session = sm.create("user:alice", metadata={"ip": "127.0.0.1"})

# Touch to extend TTL on activity
sm.touch(session.session_id)

# Read/write session data
sm.set_data(session.session_id, "last_trade", "RELIANCE")
val = sm.get_data(session.session_id, "last_trade")

# Terminate
sm.terminate(session.session_id)
```

### Lockout policy

After `MAX_LOGIN_ATTEMPTS` (default 5) consecutive failures, the principal is locked for `LOCKOUT_DURATION_SECONDS` (default 900 s = 15 min). Lockout is enforced automatically by `AuthenticationManager`.

---

## Authorization Guide

### RBAC (role-based)

```python
from iios.infrastructure.security import get_authorization_manager

am = get_authorization_manager()

# Grant / revoke roles
am.grant_role("user:alice", "trader")
am.revoke_role("user:alice", "viewer")

# Check
result = am.check("user:alice", "trade:execute", "NIFTY")
# result.decision → AccessDecision.PERMIT | DENY | NOT_APPLICABLE

# Require (raises AccessDeniedError on DENY)
am.require("user:alice", "trade:execute", "NIFTY")

# Convenience
am.is_permitted("user:alice", "trade:execute", "NIFTY")  # bool
```

### Built-in roles

| Role | Permissions |
|---|---|
| `super_admin` | `*` (all) |
| `admin` | `iios:admin`, `iios:read`, `iios:write`, `audit:read` |
| `trader` | `trade:execute`, `trade:read`, `risk:read`, `portfolio:*`, `orders:*` |
| `viewer` | `iios:read`, `trade:read`, `risk:read` |
| `risk_manager` | `risk:read`, `risk:override`, `trade:read`, `portfolio:*` |
| `service` | `iios:read`, `iios:write`, `trade:read`, `orders:*` |

### ABAC (attribute-based policies)

```python
from iios.infrastructure.security import get_authorization_manager
from iios.infrastructure.security.security_models import PolicyStatement
from iios.infrastructure.security.security_constants import PolicyEffect

am = get_authorization_manager()

# Inline allow policy
am.create_allow_policy(
    name="allow_trade_read",
    actions=["trade:read", "portfolio:*"],
    resources=["*"],
)
am.attach_policy("user:alice", "allow_trade_read")

# Policy with conditions (ABAC)
from iios.infrastructure.security import get_policy_manager
from iios.infrastructure.security.security_models import PolicyRecord

pm = get_policy_manager()
policy = PolicyRecord(
    name="time_restricted_trade",
    statements=[
        PolicyStatement(
            effect=PolicyEffect.ALLOW,
            actions=["trade:execute"],
            resources=["*"],
            conditions={"environment.market_open": {"eq": True}},
        )
    ],
)
pm.register(policy)
pm.attach("user:alice", "time_restricted_trade")

# Evaluate with context
req = AccessRequest(
    principal_id="user:alice",
    action="trade:execute",
    resource="RELIANCE",
    environment={"market_open": True},
)
result = pm.evaluate(req)
```

---

## Encryption Guide

### Symmetric encryption

```python
from iios.infrastructure.security import get_encryption_manager

em = get_encryption_manager()

# Bytes
ct = em.encrypt(b"sensitive data")
pt = em.decrypt(ct)   # → b"sensitive data"

# Text
ct_str = em.encrypt_text("hello world")
pt_str = em.decrypt_text(ct_str)

# Named key (for isolation between subsystems)
ct = em.encrypt(b"trade data", key_name="trade_keys")
pt = em.decrypt(ct, key_name="trade_keys")
```

Ciphertext format: `[1 byte: len(key_id)][key_id bytes][ciphertext]` — key ID is embedded so decryption always uses the correct key after rotation.

### Key rotation

```python
from iios.infrastructure.security import get_key_manager

km = get_key_manager()

# Generate
key_id, raw = km.generate("my_key")

# Check if rotation is needed
if km.needs_rotation("my_key"):
    new_id, new_raw = km.rotate("my_key")

# Revoke compromised key
km.revoke(key_id)
```

### Signing and verification

```python
sp = em.create_signed_payload(b"important data")
# sp.payload, sp.signature, sp.algorithm, sp.key_id, sp.signed_at

valid = em.verify_signed_payload(sp)   # True / False
```

### Hashing

```python
from iios.infrastructure.security.security_constants import HashAlgorithm

h = em.hash(b"data", HashAlgorithm.SHA256)   # hex string
h = em.hash_text("data", HashAlgorithm.SHA256)
```

### Password hashing

```python
hashed = em.hash_password("my_password")
em.verify_password("my_password", hashed)    # bool
```

---

## Secrets Management Guide

### Set and retrieve secrets

```python
from iios.infrastructure.security import get_secret_manager

sm = get_secret_manager()

# Store (encrypted at rest)
sm.set("broker/dhan/api_key", b"sk-abc123")
sm.set_api_key("broker/dhan/api_key", b"sk-abc123")   # convenience

# Retrieve
value: bytes = sm.get("broker/dhan/api_key")
value_str: str = sm.get_str("broker/dhan/api_key")
```

### Secret rotation

```python
sm.rotate("broker/dhan/api_key", b"sk-new456")
```

### Vault providers

```python
from iios.infrastructure.security import InMemoryVaultProvider, EnvironmentVaultProvider

sm = get_secret_manager()

# Fall through to environment variables when not in store
env_vault = EnvironmentVaultProvider()
sm.set_vault_provider(env_vault)

# env var IIOS_BROKER_DHAN_API_KEY → path "iios/broker/dhan/api_key"
value = sm.get("iios/broker/dhan/api_key")
```

---

## Integrity & Tamper Detection

```python
from iios.infrastructure.security import get_integrity_manager, get_tamper_detector

im = get_integrity_manager()
td = get_tamper_detector()

# Compute and store checksum
chk = im.checksum(b"critical data", "resource:trade:123")

# Later, verify (raises TamperDetectedError on mismatch)
im.verify_checksum(b"critical data", "resource:trade:123", chk.checksum)

# Sign a payload
signed = im.sign(b"payload")
im.verify_signature(signed)   # raises if invalid

# File integrity
file_hash = im.hash_file("/path/to/audit.log")
```

---

## Audit Logging

```python
from iios.infrastructure.security import get_audit_manager, AuditEventType

am = get_audit_manager()

# High-level helpers
am.login("user:alice", success=True, ip="192.168.1.1")
am.access_denied("user:bob", "trade:execute", "NIFTY")
am.secret_accessed("service:bot", "broker/dhan/api_key")
am.key_rotated("iios:system", "iios_default")
am.tamper_detected("resource:trade:123")

# Generic
am.record(
    event_type=AuditEventType.CUSTOM_EVENT,
    principal_id="user:alice",
    action="custom_action",
    resource="target",
    severity=AuditSeverity.WARNING,
    details={"reason": "demo"},
)

# Query
records = am.query(principal_id="user:alice", limit=50)
records = am.recent(100)

# Integrity verification of all stored records
passed, failed = am.verify_all()
```

All records are signed with HMAC-SHA256 on write. Any post-write modification will fail `verify_record()`.

---

## Developer Guide

### Singleton pattern

Every manager follows the same pattern:

```python
from iios.infrastructure.security import get_X_manager, reset_X_manager

mgr = get_X_manager()   # creates on first call, returns same object thereafter
reset_X_manager()       # destroys the singleton (use in tests only)
```

### Security context

```python
from iios.infrastructure.security import security_scope, system_scope, current_principal_id

# Set principal for a block of code (thread-local)
with security_scope("user:alice", session_id="ses:abc"):
    principal = current_principal_id()   # → "user:alice"

# Elevated system context
with system_scope():
    # current_principal_id() → "iios:system"
    pass
```

### Test isolation

In tests, reset all singletons in `setup_method`:

```python
def setup_method(self) -> None:
    from iios.infrastructure.security import (
        reset_identity_manager, reset_credential_manager,
        reset_session_manager, reset_token_manager,
        reset_authentication_manager, reset_security_manager,
        # ... etc
    )
    reset_identity_manager()
    reset_credential_manager()
    # ...
```

### Adding a custom identity provider

```python
from iios.infrastructure.security import IdentityProvider
from iios.infrastructure.security.principal import Principal
from typing import Optional

class DatabaseIdentityProvider(IdentityProvider):
    def find(self, principal_id: str) -> Optional[Principal]:
        # query your database
        ...
    def find_by_name(self, name: str) -> Optional[Principal]:
        ...
    def exists(self, principal_id: str) -> bool:
        ...
    def list_principals(self) -> list[Principal]:
        ...

# Register:
from iios.infrastructure.security import get_identity_manager
get_identity_manager().register_provider(DatabaseIdentityProvider())
```

### Adding a custom vault provider

```python
from iios.infrastructure.security import VaultProvider, get_secret_manager
from typing import Optional

class HashiCorpVaultProvider(VaultProvider):
    def read(self, path: str) -> Optional[bytes]: ...
    def write(self, path: str, value: bytes) -> None: ...
    def delete(self, path: str) -> bool: ...
    def exists(self, path: str) -> bool: ...
    def list_paths(self, prefix: str = "") -> list[str]: ...

get_secret_manager().set_vault_provider(HashiCorpVaultProvider())
```

---

## Module Index

| Module | Class | Singleton |
|---|---|---|
| `security_constants` | Enums + constants | — |
| `security_exceptions` | Exception hierarchy | — |
| `security_models` | Dataclass models | — |
| `security_context` | `SecurityContext` | `get_security_context()` |
| `principal` | `Principal`, `AnonymousPrincipal` | `ANONYMOUS` |
| `user_identity` | `UserIdentity` | — |
| `service_identity` | `ServiceIdentity` | — |
| `system_identity` | `SystemIdentity` | `get_system_identity()` |
| `identity_provider` | `IdentityProvider` | — |
| `identity_manager` | `IdentityManager` | `get_identity_manager()` |
| `credential_manager` | `CredentialManager` | `get_credential_manager()` |
| `session_manager` | `SessionManager` | `get_session_manager()` |
| `token_manager_new` | `SecurityTokenManager` | `get_token_manager()` |
| `authentication_provider` | `AuthenticationProvider` + 4 implementations | — |
| `authentication_manager` | `AuthenticationManager` | `get_authentication_manager()` |
| `permission_manager` | `PermissionManager` | `get_permission_manager()` |
| `role_manager` | `RoleManager` | `get_role_manager()` |
| `policy_manager` | `PolicyManager` | `get_policy_manager()` |
| `access_controller` | `AccessController` | `get_access_controller()` |
| `authorization_manager` | `AuthorizationManager` | `get_authorization_manager()` |
| `crypto_provider` | `CryptoProvider`, `FernetCryptoProvider` | `get_crypto_provider()` |
| `key_manager` | `KeyManager` | `get_key_manager()` |
| `certificate_manager` | `CertificateManager` | `get_certificate_manager()` |
| `encryption_manager` | `EncryptionManager` | `get_encryption_manager()` |
| `secret_store` | `SecretStore` | — |
| `vault_provider` | `VaultProvider`, `InMemoryVaultProvider`, `EnvironmentVaultProvider` | — |
| `secret_manager` | `SecretManager` | `get_secret_manager()` |
| `tamper_detector` | `TamperDetector` | `get_tamper_detector()` |
| `audit_recorder` | `AuditRecorder` | `get_audit_recorder()` |
| `audit_manager` | `AuditManager` | `get_audit_manager()` |
| `integrity_manager` | `IntegrityManager` | `get_integrity_manager()` |
| `security_registry` | `SecurityRegistry` | `get_security_registry()` |
| `security_manager` | `SecurityManager` | `get_security_manager()` |
