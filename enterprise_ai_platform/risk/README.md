# enterprise_ai_platform.risk

> **Status:** PLACEHOLDER -- Foundation certified. Wave 5 pending.

## Purpose
Layers 6-9: CapitalRiskEngine, RiskControl (PortfolioAllocation, StressTest), MarketSimulation, RiskGuardian (kill switch VIX=45, loss=2%)

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | LAYERS-6-9 |
| Wave | 5 |
| Owner | Platform |
| Architecture Reference | IIOS-ARC-001 Layers 6-9 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-ARC-001 Layers 6-9**.

## Dependencies

- `enterprise_ai_platform.core`
- `enterprise_ai_platform.infrastructure`
- `enterprise_ai_platform.market`
- `enterprise_ai_platform.models`
- `enterprise_ai_platform.portfolio`

## Planned Submodules

- `enterprise_ai_platform.risk.capital_risk_engine`
- `enterprise_ai_platform.risk.position_sizer`
- `enterprise_ai_platform.risk.risk_manager_ai`
- `enterprise_ai_platform.risk.portfolio_allocation`
- `enterprise_ai_platform.risk.stress_tester`
- `enterprise_ai_platform.risk.risk_guardian`
- `enterprise_ai_platform.risk.kill_switch`
- `enterprise_ai_platform.risk.vix_monitor`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
