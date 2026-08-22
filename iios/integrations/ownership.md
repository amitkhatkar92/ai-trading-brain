# Ownership: iios.integrations

**Owner:** Platform

## Purpose
External integrations -- Dhan broker (data API + orders, 451 fallback), Yahoo Finance fallback, GLOBAL_SYMBOL_MAP

## Architecture Reference
IIOS-ARC-001 Layer 11, IIOS-RCS-001

## Layer
INTEGRATIONS

## Implementation Wave
Wave 2 per IIOS-IMP-001

## Outbound Dependencies
- `iios.core`
- `iios.infrastructure.communication`
- `iios.security`
- `iios.config`

## Inbound Dependencies
See IIOS-RCS-001 Dependency Matrix.

## Certification Level
PLACEHOLDER -- Wave 2 pending.

## Change Control
Architecture Council approval required for interface changes.
See FOUNDATION_CERTIFICATION.md Section 7.7.
