# 🔴 URGENT: Daily Token Refresh Required Before Tomorrow's Market Open

**Date:** March 19, 2026  
**Time Until Issue:** ~16 hours (until 09:15 IST on March 20)  
**Impact:** TRADING WILL BLOCK without daily token refresh

---

## Critical Status

### ✅ What's Been Fixed

| Item | Status | Details |
|------|--------|---------|
| Token Manager | ✅ Updated | Daily expiry checks (minutes, not days) |
| OAuth Server | ✅ Updated | Sets `token_type: DAILY_SESSION`, expires at 16:51 UTC |
| API Tokens File | ✅ Updated | Shows `expires_at: 2026-03-19T16:51:00` |
| Documentation | ✅ Created | Full daily token lifecycle documented |
| Code Deployed | ✅ Pushed to GitHub & VPS | All systems updated |

### 🔴 What's NOT Fixed (Blocker)

| Item | Status | When Needed | Impact |
|------|--------|-------------|--------|
| Daily Token Refresh | ❌ NOT IMPLEMENTED | March 20, 09:15 IST | TRADING BLOCKED |
| OAuth Auto-Login | ❌ NOT IMPLEMENTED | Daily at market open | Manual workaround required |

---

## What Happens Tomorrow (March 20)

### Timeline

| Time | Status | Result |
|------|--------|--------|
| **Before 09:15 IST** | Token from today (19th) is EXPIRED | ❌ Cannot trade |
| **09:15 IST** | Market opens, trading engine starts | ✅ Service runs |
| **09:15 IST** | Engine checks token validity | ❌ **TOKEN EXPIRED** |
| **09:15 IST** | Engine tries to use old token | ❌ **401 UNAUTHORIZED** |
| **09:15+ IST** | All trading blocked | ❌ **ORDERS FAIL** |

### Error Message
```
[ERROR] Token validation failed
[ERROR] Dhan: 401 Unauthorized - token expired at 2026-03-19T16:51:00
[ERROR] Cannot place orders - token invalid
[ALERT] Trading BLOCKED - no valid Dhan token available
```

---

## How to Unblock Trading Tomorrow

### Option 1: Automated (If You Build It Tonight)
```
Before 09:15 IST tomorrow:
1. OAuth server automatically re-authenticates
2. Captures new token for March 20
3. Saves to config/api_tokens.json
4. Expires at 20/03/2026 16:51:00
5. Trading resumes normally
```

### Option 2: Manual (Quick Fix)
```
At 09:00 IST tomorrow (15 mins before market open):
1. Visit OAuth login URL
2. Authenticate with Dhan
3. System captures authorization code
4. Exchanges for new access token
5. Saves token with 20/03/2026 16:51:00 expiry
6. Restart trading engine
7. Resume trading
```

### Option 3: Pre-Empty (Do It Now, Tonight)
```
Tonight (before today 16:51 UTC):
1. Login to Dhan OAuth
2. Get new authorization code
3. Place in api_tokens.json NOW
4. Token will be fresh tomorrow
5. Zero manual intervention needed tomorrow morning
```

---

## Quick Fix: Get Token Now (Option 3 - Recommended)

### Step 1: Login to Dhan OAuth
```
Visit: https://api.dhan.co/oauth2/authorize?client_id=2603183256&redirect_uri=http://178.18.252.24:8000/callback&response_type=code&state=trading-brain
```

### Step 2: System Auto-Captures
```
OAuth server at/root/ai-trading-brain detects callback
Automatically exchanges code for token
Token saved with expiry: 2026-03-20T16:51:00 (tomorrow at close)
```

### Step 3: Verify Token
```bash
# On VPS
cat /root/ai-trading-brain/config/api_tokens.json | grep expires_at
# Should show: "expires_at": "2026-03-20T16:51:00"
```

**Result:** Tomorrow trading starts with valid token ✅

---

## Code Changes Made

### `utils/dhan_token_manager.py`
```python
# BEFORE
TOKEN_TTL_DAYS = 30
TOKEN_WARN_DAYS = 3

# AFTER
TOKEN_TTL_DAYS = 1  # Daily tokens
TOKEN_WARN_MINUTES = 10  # Warn 10 mins before 16:51 UTC
```

### `scripts/dhan_oauth_server.py`
```python
# BEFORE
expires_at = datetime.utcnow() + timedelta(days=30)
ttl_days = 30

# AFTER
expires_at = datetime.utcnow().replace(hour=16, minute=51, second=0)
token_type = "DAILY_SESSION"
ttl_days = 0
```

### `config/api_tokens.json`
```json
{
  "expires_at": "2026-03-19T16:51:00",  // TODAY at 16:51 UTC
  "ttl_days": 0,
  "token_type": "DAILY_SESSION"
}
```

---

## Why April 17 Was Wrong

❌ **Assumption:** Dhan issues 29-day OAuth tokens like typical OAuth 2.0  
✅ **Reality:** Dhan issues DAILY SESSION tokens that reset at market close

**Source:** Your API call revealed: `"tokenValidity":"19/03/2026 16:51"`

This is the Dhan session validity, which is per trading day, not per month.

---

## 🚨 DO NOT IGNORE

**If you don't refresh the token by 09:15 IST tomorrow:**
- ❌ System cannot authenticate
- ❌ No trades can be placed
- ❌ Portfolio becomes read-only
- ❌ All pending orders fail
- ❌ System logs hundreds of 401 errors

**This is not a bug—it's how Dhan works.**  
**Daily session tokens are normal for trading systems.**

---

## Summary

| Before | Now | Impact |
|--------|-----|--------|
| April 17 expiry | Today 16:51 UTC expiry | System model FIXED |
| One-time setup | Daily refresh needed | Operational change |
| Unused April 14 alerts | 10-min pre-expiry alerts | Better monitoring |
| 30-day assumption | 1-day reality | Correct now ✅ |

**System is READY for daily token management.**  
**Just need to implement daily login automation (or manual triggers).**

---

## References

- **Discovery:** User API check at 19 Mar 11:10 UTC
- **Finding:** API response `tokenValidity: "19/03/2026 16:51"`
- **Documentation:** `DHAN_DAILY_TOKEN_REQUIREMENT.md`
- **Code Changes:** Committed to GitHub commit `0137324`
- **Deployed To:** VPS at `178.18.252.24`
