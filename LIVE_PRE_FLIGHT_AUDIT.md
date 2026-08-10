# LIVE PRE-FLIGHT AUDIT REPORT
### IIOS — Dhan Account | Controlled Live-Trading Pilot
**Date:** 2026-08-10  
**Auditor:** GitHub Copilot (AI — read-only, no orders placed)  
**Release:** IIOS-V1.0.0 | FRZ-001 + PRR-001  
**Scope:** Read-only verification. Zero orders transmitted to Dhan.

---

## FINAL STATUS

```
╔══════════════════════════════════════════════╗
║  NOT_READY_FOR_LIVE_TRADING                 ║
╚══════════════════════════════════════════════╝
```

**3 FAIL items must be resolved before live trading can begin.**
See corrective actions at the bottom of this report.

---

## SECTION 1 — DHAN BROKER CONFIGURATION

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1.1 | ACTIVE_BROKER | ✅ PASS | `dhan` — both local and VPS |
| 1.2 | PAPER_TRADING mode | ❌ FAIL | `true` in .env and container — **live orders are impossible until set to `false`** |
| 1.3 | USE_LIVE_DATA | ✅ PASS | `true` — market data from live feeds |
| 1.4 | Dhan CLIENT_ID set | ✅ PASS | Present (length=10) |
| 1.5 | Dhan ACCESS_TOKEN set | ✅ PASS | Present (length=303, JWT format) |
| 1.6 | Token validity (JWT decode) | ❌ FAIL | **EXPIRED.** Issued: 2026-08-01 11:29 UTC. Expired: 2026-08-02 11:29 UTC. Now: 2026-08-10. Token is 8 days past expiry. |
| 1.7 | Broker API connectivity | ❌ FAIL | Dhan API returns `DH-901 Invalid_Authentication` — direct consequence of expired token |

**Section 1 verdict: NOT READY — 3 FAIL**

---

## SECTION 2 — ACCOUNT STATUS

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 2.1 | Account status retrieval | ❌ FAIL | Cannot retrieve — token expired (DH-901). Fund limits API returned `failure`. |
| 2.2 | Available cash/funds | ❌ FAIL | Cannot verify — blocked by token failure |
| 2.3 | Account suitability (equity) | ⚠️ WARNING | Cannot confirm — depends on token renewal and account verification with Dhan |
| 2.4 | API secrets exposed in report | ✅ PASS | No credentials or token values appear in this report |

**Section 2 verdict: NOT READY — cannot verify account without valid token**

---

## SECTION 3 — CAPITAL CONFIGURATION

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 3.1 | TOTAL_CAPITAL for live pilot | ❌ FAIL | Configured as **₹1,00,00,000 (₹1 Crore)** — the paper-trading test figure. Expected ₹10,000 for the live pilot. Old test capital is still the active value. |
| 3.2 | PILOT_CAPITAL | ⚠️ WARNING | Set to ₹1,00,000 (₹1 Lakh) in .env. User expects ₹10,000. Not actively used for position sizing — TOTAL_CAPITAL governs. |
| 3.3 | No ₹1 Crore live capital active | ❌ FAIL | `TOTAL_CAPITAL = 10,000,000` (₹1Cr) is active in config.py default **and** runtime. Until overridden via `.env TOTAL_CAPITAL=10000`, every position-size calculation will treat capital as ₹1Cr. |
| 3.4 | Position sizing percentage-based | ✅ PASS | `MAX_RISK_PER_TRADE_PCT = 0.0025` (0.25%), `MAX_PORTFOLIO_RISK_PCT = 0.08` (8%) — all percentage-based, no hardcoded INR amounts |
| 3.5 | ADV liquidity guard | ✅ PASS | `MIN_ADV_CRORE = 50`, `MAX_ADV_PCT = 0.02` — active |

**Section 3 verdict: NOT READY — TOTAL_CAPITAL must be set to ₹10,000 before live activation**

---

## SECTION 4 — TRADING SAFETY

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 4.1 | DECAYING edges blocked | ✅ PASS | 132/259 DECAYING edges blocked by PRR-001 Phase 1 edge gate. `KnowledgeProvider.list_edges()` returns 127 (0 DECAYING passed). |
| 4.2 | RETIRED knowledge blocked | ✅ PASS | `BLOCKED_EDGE_STATUSES = {'DECAYING', 'RETIRED'}` — 0 RETIRED edges present, gate is armed |
| 4.3 | Expired signals blocked | ✅ PASS | `is_signal_expired()` wired in `OrderManager.execute()` before order routing. Signals >15 days old are blocked. |
| 4.4 | Unverified knowledge blocked | ⚠️ WARNING | All 259 edges have `validation_status = UNKNOWN`. The edge gate only filters on lifecycle status (DECAYING/RETIRED), not validation_status. 127 CANDIDATE+ACTIVE edges pass. This is expected behaviour for bootstrap — no CONFIRMED edges yet. |
| 4.5 | SHORT DNA operational | ⚠️ WARNING | `institutional_dna.db`: 124 total DNA records — all 124 are INSTITUTIONAL lifecycle. **SHORT lifecycle = 0.** SHORT DNA is used for short-side filtering. Not a blocker for long-only pilot but limits short-side intelligence. |
| 4.6 | Automatic universe active | ✅ PASS | `data/nifty500_universe.json` present — 230 symbols. PRR MIN_ADV_CRORE = 50.0. |
| 4.7 | Portfolio limits active | ✅ PASS | `MAX_PORTFOLIO_RISK_PCT = 8%`, `MAX_OPEN_TRADES` enforced, `MAX_DRAWDOWN_PCT = 10%` |
| 4.8 | Kill switch — VIX | ✅ PASS | `FailSafeRiskGuardian` active. Kill if VIX ≥ 45. Halt if daily loss ≥ 2%. |
| 4.9 | Kill switch — daily loss | ✅ PASS | `MAX_DAILY_LOSS_PCT = 2.0%`, `DD_PAUSE_PCT = 4.0%` — halt and pause tiers operational |
| 4.10 | Confidence threshold | ✅ PASS | `MIN_CONFIDENCE_SCORE = 6.8` — decision threshold active |
| 4.11 | ATR-based stops | ✅ PASS | `ATR_STOP_MULTIPLIER = 1.5`, no hardcoded % stops |

**Section 4 verdict: PASS with 2 warnings (expected bootstrap state)**

---

## SECTION 5 — RUNTIME INTEGRITY

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 5.1 | Local commit | ✅ PASS | `64dc0ff` |
| 5.2 | Git remote (origin/main) | ✅ PASS | `64dc0ff` — Local = Remote |
| 5.3 | VPS commit | ✅ PASS | `64dc0ff` — confirmed via SSH |
| 5.4 | Container commit | ✅ PASS | `64dc0ff` — VPS container running FRZ-001 code |
| 5.5 | SYSTEM_VERSION.json commit | ⚠️ WARNING | Records `a1ca6e1` (PRR-001). Should be updated to `64dc0ff` (FRZ-001) by running `frz_runner init`. Non-critical — version file was created before FRZ-001 was committed. |
| 5.6 | ai-trading-brain container | ✅ PASS | `Up 2 days (healthy)` |
| 5.7 | trading-dashboard container | ✅ PASS | `Up 2 days (healthy)` |
| 5.8 | Scheduler configuration | ✅ PASS | 17 intraday slots defined in SCHEDULE |
| 5.9 | Market data connection | ✅ PASS | yfinance fallback operational — RELIANCE.NS quote retrieved successfully (₹1327.80) |
| 5.10 | Dhan market data (primary) | ❌ FAIL | Blocked by expired token — system will auto-fallback to yfinance |
| 5.11 | control_tower.db integrity | ✅ PASS | PRAGMA integrity_check = `ok` |
| 5.12 | institutional_dna.db integrity | ✅ PASS | PRAGMA integrity_check = `ok` |
| 5.13 | IIOS-V1.0.0 / 64dc0ff certified | ✅ PASS | FRZ-001 FROZEN, PRR-001 PRODUCTION_READY_WITH_OBSERVATIONS |
| 5.14 | Production lock | ⚠️ WARNING | `main.py` hash changed since SYSTEM_VERSION.json was written (FRZ-001 startup check patch added). Requires `frz_runner lock --confirm` acknowledgment. System is not blocked — only a governance flag. |

**Section 5 verdict: PASS with 1 FAIL (Dhan data blocked by token) and 2 warnings**

---

## SECTION 6 — LIVE EXECUTION SAFETY

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 6.1 | Paper mode prevents live orders | ✅ PASS | `OrderManager.__init__`: `self._broker = None if self._paper_mode else self._load_broker()`. With `PAPER_TRADING=True`, `_broker = None`. No Dhan connection is established. Live orders are structurally impossible. |
| 6.2 | Dhan broker adapter exists | ✅ PASS | `execution_engine/brokers/dhan_broker.py` present with `place_order()` routing to `dhanhq` |
| 6.3 | Live order pathway verified (dry) | ⚠️ WARNING | The live pathway (`PAPER_TRADING=false` → `_load_broker()` → `DhanBroker`) is code-complete but **cannot be end-to-end tested** until a valid Dhan token is in place |
| 6.4 | No orders transmitted this audit | ✅ PASS | Zero API calls to order endpoints. All checks were read-only (fund_limits, JWT decode). |
| 6.5 | Signal freshness blocks stale signals | ✅ PASS | Freshness gate operational — signals >15 days are EXPIRED and blocked pre-execution |
| 6.6 | Edge gate blocks DECAYING signals | ✅ PASS | 132 DECAYING edges cannot produce signals — patched at `KnowledgeProvider` level |

**Section 6 verdict: PASS — system is live-execution-ready architecturally, but cannot execute until token is renewed and PAPER_TRADING=false**

---

## SUMMARY TABLE

| Section | Pass | Fail | Warning |
|---------|------|------|---------|
| 1. Broker Configuration | 4 | **3** | 0 |
| 2. Account Status | 1 | **2** | 1 |
| 3. Capital Configuration | 2 | **2** | 1 |
| 4. Trading Safety | 9 | 0 | 2 |
| 5. Runtime Integrity | 11 | **1** | 2 |
| 6. Execution Safety | 5 | 0 | 1 |
| **TOTAL** | **32** | **8** | **7** |

---

## CORRECTIVE ACTIONS (in order of priority)

### BLOCKER 1 — Dhan Access Token Expired (CRITICAL)
**Symptom:** DH-901 Invalid_Authentication on all Dhan API calls.  
**Token issued:** 2026-08-01 11:29 UTC  
**Token expired:** 2026-08-02 11:29 UTC (8 days ago)  
**Action required:**
1. Log in to [dhan.co](https://dhan.co) → My Profile → API → Create App
2. Generate a new Access Token for your App
3. Update `.env` on both **local machine** and **VPS** (`/root/ai-trading-brain/.env`):
   ```
   DHAN_ACCESS_TOKEN = <new-token>
   ```
4. Restart containers: `docker compose restart` (no rebuild needed — env is injected)
5. Re-run this audit to confirm DH-901 is resolved

### BLOCKER 2 — TOTAL_CAPITAL Still Set to ₹1 Crore (CRITICAL)
**Symptom:** `config.TOTAL_CAPITAL = 10,000,000` — the paper-trading test figure.  
**Action required:**
1. Add to `.env` (both local and VPS):
   ```
   TOTAL_CAPITAL = 10000
   ```
2. Confirm `PILOT_CAPITAL` aligns:
   ```
   PILOT_CAPITAL = 10000
   ```
3. After updating .env, verify with `python -c "import config; print(config.TOTAL_CAPITAL)"`
4. Restart containers on VPS after updating VPS .env

### BLOCKER 3 — PAPER_TRADING = true (Required before live activation)
**Symptom:** System is in paper mode. No live orders possible.  
**Action required (ONLY after Blockers 1 and 2 are resolved):**
1. Update `.env` on VPS:
   ```
   PAPER_TRADING = false
   ```
2. Update local `.env` to match
3. Restart containers
4. Verify: `docker exec ai-trading-brain python -c "import config; print(config.PAPER_TRADING)"`

### NON-BLOCKER — Production Lock Acknowledgment (governance only)
**Symptom:** `main.py` hash changed since SYSTEM_VERSION.json was written during FRZ-001 init.  
**Action required (after Blockers 1-3 resolved, before tagging live release):**
```powershell
python -m release_manager.frz_runner lock --confirm --reason "FRZ-001 startup check patch — acknowledged, same commit 64dc0ff"
```

### NON-BLOCKER — SYSTEM_VERSION.json commit field (housekeeping)
**Symptom:** Records `a1ca6e1` instead of `64dc0ff`.  
**Action required (after Blockers 1-3 resolved):**
```powershell
python -m release_manager.frz_runner init --bump none --notes "FRZ-001 production release"
git add SYSTEM_VERSION.json
git commit -m "chore: update SYSTEM_VERSION to FRZ-001 commit 64dc0ff"
# then deploy
```

---

## WHAT IS READY

The architecture is production-certified. The following are fully operational and require no changes:

- ✅ All 17 trading layers functional
- ✅ Edge gate (132 DECAYING blocked at knowledge source)
- ✅ Signal freshness gate (>15 day signals blocked at execution)
- ✅ Kill switches (VIX≥45, daily loss≥2%)
- ✅ Portfolio limits (8% max, drawdown halt)
- ✅ Confidence threshold (score ≥ 6.8)
- ✅ Automatic stock universe (230 symbols)
- ✅ DB integrity (both databases clean)
- ✅ Both containers healthy (Up 2 days)
- ✅ yfinance fallback market data operational
- ✅ Dhan broker adapter code-complete and ready for live orders
- ✅ All position sizing percentage-based
- ✅ FRZ-001 architecture freeze active (commit 64dc0ff)
- ✅ PRR-001 production readiness active

---

## LIVE READINESS GATE

The system may enter controlled live trading **ONLY** when all three blockers are resolved
and this audit is re-run and shows zero FAIL items.

```
REQUIRED BEFORE LIVE ACTIVATION:
  1. ❌ New Dhan access token (valid, not expired)
  2. ❌ TOTAL_CAPITAL = 10000 in .env
  3. ❌ PAPER_TRADING = false in .env

FINAL VERDICT:
  NOT_READY_FOR_LIVE_TRADING
```

---

_Report generated: 2026-08-10 | Read-only audit — no orders placed, no rules changed, no architecture modified._
