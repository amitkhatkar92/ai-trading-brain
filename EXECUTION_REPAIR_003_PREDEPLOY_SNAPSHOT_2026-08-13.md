# EXECUTION_REPAIR_003 — Pre-Deployment Snapshot
**Date:** 2026-08-13  
**Phase:** 1 — Pre-Deployment Snapshot  
**Purpose:** Baseline state before deploying EB001/EB002/ETF-ARB fixes

---

## 1. Local Git State

| Item | Value |
|---|---|
| HEAD commit | `d082deb` |
| Commit message | `MOP-RC-001: Add implementation report and update instructions log` |
| Branch | `main` |
| Remote tracking | `origin/main` — in sync |

### Relevant Modified Files (production execution repair)
```
 M execution_engine/order_manager.py     (+20/-3)   EB001+EB002 fix
 M opportunity_engine/arbitrage_ai.py   (+7/-0)    ETF-ARB safety guard
```

### Unrelated Modified Files (not included in deployment commit)
```
 M .env.example                          — example template, no runtime impact
 M .gitignore                            — no runtime impact
 M requirements.txt                      — cosmetic reformatting only, same packages
 M scripts/setup_github_secret.ps1       — setup utility, not in live execution path
 M simulation_replay/replay_engine.py    — replay tool, not in 17-layer live path
 M simulation_replay/run_replay.py       — replay tool, not in 17-layer live path
```

**Assessment:** unrelated files do not affect production execution.  
**Deployment rule observed:** only the 2 repair files + test artifacts committed.

---

## 2. VPS Git State

| Item | Value |
|---|---|
| VPS HEAD commit | `d082deb` |
| Commit message | `MOP-RC-001: Add implementation report and update instructions log` |
| Local / VPS match | YES — identical |

---

## 3. Container State (VPS)

| Container | Status |
|---|---|
| `ai-trading-brain` | Up ~1 hour (healthy) |
| `trading-dashboard` | Up ~1 hour (healthy) |

---

## 4. Environment Configuration

| Parameter | Local | VPS |
|---|---|---|
| `PAPER_TRADING` | `false` | `false` |
| `ACTIVE_BROKER` | `dhan` | `dhan` |
| `TOTAL_CAPITAL` | `10000` | `10000` |
| `DHAN_CLIENT_ID` | `1103480765` | `1103480765` |

---

## 5. Dhan Token State — CRITICAL

| Check | Result |
|---|---|
| Token present | YES |
| Token status | **EXPIRED** (`-54h 22m` past expiry) |
| API probe result | `DH-901 Invalid_Authentication` |
| Live positions check | **BLOCKED** — cannot query (DH-901) |
| Live orders check | **BLOCKED** — cannot query (DH-901) |

**Implication:** The execution repair code will deploy correctly but live execution will fail at  
broker authentication (DH-901) until a new token is issued.  
Token refresh is a separate operational concern; it does not affect the code repair itself.  
The system handles token expiry gracefully: `TOKEN EXPIRED` warning logged, feed falls back to yfinance.

---

## 6. Local DB State (Pre-Deployment)

| Check | Result |
|---|---|
| `data/trading_brain.db` open trades (mode≠test) | **0** |
| `data/trading_brain.db` live-mode trades | **0** |
| `data/paper_trades.csv` | Header-only, 0 trade rows |
| `data/control_tower.db` | Present, no relevant open positions |

**All open trades in DB are mode=`test` artifacts from 2026-03-11 — not live positions.**

---

## 7. OrderManager State

No live-mode open positions in DB.  
`_positions` dict initialises empty at container start.  
No orphan positions detected.

---

## 8. TradeMonitor State

No open software-SL monitoring registrations expected  
(container started ~1 hour ago, no live trades today).

---

## 9. Deployment Commit Plan

**Files to commit:**
```
execution_engine/order_manager.py          # EB001 + EB002 fix
opportunity_engine/arbitrage_ai.py         # ETF-ARB safety guard
test_execution_boundary_001.py             # EB boundary tests (15)
test_execution_boundary_002.py             # broker-spy tests (16)
test_etf_arb_guard.py                      # ETF guard tests (12)
EXECUTION_REPAIR_001_2026-08-13.md         # repair report
EXECUTION_REPAIR_002_PREDEPLOY_AUDIT_2026-08-13.md  # audit report
EXECUTION_REPAIR_003_PREDEPLOY_SNAPSHOT_2026-08-13.md  # this file
```

**Files explicitly excluded from commit:**
```
.env.example
.gitignore
requirements.txt
scripts/setup_github_secret.ps1
simulation_replay/replay_engine.py
simulation_replay/run_replay.py
```

---

## 10. Known Deployment Blocker

| Blocker | Severity | Impact |
|---|---|---|
| Dhan token expired | HIGH | Live execution will fail at DH-901 authentication |
| | | Does NOT affect code correctness or container health |
| | | Resolution: issue new Dhan token, hot-swap via `/token <new_token>` Telegram command |

---

```
Production changes:  0 (pre-deploy)
VPS deployment:      0 (pre-deploy)
Real Dhan orders:    0
Dhan write calls:    0
Positions created:   0
```
