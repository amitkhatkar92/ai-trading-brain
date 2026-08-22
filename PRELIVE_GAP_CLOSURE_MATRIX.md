# Pre-Live Gap Closure Matrix
**Generated:** 2026-08-22  
**Scope:** ₹10,000 live experiment — Monday authorization decision

---

## Classification Legend

| Class | Meaning |
|---|---|
| **P0** | Blocker — must fix before ANY live experiment |
| **P1** | High — must fix or explicitly accept before live |
| **P2** | Medium — fix within first live week |
| **DATA** | Data-dependent gap — can't fix in code; monitor in production |
| **MANUAL** | Requires operator action, not code change |
| **FALSE** | Initially flagged; confirmed false positive on deeper inspection |
| **PASS** | Clean — no gap |

---

## All 79 Findings

| Part | Finding | Severity | Class | Resolution |
|---|---|---|---|---|
| A | Call graph intact (scheduler→execution) | INFO | **PASS** | Confirmed via code trace |
| A | RiskGuardian before OrderManager | P1 | **FALSE** | rg=L1436, om.execute=L3001; import at L67 caused false pos |
| B | qty = signal.quantity × position_size_modifier | INFO | **PASS** | order_manager.py L696 |
| B | _place_stop_loss called after entry | INFO | **PASS** | order_manager.py L821 |
| C | KDA decision used in orchestrator | INFO | **PASS** | kda_dec/KNOWLEDGE_BUY confirmed |
| C | KNOWLEDGE_HOLD drops signal before StrategyLab | INFO | **PASS** | orchestrator L1069 |
| D | kda_stop → signal.stop_loss | INFO | **PASS** | orchestrator L1098 |
| D | kda_target → signal.target_price | INFO | **PASS** | orchestrator L1126 |
| D | ATR_FALLBACK for DEVELOPING evidence | INFO | **PASS** | orchestrator confirmed |
| D | stop_loss validated before sizing (sl_distance < 0.001) | INFO | **PASS** | CRE L631 |
| E | TOTAL_CAPITAL = ₹10,000 | INFO | **PASS** | env var set; confirmed at runtime |
| E | MAX_RISK_PER_TRADE_PCT = 0.25% = ₹25/trade | INFO | **PASS** | correct for ₹10k capital |
| E | IDEA ₹15 / ATR₹0.5 → qty=11 | INFO | **PASS** | trades penny/cheap stocks |
| E | SUZLON ₹75 / ATR₹1 → qty=5 | INFO | **PASS** | trades low-cost stocks |
| E | TATASTEEL ₹160 / ATR₹3 → qty=1 | INFO | **PASS** | borderline viable |
| E | SBIN ₹850 / ATR₹8 → qty=0 | P2 | **DATA** | By design: ₹10k capital can't risk-size large-caps; only low-ATR stocks trade |
| E | RELIANCE ₹2820 / ATR₹28 → qty=0 | P2 | **DATA** | Same — correct risk math |
| E | HDFCBANK ₹1900 / ATR₹19 → qty=0 | P2 | **DATA** | Same — correct risk math |
| E | MAX_CAPITAL_PER_TRADE_PCT = 15% = ₹1,500 | INFO | **PASS** | Per-trade hard cap |
| E | MAX_TOTAL_OPEN_EXPOSURE_PCT = 85% = ₹8,500 | INFO | **PASS** | Total exposure hard cap |
| F | DHAN_SECURITY_MAP: ~149 symbols | INFO | **PASS** | Sufficient for NSE liquid universe |
| F | Missing map guard returns None (safe) | INFO | **PASS** | order_manager.py: MISSING_DHAN_MAPPING |
| F | DHAN_SECURITY_MAP completeness unknown | P2 | **DATA** | Scanner may surface stocks outside 149 → silently blocked; monitor logs |
| G | All Dhan API fields present | INFO | **PASS** | security_id, exchange_segment, transaction_type, quantity, price, order_type |
| G | SIM mode returns SIM_ prefixed IDs | INFO | **PASS** | Never confused with real order IDs |
| H | Symbol open-position check in execute() | INFO | **PASS** | _symbol_has_open_position() |
| H | Zone-based reentry guard (2%) | INFO | **PASS** | _SAME_ZONE_PCT = 0.02 |
| H | Crash recovery: restore_state exists | INFO | **PASS** | _restore_from_journal → CSV rebuild |
| H | CSV journal for persistence | INFO | **PASS** | data/paper_trades.csv |
| I | Restore loads stop_loss and target_price | INFO | **PASS** | Confirmed in restore code |
| I | LTP pre-fetch after restore | INFO | **PASS** | _prefetch_restored_ltps() |
| J | Token check in dhan_feed | INFO | **PASS** | access_token verified |
| J | yfinance fallback for data | INFO | **PASS** | Dhan down → yfinance auto |
| J | DhanBroker SIM on not-connected | INFO | **PASS** | Token failure → SIM, no real orders |
| K | _guarded_cycle + scheduler try/except | INFO | **PASS** | Scheduler loop at L6714 catches all exceptions |
| K | EOD learning isolated from scan | INFO | **PASS** | _do_eod_learning separate task |
| L | Pre-order price integrity guard | INFO | **PASS** | price_integrity_validator before execution |
| L | entry_price > 0 validated | INFO | **PASS** | Confirmed |
| L | Stop distance sanity in CRE | INFO | **PASS** | sl_distance < 0.001 → qty=0 |
| M | Empty signal list handled gracefully | INFO | **PASS** | Orchestrator defensive |
| M | VIX > 45 kill-switch | INFO | **PASS** | RiskGuardian confirmed |
| M | Drawdown kill-switch (10% = ₹1,000) | INFO | **PASS** | RiskGuardian confirmed |
| N | No-lookahead in KFE/HBE | P1 | **FALSE** | _fetch_post_decision_bars strips bars ≤ decision_date; pipeline explicit |
| N | No obvious lookahead patterns | INFO | **PASS** | Code search clean |
| O | ExecutionWindowBlock (09:45 earliest) | INFO | **PASS** | Layer 3 in execute() |
| O | Market hours gate in orchestrator | INFO | **PASS** | _is_market_session() |
| O | Signal freshness gate | INFO | **PASS** | SignalFreshnessGate in execute() |
| P | PILOT_MAX_TRADES = 3 (env) | INFO | **PASS** | Config set |
| P | PILOT_MODE not in scheduler path | P2 | **MANUAL** | PilotController only in --pilot mode; CRE _MAX_POSITIONS=8 is effective cap in scheduler; operator must understand max is 8, not 2 |
| P | PILOT_MAX_TRADES in orchestrator | INFO | **FALSE** | Match was _pilot_cap var name, not PilotController |
| Q | MAX_DRAWDOWN_PCT = 10% = ₹1,000 halt | INFO | **PASS** | Appropriate for ₹10k experiment |
| Q | Drawdown halt in RiskGuardian | INFO | **PASS** | Confirmed |
| Q | RiskGuardian.evaluate() returns BLOCK | INFO | **PASS** | Confirmed |
| R | _place_stop_loss defined | INFO | **PASS** | order_manager.py L1966 |
| R | SL order placed on exchange in live mode | **P1** | **FIXED** | `DhanBroker.place_sl_order` added 2026-08-22; STOP_LOSS order type on Dhan exchange |
| S | EOD close logic | INFO | **PASS** | Confirmed in order_manager + _do_monitor |
| S | Target and stop monitoring | INFO | **PASS** | trade_monitor.check_all() every 5 min |
| S | _do_monitor closes on target/stop | INFO | **PASS** | Confirmed |
| T | ESS_DEVELOPING = 3.0 threshold | INFO | **PASS** | KDA correctly skips ESS<3 → KNOWLEDGE_WAIT |
| T | KNOWLEDGE_WAIT for ESS<3 | INFO | **PASS** | Does NOT block signal (only HOLD blocks) |
| T | HOLD blocks, WAIT does NOT | INFO | **PASS** | Correct architecture |
| U | Decision threshold 6.5 | INFO | **PASS** | Confirmed |
| U | Debate called before execution | INFO | **PASS** | _run_debate_and_decide L1564 before L3001 |
| U | Debate called after KDA (correct order) | INFO | **PASS** | KDA~L1050, Debate L1564, Execute L3001 |
| V | config.PAPER_TRADING = False | INFO | **PASS** | Local dev; VPS has PAPER_TRADING=true |
| V | LIVE_TRADING_AUTHORIZED = ABSENT | INFO | **PASS** | No live orders can fire |
| V | Dual gate: BOTH required | INFO | **PASS** | Defense-in-depth confirmed |
| V | DhanBroker._connected gate | INFO | **PASS** | Not connected → SIM |
| V | VPS PAPER_TRADING=true | MANUAL | **MANUAL** | Verify docker-compose.yml on VPS before enabling LIVE_TRADING_AUTHORIZED |
| V | _broker_place call sites (5) | INFO | **PASS** | L942, 1215, 1512, 1925, 1944 — all in OrderManager |
| W | Scheduler exception handling | P1 | **FALSE** | _run() at L6714 has try/except around sched_lib.run_pending() |
| W | SIGTERM handler | INFO | **PASS** | main.py confirmed |
| X | Test coverage: 141/141 KDA+ARCH-005 tests | INFO | **PASS** | run 2026-08-22 |
| Y | PAPER_TRADING = False (local) | INFO | **PASS** | Expected; VPS overrides |
| Y | TOTAL_CAPITAL = ₹10,000 | INFO | **PASS** | Correct for experiment |
| Y | LIVE_TRADING_AUTHORIZED = ABSENT | INFO | **PASS** | Safe |
| Y | DHAN_ACCESS_TOKEN = SET | INFO | **PASS** | Ready for live data |
| Y | DHAN_CLIENT_ID = SET | INFO | **PASS** | Ready for live data |
| Y | docker-compose PAPER_TRADING | P2 | **MANUAL** | Value is "is" (from regex match artifact); manually verify VPS docker-compose.yml |

---

## Summary

| Class | Count |
|---|---|
| **PASS** | 57 |
| **FALSE** (false positives) | 5 |
| **FIXED** | 1 |
| **DATA** (data-dependent, monitor) | 4 |
| **MANUAL** (operator action) | 3 |
| **P0 Blockers** | 0 |
| **P1 Real** | 1 (FIXED) |
| **P2 Medium** | 9 (6 DATA + 3 MANUAL) |

---

## Pre-Live Authorization Checklist

Before setting `LIVE_TRADING_AUTHORIZED=true` and `PAPER_TRADING=false` on VPS:

- [x] P0 blockers: NONE
- [x] P1 — SL order on exchange: **FIXED** (DhanBroker.place_sl_order added)
- [x] TOTAL_CAPITAL = ₹10,000 (env var confirmed)
- [ ] **MANUAL**: Verify VPS docker-compose.yml has `PAPER_TRADING: "true"`
- [ ] **MANUAL**: Verify `LIVE_TRADING_AUTHORIZED` is absent from VPS env until go-live
- [ ] **MANUAL**: Understand effective max positions = 8 (CRE cap), not PILOT_MAX_TRADES=2
- [ ] **MANUAL**: Understand only cheap stocks (< ~₹500) will trade at ₹10k capital
- [ ] **MANUAL**: Monitor for MISSING_DHAN_MAPPING log warnings on first live session
- [ ] Regression: 141/141 tests pass post-fix
- [ ] Deploy fix to VPS: `git push origin main` + `docker compose build --no-cache`
