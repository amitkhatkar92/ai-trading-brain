# Dhan OAuth Token Capture System — Complete Setup Guide

**Status:** ✅ Ready for deployment  
**Date:** 2026-03-18  
**Author:** AI Trading Brain Infrastructure  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation Steps](#installation-steps)
5. [Usage Guide](#usage-guide)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Troubleshooting](#troubleshooting)
8. [Security Checklist](#security-checklist)

---

## 🎯 Overview

The **Dhan OAuth Token Capture System** automates the process of capturing Dhan broker credentials:

- **Manual Login:** User logs into Dhan in their browser
- **Automatic Capture:** OAuth code captured by server automatically
- **Zero Copy-Paste:** No manual credential handling needed
- **Dynamic Loading:** Trading engine loads token without restart
- **Expiration Alerts:** System warns before token expires

### Flow Diagram

```
┌─────────────────┐
│   User Browser  │
│   at Dhan.co    │
└────────┬────────┘
         │
         │ 1. User Login
         │ 2. Authorization
         ▼
┌─────────────────────────────────────────────┐
│ Dhan OAuth Server (https://dhan.co/oauth2)  │
└────────┬────────────────────────────────────┘
         │
         │ 3. Redirect to callback
         │    http://YOUR_IP:8000/callback?code=XXX
         ▼
┌──────────────────────────────────┐
│ OAuth Callback Server (Port 8000)│
│ scripts/dhan_oauth_server.py     │
└────────┬─────────────────────────┘
         │
         │ 4. Extract code
         │ 5. Save token
         ▼
┌──────────────────────────────────┐
│ config/api_tokens.json           │
│ (Token stored with 600 perms)    │
└────────┬─────────────────────────┘
         │
         │ 6. Trading engine
         │    loads token
         ▼
┌──────────────────────────────────┐
│ Trading Engine (daemon)          │
│ Uses token for Dhan API calls    │
└──────────────────────────────────┘
```

---

## 🏗️ Architecture

### File Structure

```
ai-trading-brain/
├── scripts/
│   ├── dhan_oauth_server.py         (New: OAuth callback server)
│   └── dhan-oauth.service           (New: systemd service definition)
├── utils/
│   └── dhan_token_manager.py        (New: token lifecycle mgmt)
├── config/
│   ├── api_tokens.json              (New: captured token storage)
│   └── .gitignore                   (Updated: exclude tokens)
└── data/logs/
    ├── oauth-callback.log           (New: OAuth server logs)
    └── oauth-callback-error.log     (New: OAuth error logs)
```

### Components

| Component | Purpose | Port | Status |
|-----------|---------|------|--------|
| **OAuth Server** | Captures tokens from Dhan | 8000 | ✅ New |
| **Token Manager** | Manages token lifecycle | N/A | ✅ New |
| **Trading Engine** | Uses managed tokens | N/A | ✅ Compatible |
| **Systemd Service** | Auto-restart OAuth server | N/A | ✅ New |

---

## ✅ Prerequisites

- ✅ **VPS Access:** SSH key-based login to 178.18.252.24
- ✅ **Python Environment:** `/root/ai-trading-brain/venv/` configured
- ✅ **Firewall:** Port 8000 open (already allowed in UFW)
- ✅ **Dhan Account:** With API credentials (client_id)
- ✅ **TOTP 2FA:** Enabled on Dhan account

### Get Your Dhan Credentials

1. **Generate Client ID:**
   - Visit: https://dhan.co
   - Login with your broker account
   - Go to: My Profile → API → Create App
   - Copy: **CLIENT_ID**

2. **Enable 2FA:**
   - Click: My Profile → 2FA Security
   - Enable: **TOTP (Google Authenticator, Authy, etc.)**
   - Save recovery codes in secure location

---

## 🚀 Installation Steps

### Step 1: Verify Firewall (VPS)

```bash
# SSH to VPS
ssh -i ~/.ssh/trading_vps root@178.18.252.24

# Check port 8000 is open
sudo ufw status | grep 8000

# Expected: 8000/tcp    ALLOW   Anywhere
```

✅ Already open from previous setup.

---

### Step 2: Deploy OAuth Server to VPS

```bash
# Copy OAuth server script to VPS
scp -i ~/.ssh/trading_vps \
  scripts/dhan_oauth_server.py \
  root@178.18.252.24:/root/ai-trading-brain/scripts/

# Copy token manager to VPS
scp -i ~/.ssh/trading_vps \
  utils/dhan_token_manager.py \
  root@178.18.252.24:/root/ai-trading-brain/utils/

# Copy systemd service file to VPS
scp -i ~/.ssh/trading_vps \
  scripts/dhan-oauth.service \
  root@178.18.252.24:/tmp/
```

---

### Step 3: Install Systemd Service (VPS)

```bash
# SSH to VPS
ssh -i ~/.ssh/trading_vps root@178.18.252.24

# Copy service file to systemd
sudo cp /tmp/dhan-oauth.service /etc/systemd/system/

# Set permissions
sudo chmod 644 /etc/systemd/system/dhan-oauth.service

# Refresh systemd daemon
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable dhan-oauth

# Start the service
sudo systemctl start dhan-oauth

# Verify it's running
sudo systemctl status dhan-oauth
```

**Expected Output:**
```
● dhan-oauth.service - Dhan OAuth Callback Server
   Loaded: loaded (/etc/systemd/system/dhan-oauth.service)
   Active: active (running)
```

---

### Step 4: Test OAuth Server Health (VPS)

```bash
# Check server is listening
curl http://localhost:8000/health

# Expected Response:
# {
#   "status": "healthy",
#   "timestamp": "2026-03-18T11:15:00",
#   "listening_on": "0.0.0.0:8000",
#   "callback_uri": "/callback"
# }
```

---

### Step 5: Integrate Token Manager into Trading Engine

Update your trading engine to use the dynamic token manager.

**File:** `orchestrator/master_orchestrator.py`

Add at initialization (after all imports):

```python
# ── Dynamic Dhan token loading ───────────────────────────────
try:
    from utils.dhan_token_manager import watch_token_file_start
    watch_token_file_start(poll_interval=30)
    log.info("✓ Dhan token file watcher started")
except Exception as e:
    log.debug(f"Token watcher unavailable: {e}")
```

**File:** `data_feeds/dhan_feed.py`

Update token loading (in `__init__` or `connect`):

```python
# ── Dynamic token loading instead of static config ──────────
try:
    from utils.dhan_token_manager import get_dhan_token
    self.access_token = get_dhan_token()
except Exception:
    self.access_token = os.getenv("DHAN_ACCESS_TOKEN", "")

if not self.access_token:
    log.error("❌ No Dhan access token available (file capture or env)")
```

---

## 🔓 Usage Guide

### Scenario 1: First-Time Token Capture

```bash
# 1. Verify OAuth server is running
sudo systemctl status dhan-oauth

# 2. Get your VPS public IP
curl ifconfig.me
# Example: 178.18.252.24

# 3. Visit in browser (your user's browser, not VPS):
https://api.dhan.co/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://178.18.252.24:8000/callback&response_type=code&state=trading-brain

# 4. User logs in with Dhan credentials + TOTP code
# 5. Dhan redirects to callback server
# 6. Server captures code automatically
# 7. Success page shown in browser
# 8. Token saved to config/api_tokens.json

# 9. Verify token was saved
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  cat /root/ai-trading-brain/config/api_tokens.json
```

---

### Scenario 2: Token Expired – Re-capture

```bash
# 1. Monitor OAuth logs
sudo tail -f /root/ai-trading-brain/data/logs/oauth-callback.log

# 2. When alert appears about expiration, repeat capture flow

# 3. System automatically reloads new token (30s watcher)
```

---

### Scenario 3: Verify Current Token Status

```bash
# SSH to VPS
ssh -i ~/.ssh/trading_vps root@178.18.252.24

# Check token file
cat /root/ai-trading-brain/config/api_tokens.json

# Check OAuth logs
tail -20 /root/ai-trading-brain/data/logs/oauth-callback.log

# Monitor server
sudo systemctl status dhan-oauth
```

---

## 📊 Monitoring & Alerts

### Log Files

| File | Purpose | Location |
|------|---------|----------|
| oauth-callback.log | Server events, token captures | `/root/ai-trading-brain/data/logs/` |
| oauth-callback-error.log | Errors | `/root/ai-trading-brain/data/logs/` |
| trading-brain.log | Main trading engine | `/root/ai-trading-brain/data/logs/` |

### Watch Logs in Real-Time

```bash
# OAuth server logs
sudo tail -f /root/ai-trading-brain/data/logs/oauth-callback.log

# Error logs
sudo tail -f /root/ai-trading-brain/data/logs/oauth-callback-error.log
```

### Alerts Triggered

| Alert | Trigger | Action |
|-------|---------|--------|
| ✅ Token Captured | OAuth redirect received | Log SUCCESS + save to file |
| ✅ Token Loaded | Trading engine initializes | Use for API calls |
| ⚠️ Token Expiring Soon | 7 days before expiration | Log WARNING |
| 🚨 Token Expired | >90 days old | Log CRITICAL + Telegram alert |
| ❌ Token Missing | File not found + no ENV | Log ERROR |

### Telegram Alerts (Optional)

If Telegram bot configured, receive automatic notifications:

```
🚨 DHAN TOKEN EXPIRED 🚨
Captured: 2026-03-18T11:09:00Z
Age: 95 days
Action: Re-login to Dhan browser to capture new token
```

---

## 🔧 Troubleshooting

### Issue: "Connection refused on port 8000"

**Cause:** OAuth server not running

**Fix:**
```bash
# Check status
sudo systemctl status dhan-oauth

# Start service
sudo systemctl start dhan-oauth

# Check for errors
sudo systemctl -l dhan-oauth

# View logs
tail -50 /root/ai-trading-brain/data/logs/oauth-callback-error.log
```

---

### Issue: "Callback URL not working in browser"

**Cause:** Firewall or firewall rule issue

**Fix:**
```bash
# Verify UFW allows port 8000
sudo ufw status | grep 8000

# If not listed, add rule
sudo ufw allow 8000/tcp

# Test from local machine
curl http://178.18.252.24:8000/health
```

---

### Issue: "Token file permissions denied"

**Cause:** Incorrect file ownership

**Fix:**
```bash
# Check permissions
ls -la /root/ai-trading-brain/config/api_tokens.json

# Should show: -rw------- (600)
# If not, fix:
sudo chmod 600 /root/ai-trading-brain/config/api_tokens.json
sudo chown root:root /root/ai-trading-brain/config/api_tokens.json
```

---

### Issue: "Trading engine not loading token"

**Cause:** Token manager not integrated yet

**Fix:**
```bash
# Verify files exist
ls -la /root/ai-trading-brain/utils/dhan_token_manager.py

# Test token loading manually
python3 << 'EOF'
import sys
sys.path.insert(0, '/root/ai-trading-brain')
from utils.dhan_token_manager import get_dhan_token, get_token_status
print(get_token_status())
EOF
```

---

## 🔐 Security Checklist

- ✅ **Token stored with 600 permissions** (rw-------)
- ✅ **Token never logged in plain text**
- ✅ **config/api_tokens.json in .gitignore** (never committed)
- ✅ **OAuth server only accepts from configured redirect_uri**
- ✅ **Port 8000 restricted to firewall** (UFW allows)
- ✅ **TOTP 2FA enabled on Dhan account** (prevents unauthorized login)
- ✅ **Token file on secure VPS partition** (/root is restricted)
- ✅ **Automatic expiration detection** (90 day TTL)
- ✅ **Alerts before expiration** (7 day warning)

---

## 📝 Quick Reference Commands

### Start OAuth Server
```bash
sudo systemctl start dhan-oauth
```

### Stop OAuth Server
```bash
sudo systemctl stop dhan-oauth
```

### Restart OAuth Server
```bash
sudo systemctl restart dhan-oauth
```

### Check Status
```bash
sudo systemctl status dhan-oauth
```

### View Logs
```bash
tail -50 /root/ai-trading-brain/data/logs/oauth-callback.log
```

### Verify Token Exists
```bash
cat /root/ai-trading-brain/config/api_tokens.json | python3 -m json.tool
```

### Test OAuth Server Health
```bash
curl http://localhost:8000/health
```

---

## 🎓 How It Works (Deep Dive)

### Token Capture Flow

1. **OAuth Server Starts**
   - Listens on `0.0.0.0:8000`
   - Awaits Dhan redirect

2. **User Initiates Login**
   - Visits: `https://api.dhan.co/oauth2/authorize?...`
   - Enters Dhan credentials
   - Confirms TOTP code

3. **Dhan Redirects**
   - Returns to: `http://YOUR_IP:8000/callback?code=XXXXX`
   - OAuth server intercepts request

4. **Token Saved**
   - Extracts `code` parameter
   - Saves to `config/api_tokens.json`
   - Sets file permissions to `600`
   - Atomic write (no partial saves)

5. **Success Shown**
   - Browser shows success page
   - Trading engine reloads token (within 30s)

6. **Continuous Monitoring**
   - Watcher checks file every 30s
   - Detects expiration (>90 days)
   - Emits alerts (7 days before expiry)

### Token File Format

```json
{
  "dhan_request_code": "REQUEST_CODE_VALUE",
  "captured_at": "2026-03-18T11:09:00Z",
  "status": "captured",
  "expires_at": "2026-06-16T11:09:00Z"
}
```

### Dynamic Loading

Instead of reading token once at startup:

```python
# OLD (static, requires restart)
token = os.getenv("DHAN_ACCESS_TOKEN")

# NEW (dynamic, no restart needed)
from utils.dhan_token_manager import get_dhan_token
token = get_dhan_token()  # Always gets latest
```

---

## 📚 Additional Resources

- **Dhan OAuth Docs:** https://api-docs.dhan.co/oauth2
- **Security Best Practices:** https://owasp.org/www-community/attacks/csrf
- **Systemd Service Docs:** https://www.freedesktop.org/software/systemd/man/systemd.service.html

---

**Questions?** Check logs or test manually:

```bash
# Test token manager
python3 << 'EOF'
from utils.dhan_token_manager import get_token_status
import json
print(json.dumps(get_token_status(), indent=2))
EOF
```

---

**Last Updated:** 2026-03-18  
**Status:** Production Ready ✅
