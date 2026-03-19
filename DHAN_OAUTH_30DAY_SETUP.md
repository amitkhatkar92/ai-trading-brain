# Dhan OAuth Token Management — April 17, 2026 Expiry

**Date:** March 19, 2026  
**Status:** ✅ Ready for Implementation  
**Your Token Expiry:** April 17, 2026 (~29 days remaining)

---

## 🎯 Overview

Your Dhan OAuth system is now configured to:

1. **Capture authorization code** automatically when you login
2. **Exchange code for access token** (automatic)
3. **Store token with April 17 expiry date** (your actual token expiry)
4. **Track days remaining** (~29 days from today)
5. **Alert before expiry** (April 14, 3-day warning)
6. **Auto-load token** into trading engine

---

## 📋 What Changed

### 1. New Token Exchange Module
**File:** `utils/dhan_token_exchange.py`

Handles automatic code → token exchange:
- Posts authorization code to Dhan token endpoint
- Receives long-lived access token (JWT)
- Stores token with explicit expiry date tracking (supports April 17, 2026)
- Monitors token age for refresh alerts (3-day warning)

### 2. Updated Token Manager
**File:** `utils/dhan_token_manager.py`

Now supports TWO token formats:

**NEW FORMAT (recommended):**
```json
{
  "access_token": "eyJhbGci...",
  "client_id": "2603183256",
  "captured_at": "2026-03-19T10:30:00",
  "expires_at": "2026-04-17T00:00:00",
  "ttl_days": 29,
  "status": "active"
}
```

**OLD FORMAT (fallback):**
```json
{
  "dhan_request_code": "AUTH_CODE",
  "captured_at": "2026-03-19T10:30:00",
  "status": "pending_exchange"
}
```

### 3. Enhanced OAuth Server
**File:** `scripts/dhan_oauth_server.py`

Now automatically:
- Receives authorization code from Dhan redirect
- Exchanges code for access_token (via DHAN_TOKEN_ENDPOINT)
- Saves in NEW format with your token's actual expiry date
- Falls back to OLD format if exchange fails

### 4. OAuth Configuration
**File:** `config/dhan_oauth_config.json`

Central config for token management:
```json
{
  "dhan": {
    "client_id": "2603183256",
    "token_ttl_days": 30,
    "sandbox_mode": true
  },
  "token_refresh": {
    "enabled": true,
    "refresh_threshold_days": 3
  }
}
```

**Note:** System will calculate actual TTL based on token's real expiry date (April 17)

### 5. Validation Script
**File:** `scripts/validate_dhan_oauth.py`

Check token status:
```bash
python3 scripts/validate_dhan_oauth.py
```

---

## 🔄 Token Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│  1. USER LOGS INTO DHAN                                     │
│     https://api.dhan.co/oauth2/authorize?...                │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. OAUTH SERVER CAPTURES CODE                              │
│     (short-lived, ~5 min expiry)                            │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. AUTOMATIC TOKEN EXCHANGE                                │
│     POST https://api.dhan.co/oauth2/token                   │
│     ├─ grant_type: "authorization_code"                     │
│     ├─ code: [captured code]                                │
│     └─ client_id: "2603183256"                              │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. SAVE ACCESS TOKEN (long-lived)                          │
│     config/api_tokens.json                                  │
│     ├─ access_token: "eyJhbGci..." (JWT)                   │
│     ├─ expires_at: April 17, 2026 (YOUR TOKEN EXPIRY)      │
│     └─ status: "active"                                     │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  5. TRADING ENGINE AUTO-LOADS TOKEN                         │
│     from config/api_tokens.json                             │
│     ├─ Via: get_dhan_token()                                │
│     ├─ Checks expiry: April 17 date                         │
│     └─ Days remaining: ~29 days (auto-calculated)           │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  6. APRIL 14 (3 DAYS BEFORE EXPIRY)                         │
│     ├─ System alerts: "Token expires in 3 days"            │
│     ├─ Alert: "April 17 is expiry date"                     │
│     ├─ Notification sent                                    │
│     └─ Plan to re-login before April 17                     │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  7. AFTER APRIL 17 (EXPIRY DATE)                            │
│     ├─ System rejects token: EXPIRED                        │
│     ├─ Trading halts: needs new token                       │
│     └─ Action: Login to Dhan for new token capture          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Step 1: Verify Configuration
```bash
python3 scripts/validate_dhan_oauth.py
```

Expected output:
```
✅ Token File STATUS
✅ OAUTH CONFIGURATION
✅ DHAN ENVIRONMENT
✅ TOKEN LOADING TEST
```

### Step 2: Login to Dhan
Open this URL in your browser (replace IP with your VPS IP):
```
https://api.dhan.co/oauth2/authorize?client_id=2603183256&redirect_uri=http://178.18.252.24:8000/callback&response_type=code&state=trading-brain
```

### Step 3: Confirm Capture
Once you login, Dhan redirects to `http://178.18.252.24:8000/callback`

OAuth server will:
1. ✅ Capture authorization code
2. ✅ Exchange for access_token
3. ✅ Save to `config/api_tokens.json`
4. ✅ Show success message in browser

### Step 4: Verify Token Saved
```bash
cat config/api_tokens.json | python3 -m json.tool
```

Should show:
```json
{
  "access_token": "eyJhbGci...",
  "client_id": "2603183256",
  "captured_at": "2026-03-19T...",
  "expires_at": "2026-04-17T...",
  "ttl_days": 29,
  "status": "active"
}
```

**Your token expires April 17, 2026 (~29 days remaining)**

---

## 📊 Token Expiry Tracking

### Check Token Status
```bash
python3 -c "
from utils.dhan_token_manager import get_token_status
import json
status = get_token_status()
print(json.dumps(status, indent=2))
"
```

### Manual Token Refresh
When token expires (or < 3 days left, **before April 17**):
1. Run login URL again
2. OAuth server captures new code
3. Automatic exchange happens
4. New token saved with fresh expiry date

### Automatic Refresh (Future)
```python
from utils.dhan_token_exchange import get_token_expiry_info

expiry_info = get_token_expiry_info()
if expiry_info['needs_refresh']:
    # Trigger re-login or refresh endpoint
    print(f"Refresh needed: {expiry_info['days_left']} days left")
```

---

## 🔧 Configuration Options

Edit `config/dhan_oauth_config.json` to customize:

```json
{
  "dhan": {
    "client_id": "2603183256",
    "token_ttl_days": 30,        // ← Adjust expiry window
    "sandbox_mode": true          // ← false for live trading
  },
  "token_refresh": {
    "enabled": true,
    "refresh_threshold_days": 3,  // ← Alert when 3 days left
    "auto_refresh": true          // ← Auto-trigger refresh (future)
  }
}
```

---

## 📝 Your Provided Information

**From yesterday's discussion:**

| Item | Value | Status |
|------|-------|--------|
| Website | https://developer.dhanhq.co/home | ✅ Reference provided |
| Application Name | ai-trading-brain | ✅ In config |
| Sandbox Client ID | 2603183256 | ✅ In dhan_oauth_config.json |
| Access Token | `eyJhbGci...` (JWT) | ✅ Format supported |
| **Actual Expiry Date** | **April 17, 2026** | ✅ System tracks this date |
| Days Remaining | ~29 days (from Mar 19) | ⏱️ Auto-calculated on load |

---

## 🔑 Key Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `utils/dhan_token_exchange.py` | NEW module | Handles code exchange |
| `utils/dhan_token_manager.py` | Updated format detection | Supports new token format |
| `scripts/dhan_oauth_server.py` | Added auto-exchange | No manual steps needed |
| `config/dhan_oauth_config.json` | NEW config | Central token settings |
| `scripts/validate_dhan_oauth.py` | NEW validation script | Test token setup |

---

## ✅ Validation Commands

```bash
# Check token file format
cat config/api_tokens.json | python3 -m json.tool

# Check token age and expiry
python3 scripts/validate_dhan_oauth.py

# Load and test token in code
python3 -c "
from utils.dhan_token_manager import get_dhan_token, get_token_status
token = get_dhan_token()
status = get_token_status()
print(f'Token: {token[:30]}...' if token else 'No token')
print(f'Status: {status}')
"

# Check OAuth config
cat config/dhan_oauth_config.json | python3 -m json.tool
```

---

## ⏰ Token Expiry: April 17, 2026

Your token has a **known expiry date: April 17, 2026**.

**Current Status (March 19):**
- Days remaining: **29 days**
- Refresh alert: **April 14** (when < 3 days left)
- Token status: **Active** ✅

**Timeline:**
| Date | Status | Action |
|------|--------|--------|
| Mar 19 | Captured | ✅ Token active in system |
| Apr 14 | Warning | ⚠️  Alert: 3 days until expiry |
| Apr 17 | **EXPIRES** | ❌ Token no longer valid |
| After Apr 17 | Expired | 🔐 Trade halted - need new token |

**System automatically:**
- ✅ Tracks April 17 as expiry date
- ✅ Counts down remaining days
- ⚠️  Alerts on April 14 (3-day warning)
- ❌ Rejects token after April 17

---

### Token not captured after login
1. Check OAuth server is running: `ps aux | grep dhan_oauth_server`
2. Check port 8000 is open: `ss -tuln | grep 8000`
3. Check redirect URI matches: http://178.18.252.24:8000/callback
4. Review logs: `tail -f data/logs/oauth-callback.log`

### Token exchange failed
1. Verify `DHAN_CLIENT_ID` in environment
2. Check `requests` library installed: `pip list | grep requests`
3. Verify Dhan token endpoint reachable
4. Falls back to old format (authorization code) - manual exchange needed

### Token not loading in trading engine
1. Check file permissions: `ls -la config/api_tokens.json` (should be 600)
2. Verify JSON format: `cat config/api_tokens.json | python3 -m json.tool`
3. Check for parsing errors in logs

---

## 📞 Next Steps

1. ✅ Verify configuration: `python3 scripts/validate_dhan_oauth.py`
2. 🔐 Login to Dhan using OAuth URL
3. 📝 Confirm token captured in `config/api_tokens.json`
4. ✅ Run trading engine - it auto-loads the token
5. ⏰ **April 14:** Alert when 3 days until expiry
6. 🔐 **Before April 17:** Re-login to capture fresh token

---

**System is ready. Your April 17 token will be automatically tracked and you'll be alerted before expiry.**
