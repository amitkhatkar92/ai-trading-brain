══════════════════════════════════════════════════════════════════════════════
  DTA-001 | DECISION TRACEABILITY AUDIT
  Symbol: BRITANNIA    Generated: 2026-08-07 12:20 IST
  DECISION TRACEABILITY AUDIT
══════════════════════════════════════════════════════════════════════════════

  SYMBOL:                          BRITANNIA
  DECISION:                        APPROVED
  CONFIDENCE:                      7.25/10
  STRATEGY:                        Mean_Reversion_RSI_HiVol
  CYCLE ID:                        2efef22a-7a2
  CYCLE TIME:                      2026-03-16T15:51:13

  ────────────────────────────────────────────────────────────────────────────
  VERDICT: 9/10 questions answered with evidence  |  Decision: APPROVED  |  Confidence: 7.25/10
  ────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
  ▸ 12-LAYER DECISION CHAIN
──────────────────────────────────────────────────────────────────────────────

  LAYER 01: RAW MARKET DATA  [OK]
  ··············································································
    Date/Time:                       2026-03-16T15:51:13
    VIX:                             14.15
    Regime:                          range_market
    Market breadth:                  0.3800
    PCR:                             0.9000
    Distortion:                      LOW
    Trading allowed:                 True
    Size multiplier:                 1.00×

  LAYER 02: FEATURE EXTRACTION  [N/A]
  ··············································································
    [No feature record found in EDE database for this symbol]

  LAYER 03: PMCI SCORE / SCANNER SIGNAL  [OK]
  ··············································································
    Scanner direction:               SHORT
    Scanner strategy:                Mean_Reversion
    Scanner confidence:              8.50/10
    Source agent:                    EquityScannerAI
    Regime probabilities:            
      bull_trend:                    0.039
      range:                         0.774
      volatile:                      0.014
      bear:                          0.173
    Dominant:                        range_market

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
    FINAL CONFIDENCE               7.2500     100%
    Position Modifier               0.931         

    Meta-top strategy:               Breakout_Volume
    Strategy allocation:             
      mean_reversion:                0.7745
      hedging:                       0.1159
      options_spread:                0.0711
      momentum:                      0.0212
      breakout:                      0.0174

  LAYER 05: INSTITUTIONAL DNA MATCHES  [MATCHED: 0]
  ··············································································
    Total DNA patterns evaluated:    124
    Matched (favorable direction):   0
    Winner DNA hits:                 0
    Loser DNA hits:                  0

    FEATURE                      DIR     CAT                      CONF   MATCH
    ──────────────────────────────────────────────────────────────────────────
    pcr                          BUY     edge_volatility         1.000      -
    sector_flow_count            BUY     edge_volatility         1.000      -
    sector_flow_count            BUY     edge_volatility         1.000      -
    macd_signal_norm             BUY     edge_momentum_volume    1.000      -
    pcr                          BUY     edge_volatility         1.000      -
    sector_flow_count            BUY     edge_volatility         1.000      -
    sector_flow_count            BUY     edge_volatility         1.000      -
    macd_signal_norm             BUY     edge_momentum_volume    1.000      -
    pcr                          BUY     edge_volatility         1.000      -
    sector_flow_count            BUY     edge_volatility         1.000      -
    sector_flow_count            BUY     edge_volatility         1.000      -
    macd_signal_norm             BUY     edge_momentum_volume    1.000      -
    volume_spike                 SHORT   loser                   1.000      -
    volume_spike                 SHORT   loser                   1.000      -
    global_bias                  BUY     edge_composite          0.917      -

  LAYER 06: KNOWLEDGE GRAPH (IKN) REFERENCES  [7 nodes]
  ··············································································
    NODE_TYPE              NAME                                         
    ──────────────────────────────────────────────────────────────────────
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
    2026-03-16     APPROVED          7.17 bull_trend      EDG_MACRO__78_EE0000
    2026-03-13     APPROVED          6.75 range_market    Mean_Reversion_RSI_HiVol
    2026-03-13     APPROVED          6.67 bull_trend      EDG_MACRO__78_EE0000
    2026-03-13     APPROVED          6.34 bull_trend      Trend_Pullback
    2026-03-13     APPROVED          6.34 bull_trend      Trend_Pullback
    2026-03-13     APPROVED          7.30 bull_trend      Momentum_Retest
    2026-03-13     APPROVED          6.34 bull_trend      Trend_Pullback
    2026-03-13     APPROVED          7.30 bull_trend      Momentum_Retest
    2026-03-13     APPROVED          6.79 bull_trend      Breakout_Volume_RSI_HiVol
    2026-03-13     APPROVED          7.30 bull_trend      Momentum_Retest

  LAYER 08: RESEARCH STUDIES
  ··············································································
    [No study references matched current feature set]

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
    Position modifier:               0.931 (93% of max)
    Portfolio drawdown:              0.00%
    Open positions:                  0
    VIX level:                       14.15
    Regime:                          range_market
    Risk flags:                      
    ! {'rejected': 6}
    Kill switch thresholds:          VIX>45 | daily_loss>2% | NIFTY_drop>-5%

  LAYER 11: PORTFOLIO DECISION  [APPROVED]
  ··············································································
    Final decision:                  APPROVED
    Confidence score:                7.2500/10
    Approval threshold:              ≥6.5 partial-size  ≥6.8 full-size
    Strategy applied:                Mean_Reversion_RSI_HiVol
    Position modifier:               0.931

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
  [✓ ANSWERED]  Decision APPROVED — BRITANNIA cleared all 12 decision layers. Strategy: Mean_Reversion_RSI_HiVol. Final confidence: 7.25/10.

    • Scanner signal: direction=SHORT  initial_confidence=8.50  strategy=Mean_Reversion
    • Market context: regime=range_market  VIX=14.2  breadth=0.380  PCR=0.90
    • Position modifier applied: 93.10% of full size (risk-adjusted entry)
    • Decision engine score: 7.25  position_modifier=0.931  regime=range_market  VIX=14.2

  Q2: Why were other stocks rejected? (Full scanner rejection audit)
  ··········································································
  [✓ ANSWERED]  15 stocks were scanned this cycle. Target (BRITANNIA) was selected. 14 others rejected or pre-filtered; 0 also approved. Rejection reasons by stock:

    • TATASTEEL        scan_conf=8.50  outcome=NOT_DECIDED   → Scanner found signal (conf=8.50) but did not reach decision engine — pre-filtere
    • SUNPHARMA        scan_conf=8.50  outcome=NOT_DECIDED   → Scanner found signal (conf=8.50) but did not reach decision engine — pre-filtere
    • DRREDDY          scan_conf=8.50  outcome=NOT_DECIDED   → Scanner found signal (conf=8.50) but did not reach decision engine — pre-filtere
    • NIFTY            scan_conf=8.00  outcome=NOT_DECIDED   → Scanner found signal (conf=8.00) but did not reach decision engine — pre-filtere
    • BANKNIFTY        scan_conf=8.00  outcome=NOT_DECIDED   → Scanner found signal (conf=8.00) but did not reach decision engine — pre-filtere
    • NTPC             scan_conf=7.85  outcome=NOT_DECIDED   → Scanner found signal (conf=7.85) but did not reach decision engine — pre-filtere
    • BANKNIFTY        scan_conf=7.75  outcome=NOT_DECIDED   → Scanner found signal (conf=7.75) but did not reach decision engine — pre-filtere
    • NIFTY            scan_conf=7.64  outcome=NOT_DECIDED   → Scanner found signal (conf=7.64) but did not reach decision engine — pre-filtere
    • NIFTYBEES        scan_conf=7.50  outcome=NOT_DECIDED   → Scanner found signal (conf=7.50) but did not reach decision engine — pre-filtere
    • BANKBEES         scan_conf=7.50  outcome=NOT_DECIDED   → Scanner found signal (conf=7.50) but did not reach decision engine — pre-filtere
    • NESTLEIND        scan_conf=6.50  outcome=NOT_DECIDED   → Scanner found signal (conf=6.50) but did not reach decision engine — pre-filtere
    • TITAN            scan_conf=6.50  outcome=NOT_DECIDED   → Scanner found signal (conf=6.50) but did not reach decision engine — pre-filtere
    • BRITANNIA scanner rank: #1 of 15 stocks by initial confidence

  Q3: Which knowledge (IKN) contributed to this decision?
  ··········································································
  [✓ ANSWERED]  IKN graph contributed 7 nodes: 0 DNA, 4 study/discovery, 2 hypothesis, 1 other.

    • [STUDY] HKAP-2021 → DISCOVERED_IN → [DISCOVERY]DISC-001
    • [STUDY] HKAP-2022 → VALIDATED_BY → [HYPOTHESIS]HYP-001
    • [FINDING] FND-2021-01 → CONTRADICTED_BY → [HYPOTHESIS]HYP-001
    • [HYPOTHESIS] HYP-001 → CONTRADICTED_BY → [FINDING]FND-2021-01
    • [HYPOTHESIS] HYP-002 → SUPERSEDES → [HYPOTHESIS]HYP-001
    • [DISCOVERY] DISC-001 → DISCOVERED_IN → [STUDY]HKAP-2021
    • [KNOWLEDGE_PACKAGE] HKAP-PKG-2021

  Q4: Which DNA patterns contributed to this decision?
  ··········································································
  [~ PARTIAL]  No DNA patterns matched. Decision made on scanner/edge signals only.

  Q5: Which PMCI factors mattered? (Scanner/signal sub-component scores)
  ··········································································
  [✓ ANSWERED]  PMCI composite: 8.50/10 broken into 1 sub-factor groups below.

    • PMCI composite score: 8.50/10  (strategy=Mean_Reversion  direction=SHORT)

  Q6: Which CDS factors mattered? (Decision engine sub-score breakdown)
  ··········································································
  [✓ ANSWERED]  CDS final score: 7.25/10 via 4 sub-components (technical + risk + macro + regime). Position modifier: 93% of max size.

    • Final confidence: 7.2500/10
    • Scanner (pre-CDS): 8.50/10
    • CDS adjustment: -1.25 (reduced by risk/regime filters)
    • POSITION MODIFIER: 0.931 (93% of max position) — applied by regime (range_market) and VIX (14.2)
    • STRATEGY ALLOCATION (meta-learning weights): mean_reversion=0.774  hedging=0.116  options_spread=0.071

  Q7: Which historical studies supported this decision?
  ··········································································
  [✓ ANSWERED]  0 study files and 4 IKN study nodes reference features in this decision.

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
  [✓ ANSWERED]  4 counterfactual conditions identified that could flip this decision from APPROVED to the opposite outcome.

    • CONFIDENCE BUFFER: 0.75 pts above threshold. Decision would flip to REJECTED if confidence fell to < 6.5 (needs -0.75)
    • VIX ESCALATION: If VIX rises from 14.2 above 30, position_modifier decreases and confidence drops below threshold
    • REGIME SHIFT: Current regime='range_market'. If regime transitions to 'volatile' or 'bear_market', breakout strategy weight drops → confidence below threshold
    • DNA FLIP: 7 high-confidence loser DNA patterns are NOT yet triggered. If volume_spike, volume_spike, volume_spike values shift to loser range, decision could reverse

  Q10: If this trade loses, what EXACTLY will be learned? (Named records)
  ··········································································
  [✓ ANSWERED]  If this trade results in a loss, 6 specific knowledge records will be updated (named below).

    • STRATEGY TRACKER ['Mean_Reversion_RSI_HiVol']: Will record 1 loss. Auto-disable triggers if consecutive losses reach threshold.
    • HYPOTHESIS [H2026-08-001] 'Loser DNA cross-year validation': Counter-evidence recorded. If confirmation_rate drops below 50%, status may revert to PROPOSED.
    • HYPOTHESIS ENGINE: New hypothesis auto-generated: 'Mean_Reversion_RSI_HiVol BUY in range_market with VIX=14.2 has negative outcome' — enters registry for next study run.
    • META-LEARNING (regime_strategy_map): Strategy 'Breakout_Volume' in regime 'range_market' records 1 loss. k-NN weight updated on next retrain. Allocation weight reduces in subsequent cycle's strategy_mix.
    • IKN GRAPH: 3 study/discovery nodes referenced this trade. Loss outcome stored as evidence. Edge confidence re-weighted in next IKN update cycle.
    • KNN REGIME MODEL: Feature vector for BRITANNIA (regime=range_market, VIX=14.2) added to training set with label=LOSS. Model retrained in next walk-forward validation run.

──────────────────────────────────────────────────────────────────────────────
  ▸ REJECTION AUDIT — Why Other Stocks Were Not Selected
──────────────────────────────────────────────────────────────────────────────
    Scanner universe this cycle: 15 stocks scanned
    Target: BRITANNIA | Decision: APPROVED

    SYMBOL           SCAN_CONF OUTCOME       GAP_VS_TARGET  REJECTION REASON
    ──────────────────────────────────────────────────────────────────────────────────────────
    TATASTEEL             8.50 NOT_DECIDED             N/A  Scanner found signal (conf=8.50) but did not reach decision 
    SUNPHARMA             8.50 NOT_DECIDED             N/A  Scanner found signal (conf=8.50) but did not reach decision 
    DRREDDY               8.50 NOT_DECIDED             N/A  Scanner found signal (conf=8.50) but did not reach decision 
    NIFTY                 8.00 NOT_DECIDED             N/A  Scanner found signal (conf=8.00) but did not reach decision 
    BANKNIFTY             8.00 NOT_DECIDED             N/A  Scanner found signal (conf=8.00) but did not reach decision 
    NTPC                  7.85 NOT_DECIDED             N/A  Scanner found signal (conf=7.85) but did not reach decision 
    BANKNIFTY             7.75 NOT_DECIDED             N/A  Scanner found signal (conf=7.75) but did not reach decision 
    NIFTY                 7.64 NOT_DECIDED             N/A  Scanner found signal (conf=7.64) but did not reach decision 
    NIFTYBEES             7.50 NOT_DECIDED             N/A  Scanner found signal (conf=7.50) but did not reach decision 
    BANKBEES              7.50 NOT_DECIDED             N/A  Scanner found signal (conf=7.50) but did not reach decision 
    NESTLEIND             6.50 NOT_DECIDED             N/A  Scanner found signal (conf=6.50) but did not reach decision 
    TITAN                 6.50 NOT_DECIDED             N/A  Scanner found signal (conf=6.50) but did not reach decision 
    HDFCBANK              6.44 NOT_DECIDED             N/A  Scanner found signal (conf=6.44) but did not reach decision 
    M&M                   5.91 NOT_DECIDED             N/A  Scanner found signal (conf=5.91) but did not reach decision 

──────────────────────────────────────────────────────────────────────────────
  ▸ ALTERNATIVE CANDIDATES (Same Cycle)
──────────────────────────────────────────────────────────────────────────────
    SYMBOL           DIRECTION   CONFIDENCE STRATEGY
    ──────────────────────────────────────────────────────────────
    TATASTEEL        SHORT             8.50 Mean_Reversion
    SUNPHARMA        SHORT             8.50 Mean_Reversion
    DRREDDY          SHORT             8.50 Mean_Reversion
    NIFTY            SHORT             8.00 Futures_Basis_Arb
    BANKNIFTY        SHORT             8.00 Futures_Basis_Arb
    NTPC             BUY               7.85 Breakout_Volume
    BANKNIFTY        SELL              7.75 Short_Straddle_IV_Spike
    NIFTY            SELL              7.64 Short_Straddle_IV_Spike
    NIFTYBEES        BUY               7.50 ETF_NAV_Arb
    BANKBEES         SELL              7.50 ETF_NAV_Arb
    NESTLEIND        BUY               6.50 Momentum_Retest
    TITAN            BUY               6.50 Momentum_Retest
    HDFCBANK         BUY               6.44 Mean_Reversion
    M&M              BUY               5.91 Mean_Reversion

──────────────────────────────────────────────────────────────────────────────
  ▸ ACTIVE EDGE CONDITIONS (Fully Evaluated)
──────────────────────────────────────────────────────────────────────────────

    [PARTIAL 0/4] EDG_MOMENT_86_EE0002
    precision=86%  sharpe=17.38  oos_wr=85%
       ?   macd_signal_norm             <= 0.6361  (current='N/A')
       ?   volume_ratio_raw             > 2.0109  (current='N/A')
       ?   volume_ratio_raw             <= 2.3279  (current='N/A')
       ?   adx_score                    > 0.0042  (current='N/A')

    [PARTIAL 0/4] EDG_COMPOS_73_EE0001
    precision=74%  sharpe=7.68  oos_wr=71%
       ?   intra_range                  > 0.0219  (current='N/A')
       ?   avg_conviction               <= 0.6215  (current='N/A')
       ?   breadth                      <= 0.1695  (current='N/A')
       ?   breadth                      > 0.1411  (current='N/A')

══════════════════════════════════════════════════════════════════════════════
  DTA-001 | Generated: 2026-08-07 12:20 IST
  READ-ONLY AUDIT — No knowledge was modified.
══════════════════════════════════════════════════════════════════════════════