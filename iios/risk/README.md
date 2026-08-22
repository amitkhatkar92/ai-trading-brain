# iios.risk

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

- `iios.core`
- `iios.infrastructure`
- `iios.market`
- `iios.models`
- `iios.portfolio`

## Planned Submodules

- `iios.risk.capital_risk_engine`
- `iios.risk.position_sizer`
- `iios.risk.risk_manager_ai`
- `iios.risk.portfolio_allocation`
- `iios.risk.stress_tester`
- `iios.risk.risk_guardian`
- `iios.risk.kill_switch`
- `iios.risk.vix_monitor`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
