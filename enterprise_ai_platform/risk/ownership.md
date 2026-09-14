# Ownership: enterprise_ai_platform.risk

**Owner:** Platform

## Purpose
Layers 6-9: CapitalRiskEngine, RiskControl (PortfolioAllocation, StressTest), MarketSimulation, RiskGuardian (kill switch VIX=45, loss=2%)

## Architecture Reference
IIOS-ARC-001 Layers 6-9

## Layer
LAYERS-6-9

## Implementation Wave
Wave 5 per IIOS-IMP-001

## Outbound Dependencies
- `enterprise_ai_platform.core`
- `enterprise_ai_platform.infrastructure`
- `enterprise_ai_platform.market`
- `enterprise_ai_platform.models`
- `enterprise_ai_platform.portfolio`

## Inbound Dependencies
See IIOS-RCS-001 Dependency Matrix.

## Certification Level
PLACEHOLDER -- Wave 5 pending.

## Change Control
Architecture Council approval required for interface changes.
See FOUNDATION_CERTIFICATION.md Section 7.7.
