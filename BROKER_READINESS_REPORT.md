# BROKER READINESS REPORT
## LTR-001 — Phase 4

**Date:** 2026-08-06  
**Broker:** DHAN (DhanHQ)  
**SDK:** dhanhq v2.1+ (also supports v2.0.x)  
**Auditor:** LTR-001 Certification Process

---

## 1. AUTHENTICATION

### Credential Management

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Client ID | `os.getenv("DHAN_CLIENT_ID")` | ✅ Ready |
| Access Token | `os.getenv("DHAN_ACCESS_TOKEN")` | ✅ Ready |
| JWT Expiry Parsing | `_parse_jwt_expiry()` — base64 decode + regex fallback | ✅ Ready |
| Credential validation at startup | `_connect()` checks both fields non-empty | ✅ Ready |
| Startup auth state log | `[DhanAuthState] token_present=... expires_in=... api_mode=...` | ✅ Ready |

### Token Refresh

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Hot-swap without restart | `reload_token(new_token)` | ✅ Ready |
| Telegram `/token <new_token>` command | Wired in `notifications/telegram_bot.py` | ✅ Ready |
| .env persistence after hot-swap | Direct write (atomic rename avoided for bind-mounts) | ✅ Ready |
| State reset after refresh | `_live=False` → `_connect()` → re-verify | ✅ Ready |
| Expiry warning (≤30 min) | `check_token_expiry()` — fires once, suppressed thereafter | ✅ Ready |
| Expiry alert (expired) | ERROR log + Telegram alert, hourly reminder | ✅ Ready |

---

## 2. WebSocket LIVE FEED

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Connection init | `start_live_feed(symbols)` | ✅ Ready |
| Background thread | `_ws_loop()` — daemon thread, auto-reconnect every 5s | ✅ Ready |
| SDK v2.1+ support | `from dhanhq import MarketFeed` | ✅ Ready |
| SDK v2.0.x support | `from dhanhq.marketfeed import DhanFeed` (fallback) | ✅ Ready |
| DhanContext support | v2.1+ `MarketFeed(self._context, instruments)` | ✅ Ready |
| Tick parsing | `_handle_ws_tick(data)` → updates `_ws_cache` | ✅ Ready |
| Quote cache priority | WS cache used if tick < 5 seconds old | ✅ Ready |
| Reconnect on failure | `while self._ws_running` loop with 5s sleep | ✅ Ready |
| Stop mechanism | `stop_live_feed()` sets `_ws_running = False` | ✅ Ready |
| Segment mapping | `_WS_SEGMENT` dict: NSE_EQ=1, NSE_FNO=2, IDX_I=13 | ✅ Ready |

---

## 3. ORDER PLACEMENT

### API Capability

| Capability | Implementation | Status |
|-----------|---------------|--------|
| `place_order()` method | `dhan_feed.py:2023` — wraps `self._dhan.place_order()` | ✅ Ready |
| Order type support | LIMIT, MARKET | ✅ Ready |
| Exchange segment | NSE_EQ (equities) | ✅ Ready |
| Paper mode guard | `PAPER_TRADING=True` default → no live orders sent | ✅ Ready |
| Live order routing | `PAPER_TRADING=False` + `ACTIVE_BROKER=dhan` → DhanFeed | ✅ Ready |

### Paper vs Live Switch

The `OrderManager` reads `config.PAPER_TRADING`:
```python
self._paper_mode = getattr(_cfg, "PAPER_TRADING", True)
self._broker = None if self._paper_mode else self._load_broker()
```

**To enable live trading:** Set `PAPER_TRADING=false` in `.env`. No code change required.

---

## 4. ORDER MODIFICATION AND CANCELLATION

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Order cancellation | `OrderManager.cancel_order()` via broker adapter | ✅ Ready |
| AET pending cancellation | `_aet_pending` slots expire by time + context | ✅ Ready |
| Limit expiry cancellation | `LIMIT_CANDLE_EXPIRY = 8 candles (40 min)` | ✅ Ready |
| Regime-based cancellation | VIX spike, distortion event, regime change | ✅ Ready |
| Re-entry after expiry | `ReentrySlot` with `REENTRY_MAX_RETRIES = 2` | ✅ Ready |

---

## 5. ORDER STATUS

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Order record lifecycle | `OrderRecord.status`: open → closed/cancelled | ✅ Ready |
| Fill price tracking | `OrderRecord.fill_price` | ✅ Ready |
| Partial fill handling | Status transitions: SUBMITTED → PARTIALLY_FILLED | ✅ Ready |
| Governance state | `OrderRecord.governance_state`: ACTIVE/CARRY/ORPHAN | ✅ Ready |

---

## 6. POSITION SYNC

| Capability | Implementation | Status |
|-----------|---------------|--------|
| In-memory portfolio | `Portfolio.positions: Dict[str, Position]` | ✅ Ready |
| Journal persistence | `data/paper_trades.csv` (CSV write on every event) | ✅ Ready |
| Restart recovery | `_restore_from_journal()` — rehydrates all open positions | ✅ Ready |
| Closed-order registry | `data/closed_orders_{date}.txt` — prevents ghost re-open | ✅ Ready |
| Expiry retry sidecar | `data/expiry_retries.json` — survives container restarts | ✅ Ready |

---

## 7. HOLDINGS AND FUNDS

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Capital tracking | `Portfolio.capital`, `available_capital` | ✅ Ready |
| PnL tracking | `Portfolio.total_pnl`, per-position PnL | ✅ Ready |
| Live holdings fetch | Via `OrderManager._broker.get_positions()` (live mode) | ✅ Ready |
| Available margin | `MIN_MARGIN_BUFFER_PCT = 20%` enforced by RiskGuardian | ✅ Ready |

---

## 8. TRADE BOOK

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Per-trade journal | `data/paper_trades.csv` — every OPEN and CLOSE event | ✅ Ready |
| Journal columns | timestamp, order_id, symbol, direction, quantity, entry_price, stop_loss, target, strategy, confidence, rr, event, exit_price, pnl, reason | ✅ Ready |
| Trade analytics | `TradeMonitor` + `StrategyHealthMonitor` | ✅ Ready |
| EOD learning | Win rate, avg-R, strategy health per strategy | ✅ Ready |

---

## 9. ERROR HANDLING

| Capability | Implementation | Status |
|-----------|---------------|--------|
| API failure classification | `_classify_dhan_response()` — 13 failure categories | ✅ Ready |
| Circuit breaker | `_DHAN_CIRCUIT_OPEN_AFTER = 5` consecutive failures → FALLBACK | ✅ Ready |
| Circuit break notification | Telegram alert + subsystem state snapshot | ✅ Ready |
| Auth error detection | AUTH_EXPIRED, AUTH_INVALID categories | ✅ Ready |
| Entitlement detection | ENTITLEMENT_MISSING (HTTP 451) — does NOT trip circuit | ✅ Ready |
| Rate limit detection | RATE_LIMIT (HTTP 429) | ✅ Ready |
| Timeout detection | TIMEOUT | ✅ Ready |
| Parse failure | PARSE_FAILURE — malformed JSON/dict | ✅ Ready |

---

## 10. RECONNECT LOGIC

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Data API reconnect | `reload_token()` → `_connect()` | ✅ Ready |
| Options session auto-reconnect | After `_OPT_RECONNECT_THRESHOLD = 3` consecutive failures per symbol | ✅ Ready |
| WebSocket reconnect | 5-second loop in `_ws_loop()` | ✅ Ready |
| Circuit breaker reset | On successful `reload_token()` | ✅ Ready |

---

## 11. RATE LIMIT HANDLING

Dhan v2 documented limits:
- REST: 10 req/s | 250 req/min | 7,000 req/day
- WebSocket: unlimited tick stream

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Batch quote calls | `get_multiple_quotes()` — one call per segment | ✅ Ready |
| WebSocket priority | WS cache checked before REST call | ✅ Ready |
| Rate limit detection | HTTP 429 → RATE_LIMIT category (retryable) | ✅ Ready |

---

## 12. LOGGING AND AUDIT TRAIL

| Log Tag | Purpose | Status |
|---------|---------|--------|
| `[DhanAuthState]` | Token presence, expiry, API mode | ✅ Active |
| `[DhanReadinessAudit]` | Full equity/options probe result | ✅ Active |
| `[ReadinessScore]` | Weighted readiness score (auth+equity+options+latency) | ✅ Active |
| `[DhanSubsystemState]` | 5-domain state snapshot | ✅ Active |
| `[DhanSessionState]` | Per-trigger truth snapshot | ✅ Active |
| `[DhanRuntimeMode]` | Mode at degradation/recovery events | ✅ Active |
| `[DhanRuntimeSummary]` | EOD cycle-mode breakdown | ✅ Active |
| `[DhanPartialSuccess]` | Per-batch success rate | ✅ Active |
| `[DhanSegmentHealth]` | Per-segment live/degraded status | ✅ Active |
| `[DhanLiveReadiness]` | Rolling equity/options reliability scores | ✅ Active |
| `[DhanOptionsAudit]` | Per-chain: strikes, OI, IV coverage, PCR | ✅ Active |
| `[DhanDailySummary]` | EOD Dhan health summary | ✅ Active |
| `[TokenGovernance]` | Token warning governance events | ✅ Active |
| `[DhanModeTransition]` | Mode change events | ✅ Active |

---

## 13. LIVE ORDER SAFETY GUARANTEE

> **No live orders were placed during this certification.**

All broker integration was verified through:
1. Code inspection of `order_manager.py` — `PAPER_TRADING=True` default confirmed
2. Code inspection of `dhan_feed.py` — `place_order()` exists and is callable
3. Credential environment variable verification — no live credentials in codebase
4. The `_paper_mode` flag in `OrderManager.__init__()` sets `self._broker = None` when True

---

## 14. KNOWN LIMITATIONS — DHAN DATA API

**Status:** Dhan Data API returns HTTP 451 (ENTITLEMENT_MISSING) for equity quotes.

| Component | Impact | Workaround |
|-----------|--------|-----------|
| `get_quote()` / `get_multiple_quotes()` | Falls back to yfinance automatically | ✅ yfinance active |
| `get_history()` | Falls back to sim history | ✅ yfinance active |
| `get_options_chain()` | May fail for some symbols | ⚠️ NSEFeed fallback |
| **Order placement** | **Not affected by data subscription** | ✅ Separate API |

**Resolution Required Before Live:** Activate Dhan Market Data subscription to eliminate the 451 fallback dependency on yfinance. Order execution is on a separate API and is not blocked.

---

## 15. PRE-LIVE CHECKLIST

| Item | Status |
|------|--------|
| `DHAN_CLIENT_ID` set in `.env` | Requires operator action |
| `DHAN_ACCESS_TOKEN` set in `.env` (valid, unexpired JWT) | Requires operator action |
| `PAPER_TRADING=false` set in `.env` | Requires operator action |
| `ACTIVE_BROKER=dhan` set in `.env` | Requires operator action |
| Dhan Data API subscription active | Recommended (not blocking) |
| Test order in Dhan sandbox before first live order | Recommended |

---

## BROKER READINESS VERDICT

| Domain | Result |
|--------|--------|
| Authentication | ✅ READY |
| Token Refresh | ✅ READY |
| WebSocket | ✅ READY |
| Order Placement (API) | ✅ READY |
| Order Modification / Cancellation | ✅ READY |
| Order Status | ✅ READY |
| Position Sync | ✅ READY |
| Holdings / Funds | ✅ READY |
| Trade Book | ✅ READY |
| Error Handling | ✅ READY |
| Reconnect Logic | ✅ READY |
| Rate Limit Handling | ✅ READY |
| Logging / Audit Trail | ✅ READY |
| No Live Orders in Certification | ✅ CONFIRMED |
| Data API (equity quotes) | ⚠️ 451 — yfinance fallback active |

**Overall Broker Readiness: READY WITH OBSERVATION**  
Observation: Dhan Data subscription needed for native quote feed. Order execution unaffected.

*Report completed: 2026-08-06*
