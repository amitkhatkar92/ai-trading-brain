# iios.execution

> **Status:** PLACEHOLDER -- Foundation certified. Wave 6 pending.

## Purpose
Layers 11-12: ExecutionEngine (OrderManager, paper trades at data/paper_trades.csv), TradeMonitoring, StrategyHealthMonitor

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | LAYERS-11-12 |
| Wave | 6 |
| Owner | Platform |
| Architecture Reference | IIOS-ARC-001 Layers 11-12 |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-ARC-001 Layers 11-12**.

## Dependencies

- `iios.core`
- `iios.infrastructure`
- `iios.decisions`
- `iios.integrations`
- `iios.portfolio`

## Planned Submodules

- `iios.execution.order_manager`
- `iios.execution.trade_monitor`
- `iios.execution.paper_trade_journal`
- `iios.execution.execution_engine`
- `iios.execution.trade_executor`
- `iios.execution.strategy_health_monitor`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
