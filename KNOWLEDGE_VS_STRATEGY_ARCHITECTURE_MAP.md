# Knowledge vs. Strategy Architecture Map
## AI Trading Brain — Pipeline Trace
**Audit:** KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001  
**Date:** 2026-08-14  
**Methodology:** Read-only trace from actual source code; no production changes made.

---

## 1. Source Files Traced

| File | Role |
|---|---|
| `opportunity_engine/equity_scanner_ai.py` | Knowledge layer — signal generation |
| `strategy_lab/meta_strategy_controller.py` | Strategy gate — regime matching + quality filter |
| `decision_ai/decision_engine.py` | Debate orchestration + threshold decision |
| `models/trade_signal.py` | Signal data model (TradeSignal) |
| `risk_control/capital_risk_engine.py` | Position sizing |
| `risk_guardian/risk_guardian.py` | Kill-switch logic |
| `execution_engine/order_manager.py` | Order routing |

---

## 2. Full Pipeline (9 Layers, Sequential)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: UNIVERSE                                                            │
│ Source: nifty500_universe.json                                               │
│ n = 230 stocks (phase D pre-filtered from 500)                              │
│ Role: Defines the eligible investment universe                               │
│ Data: Symbol, exchange, sector                                               │
│ Output: 230 candidate symbols per cycle                                      │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: PHASE D SCANNER (market_scanner.py)                                 │
│ Role: Broad opportunity filter                                               │
│ Logic: ATR momentum + basic technical score ≥ 0.55                          │
│ Data: Price, volume, ATR from yfinance                                       │
│ Output: ~54 candidates per day → daily_candidates.json                      │
│ Classification: KNOWLEDGE layer                                              │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: EQUITY SCANNER AI (EquityScannerAI)                                │
│ File: opportunity_engine/equity_scanner_ai.py                                │
│ Role: Core signal factory                                                    │
│ Classification: PRIMARY KNOWLEDGE LAYER                                      │
│                                                                              │
│ What it computes:                                                            │
│  - entry_price (current ask / LTP)                                           │
│  - stop_loss (entry - 1.5×ATR14)                                            │
│  - target (entry + 3×ATR14 for standard; adjusted per strategy)             │
│  - atr (ATR14 from yfinance history)                                        │
│  - confidence (base score from technical indicators)                         │
│  - strategy_name (selected from active registry)                            │
│  - direction (LONG / SHORT)                                                  │
│  - expected_move_pct = (ATR14 / entry) × RR × 100  ← OBSERVATIONAL ONLY   │
│  - _obs_candidate_score (MOP-RC-001 observer field)                         │
│  - _obs_regime (MOP-RC-001 observer field)                                  │
│                                                                              │
│ Technical indicators used (KNOWLEDGE inputs):                                │
│  - RSI (14) — momentum, overbought/oversold                                 │
│  - MACD — trend direction                                                    │
│  - Volume ratio (current / 20d avg) — volume surge                          │
│  - 20 DMA — trend alignment                                                  │
│  - Bollinger Bands — mean reversion zones                                    │
│  - ATR (14) — volatility / range                                             │
│  - Support / resistance levels                                               │
│                                                                              │
│ TradeSignal output → sent to Layer 4                                        │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: META-STRATEGY CONTROLLER (MetaStrategyController)                  │
│ File: strategy_lab/meta_strategy_controller.py                               │
│ + StrategyHealthMonitor                                                      │
│ Classification: STRATEGY GATE — MANDATORY, RUNS BEFORE DEBATE               │
│                                                                              │
│ Two sub-gates run in sequence:                                               │
│                                                                              │
│ Sub-gate A: Regime Matching                                                  │
│  - Current regime → valid strategy list                                      │
│  - range_market → [Mean_Reversion, Iron_Condor_Range, Breakout_Volume]     │
│  - bull_trend   → [Momentum_Retest, Trend_Pullback, Breakout_Volume]       │
│  - bear_trend   → [Defensive_Short, Hedging_Model]                          │
│  - Signal whose strategy ∉ valid list → BLOCKED (never reaches debate)     │
│                                                                              │
│ Sub-gate B: Quality Gate (StrategyHealthMonitor)                             │
│  REQUIREMENT: win_rate ≥ 0.50 AND sharpe > 0.8                             │
│  - Checked against learning_db.json → strategy_stats                        │
│  - FAIL → strategy disabled → signals BLOCKED with EARLY_ABORT_LOW_WR      │
│                                                                              │
│ As of 2026-08-14 quality gate status (from learning_db):                    │
│  - Mean_Reversion:       WR=16.7% (36 trades) → DISABLED                   │
│  - Momentum_Retest:      WR= 7.0% (43 trades) → DISABLED                   │
│  - Trend_Pullback:       WR= 0.0% (5 trades)  → DISABLED                   │
│  - EDG_MOMENT_95_EE0000: WR=12.5% (8 trades)  → DISABLED                   │
│  - EDG_MOMENT_100_EE0005: WR=0.0% (8 trades)  → DISABLED                   │
│  - Bull_Call_Spread:     WR= 0.0% (4 trades)  → DISABLED                   │
│                                                                              │
│ Effect: ALL strategies that have collected ≥5 samples are disabled.         │
│ Only Breakout_Volume, Hedging_Model, and new evolved strategies pass.       │
│                                                                              │
│ Output: TradeSignal with strategy_name confirmed → passed to Layer 5        │
│         OR BLOCKED → recorded as EARLY_ABORT_LOW_WR in signal_births       │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ (only signals that pass Layer 4 continue)
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: DEBATE AGENTS (5 AI Agents)                                         │
│ File: decision_ai/debate_agents.py, agent modules                            │
│ Classification: KNOWLEDGE-ENHANCED REASONING                                │
│                                                                              │
│ Agent 1: TechnicalAnalystAI    weight=0.30                                  │
│  Inputs: RSI, MACD, BB, ATR, volume, pattern recognition                    │
│  Output: technical_score (0-10)                                             │
│                                                                              │
│ Agent 2: MacroAnalystAI        weight=0.20                                  │
│  Inputs: GlobalSnapshot (S&P, Nikkei, bonds, FX), VIX, FII flow            │
│  Output: macro_score (0-10)                                                 │
│                                                                              │
│ Agent 3: RiskDebateAI          weight=0.25                                  │
│  Inputs: portfolio exposure, SL size, ATR, beta, sector concentration       │
│  Output: risk_score (0-10), hard_reject flag                                │
│                                                                              │
│ Agent 4: SentimentAI           weight=0.15                                  │
│  Inputs: options PCR, FII/DII net, news sentiment (when available)          │
│  Output: sentiment_score (0-10)                                             │
│                                                                              │
│ Agent 5: RegimeDebateAI        weight=0.10                                  │
│  Inputs: market regime label, breadth, advance/decline ratio                │
│  Output: regime_score (0-10)                                                │
│                                                                              │
│ Optional: InstitutionalDNAAI   weight=0.08 (DNA evidence only)             │
│                                                                              │
│ Any agent hard_reject → immediate REJECT (does not reach Layer 6)           │
│ Output: weighted composite score → passed to Layer 6                        │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: DECISION ENGINE (DecisionEngine)                                    │
│ File: decision_ai/decision_engine.py                                         │
│ Classification: FINAL KNOWLEDGE + CONTEXT GATE                              │
│                                                                              │
│ Threshold logic:                                                             │
│  - VIX < 20:  threshold = 6.5                                               │
│  - VIX 20-25: threshold = 6.6                                               │
│  - VIX 25-30: threshold = 6.7                                               │
│  - VIX > 30:  threshold = 6.9                                               │
│  - VIX > 45:  KILL (all trading halted)                                     │
│                                                                              │
│ Asymmetry bonus (reduces threshold):                                         │
│  - RR ≥ 4.0 → -1.0 (threshold becomes 5.5)                                 │
│  - RR ≥ 3.0 → -0.5 (threshold becomes 6.0)                                 │
│                                                                              │
│ Decision:                                                                    │
│  - score ≥ threshold → APPROVED → logged to ct_decisions                   │
│  - score < threshold → REJECTED → logged to ct_decisions                   │
│  - Records: confidence, technical_score, risk_score, macro_score,           │
│             sentiment_score, regime_score, rejection_reason                  │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ (APPROVED signals only)
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 7: CAPITAL RISK ENGINE (CapitalRiskEngine)                            │
│ Role: Position sizing (SL-based, risk-per-trade)                            │
│ Logic: qty = floor(max_risk_₹ / (entry - stop_loss))                       │
│ At ₹10k capital: deployable≈₹5k, budget/trade≈₹900                         │
│ Effect: qty=0 if entry_price > budget (most large-cap rejected here)        │
│ Classification: RISK MANAGEMENT                                              │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 8: RISK GUARDIAN (RiskGuardian)                                        │
│ Kill conditions:                                                             │
│  - VIX > 45                                                                  │
│  - Daily loss > 2% of capital                                               │
│ Classification: RISK MANAGEMENT (final kill-switch)                         │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 9: ORDER MANAGER → DHAN BROKER                                         │
│ PAPER_TRADING=false, ACTIVE_BROKER=dhan                                     │
│ Dhan data API returning 451 → auto-fallback to yfinance                     │
│ Order routing: Dhan OrderManager                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Classification of Each Layer

| Layer | Layer Name | Classification | Who decides? |
|---|---|---|---|
| 1 | Universe | Static config | Human config |
| 2 | Phase D Scanner | KNOWLEDGE | ATR, volume filter |
| 3 | Equity Scanner AI | PRIMARY KNOWLEDGE | Technical indicators |
| 4A | Regime Matching | STRATEGY | Regime → strategy map |
| 4B | Quality Gate | STRATEGY | WR/Sharpe threshold |
| 5 | Debate Agents | KNOWLEDGE-AUGMENTED | 5 AI agents, macro, risk |
| 6 | Decision Engine | CONTEXT-AWARE FILTER | VIX-adjusted threshold |
| 7 | Capital Risk Engine | RISK MANAGEMENT | Kelly/SL sizing |
| 8 | Risk Guardian | RISK MANAGEMENT | Kill-switch |
| 9 | Order Manager | EXECUTION | Broker API |

---

## 4. Where Knowledge Enters the Pipeline

Knowledge flows from multiple sources and enters at different pipeline stages:

```
Technical Knowledge (Layers 2-3):
  ├── RSI, MACD, Bollinger Bands → entry/exit signals
  ├── Volume ratio (current/20d avg) → momentum confirmation
  ├── 20-day DMA → trend direction
  └── ATR → SL / target sizing

Macro Knowledge (Layer 5 — MacroAnalystAI):
  ├── S&P500, Nikkei, Hang Seng → global sentiment
  ├── USD/INR, VIX → risk environment
  └── FII net flow → institutional direction

Institutional / DNA Knowledge (Layer 5 — InstitutionalDNAAI):
  └── Historical institutional behaviour patterns (optional)

Market Structure Knowledge (Layer 5 — RegimeDebateAI):
  ├── Market regime (bull/range/bear)
  └── Breadth, advance/decline ratio

Historical Performance Knowledge (Layer 4B):
  └── learning_db.json → win_rate, sharpe per strategy
```

---

## 5. Where Strategy Enters the Pipeline

Strategy enters ONLY at Layer 4 (before Layers 5-6):

```
Layer 4A: Regime → Strategy mapping
  - Assigns valid strategies for current market regime
  - Source: meta_strategy_controller.py REGIME_STRATEGY_MAP

Layer 4B: Quality gate
  - Enforces min WR ≥ 50%, Sharpe > 0.8
  - Source: learning_db.json strategy_stats
  - Effect as of 2026-08-14: ALL strategies disabled (WR all < 20%)
```

**Critical architectural fact:** Strategy gate (Layer 4) runs BEFORE debate agents (Layer 5). A signal blocked at Layer 4 never receives debate evaluation. The debate agents only see signals that already passed the strategy gate.

---

## 6. Data Flow Diagram

```
230 stocks
    │
    │ Phase D filter (ATR score ≥ 0.55)
    ▼
~54 candidates/day  ←── Knowledge: volume, price, ATR
    │
    │ EquityScannerAI._identify_setup()
    ▼
TradeSignal(entry, SL, target, atr, strategy_name, confidence)
    │
    │ MetaStrategyController + StrategyHealthMonitor
    │
    ├──[regime mismatch]──► BLOCKED (never seen again)
    ├──[WR < 50%]─────────► BLOCKED (EARLY_ABORT_LOW_WR → signal_births)
    │
    ▼ (passes gate)
Debate(5 agents) × weights
    │
    │ composite_score = Σ(agent_score × weight)
    │
    ├──[score < threshold]─► REJECTED (→ ct_decisions rejected)
    │
    ▼ (score ≥ threshold)
APPROVED (→ ct_decisions approved)
    │
    ▼
CRE sizing → QTY_ZERO if budget < entry_price
    │
    ▼
RiskGuardian kill-switch check
    │
    ▼
OrderManager → Dhan / Paper log
```

---

## 7. Key Architectural Gaps Identified

| Gap ID | Description | Impact |
|---|---|---|
| G1 | OIOS signal_births has `actual_move_pct=0`, `final_state=UNKNOWN` for ALL 3335 rows | Cannot compare strategy-gated vs ungated outcomes empirically |
| G2 | `ml_performance_dataset.json` has 21 rows from ONE date (2026-05-13) only | ML training data insufficient for regime analysis |
| G3 | `closed_orders_*.txt` files store order IDs (not JSON P&L records) | Cannot reconstruct historical strategy P&L from these files |
| G4 | Strategy gate blocks signals BEFORE debate agents see them | Debate layer cannot evaluate (and potentially approve) blocked signals |
| G5 | `above_20dma` and `volume_ratio` — strongest knowledge features — not used as primary scanner filters | Signals selected by other criteria; feature value not maximized |
| G6 | All tracked strategies have WR < 20% (far below 50% threshold) | System is in governance-suspended state; only evolved strategies trade |

---

*Architecture trace completed: 2026-08-14. Source files read: 4. Data sources: 5 databases. No production changes made.*
