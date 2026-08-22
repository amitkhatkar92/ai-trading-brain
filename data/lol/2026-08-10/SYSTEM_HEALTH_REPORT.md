========================================================================
  SYSTEM HEALTH REPORT
  Date: 2026-08-10
  Generated: 2026-08-10 11:23:38 IST
  Overall: [ READY ]
========================================================================

HEALTH CHECK SUMMARY
--------------------
  Overall status:                          [ READY ]
  Checks passed:                           18/20
  Warnings:                                2
  Failures:                                0
  Blocking failures:                       0
  Health score:                            95%
  Duration:                                3.9s

DETAILED CHECKS
---------------
  ✓  System Clock:                         Clock: 2026-08-10 11:23:34 IST  (0ms)
  ✓  Python Version:                       Python 3.14  (0ms)
  ✓  Configuration:                        capital=₹10,000  broker=dhan  mode=LIVE  (5ms)
  ✓  Internet Connectivity:                Internet reachable  (519ms)
  ✓  Disk Space:                           75.3GB free  (1ms)
  ⚠  Memory:                               psutil not installed — memory check skipped  (1ms)
  ⚠  CPU Load:                             psutil not installed — CPU check skipped  (1ms)
  ✓  Market Calendar:                      Weekday Monday 2026-08-10  (0ms)
  ✓  Market Data Feed:                     NIFTY=24571  mode=LIVE  (2406ms)
  ✓  Broker Authentication:                Dhan token valid  expires_in=23h  (0ms)
  ✓  Broker Connectivity:                  Dhan credentials present — connectivity verified at startup  (0ms)
  ✓  Control Tower DB:                     control_tower.db  tables=4  (2ms)
  ✓  IIOS DB:                              iios.db  tables=4  (2ms)
  ✓  Feature Database:                     205,274 feature records  (785ms)
  ✓  Hypothesis Registry:                  16 hypothesis records  (1ms)
  ✓  Paper Trades Journal:                 paper_trades.csv  0KB  (0ms)
  ✓  Scientific Director:                  ScientificDirector importable  (56ms)
  ✓  Market Learning (MLC):                MarketLearningCoordinator importable  (84ms)
  ✓  Research Coordinator:                 ResearchCoordinator importable  (0ms)
  ✓  IKN Module:                           IKN module importable  (8ms)

========================================================================