# Real-World Usage Examples

## Smart Execution + Correlation System

---

## Example 1: Bank Stock Heavy Day

### Scenario
It's 10 AM. The opportunity engine generates 8 signals:

```
HDFC       BUY   confidence=0.88  sector=BANK
ICICI      BUY   confidence=0.85  sector=BANK
AXIS       BUY   confidence=0.82  sector=BANK
SBIN       BUY   confidence=0.80  sector=BANK
KOTAK      BUY   confidence=0.78  sector=BANK
INFY       BUY   confidence=0.75  sector=IT
TCS        BUY   confidence=0.72  sector=IT
RELIANCE   SELL  confidence=0.70  sector=ENERGY
```

### System Process (First Filter: Correlation)

**Before Correlation:**
- 8 signals, looks like 8 independent bets
- Actually: 5 banking stocks = 1 correlated bet

**After CorrelationEngine.reduce_correlation():**
```
Sector BANK: has 5 trades, max 2 allowed
  → Keep top 2 by confidence:
    HDFC (0.88) ✓
    ICICI (0.85) ✓
    
  → Reject: AXIS, SBIN, KOTAK

Sector IT: has 2 trades, max 2 allowed
  → Keep both:
    INFY (0.75) ✓
    TCS (0.72) ✓

Sector ENERGY: has 1 trade
  → Keep:
    RELIANCE SELL (0.70) ✓

Output: 5 signals (reduced from 8)
```

### System Process (Second Filter: Smart Execution)

**Capital Management:**
```
Total Capital: $100,000
Max Exposure: $80,000 (80%)
Max Per Direction: $70,000
Max Per Sector: Already managed (2 per sector)
Current VIX: 17.5
Current Drawdown Factor: 1.0 (no losses yet)
```

**Position Sizing for each trade:**

1. **HDFC (BUY | Confidence 0.88)**
   - confidence_factor = min(0.88, 0.9) = 0.88
   - vix_factor = max(0.4, min(1.0, 1.0 - (17.5-15)/20)) = 0.875
   - position_size = 100k × 0.88 × 0.875 × 1.0 = $77,000
   - ✓ Would fit BUT:
     - Bullish exposure would become $77,000 (exceeds 70k limit)
   - → REJECTED: direction_limit_bullish

2. **HDFC Re-evaluated at Reduced Confidence Level:**
   - The engine processes INFY next (higher confidence adjustment)
   - Actually: INFY has lower confidence (0.75) but different sector
   - proceeds with INFY first

**Actual Execution Order (by confidence, after sector pass):**

1. **HDFC (BUY | 0.88)**
   - Size: $100k × 0.88 × 0.875 = $77,000
   - Check capital: $77k < $80k ✓
   - Check bullish: $77k > $70k ✗
   - **REJECTED: direction_limit_bullish**

2. **ICICI (BUY | 0.85)**
   - Size: $100k × 0.85 × 0.875 = $74,375
   - Check capital: $74,375 < $80k ✓
   - Check bullish (new): $74,375 > $70k ✗
   - **REJECTED: direction_limit_bullish**

3. **INFY (BUY | 0.75)**
   - Size: $100k × 0.75 × 0.875 = $65,625
   - Check capital: $65,625 < $80k ✓
   - Check bullish (new): $65,625 < $70k ✓
   - **ACCEPTED**
   - Running totals: capital=$65,625, bullish=$65,625

4. **TCS (BUY | 0.72)**
   - Size: $100k × 0.72 × 0.875 = $63,000
   - Check capital: $65,625 + $63,000 = $128,625 > $80k ✗
   - **REJECTED: capital_limit**

5. **RELIANCE (SELL | 0.70)**
   - Size: $100k × 0.70 × 0.875 = $61,250
   - Check capital: $65,625 + $61,250 = $126,875 > $80k ✗
   - **REJECTED: capital_limit**

### Final Output from SmartExecutionEngine

```
✅ Accepted: 1 trade
  INFY (BUY) — Position Size: $65,625

❌ Rejected: 4 trades
  HDFC — reason: direction_limit_bullish
  ICICI — reason: direction_limit_bullish
  TCS — reason: capital_limit
  RELIANCE — reason: capital_limit

Exposure Summary:
  Total Exposure: $65,625 / $80,000 (82.0%)
  Bullish: $65,625
  Bearish: $0
  Sector Breakdown:
    IT: $65,625
```

### What Happens Next

Only 1 signal goes to Debate & Decision:
- INFY (BUY)

The system debates INFY, votes on it, and if approved:
- **1 trade executed** (INFY, $65,625)

### Result Summary

```
Old System (Before):
  Generated 8 signals
  → 8 signals debated
  → Maybe 5-8 trades executed
  → Risk: High correlated bank exposure, overleverage

New System (After):
  Generated 8 signals
  → Correlation filter: 5 → 2 (banking controlled)
  → Smart execution filter: [HDFC, ICICI, INFY, TCS, RELIANCE] → [INFY]
  → 1 signal debated
  → 1 trade executed
  → Risk: LOW. Single sector (IT), balanced capital use, directional control
```

---

## Example 2: Diversified Good Day

### Scenario
Mixed signals with good diversification and confidence:

```
IT Sector (3 signals):
  INFY       BUY   confidence=0.90  sector=IT
  TCS        BUY   confidence=0.85  sector=IT
  WIPRO      BUY   confidence=0.82  sector=IT

BANK Sector (3 signals):
  HDFC       BUY   confidence=0.88  sector=BANK
  ICICI      BUY   confidence=0.83  sector=BANK
  AXIS       BUY   confidence=0.78  sector=BANK

Energy Sector (1 signal):
  RELIANCE   BUY   confidence=0.75  sector=ENERGY

Pharma Sector (1 signal):
  SUNITPHARM BUY   confidence=0.72  sector=PHARMA
```

### After CorrelationEngine

```
IT: 3 signals → Keep top 2
  INFY (0.90) ✓
  TCS (0.85) ✓
  (reject WIPRO 0.82)

BANK: 3 signals → Keep top 2
  HDFC (0.88) ✓
  ICICI (0.83) ✓
  (reject AXIS 0.78)

ENERGY: 1 signal → Keep 1
  RELIANCE (0.75) ✓

PHARMA: 1 signal → Keep 1
  SUNITPHARM (0.72) ✓

Output: 6 signals
```

### After SmartExecutionEngine

**Capital:** $100k, VIX: 15.0 (normal)

**Processing Order (by confidence):**

1. **INFY (0.90)** → Size: $100k × 0.90 × 1.0 = $90,000
   - Capital check: $90k > $80k ✗
   - **REJECTED: capital_limit**

2. **HDFC (0.88)** → Size: $100k × 0.88 × 1.0 = $88,000
   - Capital check: $88k > $80k ✗
   - **REJECTED: capital_limit**

3. **TCS (0.85)** → Size: $100k × 0.85 × 1.0 = $85,000
   - Capital check: $85k > $80k ✗
   - **REJECTED: capital_limit**

4. **ICICI (0.83)** → Size: $100k × 0.83 × 1.0 = $83,000
   - Capital check: $83k > $80k ✗
   - **REJECTED: capital_limit**

5. **RELIANCE (0.75)** → Size: $100k × 0.75 × 1.0 = $75,000
   - Capital check: $75k < $80k ✓
   - Direction check (bullish): $75k < $70k ✗
   - **REJECTED: direction_limit_bullish**

6. **SUNITPHARM (0.72)** → Size: $100k × 0.72 × 1.0 = $72,000
   - Capital check: $72k < $80k ✓
   - Direction check (bullish): $72k < $70k ✗
   - **REJECTED: direction_limit_bullish**

### Result

```
❌ ALL REJECTED (capital & direction limits bite hard with 100% VIX)
```

**Why?** At VIX normal (15) with high confidence (0.75–0.90), position sizes are too large.

**What System Does:** Waits for one of:
1. Lower-confidence signals (smaller positions)
2. Higher VIX (scales down positions)
3. Mix of BUY/SELL signals (balanced direction)

---

## Example 3: Balanced Day with Risk Management

### Scenario
Same quality, but mix of BUY & SELL, and slightly elevated VIX:

```
Signals (same confidence as Example 2, but mixed direction):
  INFY       BUY   confidence=0.90  sector=IT
  HDFC       BUY   confidence=0.88  sector=BANK
  RELIANCE   SELL  confidence=0.80  sector=ENERGY
  TCS        BUY   confidence=0.85  sector=IT
  BAJAJFINSV SELL  confidence=0.78  sector=AUTO
  SBIN       BUY   confidence=0.75  sector=BANK

VIX: 20 (elevated)
```

### After CorrelationEngine

```
IT: 1 signal
  INFY (0.90) ✓

BANK: 2 signals
  HDFC (0.88) ✓
  SBIN (0.75) ✓

ENERGY: 1 signal
  RELIANCE SELL (0.80) ✓

AUTO: 1 signal
  BAJAJFINSV SELL (0.78) ✓

Output: 5 signals
```

### After SmartExecutionEngine

**Capital:** $100k, VIX: 20.0 (elevated, reduces sizes)

**VIX factor:** 1.0 - (20 - 15) / 20 = 0.75

**Processing Order (by confidence):**

1. **INFY BUY (0.90)** → Size: $100k × 0.90 × 0.75 = $67,500
   - Capital: $67.5k < $80k ✓
   - Bullish: $67.5k < $70k ✓
   - Sector IT: 1 ≤ 2 ✓
   - **ACCEPTED**
   - Running: capital=$67.5k, bullish=$67.5k

2. **HDFC BUY (0.88)** → Size: $100k × 0.88 × 0.75 = $66,000
   - Capital: $67.5k + $66k = $133.5k > $80k ✗
   - **REJECTED: capital_limit**

3. **RELIANCE SELL (0.80)** → Size: $100k × 0.80 × 0.75 = $60,000
   - Capital: $67.5k + $60k = $127.5k > $80k ✗
   - **REJECTED: capital_limit**

4. **TCS BUY (0.85)** [NOT IN LIST - typo in example]

   Actually processed from correlation output:
   
   4. **SBIN BUY (0.75)** → Size: $100k × 0.75 × 0.75 = $56,250
   - Capital: $67.5k + $56.25k = $123.75k > $80k ✗
   - **REJECTED: capital_limit**

5. **BAJAJFINSV SELL (0.78)** → Size: $100k × 0.78 × 0.75 = $58,500
   - Capital: $67.5k + $58.5k = $126k > $80k ✗
   - **REJECTED: capital_limit**

### Result

```
✅ Accepted: 1 trade
  INFY (BUY) — Position Size: $67,500

❌ Rejected: 4 trades (all due to capital_limit at VIX=20)

Why: High VIX reduced sizes, but still too large individually
Recovery: Roll your losses OR close some positions OR wait for lower VIX
```

---

## Key Insights from Examples

### Pattern 1: Capital Limit is the Most Common Rejection
- When VIX is normal (15) and confidence is high (0.8+), positions are large
- Second trade often exceeds capital limit
- Solution: Run multiple small trades OR reduce position sizing multiplier

### Pattern 2: Directional Limit Prevents One-Sided Bets
- All BUY signals with high confidence → bullish limit hits first
- Forces diversification (need some SELL or HOLD)
- Protects against directional blowups

### Pattern 3: Sector Limit is Implicit (Manages Earlier)
- By reducing correlated sectors first, fewer positions compete for capital
- Avoids large sector concentrations

### Pattern 4: VIX Scaling is Powerful
- VIX 15 → positions large → limited number fit in capital budget
- VIX 20 → positions smaller → more positions fit BUT still hit capital limit
- VIX 30 → positions tiny → many positions fit but very conservative

---

## Professional Implication

**Before Smart Execution:**
- 8 signals → debate all 8 → execute all 8 (if approved)
- Risk: Correlated sector concentration, overwired capital

**After Smart Execution:**
- 8 signals → filter to best 1–3 → debate only best → execute best
- Benefit: Anti-correlated, balanced, capital-efficient, PROFESSIONAL

This is how hedge funds operate: **Quality over Quantity.**

---

**End of Examples**
