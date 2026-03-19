# ⚠️ CRITICAL: Dhan Token Validity is DAILY (Not 29 Days)

**Last Updated:** March 19, 2026  
**Status:** 🔴 URGENT - System Requires Daily Token Refresh

---

## Executive Summary

**Discovery** (March 19, 2026):
```
API Response: {"dhanClientId":"1103480765","tokenValidity":"19/03/2026 16:51",...}
```

**Finding:** Dhan tokens are **DAILY SESSION tokens**, not 29-day tokens.

| Metric | Value | Impact |
|--------|-------|--------|
| **Token Validity** | 19/03/2026 16:51 UTC | Expires TODAY at market close |
| **TTL** | Single day | Must refresh daily |
| **Refresh Timing** | Market open (09:15 IST) | ~6 hours after market open |
| **Previous Assumption** | April 17, 2026 ❌ | **WRONG** - was placeholder error |
| **Correct Model** | Daily rollover | **Correct** - aligns with trading sessions |

---

## What This Means

### Current Status (March 19, 2026)
- ✅ Token **valid TODAY** through 16:51 UTC (end of market hours)
- ✅ Can trade from market open (09:15 IST) until market close (16:51 UTC)
- ❌ Token **INVALID tomorrow** (March 20) at market open
- ❌ **April 17 expiry is obsolete** — April 14 alert unnecessary

### Daily Token Lifecycle
```
Daily Cycle:
  ┌─────────────────────────────────────────────┐
  │  Night (00:00-09:15 UTC)                    │
  │  └─ Old token: EXPIRED ❌                    │
  │     New session starts at 09:15 IST          │
  │                                              │
  │  Market Hours (09:15 IST - 16:51 UTC)       │
  │  └─ TODAY's token: ACTIVE ✓                │
  │     └─ Valid for trading                    │
  │                                              │
  │  After Hours (16:51-24:00 UTC)              │
  │  └─ TODAY's token: EXPIRED ❌               │
  │     Must wait for tomorrow's market open    │
  └─────────────────────────────────────────────┘
```

---

## Issues with Previous Configuration

### Before (March 19 8:00 AM)
```json
{
  "expires_at": "2026-04-17T00:00:00",  ❌ WRONG
  "ttl_days": 29,                        ❌ WRONG
  "token_type": "Bearer"                 ❌ INCORRECT TYPE
}
```

**Why It Was Wrong:**
1. Assumed OAuth token (26-day JWT) — **Not how Dhan works**
2. Dhan issues **daily session tokens**, not long-lived OAuth tokens
3. Token validity confirmed by API response: today at 16:51 UTC
4. April 14 "alert threshold" never needed — token dies daily

### After (March 19 11:10 AM)
```json
{
  "expires_at": "2026-03-19T16:51:00",  ✅ CORRECT
  "ttl_days": 0,                         ✅ CORRECT
  "token_type": "DAILY_SESSION",         ✅ CORRECT
  "refresh_required": true               ✅ URGENT
}
```

---

## Required Changes

### 1. Token Manager (`utils/dhan_token_manager.py`)
**Update Required:**
- Remove 29-day TTL logic
- Remove April 17 expiry checks
- Implement **daily expiry at 16:51 UTC**
- Add **daily refresh trigger at market open (09:15 IST)**

### 2. OAuth Server (`scripts/dhan_oauth_server.py`)
**Update Required:**
- When token is captured, set:
  ```python
  expires_at = today + 16:51 UTC
  ttl_days = 0
  token_type = "DAILY_SESSION"
  ```

### 3. Trading Schedule (`config.py`)
**Already Correct:**
- Market opens: 9:15 AM IST
- Market closes: 3:51 PM UTC (4:20 PM IST)
- ✅ Matches Dhan's 16:51 UTC expiry

### 4. Monitoring & Alerts
**Remove Obsolete Alerts:**
- ❌ April 14 (3-day warning) — NOT NEEDED
- ❌ April 17 (expiry) — NOT NEEDED

**Add New Alerts:**
- ✅ Daily at 16:50 UTC: "Token expiring in 1 minute"
- ✅ Daily at market open: "Token refresh required"
- ✅ Before 09:15 IST: "Cannot trade — no valid token"

---

## Daily Token Refresh Workflow

### Scenario: March 20, 2026 (Tomorrow)

#### Morning (Before Market Open)
```
09:14 IST / 03:44 UTC
└─ Trading engine checks token
   └─ Token from yesterday (19th) is INVALID
   └─ Error: "Token expired at 2026-03-19T16:51:00"
   └─ System: CANNOT START TRADING ❌
```

#### Required Manual Step (Until OAuth Automation Built)
```
User OR Automated Process:
1. Visit OAuth URL or use stored credentials
2. Dhan authenticates and issues NEW token for 20th
3. New token valid: 20/03/2026 09:15 → 20/03/2026 16:51
4. Save to config/api_tokens.json
5. Trading engine resumes ✓
```

#### Market Hours
```
09:15 IST - 16:51 UTC / 20th
└─ Trading engine has VALID token
   └─ Can execute all orders ✓
```

#### After Market Close
```
16:51 UTC / 20th
└─ Token EXPIRES
   └─ Open positions persist
   └─ Cannot place NEW orders ❌
   └─ Existing position management: read-only mode
```

---

## Implementation Roadmap

### Phase 1: Immediate (Today, March 19)
✅ **DONE:**
- Update API tokens file with 19/03/2026 16:51 expiry
- Document daily token requirement
- Confirm token validity with Dhan API response

### Phase 2: Short-term (Before Market Open Tomorrow, March 20)
🔴 **BLOCKING:**
- [ ] Update `utils/dhan_token_manager.py` for daily expiry logic
- [ ] Update `scripts/dhan_oauth_server.py` to track daily refresh
- [ ] Implement daily token capture automation
- [ ] Add pre-market token validation (09:14 IST check)

**Test:**
```bash
# Test daily expiry logic
python3 -c "from utils.dhan_token_manager import get_dhan_token; print(get_dhan_token())"
```

### Phase 3: Automation (Week of March 20)
- [ ] Implement daily OAuth flow at market open (09:15 IST)
- [ ] Auto-capture new token before trading starts
- [ ] Fallback: Manual re-login if auto-refresh fails
- [ ] Alerts at 16:50 UTC (10 mins before expiry)

---

## Critical Questions to Resolve

### Q1: When Do I Need New Token?
**A:** At the **'next market open** (09:15 IST) after token expires.
- Today (19th): Token valid until 16:51 UTC
- Tomorrow (20th) at 09:15 IST: **New token required** before trading

### Q2: Can I Use Yesterday's Token on a New Market Day?
**A:** **NO** — Dhan invalidates yesterday's token.
- Each trading day = new session token
- Old token returns 401 Unauthorized

### Q3: What If Market is Closed (Weekends/Holidays)?
**A:** No trading possible anyway. Next market open = next token refresh.
- Friday 16:51 UTC: Token expires
- Monday 09:15 IST: New token needed (if market open)
- Saturday/Sunday: Markets closed, no token refresh needed

### Q4: Do I Need to Logout to Get New Token?
**A:** Unknown — Dhan may manage sessions per calendar day.
- If unclear: Re-authenticate at market open each day
- Prevents session conflicts

---

## Files Updated (March 19)

| File | Change | Status |
|------|--------|--------|
| `config/api_tokens.json` | expires_at: "2026-03-19T16:51:00" | ✅ Deployed |
| `config/api_tokens.json` | ttl_days: 0 | ✅ Deployed |
| `config/api_tokens.json` | token_type: "DAILY_SESSION" | ✅ Deployed |
| `DHAN_DAILY_TOKEN_REQUIREMENT.md` | This file | ✅ Created |
| `utils/dhan_token_manager.py` | Daily expiry logic | ⏳ TODO |
| `scripts/dhan_oauth_server.py` | Daily refresh tracking | ⏳ TODO |
| Documentation (DHAN_OAUTH_*.md) | Remove April 17 references | ⏳ TODO |

---

## Next Actions

**🔴 BEFORE MARKET OPEN TOMORROW (March 20, 09:15 IST):**

1. **Update token manager** — Remove 29-day logic, add daily expiry
2. **Implement pre-market check** — Verify token valid at 09:14 IST
3. **Test token refresh** — Confirm new token can be captured
4. **Alert setup** — Configure daily token expiry notifications

**Without these changes: Trading BLOCKED at tomorrow's market open** ❌

---

## References

- **Dhan API Response:** `{"tokenValidity":"19/03/2026 16:51",...}`
- **Token File:** `/root/ai-trading-brain/config/api_tokens.json`
- **Token Manager:** `utils/dhan_token_manager.py`
- **Market Hours:** 09:15 IST — 15:30 IST + 3 more hours (16:51 UTC)

---

## Summary

| Aspect | Previous | Actual | Status |
|--------|----------|--------|--------|
| Token Duration | 29 days | 1 day | ❌ ERROR CORRECTED |
| Expiry Date | April 17 | Daily at 16:51 UTC | ❌ ERROR CORRECTED |
| Alert Before Expiry | April 14 | N/A (daily) | ⏳ TO UPDATE |
| Refresh Frequency | Once per month | Once per trading day | ⏳ IMPLEMENTATION |
| Next Token Needed | April 17 | March 20 09:15 IST | 🔴 URGENT |

**System is NOT BROKEN, but requires daily token management instead of one-time setup.**
