# LIVE TRADING CERTIFICATE
## LTR-001 — Investment Intelligence Operating System (IIOS)

```
╔══════════════════════════════════════════════════════════════════╗
║          LIVE TRADING READINESS CERTIFICATE                      ║
║          LTR-001 — IIOS V1                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  Date Issued      : 2026-08-06                                   ║
║  System           : IIOS V1 (Investment Intelligence OS)         ║
║  Architecture     : Frozen — IIOS_V1_ARCHITECTURE_FREEZE.md      ║
║  Certification ID : LTR001-20260806                              ║
║  Result           : PASS WITH OBSERVATIONS                       ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## CERTIFICATION SCOPE

This certificate covers a one-time production readiness certification of the IIOS V1 system.

**This is NOT:** shadow trading, paper trading, a new strategy, or an architecture review.  
**This IS:** verification that IIOS V1 is production-safe for live market deployment.

**Governance completed prior to this certification:**
- Scientific governance: COMPLETE
- Research pipeline: COMPLETE
- Knowledge infrastructure: COMPLETE
- Architecture freeze: COMPLETE (`IIOS_V1_ARCHITECTURE_FREEZE.md`)

---

## FIVE-PHASE CERTIFICATION RESULTS

### Phase 1 — Capital Independence Audit

**File:** `CAPITAL_INDEPENDENCE_AUDIT.md`

| Question | Answer |
|----------|--------|
| Is every trading decision capital-independent? | **YES** |
| Do only position quantities change with capital? | **YES** |
| Can IIOS trade with ₹10,000 without modifying logic? | **YES** |

**Evidence:**
- All risk limits expressed as percentages of `TOTAL_CAPITAL`
- `TOTAL_CAPITAL` is an environment variable (default 1Cr, freely configurable)
- Sizing formula: `qty = (TOTAL_CAPITAL × 0.0025) / SL_distance` — scales naturally
- Ranking, PMCI, CDS, PIG, debate votes, conviction scores: all dimensionless

**One Observation:** `master_orchestrator.py:5145` contains hard-coded `-50000` in the System Readiness Assessment diagnostic. This label may misreport for portfolios under ₹25,000. The actual trading halt (`FailSafeRiskGuardian`) correctly uses `TOTAL_CAPITAL × 2.0%`.

**Result: PASS WITH ONE OBSERVATION**

---

### Phase 2 — Live Execution Audit

**File:** `LIVE_EXECUTION_AUDIT.md`

| Domain | Result |
|--------|--------|
| Order creation (signal-to-order pipeline) | ✅ PASS |
| Order validation (3-layer defence) | ✅ PASS |
| Position sizing (institutional formula) | ✅ PASS |
| Capital reservation | ✅ PASS |
| Partial fills | ✅ PASS |
| Order rejection | ✅ PASS |
| Order cancellation | ✅ PASS |
| Portfolio replacement (smart-swap) | ✅ PASS |
| Emergency exit | ✅ PASS |
| Kill switch | ✅ PASS |
| Broker reconnect | ✅ PASS |
| Market close handling | ✅ PASS |
| Restart recovery | ✅ PASS |

**Result: PASS**

---

### Phase 3 — Portfolio Behaviour Audit

**Scenario: Four capital levels tested**

| Capital | Risk/Trade | Behaviour |
|---------|-----------|-----------|
| ₹10,000 | ₹25/trade | Low-price stocks tradeable; high-price (MARUTI, NESTLEIND) yield qty=0 → correctly dropped |
| ₹20,000 | ₹50/trade | More stocks tradeable; rankings unchanged |
| ₹1,00,000 | ₹250/trade | Typical small trader; normal operation |
| ₹1,00,00,000 | ₹25,000/trade | Full institutional capacity |

**What remains IDENTICAL across all capital levels:**
- Signal ranking order
- PMCI scores
- CDS scores  
- PIG (Institutional DNA) influence
- Decision Engine debate votes
- Risk ranking
- Opportunity ranking
- Entry/exit timing logic
- Strategy selection
- Regime detection

**What CHANGES:**
- Position quantities (qty = f(capital))
- Some stocks become untradeable at very low capital (qty → 0) — this is correct

**Result: PASS**

---

### Phase 4 — Broker Integration Audit

**File:** `BROKER_READINESS_REPORT.md`

| Domain | Status |
|--------|--------|
| Authentication | ✅ READY |
| Token refresh (hot-swap) | ✅ READY |
| WebSocket live feed | ✅ READY |
| Order placement API | ✅ READY |
| Order modification / cancellation | ✅ READY |
| Order status tracking | ✅ READY |
| Position sync | ✅ READY |
| Holdings / funds | ✅ READY |
| Trade book / audit trail | ✅ READY |
| Error handling (13 failure categories) | ✅ READY |
| Reconnect logic | ✅ READY |
| Rate limit handling | ✅ READY |
| Logging | ✅ READY |
| No live orders placed in certification | ✅ CONFIRMED |
| Dhan equity data (451 ENTITLEMENT) | ⚠️ yfinance fallback active |

**One Observation:** Dhan Data API subscription not active. Equity quotes fall back to yfinance. Order placement API is on a separate endpoint and is NOT affected. Live trading can proceed; data subscription recommended for native quote feed.

**Result: PASS WITH ONE OBSERVATION**

---

### Phase 5 — Production Safety Audit

**File:** `PRODUCTION_SAFETY_REPORT.md`

| Safety Control | Status |
|----------------|--------|
| Kill Switch (VIX ≥ 45) | ✅ VERIFIED |
| Kill Switch (Nifty ≤ -5%) | ✅ VERIFIED |
| Maximum Daily Loss (2%) | ✅ VERIFIED |
| Maximum Portfolio Risk (5% / 8%) | ✅ VERIFIED |
| Maximum Exposure (85%) | ✅ VERIFIED |
| Maximum Open Positions (8–15) | ✅ VERIFIED |
| Duplicate Order Protection | ✅ VERIFIED |
| Trading Circuit Breaker | ✅ VERIFIED |
| Broker Circuit Breaker | ✅ VERIFIED |
| Market Holiday Handling | ✅ VERIFIED |
| Restart Recovery | ✅ VERIFIED |
| Timing Governance (09:45/14:30) | ✅ VERIFIED |

**Result: PASS WITH ONE OBSERVATION**

---

## FINAL ANSWERS — CERTIFICATION QUESTIONS

| # | Question | Answer |
|---|----------|--------|
| 1 | Is every trading decision capital-independent? | **YES** |
| 2 | Does only position quantity change with capital? | **YES** |
| 3 | Can IIOS trade with ₹10,000 without modifying any trading logic? | **YES** |
| 4 | Is DHAN integration production ready? | **YES** — order API ready; data subscription needed for native quotes |
| 5 | Can live trading begin? | **YES — with three operator actions required** |

---

## OBSERVATIONS SUMMARY

Three observations noted. None are blocking. All are operational configuration items.

| # | Observation | Severity | Blocking? |
|---|-------------|----------|-----------|
| O-1 | `master_orchestrator.py:5145`: SRA diagnostic uses hard-coded `-50000` instead of `TOTAL_CAPITAL × 2%` | LOW | NO |
| O-2 | Dhan Data API subscription not active (HTTP 451); yfinance fallback in use | MEDIUM | NO |
| O-3 | `PAPER_TRADING=false` must be set in `.env` to enable live execution | INFO | Operator action |

---

## REQUIRED OPERATOR ACTIONS BEFORE FIRST LIVE TRADE

These are configuration steps, not code changes:

```bash
# In .env on the VPS:
PAPER_TRADING=false
ACTIVE_BROKER=dhan
DHAN_CLIENT_ID=<your-client-id>
DHAN_ACCESS_TOKEN=<valid-jwt-token>
TOTAL_CAPITAL=<your-live-capital-in-INR>
```

After setting, redeploy:
```powershell
git add .env
git commit -m "LTR-001: Enable live trading"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

**Verify both containers show `Up ... (healthy)` before market open.**

---

## RECOMMENDED ACTIONS (NOT BLOCKING)

| Priority | Action |
|----------|--------|
| HIGH | Activate Dhan Market Data subscription to eliminate yfinance fallback |
| LOW | Replace `master_orchestrator.py:5145` `-50000` with `TOTAL_CAPITAL × MAX_DAILY_LOSS_PCT` |

---

## CERTIFICATION STATEMENT

The IIOS V1 system has been inspected across all five phases of the LTR-001 production certification protocol. The system:

1. Makes **all trading decisions independent of portfolio capital**
2. Changes **only position quantities** when capital changes
3. Has a **complete and correct kill-switch and circuit-breaker stack**
4. Has a **production-ready Dhan broker integration** (order API)
5. Has **complete restart recovery** and audit trail infrastructure
6. Has **no hard-coded monetary values in any critical decision path**

The system is certified for live market deployment subject to the three operator configuration actions listed above.

```
╔══════════════════════════════════════════════════════════════════╗
║  CERTIFICATION RESULT: PASS WITH OBSERVATIONS                    ║
║  System: IIOS V1                                                 ║
║  Date: 2026-08-06                                                ║
║  Observations: 3 (none blocking)                                 ║
║  Operator actions required: 3 (.env configuration only)         ║
║  Architecture changes: NONE                                      ║
║  Trading logic changes: NONE                                     ║
║  Research changes: NONE                                          ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## CERTIFICATE OF RECORD

| Field | Value |
|-------|-------|
| Certificate ID | LTR001-20260806 |
| System | IIOS V1 |
| Architecture Freeze | IIOS_V1_ARCHITECTURE_FREEZE.md |
| Scientific Governance | COMPLETE |
| Research Pipeline | COMPLETE |
| Knowledge Infrastructure | COMPLETE |
| Certification Date | 2026-08-06 |
| Result | **PASS WITH OBSERVATIONS** |
| Live Trading Authorised | **YES** — pending operator config actions |

*LTR-001 Live Trading Readiness Certification — IIOS V1*
