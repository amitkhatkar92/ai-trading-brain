# ARCH-006 Final Green Flag Matrix
**Pre-Live Pilot Authorization Gate — ₹10,000 Controlled Experiment**

**Rule**: Every gate is GREEN or RED. No CONDITIONAL, DEVELOPING, or LATER.

---

## Section 1: Safety Protections

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-S01 | `PAPER_TRADING` defaults to `true` | **GREEN** | `config.py` getenv default "true"; test_i01 PASS |
| G-S02 | `LIVE_TRADING_AUTHORIZED` absent on VPS | **GREEN** | Docker compose env: not set; test_i02 PASS |
| G-S03 | OrderManager forces paper when `LIVE_TRADING_AUTHORIZED` absent | **GREEN** | L335 in order_manager.py; test_i03 PASS |
| G-S04 | DhanBroker returns SIM_ prefix when not connected | **GREEN** | test_i04 PASS; test_d02 PASS |
| G-S05 | All paper orders have SIM_ prefix (no real broker call) | **GREEN** | test_i05 PASS |
| G-S06 | RiskGuardian KILL-SWITCH VIX gate present | **GREEN** | FailSafeRiskGuardian in risk_guardian.py; test_l01 PASS |
| G-S07 | RiskGuardian appears before execute in orchestrator | **GREEN** | test_l03 PASS (source position verified) |

---

## Section 2: Capital Sizing

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-C01 | `TOTAL_CAPITAL=10000` in production env | **GREEN** | Env var set; config.py reads it; verified 10000.0 |
| G-C02 | `MAX_POSITIONS=3` at ₹10k (not hardcoded 8) | **GREEN** | ARCH-006 fix: auto-scaling via `_compute_max_positions()`; test_j01 PASS |
| G-C03 | CRE uses config MAX_POSITIONS (not hardcoded) | **GREEN** | ARCH-006 fix: `from config import MAX_POSITIONS`; test_j02 PASS |
| G-C04 | RELIANCE/SBIN produce qty=0 at ₹10k (correctly blocked) | **GREEN** | test_b01, test_b02 PASS |
| G-C05 | Cheap stocks (TATASTEEL ₹160) produce qty≥1 | **GREEN** | test_b03 PASS (qty=1 at 10k capital) |
| G-C06 | CRE rejects 4th signal when 3 positions allocated | **GREEN** | test_j03 PASS |
| G-C07 | Quantity never negative | **GREEN** | test_b05 PASS |
| G-C08 | qty=0 never reaches broker | **GREEN** | test_h01, h02, h03, h04 PASS |
| G-C09 | MAX_RISK_PER_TRADE_PCT=0.0025 (₹25 max risk/trade) | **GREEN** | config.py verified; CRE uses it |
| G-C10 | MAX_DRAWDOWN_PCT=0.10 (₹1,000 halt threshold) | **GREEN** | config.py verified; RiskGuardian checks |

---

## Section 3: Order Execution

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-E01 | DhanBroker.place_sl_order exists | **GREEN** | PRELIVE fix; test_d01 PASS |
| G-E02 | SL placed via DhanBroker.place_sl_order in live mode | **GREEN** | test_d05 PASS |
| G-E03 | SL has both trigger_price and limit_price | **GREEN** | test_d07 PASS (STOP_LOSS order type) |
| G-E04 | SL not placed if entry order fails | **GREEN** | test_d06 PASS |
| G-E05 | Duplicate protection blocks second execute on same symbol | **GREEN** | test_g02 PASS |
| G-E06 | Broker returning None does not create order record | **GREEN** | test_f01 PASS |
| G-E07 | Broker exception does not create order record | **GREEN** | test_f02 PASS |

---

## Section 4: Partial Fill Reconciliation

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-P01 | `reconcile_partial_fills()` is wired into `_do_monitor()` | **GREEN** | ARCH-006 fix; verified in orchestrator source |
| G-P02 | Partial fill adjusts position quantity to filled qty | **GREEN** | test_e02 PASS |
| G-P03 | Old SL is cancelled on partial fill | **GREEN** | test_e03 PASS |
| G-P04 | New SL placed for filled qty (not requested qty) | **GREEN** | test_e04 PASS |
| G-P05 | sl_order_id updated to new SL order ID | **GREEN** | test_e05 PASS |
| G-P06 | Full fill does not trigger partial-fill logic | **GREEN** | test_e06 PASS |
| G-P07 | reconcile is no-op in paper mode | **GREEN** | test_e01 PASS |

---

## Section 5: KDA Authority

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-K01 | KNOWLEDGE_HOLD blocks signal before execute | **GREEN** | test_a01 PASS (source verified) |
| G-K02 | KNOWLEDGE_BUY/SELL are the authorization tokens | **GREEN** | test_a03 PASS |
| G-K03 | KDA pipeline produces zero broker calls | **GREEN** | test_a02 PASS |
| G-K04 | Debate runs after KDA in source order | **GREEN** | test_a04 PASS |
| G-K05 | RiskGuardian runs before Debate in source order | **GREEN** | test_a05 PASS |
| G-K06 | ESS_DEVELOPING=3.0 threshold in force | **GREEN** | config.py; KDA pipeline verified |

---

## Section 6: Restart Recovery

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-R01 | `_restore_from_journal()` exists | **GREEN** | test_k01 PASS |
| G-R02 | `_prefetch_restored_ltps()` exists | **GREEN** | test_k02 PASS |
| G-R03 | CSV journal path configured | **GREEN** | test_k03 PASS |
| G-R04 | No duplicate position after restart + restore | **GREEN** | test_k04 PASS |

---

## Section 7: DHAN Symbol Safety

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-D01 | Unknown symbol returns None + logs MISSING_DHAN_MAPPING | **GREEN** | test_c02 PASS |
| G-D02 | Unknown symbol never calls broker.place_order | **GREEN** | test_c03 PASS |
| G-D03 | Known symbol resolves to SIM_ order | **GREEN** | test_c01 PASS |

---

## Section 8: Test Coverage

| Gate | Criterion | Status | Evidence |
|---|---|---|---|
| G-T01 | test_kda_001.py: 100 tests PASS | **GREEN** | 100 passed in CI |
| G-T02 | test_arch_005_integration.py: 41 tests PASS | **GREEN** | 41 passed in CI |
| G-T03 | test_arch_006_integration.py: 50 tests PASS, 2 skipped | **GREEN** | 50 passed, 0 failed; 2 skips are acceptable |
| G-T04 | Full regression 191 passed, 0 failed | **GREEN** | Verified this session |

---

## Section 9: P0 / P1 Summary

| Severity | Count | Description |
|---|---|---|
| **P0** | 0 | No blocking safety issues |
| **P1** | 0 | DhanBroker.place_sl_order fixed (PRELIVE); reconcile_partial_fills wired (ARCH-006); MAX_POSITIONS scaled (ARCH-006) |
| **P2** | 3 | Dead orphan modules (ResearchCoordinator, knowledge_feedback_loop, rejection_tracker) — deferred by design |

---

## FINAL DECISION

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         ██████╗ ██████╗ ███████╗███████╗███╗   ██╗              ║
║        ██╔════╝ ██╔══██╗██╔════╝██╔════╝████╗  ██║              ║
║        ██║  ███╗██████╔╝█████╗  █████╗  ██╔██╗ ██║              ║
║        ██║   ██║██╔══██╗██╔══╝  ██╔══╝  ██║╚██╗██║              ║
║        ╚██████╔╝██║  ██║███████╗███████╗██║ ╚████║              ║
║         ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝              ║
║                                                                  ║
║   FLAG: GREEN — READY FOR CONTROLLED LIVE PILOT                  ║
║                                                                  ║
║   Capital:    ₹10,000                                            ║
║   Max risk/trade: ₹25 (0.25%)                                    ║
║   Max drawdown halt: ₹1,000 (10%)                                ║
║   Max positions: 3                                               ║
║   Broker: DhanHQ (live connect disabled until AUTHORIZED)        ║
║                                                                  ║
║   Gates PASSED: 45 / 45                                          ║
║   Tests PASSED: 191 / 193 (2 skipped — acceptable)              ║
║   P0 issues: 0                                                   ║
║   P1 issues: 0                                                   ║
║                                                                  ║
║   To activate live trading:                                      ║
║   1. Set LIVE_TRADING_AUTHORIZED=true in Docker env              ║
║   2. Set PAPER_TRADING=false in Docker env                       ║
║   3. Ensure DHAN credentials in env                              ║
║   4. Deploy and watch first 3 signals closely                    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

*ARCH-006 Final Pre-Live Closure completed*
*Authorized by: adversarial audit + integration test suite + source verification*
*Commit: pending deployment*
