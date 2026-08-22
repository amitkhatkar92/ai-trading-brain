# IIOS Developer Guide

> Foundation: IIOS-FCR-001 (CERTIFIED) | Architecture: IIOS-ARC-001

---

## Table of Contents

1. [Setup](#setup)
2. [Repository Structure](#repository-structure)
3. [Running IIOS](#running-iios)
4. [Testing](#testing)
5. [Code Quality](#code-quality)
6. [Architecture Invariants](#architecture-invariants)
7. [Wave Schedule Reference](#wave-schedule-reference)
8. [Contribution Workflow](#contribution-workflow)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## Setup

### Prerequisites

- Python 3.12 or later (`python --version`)
- Git
- A Dhan broker account (for live data; yfinance is the automatic fallback)
- Telegram account (optional, for bot operator commands)

### First-Time Setup

```powershell
# 1. Clone the repository
git clone https://github.com/your-org/iios.git
cd iios

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Install development dependencies
pip install -r requirements-dev.txt

# 5. Install IIOS package in editable mode
pip install -e .

# 6. Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# 7. Copy environment template
copy .env.example .env.development
# Edit .env.development with your Dhan API keys and Telegram credentials

# 8. Verify the bootstrap
python bootstrap.py
```

Expected output from `bootstrap.py`:
```
  [ OK ] PASS  python_version            3.12.x
  [ OK ] PASS  dependencies              8 core packages installed
  [ OK ] PASS  directory_structure       13 directories present
  [ OK ] PASS  iios_init_files           4 __init__.py files present
  [ OK ] PASS  config_module             PAPER_TRADING=True
  [ OK ] PASS  env_file                  Found: .env.development
  [ OK ] PASS  data_dir_writable         data/ is writable
  [ OK ] PASS  pyproject_toml            found
  STATUS:   READY — Wave 1 implementation can begin.
```

---

## Repository Structure

```
ai_trading_brain/
│
├── iios/                     Python package (44 sub-packages, see iios/__init__.py)
├── tests/                    Test suite (unit / integration / performance / security)
├── docs/                     Engineering specifications and runbooks
├── data/                     Runtime persistent data (SQLite, CSV journals)
├── logs/                     Runtime log files (gitignored)
├── scripts/                  Operational scripts (deployment, maintenance, analysis)
├── resources/                Static resources (symbol lists, templates, fixtures)
│
├── config.py                 System-wide constants — NEVER modify thresholds here
├── main.py                   Production orchestrator entry point
├── run.py                    Thin production wrapper (loads .env, delegates to main.py)
├── dev.py                    Development mode wrapper (forces DEBUG, paper trading)
├── healthcheck.py            Docker health check (exit 0=healthy, 1=unhealthy)
├── bootstrap.py              Pre-implementation readiness verification
│
├── pyproject.toml            Build system + tooling configuration
├── requirements.txt          Production dependencies
├── requirements-dev.txt      Development + test dependencies
├── .env.example              Environment template (committed, no real secrets)
├── .env.development          Local dev config (gitignored, fill in your values)
├── .env.testing              Test config (gitignored)
├── .env.production           Production template (gitignored, use Docker secrets)
├── .gitignore                Comprehensive Python + IIOS rules
├── .editorconfig             Editor configuration
├── .pre-commit-config.yaml   Pre-commit hook configuration
│
├── docker-compose.yml        Two-container deployment (ai-trading-brain, trading-dashboard)
├── Dockerfile                Container build definition
│
├── ARCHITECTURE.md           17-layer system architecture
├── README.md                 Project overview and quick start
├── LICENSE                   MIT license
└── DEVELOPMENT.md            This file
```

---

## Running IIOS

### Paper Trading Mode (Recommended)

Always run in paper trading mode during development:

```powershell
# Paper trading mode
python main.py --paper

# With Telegram bot operator commands
python main.py --paper --telegram

# Check system status without running a cycle
python main.py --status
```

### Development Mode

```powershell
# Forces IIOS_ENV=development, IIOS_PAPER_TRADING=true, IIOS_LOG_LEVEL=DEBUG
python dev.py
```

### Docker (matches VPS production)

```powershell
docker compose up
```

Both containers must reach `(healthy)`:
- `ai-trading-brain` — Python orchestrator
- `trading-dashboard` — Streamlit dashboard on port 8501

### Health Check

```powershell
python healthcheck.py
# Prints JSON status; exits 0=healthy, 1=unhealthy
```

---

## Testing

### Run All Tests

```powershell
pytest tests/ -v
```

### Run by Category

```powershell
pytest tests/unit/ -v -m unit
pytest tests/integration/ -v -m integration
pytest tests/performance/ -v -m performance
pytest tests/security/ -v -m security
```

### Run with Coverage

```powershell
pytest tests/ --cov=iios --cov-report=html --cov-report=term-missing
# Coverage report: htmlcov/index.html
# Minimum required: 95%
```

### Run a Single Test File

```powershell
pytest tests/unit/test_something.py -v
```

### Test Markers

| Marker | Description | Speed |
|--------|-------------|-------|
| `unit` | Isolated unit tests | Fast (< 100ms each) |
| `integration` | Multi-layer integration | Medium (< 5s each) |
| `performance` | Latency SLA benchmarks | Medium |
| `security` | OWASP compliance | Fast |
| `slow` | Tests > 5s | Slow |
| `requires_market` | Needs live market data | Skip in CI |

### Writing Tests

```python
import pytest

@pytest.mark.unit
def test_example() -> None:
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...

@pytest.mark.performance
def test_global_intelligence_sla(benchmark: Any) -> None:
    """GlobalIntelligence must complete within 17ms (cached)."""
    result = benchmark(lambda: GlobalDataAI.fetch())
    assert benchmark.stats.mean < 0.017  # 17ms SLA
```

---

## Code Quality

### Formatting

```powershell
# Format all Python files
black iios/ tests/
isort iios/ tests/

# Check without modifying
black --check iios/ tests/
isort --check iios/ tests/
```

### Linting

```powershell
ruff check iios/ tests/
flake8 iios/ tests/
```

### Type Checking

```powershell
mypy iios/
```

All iios/ code must be type-checked. `mypy --strict` is enforced.

### Security

```powershell
# Static analysis for security vulnerabilities
bandit -r iios/

# Check for secrets accidentally left in code
detect-secrets scan

# Check dependencies for known CVEs
pip-audit
```

### Pre-commit (Runs All Checks)

```powershell
# Run on all files
pre-commit run --all-files

# Run on staged files only (automatic on git commit)
pre-commit run
```

---

## Architecture Invariants

These are **immutable** constraints enforced by the Foundation Constitution (IIOS-FCR-001).
Violating any of them requires Architecture Council approval.

### Critical Constants (config.py — never change values)

```python
DECISION_THRESHOLD = 6.5     # FC-RULE-017 — Layer 10 DebateAndDecision
VIX_THRESHOLD      = 45.0    # FC-RULE-018 — Layer 9 RiskGuardian kill switch
DAILY_LOSS_PCT     = 0.02    # FC-RULE-018 — Daily loss limit (2%)
DEBATE_AGENTS      = 5       # FC-RULE-019 — Exactly 5 debate agents
LAYERS             = 17      # FC-RULE-001 — Pipeline layer count
```

### Latency SLA (system_monitor/system_monitor.py)

```python
LAYER_LATENCY_WARN_MS = 2_000    # Per-layer default warn threshold
LAYER_LATENCY_CRIT_MS = 5_000    # Per-layer default critical threshold (cycle abort)

# Override exceptions
LAYER_LATENCY_WARN_OVERRIDES = {"GlobalIntelligence": 5_000}
LAYER_LATENCY_CRIT_OVERRIDES = {"GlobalIntelligence": 12_000}
```

**Performance baseline (do not regress):**
- GlobalIntelligence: 17ms (cached + background pre-warm)
- MarketIntelligence: 19ms
- Full cycle: 172ms (SLA: 200ms)

### Protected Singletons

Access only via factory functions — never instantiate directly:

```python
from learning_system.strategy_performance_tracker import get_performance_tracker
from meta_learning.regime_strategy_map import get_regime_strategy_map
from notifications.telegram_bot import get_telegram_bot
from data_feeds.data_feed_manager import get_feed_manager
```

### Protected Modules (edit only with explicit Council approval)

| Module | Protection Reason |
|--------|-------------------|
| `risk_guardian/risk_guardian.py` | Kill-switch logic — wrong edit = live loss |
| `strategy_lab/backtesting_ai.py` | WFT/OOS quality gates calibrated |
| `validation_engine/` | 6-stage promotion pipeline |
| `strategy_lab/evolved_strategies/` | Earned through evolution runs |
| `data/` directory | Live SQLite databases + persisted state |
| `data_feeds/dhan_feed.py` | Broker auth + live order routing |

### Layer Ordering (do not reorder the 17-layer pipeline)

Layers execute sequentially: 1 → 17. Adding a layer requires Architecture Council approval
and a full regression test across the entire pipeline.

---

## Wave Schedule Reference

IIOS implementation follows a 20-wave schedule. Each wave unlocks the next.

| Wave | Focus | Key Deliverables |
|------|-------|-----------------|
| 1 | Core Foundation | `iios/core/` — types, enums, base classes, constants |
| 2 | Infrastructure | 46 services (Config, DI, Lifecycle, Observability, Security, Platform, Comms, Ops) |
| 3 | Knowledge Base | Market ontology, 5 ontology sub-packages |
| 4 | Intelligence Agents | Layers 1–3 (Global, Market, MetaLearning), ~62 agents scaffold |
| 5 | Opportunity & Risk | Layers 4–9 (OpportunityEngine → RiskGuardian) |
| 6 | Execution & Capital | Layers 11–12 (ExecutionEngine, TradeMonitoring) |
| 7 | Monitoring | Layer 17 (ControlTower, Streamlit dashboard) |
| 8 | Learning | Layers 13–14 (LearningSystem, PerformanceAnalytics) |
| 9 | Research | Layer 15 (ResearchLab, promotion gates) |
| 10 | Replay & Simulation | Layer 8 MC + full replay engine |
| 11–15 | Optimization | Walk-forward tests, sensitivity analysis, cross-market |
| 16–18 | API & Integration | REST/WebSocket API, external integrations |
| 19 | System Certification | SYSTEM_CERTIFIED criteria: WinRate≥50%, Sharpe>0.8, MaxDD<15% |
| 20 | Live Trading | Enable live trading (IIOS_ENABLE_LIVE_TRADING=true) |

---

## Contribution Workflow

### Branch Strategy

```
main          — protected, deployable, requires PR
feature/*     — new feature branches
fix/*         — bug fix branches
chore/*       — tooling, docs, config changes
```

### Making a Change

```powershell
# 1. Create a branch
git checkout -b feature/my-feature

# 2. Make changes (follow Architecture Invariants)
# 3. Run tests
pytest tests/ -v

# 4. Run pre-commit
pre-commit run --all-files

# 5. Commit (pre-commit hooks run automatically)
git add <files>
git commit -m "feat(wave1): add core type definitions"

# 6. Push and open PR
git push origin feature/my-feature
```

### Commit Message Format

```
<type>(<scope>): <description>

Types: feat, fix, perf, refactor, test, docs, chore, security
Scope: wave1, wave2, layer3, config, infra, risk, execution, ...

Examples:
  feat(wave1): add MarketRegime enum to iios/core/enums.py
  fix(layer9): correct VIX threshold comparison operator
  perf(layer1): add 5-min cache to GlobalDataAI.fetch()
  security(infra): rotate test credential placeholders
```

### Before Merging

All of the following must pass:
- [ ] `pytest tests/ --cov=iios` — coverage >= 95%
- [ ] `mypy iios/` — no type errors
- [ ] `ruff check iios/` — no lint errors
- [ ] `bandit -r iios/` — no high/critical security findings
- [ ] `pre-commit run --all-files` — all hooks pass
- [ ] Architecture invariants not violated (check constants, SLAs, singletons)

---

## Deployment

### Standard Deploy (after every code change)

```powershell
# 1. Commit
git add <files>
git commit -m "<type>(<scope>): <description>"

# 2. Push
git push origin main

# 3. Deploy to VPS
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

### Definition of Done

Deploy is complete **only** when both containers show `Up … (healthy)`:

```
ai-trading-brain          Up N seconds (healthy)
trading-dashboard         Up N seconds (healthy)
```

If unhealthy, diagnose before continuing:

```bash
docker logs ai-trading-brain --tail=50
docker logs trading-dashboard --tail=20
```

### VPS Info

- **Host:** `root@178.18.252.24`
- **SSH key:** `~/.ssh/trading_vps`
- **App directory:** `/root/ai-trading-brain`
- **Data volume:** `./data:/app/data` (persistent across restarts)

---

## Troubleshooting

### `iios` package not importable

```powershell
pip install -e .
```

### Missing dependencies

```powershell
pip install -r requirements.txt
# For dev:
pip install -r requirements-dev.txt
```

### Data API blocked (Dhan 451 error)

Expected during development. yfinance fallback activates automatically.
See `DHAN_DAILY_TOKEN_REQUIREMENT.md` for token refresh procedure.

### Pre-commit hook failures

```powershell
# Fix formatting automatically
black iios/ tests/
isort iios/ tests/
ruff check --fix iios/ tests/

# Then commit again
git add .
git commit -m "..."
```

### `detect-secrets` blocking commit

A secret was detected. Either:
1. Remove the secret from the code
2. If it's a false positive: `detect-secrets scan --baseline .secrets.baseline`

### Port 8501 already in use

```powershell
# Find and kill the process using port 8501
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

### Docker health check failing

```powershell
python healthcheck.py    # Run locally to see JSON status
```

Common causes:
- `data/` directory not writable — check volume mount permissions
- SQLite corruption — check with `PRAGMA integrity_check` directly
- `logs/` directory missing — created automatically on first run

---

*For architecture questions, see [ARCHITECTURE.md](ARCHITECTURE.md).*  
*For Foundation Certification details, see [FOUNDATION_CERTIFICATION.md](FOUNDATION_CERTIFICATION.md).*
