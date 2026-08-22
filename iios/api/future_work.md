# Future Work: iios.api

## Status
PLACEHOLDER -- Wave 18 pending.

## Architecture Reference
**IIOS-IMP-001 Wave 18**

## Wave
Wave **18** -- IMPLEMENTATION_MASTER_PLAN.md (IIOS-IMP-001)

## Planned Submodules
### `rest_api`
_See 

### `websocket_api`
_See 

### `api_auth`
_See 

### `api_schemas`
_See 

### `api_handlers`
_See 

### `rate_limiter`
_See 

## Engineering Rules
- Foundation Constitution 90 rules (IIOS-FCR-001 Part VIII).
- All constants from ``config.py`` only.
- Layer hierarchy enforced (no upward imports).
- Services registered with DI Container.
- Coverage >= 95% before wave PR merge.

## Certification
FOUNDATION_CERTIFICATION.md Part V + IIOS-CIS-001 Part X.
