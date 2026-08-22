# FINAL DHAN READINESS REPORT
**Scope:** Broker-readiness verification for ₹10,000 controlled live pilot
**Date:** 2026-08-22
**VPS:** `root@178.18.252.24` | Commit `709948e` (+ dhan_broker.py field fix — pending commit)

---

## A. GREEN (confirmed ready)

| # | Item | Finding |
|---|---|---|
| A-01 | Both containers healthy | `ai-trading-brain Up (healthy)` · `trading-dashboard Up (healthy)` |
| A-02 | Deployed commit | `709948e` — ARCH-006 all fixes applied |
| A-03 | `PAPER_TRADING` | `true` (read from `.env` inside container) |
| A-04 | `LIVE_TRADING_AUTHORIZED` | `NOT_SET` (absent — paper mode forced) |
| A-05 | `broker_calls` | 0 (DhanBroker in SIM mode; all calls return SIM_ prefix) |
| A-06 | `real_orders` | 0 |
| A-07 | VPS public IPv4 | `178.18.252.24` — stable (Hetzner static IP, does not change on restart) |
| A-08 | `DHAN_CLIENT_ID` | Present in container `.env` (len=10) |
| A-09 | `DHAN_ACCESS_TOKEN` | Present in container `.env` (len=304) |
| A-10 | `ACTIVE_BROKER` | `dhan` |
| A-11 | `TOTAL_CAPITAL` | `10000.0` — confirmed at runtime |
| A-12 | `MAX_POSITIONS` | `3` — auto-scaled from ₹10k capital |
| A-13 | CRE `_MAX_POSITIONS` | `3` — confirmed matching config |
| A-14 | Security mapping: scanner coverage | 38/38 scanner symbols mapped (100%). All 20 base + 18 extended symbols present in `DHAN_SECURITY_MAP`. |
| A-15 | Security mapping: unmapped consequence | `IDEA`, `SUZLON`, `YESBANK`, `PNB` are NOT in scanner universe — test-only. No production signal can be blocked by a missing mapping. |
| A-16 | API compatibility: `place_order` | V2 params match. `trigger_price` (SDK snake_case → API camelCase internally). `validity` has default `'DAY'`. All required fields sent. |
| A-17 | API compatibility: `cancel_order` | Calls `dhan.cancel_order(order_id)` — matches V2 DELETE `/orders/{id}`. |
| A-18 | API compatibility: `get_order_status` | Calls `get_order_by_id(order_id)`. Response wrapped in `data` key (confirmed for v2.2.0). |
| A-19 | **P1 FIXED: `get_order_status` field names** | V2 API returns `filledQty` + `averageTradedPrice`. Code was reading `tradedQty` + `tradedPrice` (always 0 → partial fills never detected). Fixed in `dhan_broker.py` to `filledQty` with `tradedQty` fallback. |
| A-20 | SL order structure (V2-valid, template) | `order_type="STOP_LOSS"`, `product_type="INTRADAY"`, `trigger_price=<stop_loss>`, `price=<stop_loss * 0.995>`, `validity="DAY"`. Valid V2 SL-L request. |
| A-21 | ₹10k max risk per trade | ₹25.00 (0.25% of ₹10,000) |
| A-22 | ₹10k max drawdown halt | ₹1,000 (10% of ₹10,000) |
| A-23 | ₹10k max capital per trade | ₹1,500 (15% of ₹10,000) |
| A-24 | ₹10k max total exposure | ₹8,500 (85% of ₹10,000) — cannot exceed capital |
| A-25 | ₹10k worst-case 3 positions | ₹4,500 max (3 × ₹1,500) — well within ₹10,000 |
| A-26 | RELIANCE at ₹10k → qty=0 | Correct: ₹2,820 entry × 1 share = ₹2,820 > ₹1,500 cap → qty=0 → blocked |
| A-27 | TATASTEEL at ₹10k → qty=8 | ₹160 × 8 = ₹1,280 ≤ ₹1,500 cap. Risk = 8 × ₹3 = ₹24 ≤ ₹25 limit. ✓ |
| A-28 | Auth failure → NO TRADE | `DhanBroker._connected=False` → SIM mode. If token rejected → `_connect()` fails → `_connected=False` → all orders SIM-only. |
| A-29 | Order status uncertainty → no blind retry | `reconcile_partial_fills` catches exceptions per order; fails open (skips, does not retry). |
| A-30 | SL failure → no unprotected continuation | SL failure sets `rec.sl_order_id=""` — software SL via `TradeMonitor` remains active. |
| A-31 | Duplicate protection | `_symbol_has_open_position()` blocks identical second execute on same symbol. |
| A-32 | `order_manager.py` paper gate | Defense-in-depth: `PAPER_TRADING=true` → paper mode → `_broker=None` → no broker object created. |
| A-33 | `order_manager.py` authorization gate | `LIVE_TRADING_AUTHORIZED` absent → forces paper mode even if `PAPER_TRADING=false`. Log: `[OrderManager] forcing paper mode`. |
| A-34 | SDK v2.2.0 on VPS: `DhanContext` handled | `_connect()` wraps `DhanContext` import in `try/except ImportError` — falls back to legacy init. V2.2.0 uses `DhanContext` path correctly. |
| A-35 | SDK v2.2.0 `place_order` signature | Identical to v2.0.2 plus `should_slice=False` (unused by our code). Fully compatible. |

---

## B. RED (must be resolved before live activation)

| # | Item | Finding | Required Action |
|---|---|---|---|
| **R-01** | **Dhan access token EXPIRED** | All API calls return `DH-901: Client ID or user generated access token is invalid or expired`. Fund balance, positions, orders — none can be verified. Token in `.env` has length 304 but is rejected by Dhan. | **Regenerate token from DhanHQ developer console. Update `.env` on VPS. Verify token works by re-running account check.** |
| **R-02** | **VPS IP whitelist unverifiable** | Because token is expired (R-01), `DhanLogin.get_ip()` cannot be called. Cannot confirm `178.18.252.24` is whitelisted. Without IP whitelist, order placement is blocked at exchange level regardless of token. | **After renewing token: run `DhanLogin.get_ip(access_token)` and confirm `178.18.252.24` is listed as PRIMARY or SECONDARY. If not, add it via DhanHQ developer console.** |
| **R-03** | **Open positions/orders unverifiable** | With expired token, cannot confirm whether existing positions or orders exist on Dhan account that the system might incorrectly interpret. | **After renewing token: run read-only account check (positions + order book). Confirm clean slate before enabling live trading.** |
| **R-04** | **SDK version mismatch: Local=2.0.2, VPS=2.2.0** | All local testing (pytest, test_arch_006_integration.py) ran against dhanhq==2.0.2. VPS container has 2.2.0. The `DhanContext` path, `DhanHTTP` response structure, and `_parse_response` all differ. Code handles this via `try/except ImportError` but integration tests were not run against v2.2.0. | **Upgrade local dhanhq to 2.2.0 (`pip install dhanhq==2.2.0`) and re-run full test suite before live activation. OR lock VPS to 2.0.2 in requirements.txt.** |

---

## C. INFORMATION REQUIRED FROM OPERATOR

| # | Information needed | Why it cannot be auto-verified |
|---|---|---|
| C-01 | DhanHQ access token expiry policy | Dhan tokens expire periodically (typically every 30 days). Operator must know when the current token was generated to assess whether regeneration is routine or unexpected. |
| C-02 | Static IP confirmation | Must be verified in DhanHQ developer console UI or via `get_ip()` after token renewal. The VPS IP `178.18.252.24` must appear as PRIMARY in the whitelist before order placement is permitted by the exchange. |
| C-03 | Account balance confirmation | After token renewal, run `dhan.get_fund_limits()` to confirm `availableBalance ≥ ₹10,000` before activating live mode. |
| C-04 | Clean slate (no orphan positions) | After token renewal, run `dhan.get_positions()` to confirm zero open positions on the Dhan account. Any existing position not tracked by this system would cause incorrect P&L accounting. |

---

## Defect Fixed This Session

### Fix: `get_order_status` reads wrong field names (V2 API field mismatch)

**File:** `execution_engine/brokers/dhan_broker.py`

**Root cause:** Dhan V2 Order Book API (`GET /orders/{id}`) returns `filledQty` and `averageTradedPrice`. Code was reading `tradedQty` and `tradedPrice` — fields from the Trade Book response (`GET /trades`), not the Order Book.

**Impact:** `reconcile_partial_fills()` would always read `filled_qty=0` → `filled <= 0` branch → skip reconciliation → partial fills silently ignored → SL sized for wrong quantity.

**Fix applied:**
```python
# Before (wrong field names from Trade Book response)
"filled_qty":     int(data.get("tradedQty", 0) or 0),
"avg_fill_price": float(data.get("tradedPrice", 0.0) or 0.0),

# After (correct field names from Order Book response, with Trade Book fallback)
"filled_qty":     int(data.get("filledQty", data.get("tradedQty", 0)) or 0),
"avg_fill_price": float(data.get("averageTradedPrice", data.get("tradedPrice", 0.0)) or 0.0),
```

---

## Pilot Activation: Exact Environment Changes Required

When the operator chooses to activate live trading (after resolving R-01 through R-04):

```bash
# In /root/ai-trading-brain/.env — change THESE TWO LINES ONLY:
PAPER_TRADING  = false           # was: true
LIVE_TRADING_AUTHORIZED = true   # was: absent

# Then redeploy:
docker compose down && docker compose up -d
```

**These changes have NOT been made. Do not make them until all RED items are resolved.**

---

## ₹10,000 Pilot — Final Verdict

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   RED — DO NOT ENABLE LIVE TRADING                              │
│                                                                 │
│   Reason:                                                       │
│   R-01: Dhan access token EXPIRED (DH-901)                      │
│   R-02: VPS IP whitelist cannot be confirmed                    │
│   R-03: Account state (positions/orders) cannot be verified     │
│   R-04: SDK version mismatch (Local 2.0.2 vs VPS 2.2.0)        │
│                                                                 │
│   Software architecture: GREEN (ARCH-006 complete)              │
│   Broker connectivity:   RED (token expired, IP unconfirmed)    │
│                                                                 │
│   1 defect fixed this session:                                  │
│     get_order_status field names (filledQty vs tradedQty)       │
│                                                                 │
│   Requires operator action before re-evaluation:                │
│   1. Regenerate Dhan access token                               │
│   2. Update /root/ai-trading-brain/.env on VPS                  │
│   3. Confirm 178.18.252.24 in Dhan IP whitelist                 │
│   4. Confirm clean account (zero positions, zero orders)        │
│   5. Upgrade local dhanhq to 2.2.0 and re-run tests            │
│   6. Re-run this readiness check                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

*FINAL_DHAN_READINESS_REPORT.md | Session: d8a34282 | Generated: 2026-08-22*
