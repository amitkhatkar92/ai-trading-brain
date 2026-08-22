# Investment Intelligence Operating System (IIOS)

> **Status:** Foundation Certified — Wave 1 Implementation Ready  
> **Foundation:** IIOS-FCR-001 | **Architecture:** IIOS-ARC-001  
> **Version:** 0.1.0 | **Python:** 3.12+

A 17-layer hierarchical multi-agent trading system for NSE/BSE algorithmic trading.

---

## Quick Start

```bash
# 1. Clone and enter the repository
git clone https://github.com/your-org/iios.git
cd iios

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env.development
# Edit .env.development with your API keys

# 5. Verify bootstrap
python bootstrap.py

# 6. Run in paper trading mode
python main.py --paper
```

---

## Architecture Overview

IIOS operates as a **17-layer pipeline** that runs every trading cycle:

```
Layer 1   GlobalIntelligence     Overnight global context (S&P, Nikkei, bonds, FX)
Layer 2   MarketIntelligence     NIFTY/BANKNIFTY regime, sector, liquidity
Layer 3   MetaLearning           k-NN strategy weight predictor
Layer 4   OpportunityEngine      Equity scanner, options, arbitrage
Layer 5   StrategyLab            MetaStrategyController, backtesting, evolution
Layer 6   CapitalRiskEngine      Position sizing per strategy budget
Layer 7   RiskControl            RiskManagerAI, PortfolioAllocation, StressTest
Layer 8   MarketSimulation       Monte Carlo, 14 scenarios
Layer 9   RiskGuardian           Kill switch (VIX>45, daily loss>2%)
Layer 10  DebateAndDecision      5-agent debate, DecisionEngine (threshold 6.5)
Layer 11  ExecutionEngine        OrderManager → Dhan broker (paper/live)
Layer 12  TradeMonitoring        TradeMonitor, StrategyHealthMonitor
Layer 13  LearningSystem         LearningEngine, StrategyPerformanceTracker
Layer 14  PerformanceAnalytics   DrawdownAnalyzer, WalkForwardTester
Layer 15  ResearchLab            Promotion gates: WinRate≥50%, Sharpe>0.8, MaxDD<15%
Layer 16  ValidationEngine       6-stage validation pipeline
Layer 17  ControlTower           SQLite telemetry, Streamlit dashboard, EventBus
```

**Full cycle baseline:** 172ms | **SLA:** 200ms | **Mode:** Paper trading

---

## Repository Structure

```
iios/                          Python package root
├── core/                      Base classes, types, enums (Wave 1)
├── config/                    Configuration management (Wave 2)
├── bootstrap/                 System startup (Wave 2)
├── infrastructure/            46 infrastructure services (Wave 2)
│   ├── configuration/         Config, Env, DI Container
│   ├── lifecycle/             Service Registry, Lifecycle Manager
│   ├── observability/         Health, Metrics, Logging, Audit
│   ├── infra_security/        Auth, Secrets, Encryption
│   ├── platform/              Clock, Scheduler, UUID, File
│   ├── communication/         EventBus, Notification, Cache, Storage
│   └── operations/            Recovery, Retry, CircuitBreaker
├── knowledge/                 Knowledge base + 5 ontology packages
├── reasoning/                 Layers 1-3
├── market/                    Layer 2 market intelligence
├── risk/                      Layers 6-9
├── decisions/                 Layer 10 debate + decision
├── execution/                 Layers 11-12
├── learning/                  Layers 13-14
├── research/                  Layer 15 research lab
├── simulation/                Layer 8 Monte Carlo
├── monitoring/                Layer 17 ControlTower
├── dashboard/                 Streamlit dashboard
├── cli/                       Telegram bot + 13 commands
├── agents/                    All ~62 AI agents
├── models/                    ML models, strategies
├── integrations/              Dhan broker, Yahoo Finance
└── ...                        (see iios/ for complete list)

tests/
├── unit/                      Unit tests (>= 95% coverage required)
├── integration/               Multi-layer integration tests
├── performance/               Latency SLA benchmarks
└── security/                  OWASP compliance tests

data/                          Runtime data (persistent, do not delete)
├── iios.db                    SQLite main database
└── paper_trades.csv           Paper trade journal

docs/                          Engineering specifications
scripts/                       Operational scripts
```

---

## Development Commands

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=iios --cov-report=html

# Type checking
mypy iios/

# Linting
ruff check iios/ tests/
black --check iios/ tests/

# Security scan
bandit -r iios/
detect-secrets scan

# Bootstrap verification
python bootstrap.py
```

---

## Running IIOS

```bash
# Paper trading mode (recommended during development)
python main.py --paper

# With Telegram bot
python main.py --paper --telegram

# System status
python main.py --status

# Development mode (auto-reload, debug logging)
python dev.py

# Health check
python healthcheck.py
```

---

## Telegram Commands

Once running with `--telegram`, the following operator commands are available:

| Command | Description |
|---------|-------------|
| `/health` | System health status |
| `/pnl` | Today's P&L |
| `/perf` | Strategy performance |
| `/signals` | Current signals |
| `/positions` | Open positions |
| `/strategies` | Active strategies |
| `/learn` | Learning system status |
| `/diag` | Diagnostic report |
| `/mode` | Current operational mode |
| `/safe` | Activate safe mode |
| `/resume` | Resume from safe mode |
| `/status` | Full system status |
| `/help` | Command list |

---

## Critical Architecture Invariants

These values are **immutable** — never change them without Architecture Council approval:

| Constant | Value | Location |
|----------|-------|----------|
| `DECISION_THRESHOLD` | 6.5 | `config.py` |
| `VIX_THRESHOLD` | 45.0 | `config.py` |
| `DAILY_LOSS_PCT` | 0.02 | `config.py` |
| Debate agents | exactly 5 | Component Registry |
| Singletons | 4 (via factory functions) | DI Container |

---

## Deployment

```powershell
# Standard VPS deployment
git add <files>
git commit -m "<message>"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

Deployment is complete **only** when both containers show `Up … (healthy)`.

---

## Foundation Documents

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 17-layer architecture specification |
| [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) | 20-wave development plan |
| [SYSTEM_BOOTSTRAP_SPECIFICATION.md](SYSTEM_BOOTSTRAP_SPECIFICATION.md) | 45-stage startup sequence |
| [CORE_REPOSITORY_CONSTRUCTION_SPECIFICATION.md](CORE_REPOSITORY_CONSTRUCTION_SPECIFICATION.md) | Repository structure spec |
| [CORE_INFRASTRUCTURE_SPECIFICATION.md](CORE_INFRASTRUCTURE_SPECIFICATION.md) | 46 infrastructure services |
| [FOUNDATION_CERTIFICATION.md](FOUNDATION_CERTIFICATION.md) | Foundation certification |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Developer guide |

---

## License

MIT — see [LICENSE](LICENSE)

> **Risk Disclaimer:** Algorithmic trading involves significant financial risk. Always run in
> paper trading mode and satisfy all SYSTEM_CERTIFIED criteria before live trading.
