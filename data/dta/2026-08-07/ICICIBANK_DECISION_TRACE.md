══════════════════════════════════════════════════════════════════════════════
  DTA-001 | DECISION TRACEABILITY AUDIT
  Symbol: ICICIBANK    Generated: 2026-08-07 12:20 IST
  DECISION TRACEABILITY AUDIT
══════════════════════════════════════════════════════════════════════════════

  SYMBOL:                          ICICIBANK
  DECISION:                        APPROVED
  CONFIDENCE:                      6.73/10
  STRATEGY:                        Breakout_Volume_RSI_HiVol
  CYCLE ID:                        1ea15c15-2f6
  CYCLE TIME:                      2026-03-18T10:30:06

  ────────────────────────────────────────────────────────────────────────────
  VERDICT: 10/10 questions answered with evidence  |  Decision: APPROVED  |  Confidence: 6.73/10
  ────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
  ▸ 12-LAYER DECISION CHAIN
──────────────────────────────────────────────────────────────────────────────

  LAYER 01: RAW MARKET DATA  [OK]
  ··············································································
    Date/Time:                       2026-03-18T10:30:06
    VIX:                             18.88
    Regime:                          range_market
    Market breadth:                  0.7200
    PCR:                             1.3700
    Distortion:                      NORMAL
    Trading allowed:                 True
    Size multiplier:                 1.00×

  LAYER 02: FEATURE EXTRACTION  [OK]
  ··············································································
    Feature record date:             2026-07-30 15:30
    Total features:                  51

    FEATURE                               VALUE
    ────────────────────────────────────────────
    rsi                                 70.3895
    rsi_overbought                       1.0000
    rsi_oversold                         0.0000
    macd_signal_norm                     1.0000
    macd_bull                            1.0000
    macd_bear                            0.0000
    volume_ratio_raw                     1.3881
    volume_spike                         0.0000
    mom_1d                               0.0069
    mom_5d                               0.0279
    mom_20d                              0.0947
    breadth                              0.5131
    pcr                                  0.4500
    vix                                  0.3500
    adx_score                            0.0000
    regime_score                         0.5000
    regime_bull                          0.0000
    regime_range                         1.0000
    global_bias                          0.5000
    sector_flow_count                    1.2000
    Forward return (recorded):       0.0000

  LAYER 03: PMCI SCORE / SCANNER SIGNAL  [OK]
  ··············································································
    Scanner direction:               BUY
    Scanner strategy:                Breakout_Volume
    Scanner confidence:              8.72/10
    Source agent:                    EquityScannerAI
    Regime probabilities:            
      bull_trend:                    0.452
      range:                         0.274
      volatile:                      0.224
      bear:                          0.050
    Dominant:                        bull_trend

    PMCI SUB-FACTORS:
    GROUP        FEATURE                           VALUE
    ──────────────────────────────────────────────────────
    MOMENTUM     mom_1d                           0.0069
    MOMENTUM     mom_5d                           0.0279
    MOMENTUM     mom_20d                          0.0947
    MOMENTUM     adx_score                        0.0000
                                                          
    VOLUME       volume_ratio_raw                 1.3881
    VOLUME       volume_spike                     0.0000
                                                          
    TECHNICAL    rsi                             70.3895
    TECHNICAL    rsi_overbought                   1.0000
    TECHNICAL    rsi_oversold                     0.0000
    TECHNICAL    macd_signal_norm                 1.0000
    TECHNICAL    macd_bull                        1.0000
    TECHNICAL    macd_bear                        0.0000
                                                          
    REGIME       regime_bull                      0.0000
    REGIME       regime_range                     1.0000
    REGIME       regime_score                     0.5000
    REGIME       global_bias                      0.5000
                                                          
    SENTIMENT    breadth                          0.5131
    SENTIMENT    pcr                              0.4500
    SENTIMENT    sector_flow_count                1.2000
                                                          

  LAYER 04: CDS SCORE / DECISION ENGINE
  ··············································································
    CDS COMPONENT SCORES:
    COMPONENT                       SCORE   WEIGHT
    ────────────────────────────────────────────────
    Technical Score                0.0000      N/A
    Risk Score                     0.0000      N/A
    Macro Score                    0.0000      N/A
    Regime Score                   0.0000      N/A
    ────────────────────────────────────────────────
    FINAL CONFIDENCE               6.7300     100%
    Position Modifier               0.794         

    Meta-top strategy:               Breakout_Volume
    Strategy allocation:             
      mean_reversion:                0.2740
      momentum:                      0.2484
      breakout:                      0.2033
      options_spread:                0.1857
      hedging:                       0.0886

  LAYER 05: INSTITUTIONAL DNA MATCHES  [MATCHED: 42]
  ··············································································
    Total DNA patterns evaluated:    124
    Matched (favorable direction):   42
    Winner DNA hits:                 0
    Loser DNA hits:                  0

    FEATURE                      DIR     CAT                      CONF   MATCH
    ──────────────────────────────────────────────────────────────────────────
    pcr                          BUY     edge_volatility         1.000   ✓ HIT
    sector_flow_count            BUY     edge_volatility         1.000   ✓ HIT
    sector_flow_count            BUY     edge_volatility         1.000   ✓ HIT
    macd_signal_norm             BUY     edge_momentum_volume    1.000   ✓ HIT
    pcr                          BUY     edge_volatility         1.000   ✓ HIT
    sector_flow_count            BUY     edge_volatility         1.000   ✓ HIT
    sector_flow_count            BUY     edge_volatility         1.000   ✓ HIT
    macd_signal_norm             BUY     edge_momentum_volume    1.000   ✓ HIT
    pcr                          BUY     edge_volatility         1.000   ✓ HIT
    sector_flow_count            BUY     edge_volatility         1.000   ✓ HIT
    sector_flow_count            BUY     edge_volatility         1.000   ✓ HIT
    macd_signal_norm             BUY     edge_momentum_volume    1.000   ✓ HIT
    global_bias                  BUY     edge_composite          0.917   ✓ HIT
    breadth                      BUY     edge_macro_flow         0.917   ✓ HIT
    global_bias                  BUY     edge_composite          0.917   ✓ HIT

  LAYER 06: KNOWLEDGE GRAPH (IKN) REFERENCES  [20 nodes]
  ··············································································
    NODE_TYPE              NAME                                         
    ──────────────────────────────────────────────────────────────────────
    DNA                    rsi_5::WINNERS_HIGHER
      └─ BELONGS_TO → [CLUSTER]CL-DNA
      └─ CO_OCCURS_WITH → [DNA]volume_ratio::WINNERS_HIGHER
    DNA                    volume_ratio::WINNERS_HIGHER
      └─ CO_OCCURS_WITH → [DNA]rsi_5::WINNERS_HIGHER
    EDGE                   EDGE-rsi_5
      └─ EVOLVED_TO → [DNA]rsi_5::WINNERS_HIGHER
    FEATURE                rsi_5
      └─ GENERALIZES → [DNA]rsi_5::WINNERS_HIGHER
      └─ REQUIRES → [PMCI_COMPONENT]SIGNAL_RSI
    FEATURE                volume_ratio
    STUDY                  HKAP-2021
      └─ DISCOVERED_IN → [DISCOVERY]DISC-001
      └─ GENERATED_BY → [DISCOVERY]DISC-001
    STUDY                  HKAP-2022
      └─ VALIDATED_BY → [HYPOTHESIS]HYP-001
    FINDING                FND-2021-01
      └─ CONTRADICTED_BY → [HYPOTHESIS]HYP-001
      └─ SPECIALIZES → [DISCOVERY]DISC-001
    HYPOTHESIS             HYP-001
      └─ CONTRADICTED_BY → [FINDING]FND-2021-01
      └─ SUPERSEDES → [HYPOTHESIS]HYP-002
    HYPOTHESIS             HYP-002
      └─ SUPERSEDES → [HYPOTHESIS]HYP-001
    DISCOVERY              DISC-001
      └─ DISCOVERED_IN → [STUDY]HKAP-2021
      └─ GENERATED_BY → [STUDY]HKAP-2021
    KNOWLEDGE_PACKAGE      HKAP-PKG-2021

  LAYER 07: HISTORICAL EVIDENCE
  ··············································································
    Total decision history records:  10

    DATE           DECISION    CONFIDENCE REGIME          STRATEGY
    ────────────────────────────────────────────────────────────────────────
    2026-03-18     APPROVED          6.73 range_market    Breakout_Volume_RSI_HiVol
    2026-03-18     APPROVED          6.72 range_market    Breakout_Volume_RSI_HiVol
    2026-03-17     APPROVED          6.71 range_market    Breakout_Volume_RSI_HiVol
    2026-03-17     APPROVED          6.71 range_market    Breakout_Volume_RSI_HiVol
    2026-03-17     APPROVED          6.72 range_market    Breakout_Volume_RSI_HiVol
    2026-03-17     APPROVED          6.72 range_market    Breakout_Volume_RSI_HiVol
    2026-03-16     APPROVED          7.26 range_market    Breakout_Volume_RSI_HiVol
    2026-03-16     APPROVED          7.26 range_market    Breakout_Volume_RSI_HiVol
    2026-03-16     APPROVED          7.26 range_market    Breakout_Volume_RSI_HiVol
    2026-03-16     APPROVED          7.21 range_market    Breakout_Volume_RSI_HiVol

  LAYER 08: RESEARCH STUDIES
  ··············································································
    • study002 [2026-08-01] — 'Study 002 — One-Year Historical Market Learning' | obs=0 | features matched: breadth
    • study002a [2026-08-03] — 'Study 2A — Winner DNA Discovery' | obs=280,909 | features matched: regime_score, mom_1d, gap_pct, mom_5d, mom_20d
    • ars_study_003 [2026-08-05] — 'Study 003 — Systematic Loser DNA Discovery' | obs=500 | features matched: vix_high, pcr, mom_10d, regime_bear, regime_score
    • ars_study_h001 [2026-08-05] — 'Study H001 — Loser DNA Cross-Year Validation' | obs=500 | features matched: pcr, mom_10d, volume_spike, volume_ratio, event_count
    • ars_study_irp002 [2026-08-06] — 'ars_study_irp002' | obs=500 | features matched: mom_5d

  LAYER 09: SCIENTIFIC DIRECTOR OBSERVATIONS
  ··············································································
    Confirmed hypotheses:            1
    Proposed hypotheses:             9
    ✓ CONFIRMED: [H2026-08-001] Loser DNA cross-year validation
    ○ PROPOSED:  [H2026-08-002] High-OOS low-support statistical significance
    ○ PROPOSED:  [H2026-08-003] Regime transition prediction
    ○ PROPOSED:  [H2026-08-004] Edge decay mechanism investigation
    ○ PROPOSED:  [H2026-08-005] Signal approval rate optimisation
    ○ PROPOSED:  [H2026-08-006] Sector rotation cycle mapping

  LAYER 10: RISK ANALYSIS  [PASSED]
  ··············································································
    Risk check:                      PASSED
    Monte Carlo simulation:          APPROVED
    Risk Guardian:                   APPROVED
    Position modifier:               0.794 (79% of max)
    Portfolio drawdown:              0.00%
    Open positions:                  0
    VIX level:                       18.88
    Regime:                          range_market
    Risk flags:                      None
    Kill switch thresholds:          VIX>45 | daily_loss>2% | NIFTY_drop>-5%

  LAYER 11: PORTFOLIO DECISION  [APPROVED]
  ··············································································
    Final decision:                  APPROVED
    Confidence score:                6.7300/10
    Approval threshold:              ≥6.5 partial-size  ≥6.8 full-size
    Strategy applied:                Breakout_Volume_RSI_HiVol
    Position modifier:               0.794

  LAYER 12: BROKER ORDER
  ··············································································
    Order status:                    PLACED (if paper trading) or LIVE
    Broker:                          Dhan (live) / Paper journal (PAPER_TRADING=True)
    Note:                            paper_trades.csv logs open/close if paper mode active
    Replay reference win rate:       50.0%
    Replay avg R-multiple:           0.750
    Replay profit factor:            3.96

──────────────────────────────────────────────────────────────────────────────
  ▸ 10 AUDIT QUESTIONS — Investment Committee Decision Reconstruction
──────────────────────────────────────────────────────────────────────────────

  Q1: Why BUY? (or: What drove this decision?)
  ··········································································
  [✓ ANSWERED]  Decision APPROVED — ICICIBANK cleared all 12 decision layers. Strategy: Breakout_Volume_RSI_HiVol. Final confidence: 6.73/10.

    • Scanner signal: direction=BUY  initial_confidence=8.72  strategy=Breakout_Volume
    • Market context: regime=range_market  VIX=18.9  breadth=0.720  PCR=1.37
    • Active edge fully satisfied: EDG_VOLATI_78_EE0000 (prec=78.3% oos_wr=59.3%), EDG_MOMENT_67_EE0003 (prec=67.6% oos_wr=85.0%), EDG_MOMENT_67_EE0004 (prec=67.2% oos_wr=76.5%)
    • DNA matches: 42 total  0 winner DNA  avg_confidence=0.903
    • Position modifier applied: 79.40% of full size (risk-adjusted entry)
    • Decision engine score: 6.73  position_modifier=0.794  regime=range_market  VIX=18.9

  Q2: Why were other stocks rejected? (Full scanner rejection audit)
  ··········································································
  [✓ ANSWERED]  16 stocks were scanned this cycle. Target (ICICIBANK) was selected. 11 others rejected or pre-filtered; 4 also approved. Rejection reasons by stock:

    • BANKBARODA       scan_conf=9.50  outcome=NOT_DECIDED   → Scanner found signal (conf=9.50) but did not reach decision engine — pre-filtere
    • TATASTEEL        scan_conf=8.97  outcome=NOT_DECIDED   → Scanner found signal (conf=8.97) but did not reach decision engine — pre-filtere
    • RELIANCE         scan_conf=8.48  outcome=APPROVED      gap_vs_target=+0.06  → Also APPROVED in this cycle (confidence=6.67)
    • BAJFINANCE       scan_conf=8.22  outcome=NOT_DECIDED   → Scanner found signal (conf=8.22) but did not reach decision engine — pre-filtere
    • POWERGRID        scan_conf=8.09  outcome=NOT_DECIDED   → Scanner found signal (conf=8.09) but did not reach decision engine — pre-filtere
    • LT               scan_conf=8.05  outcome=APPROVED      gap_vs_target=+0.18  → Also APPROVED in this cycle (confidence=6.55)
    • COALINDIA        scan_conf=8.04  outcome=APPROVED      gap_vs_target=+0.18  → Also APPROVED in this cycle (confidence=6.55)
    • NIFTY            scan_conf=8.00  outcome=NOT_DECIDED   → Scanner found signal (conf=8.00) but did not reach decision engine — pre-filtere
    • BANKNIFTY        scan_conf=8.00  outcome=NOT_DECIDED   → Scanner found signal (conf=8.00) but did not reach decision engine — pre-filtere
    • HDFCBANK         scan_conf=7.79  outcome=APPROVED      gap_vs_target=+0.25  → Also APPROVED in this cycle (confidence=6.48)
    • BANKNIFTY        scan_conf=7.75  outcome=NOT_DECIDED   → Scanner found signal (conf=7.75) but did not reach decision engine — pre-filtere
    • NIFTY            scan_conf=7.64  outcome=NOT_DECIDED   → Scanner found signal (conf=7.64) but did not reach decision engine — pre-filtere
    • ICICIBANK scanner rank: #3 of 16 stocks by initial confidence

  Q3: Which knowledge (IKN) contributed to this decision?
  ··········································································
  [✓ ANSWERED]  IKN graph contributed 20 nodes: 10 DNA, 4 study/discovery, 2 hypothesis, 4 other.

    • [DNA] rsi_5::WINNERS_HIGHER → BELONGS_TO → [CLUSTER]CL-DNA
    • [DNA] volume_ratio::WINNERS_HIGHER → CO_OCCURS_WITH → [DNA]rsi_5::WINNERS_HIGHER
    • [EDGE] EDGE-rsi_5 → EVOLVED_TO → [DNA]rsi_5::WINNERS_HIGHER
    • [FEATURE] rsi_5 → GENERALIZES → [DNA]rsi_5::WINNERS_HIGHER
    • [FEATURE] volume_ratio
    • [STUDY] HKAP-2021 → DISCOVERED_IN → [DISCOVERY]DISC-001
    • [STUDY] HKAP-2022 → VALIDATED_BY → [HYPOTHESIS]HYP-001
    • [FINDING] FND-2021-01 → CONTRADICTED_BY → [HYPOTHESIS]HYP-001
    • [HYPOTHESIS] HYP-001 → CONTRADICTED_BY → [FINDING]FND-2021-01
    • [HYPOTHESIS] HYP-002 → SUPERSEDES → [HYPOTHESIS]HYP-001

  Q4: Which DNA patterns contributed to this decision?
  ··········································································
  [✓ ANSWERED]  42/124 DNA patterns matched. Winner DNA: 0  Loser DNA warns: 0  High-confidence (lifecycle=ESTABLISHED/CONFIRMED_WINNER): 0

  Q5: Which PMCI factors mattered? (Scanner/signal sub-component scores)
  ··········································································
  [✓ ANSWERED]  PMCI composite: 8.72/10 broken into 7 sub-factor groups below.

    • PMCI composite score: 8.72/10  (strategy=Breakout_Volume  direction=BUY)
    • MOMENTUM: mom_1d=0.0069  mom_5d=0.0279  mom_20d=0.0947  adx_score=0.0000
    • VOLUME: volume_ratio_raw=1.3881  volume_spike=0.0000
    • TECHNICAL: rsi=70.3895  rsi_overbought=1.0000  rsi_oversold=0.0000  macd_signal_norm=1.0000  macd_bull=1.0000  macd_bear=0.0000
    • REGIME: regime_bull=0.0000  regime_range=1.0000  regime_score=0.5000  global_bias=0.5000
    • SENTIMENT: breadth=0.5131  pcr=0.4500  sector_flow_count=1.2000
    • EDGE CONFIRMATION: 25 active edge(s) fully satisfied — EDG_VOLATI_78_EE0000 (prec=78.3%), EDG_MOMENT_67_EE0003 (prec=67.6%), EDG_MOMENT_67_EE0004 (prec=67.2%)

  Q6: Which CDS factors mattered? (Decision engine sub-score breakdown)
  ··········································································
  [✓ ANSWERED]  CDS final score: 6.73/10 via 4 sub-components (technical + risk + macro + regime). Position modifier: 79% of max size.

    • Final confidence: 6.7300/10
    • Scanner (pre-CDS): 8.72/10
    • CDS adjustment: -1.99 (reduced by risk/regime filters)
    • POSITION MODIFIER: 0.794 (79% of max position) — applied by regime (range_market) and VIX (18.9)
    • STRATEGY ALLOCATION (meta-learning weights): mean_reversion=0.274  momentum=0.248  breakout=0.203

  Q7: Which historical studies supported this decision?
  ··········································································
  [✓ ANSWERED]  5 study files and 4 IKN study nodes reference features in this decision.

    • study002 [2026-08-01] — 'Study 002 — One-Year Historical Market Learning' | obs=0 | features matched: breadth
    • study002a [2026-08-03] — 'Study 2A — Winner DNA Discovery' | obs=280,909 | features matched: regime_score, mom_1d, gap_pct, mom_5d, mom_20d
    • ars_study_003 [2026-08-05] — 'Study 003 — Systematic Loser DNA Discovery' | obs=500 | features matched: vix_high, pcr, mom_10d, regime_bear, regime_score
    • ars_study_h001 [2026-08-05] — 'Study H001 — Loser DNA Cross-Year Validation' | obs=500 | features matched: pcr, mom_10d, volume_spike, volume_ratio, event_count
    • ars_study_irp002 [2026-08-06] — 'ars_study_irp002' | obs=500 | features matched: mom_5d
    • IKN [STUDY] HKAP-2021
    • IKN [STUDY] HKAP-2022
    • IKN [FINDING] FND-2021-01

  Q8: Which hypotheses supported this decision?
  ··········································································
  [✓ ANSWERED]  1 confirmed + 9 proposed hypotheses in registry. 2 hypothesis IKN nodes matched features.

    • ✓ CONFIRMED [H2026-08-001] Loser DNA cross-year validation (conf=0.48)
    • ○ PROPOSED  [H2026-08-002] High-OOS low-support statistical significance
    • ○ PROPOSED  [H2026-08-003] Regime transition prediction
    • ○ PROPOSED  [H2026-08-004] Edge decay mechanism investigation
    • ○ PROPOSED  [H2026-08-005] Signal approval rate optimisation
    • ○ PROPOSED  [H2026-08-006] Sector rotation cycle mapping
    • IKN [HYPOTHESIS] HYP-001
    • IKN [HYPOTHESIS] HYP-002

  Q9: What could have changed the decision? (Sensitivity / counterfactual)
  ··········································································
  [✓ ANSWERED]  7 counterfactual conditions identified that could flip this decision from APPROVED to the opposite outcome.

    • CONFIDENCE BUFFER: 0.23 pts above threshold. Decision would flip to REJECTED if confidence fell to < 6.5 (needs -0.23)
    • EDGE MARGIN 'EDG_VOLATI_78_EE0000': mom_1d=0.0069 is only 0.0020 units from breaking condition > 0.0049
    • EDGE MARGIN 'EDG_VOLATI_78_EE0000': pcr=0.4500 is only 0.0421 units from breaking condition > 0.4079
    • EDGE MARGIN 'EDG_MOMENT_67_EE0003': mom_10d=0.0396 is only 0.0644 units from breaking condition > -0.0248
    • VIX ESCALATION: If VIX rises from 18.9 above 30, position_modifier decreases and confidence drops below threshold
    • REGIME SHIFT: Current regime='range_market'. If regime transitions to 'volatile' or 'bear_market', breakout strategy weight drops → confidence below threshold
    • DNA FLIP: 7 high-confidence loser DNA patterns are NOT yet triggered. If volume_spike, volume_spike, volume_spike values shift to loser range, decision could reverse

  Q10: If this trade loses, what EXACTLY will be learned? (Named records)
  ··········································································
  [✓ ANSWERED]  If this trade results in a loss, 9 specific knowledge records will be updated (named below).

    • STRATEGY TRACKER ['Breakout_Volume_RSI_HiVol']: Will record 1 loss. Auto-disable triggers if consecutive losses reach threshold.
    • EDGE RECORD ['EDG_VOLATI_78_EE0000' ID=EDG_VOLATI_78_EE0000]: live_trades +1, live_wins unchanged. live_sharpe degrades. If below DECAYING threshold, status transitions ACTIVE → DECAYING.
    • EDGE RECORD ['EDG_MOMENT_67_EE0003' ID=EDG_MOMENT_67_EE0003]: live_trades +1, live_wins unchanged. live_sharpe degrades. If below DECAYING threshold, status transitions ACTIVE → DECAYING.
    • EDGE RECORD ['EDG_MOMENT_67_EE0004' ID=EDG_MOMENT_67_EE0004]: live_trades +1, live_wins unchanged. live_sharpe degrades. If below DECAYING threshold, status transitions ACTIVE → DECAYING.
    • HYPOTHESIS [H2026-08-001] 'Loser DNA cross-year validation': Counter-evidence recorded. If confirmation_rate drops below 50%, status may revert to PROPOSED.
    • HYPOTHESIS ENGINE: New hypothesis auto-generated: 'Breakout_Volume_RSI_HiVol BUY in range_market with VIX=18.9 has negative outcome' — enters registry for next study run.
    • META-LEARNING (regime_strategy_map): Strategy 'Breakout_Volume' in regime 'range_market' records 1 loss. k-NN weight updated on next retrain. Allocation weight reduces in subsequent cycle's strategy_mix.
    • IKN GRAPH: 3 study/discovery nodes referenced this trade. Loss outcome stored as evidence. Edge confidence re-weighted in next IKN update cycle.
    • KNN REGIME MODEL: Feature vector for ICICIBANK (regime=range_market, VIX=18.9) added to training set with label=LOSS. Model retrained in next walk-forward validation run.

──────────────────────────────────────────────────────────────────────────────
  ▸ REJECTION AUDIT — Why Other Stocks Were Not Selected
──────────────────────────────────────────────────────────────────────────────
    Scanner universe this cycle: 16 stocks scanned
    Target: ICICIBANK | Decision: APPROVED

    SYMBOL           SCAN_CONF OUTCOME       GAP_VS_TARGET  REJECTION REASON
    ──────────────────────────────────────────────────────────────────────────────────────────
    BANKBARODA            9.50 NOT_DECIDED             N/A  Scanner found signal (conf=9.50) but did not reach decision 
    TATASTEEL             8.97 NOT_DECIDED             N/A  Scanner found signal (conf=8.97) but did not reach decision 
    RELIANCE              8.48 APPROVED              +0.06  Also APPROVED in this cycle (confidence=6.67)
    BAJFINANCE            8.22 NOT_DECIDED             N/A  Scanner found signal (conf=8.22) but did not reach decision 
    POWERGRID             8.09 NOT_DECIDED             N/A  Scanner found signal (conf=8.09) but did not reach decision 
    LT                    8.05 APPROVED              +0.18  Also APPROVED in this cycle (confidence=6.55)
    COALINDIA             8.04 APPROVED              +0.18  Also APPROVED in this cycle (confidence=6.55)
    NIFTY                 8.00 NOT_DECIDED             N/A  Scanner found signal (conf=8.00) but did not reach decision 
    BANKNIFTY             8.00 NOT_DECIDED             N/A  Scanner found signal (conf=8.00) but did not reach decision 
    HDFCBANK              7.79 APPROVED              +0.25  Also APPROVED in this cycle (confidence=6.48)
    BANKNIFTY             7.75 NOT_DECIDED             N/A  Scanner found signal (conf=7.75) but did not reach decision 
    NIFTY                 7.64 NOT_DECIDED             N/A  Scanner found signal (conf=7.64) but did not reach decision 
    TITAN                 7.63 NOT_DECIDED             N/A  Scanner found signal (conf=7.63) but did not reach decision 
    SUNPHARMA             7.61 NOT_DECIDED             N/A  Scanner found signal (conf=7.61) but did not reach decision 
    DIVISLAB              7.61 NOT_DECIDED             N/A  Scanner found signal (conf=7.61) but did not reach decision 

──────────────────────────────────────────────────────────────────────────────
  ▸ ALTERNATIVE CANDIDATES (Same Cycle)
──────────────────────────────────────────────────────────────────────────────
    SYMBOL           DIRECTION   CONFIDENCE STRATEGY
    ──────────────────────────────────────────────────────────────
    BANKBARODA       BUY               9.50 Breakout_Volume
    TATASTEEL        BUY               8.97 Breakout_Volume
    RELIANCE         BUY               8.48 Breakout_Volume
    BAJFINANCE       BUY               8.22 Breakout_Volume
    POWERGRID        BUY               8.09 Breakout_Volume
    LT               BUY               8.05 Breakout_Volume
    COALINDIA        BUY               8.04 Breakout_Volume
    NIFTY            SHORT             8.00 Futures_Basis_Arb
    BANKNIFTY        SHORT             8.00 Futures_Basis_Arb
    HDFCBANK         BUY               7.79 Breakout_Volume
    BANKNIFTY        SELL              7.75 Short_Straddle_IV_Spike
    NIFTY            SELL              7.64 Short_Straddle_IV_Spike
    TITAN            BUY               7.63 Breakout_Volume
    SUNPHARMA        BUY               7.61 Breakout_Volume
    DIVISLAB         BUY               7.61 Breakout_Volume

──────────────────────────────────────────────────────────────────────────────
  ▸ ACTIVE EDGE CONDITIONS (Fully Evaluated)
──────────────────────────────────────────────────────────────────────────────

    [PARTIAL 1/4] EDG_MOMENT_86_EE0002
    precision=86%  sharpe=17.38  oos_wr=85%
       ✗   macd_signal_norm             <= 0.6361  (current=1.0)
       ✗   volume_ratio_raw             > 2.0109  (current=1.3880719231414087)
       ✓   volume_ratio_raw             <= 2.3279  (current=1.3880719231414087)
       ✗   adx_score                    > 0.0042  (current=0.0)

    [PARTIAL 1/4] EDG_COMPOS_73_EE0001
    precision=74%  sharpe=7.68  oos_wr=71%
       ?   intra_range                  > 0.0219  (current='N/A')
       ?   avg_conviction               <= 0.6215  (current='N/A')
       ✗   breadth                      <= 0.1695  (current=0.5131)
       ✓   breadth                      > 0.1411  (current=0.5131)

══════════════════════════════════════════════════════════════════════════════
  DTA-001 | Generated: 2026-08-07 12:20 IST
  READ-ONLY AUDIT — No knowledge was modified.
══════════════════════════════════════════════════════════════════════════════