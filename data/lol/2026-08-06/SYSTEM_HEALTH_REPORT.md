========================================================================
  SYSTEM HEALTH REPORT
  Date: 2026-08-06
  Generated: 2026-08-06 12:45:42 IST
  Overall: [ NOT READY ]
========================================================================

HEALTH CHECK SUMMARY
--------------------
  Overall status:                          [ NOT READY ]
  Checks passed:                           17/20
  Warnings:                                2
  Failures:                                1
  Blocking failures:                       0
  Health score:                            90%
  Duration:                                2.6s

DETAILED CHECKS
---------------
  ✓  System Clock:                         Clock: 2026-08-06 12:45:40 IST  (0ms)
  ✓  Python Version:                       Python 3.14  (0ms)
  ✓  Configuration:                        capital=₹10,000,000  broker=dhan  mode=PAPER  (5ms)
  ✓  Internet Connectivity:                Internet reachable  (438ms)
  ✓  Disk Space:                           74.6GB free  (0ms)
  ⚠  Memory:                               psutil not installed — memory check skipped  (1ms)
  ⚠  CPU Load:                             psutil not installed — CPU check skipped  (0ms)
  ✓  Market Calendar:                      Weekday Thursday 2026-08-06  (0ms)
  ✓  Market Data Feed:                     NIFTY=24625  mode=LIVE  (1340ms)
  ✗  Broker Authentication:                Dhan token EXPIRED 92h ago  (0ms)
  ✓  Broker Connectivity:                  PAPER_TRADING=True — broker connectivity not required  (0ms)
  ✓  Control Tower DB:                     control_tower.db  tables=4  (0ms)
  ✓  IIOS DB:                              iios.db  tables=4  (2ms)
  ✓  Feature Database:                     205,274 feature records  (737ms)
  ✓  Hypothesis Registry:                  16 hypothesis records  (1ms)
  ✓  Paper Trades Journal:                 paper_trades.csv  0KB  (0ms)
  ✓  Scientific Director:                  ScientificDirector importable  (39ms)
  ✓  Market Learning (MLC):                MarketLearningCoordinator importable  (54ms)
  ✓  Research Coordinator:                 ResearchCoordinator importable  (0ms)
  ✓  IKN Module:                           IKN module importable  (5ms)

========================================================================