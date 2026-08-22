# FINAL_ARCHITECTURE_PROMOTION_POLICY_001
**Status:** ACTIVE  
**Date:** 2026-08-18  
**Applies to:** FINAL_TRADING_ARCHITECTURE_SHADOW_001  
**Linked architecture:** FINAL_KNOWLEDGE_LED_C2_ARCHITECTURE_001.md

---

## Purpose

This document defines the quantitative criteria that must be met before the shadow
C2 architecture transitions from **shadow observation** to **paper trading**, and
from paper trading to **live (limited capital) deployment**.

It also defines the criteria for **demoting** Strategy from "context" to "ignored",
or **promoting** Strategy to a genuine gate role.

---

## Stage 1 → Stage 2: Shadow → Paper Trading

**Minimum observation period:** 50 OOS trading days  
**All of the following must hold:**

| Gate | Threshold | Notes |
|------|-----------|-------|
| UP dir_acc (top-5) | ≥ 0.58 | Sustained above random (0.50) + margin |
| DOWN dir_acc (top-5) | ≥ 0.57 | Same rationale |
| UP ge2 rate | ≥ 0.22 | Minimum profitability floor |
| DOWN ge2 rate | ≥ 0.20 | |
| Sharpe proxy (dir_acc − 0.5) / std | > 0 | Positive risk-adjusted signal |
| No single regime dominates | ≥ 3 regimes observed | Avoid regime-specific bias |
| Lift (top-5 vs pool) | ≥ 1.15× both directions | C2 must still separate |

**Action:** Create paper trading mode in shadow script.  
**Capital:** Zero (paper only). No execution engine integration yet.

---

## Stage 2 → Stage 3: Paper → Live (Limited Capital)

**Minimum observation period:** 30 additional paper-trading days  
**Gates:**

| Gate | Threshold |
|------|-----------|
| Paper dir_acc UP | ≥ 0.58 |
| Paper dir_acc DOWN | ≥ 0.57 |
| Max single-day drawdown | < 4% hypothetical |
| Strategy REJECT events | ≥ 20 (enough to evaluate Q5) |
| Model A ≥ Model B (dir_acc) | or within 2% — C2 stands on its own |

**Action:** Begin with ≤ 2 stocks/direction, ≤ ₹20,000 per position.  
**Capital controller:** `CapitalRiskEngine` (existing Layer 6) governs.

---

## Strategy Promotion/Demotion Gate (Q5 Evidence)

After **≥ 30 REJECT events** have been observed:

### Strategy Promotion to Gate Role

All of the following must hold:
1. Model B dir_acc > Model A dir_acc by **≥ 3 percentage points** consistently
2. Model B ge2_rate > Model A ge2_rate by **≥ 2 percentage points**
3. This holds across **≥ 2 different regime types** (not just BEAR)
4. **No look-ahead**: validated by independent out-of-sample computation

**Action:** Move Strategy from context → soft gate (flag, not block).  
**Never:** Move to hard veto without 100+ events and explicit human review.

### Strategy Demotion to "Ignored"

If **any** of:
1. Model A dir_acc > Model B dir_acc by **≥ 2 pp** (strategy hurts performance)
2. Model A ge2_rate > Model B ge2_rate consistently
3. Strategy fires on ≥ 30% of top-5 UP selections (too aggressive)

**Action:** Record `strategy_status` but stop using it even for Model B.  
Add `STRATEGY_DEMOTED` flag to daily summary.

---

## Invalidation Criteria (Architecture Must Be Redesigned)

The architecture is invalidated if any hold after **80 OOS days**:

| Criterion | Threshold |
|-----------|-----------|
| UP dir_acc (top-5) | < 0.53 for 20 consecutive days |
| DOWN dir_acc (top-5) | < 0.52 for 20 consecutive days |
| C2 lift < 1.0 | Top-5 worse than random pool draw |
| Regime collapse | All regime labels = same value for > 15 days |
| V3 pool < 10 | V3 consistently returns < 10 candidates per direction |

**Action:** Open ARCHITECTURE_REVIEW_002. Do not promote to live.

---

## Review Schedule

| Milestone | Action |
|-----------|--------|
| Day 10 | First informal check (sufficient pool? V3 working?) |
| Day 25 | Formal Q1-Q4 review (pool + C2 mechanics confirmed?) |
| Day 50 | Stage 1 → 2 gate review |
| Day 80 | Strategy Q5 sufficient evidence review |
| Day 80 + 30 paper | Stage 2 → 3 gate review |

---

## Responsible Decisions

| Decision | Who |
|----------|-----|
| Stage 1 → 2 promotion | Copilot agent + human confirmation |
| Stage 2 → 3 promotion | **Human confirmation required** |
| Strategy role change | Human confirmation required |
| Architecture invalidation | Human decision |
| Adding new C2 features | New research cycle required (not ad hoc) |

---

## What Is Never Permitted Without New Research

1. Changing the C2 formula (frozen: `gap_pct = (T1_open/T0_close−1)×100`)
2. Changing C2_TOP_N from 5 without a new OOS validation
3. Changing V3 pool size during active shadow collection
4. Adding Strategy as a hard veto on less than 100 OOS events
5. Promoting to live trading without paper trading phase
