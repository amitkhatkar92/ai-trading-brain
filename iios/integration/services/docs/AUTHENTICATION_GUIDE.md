# Authentication Guide

## Supported Authentication Methods

| AuthScheme | Key Field | Description |
|---|---|---|
| `NONE` | — | No authentication |
| `API_KEY` | `api_key` | API key in header or query |
| `BEARER_TOKEN` | `token` | Bearer token (JWT/OAuth) |
| `BASIC` | `username` + `password` | HTTP Basic auth |
| `OAUTH2` | `client_id` + `client_secret` | OAuth 2.0 client credentials |
| `MTLS` | `certificate` + `private_key` | Mutual TLS |
| `SAML` | `assertion` | SAML 2.0 assertion |
| `CUSTOM` | `credential` | Custom auth credential |

## Authentication Engine

```python
from iios.integration.services import AuthenticationEngine, AuthScheme

auth = AuthenticationEngine()
result = auth.authenticate(
    scheme      = AuthScheme.API_KEY,
    credentials = {"api_key": "my-secret-key", "client_id": "my-app"},
)
if result.success:
    print(f"Token: {result.token.token_id}")
```

## Credential Provider

Store credentials securely (never logs secrets):

```python
from iios.integration.services import CredentialProvider, AuthScheme

provider = CredentialProvider()
cred_id = provider.store(
    scheme      = AuthScheme.API_KEY,
    principal   = "my-connector",
    credentials = {"api_key": "my-secret"},
)
entry = provider.retrieve(cred_id)
```

## Secret Manager

Versioned secrets with rotation support:

```python
from iios.integration.services import SecretManager

secrets = SecretManager()
v1 = secrets.set_secret("db-password", "old-password")
v2 = secrets.rotate_secret("db-password", "new-password")
current = secrets.get_secret("db-password")  # returns "new-password"
```

## Certificate Manager

mTLS certificate registration:

```python
from iios.integration.services import CertificateManager

certs = CertificateManager()
entry = certs.register(
    common_name = "my-service.example.com",
    certificate = "-----BEGIN CERTIFICATE-----...",
    private_key = "-----BEGIN PRIVATE KEY-----...",
    issuer      = "My CA",
)
```
