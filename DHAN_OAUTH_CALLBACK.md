# Dhan OAuth Callback — Automatic Token Capture

## Overview

Instead of manually copying tokens, Dhan automatically redirects to a callback server on your VPS. This script captures the authorization code with **zero manual intervention** (except login).

## Workflow

```
You login manually
      ↓
Dhan validates credentials
      ↓
Dhan redirects to: http://178.18.252.24:8000/?code=ABC123DEF456
      ↓
Callback server captures code automatically
      ↓
Code saved to: config/api_tokens.json
      ↓
Trading system exchanges code for session token
      ↓
✅ Ready to trade
```

## How to Get Authorization Code

### Step 1: Register Callback URL with Dhan

You need to tell Dhan where to send the authorization code.

**On Dhan's developer dashboard:**

1. Log in to: https://api.dhan.co/
2. Go to **App Settings** → **Callback URL**
3. Set it to: `http://178.18.252.24:8000/` (your VPS public IP)
4. Save changes

**Why this URL?**
- `178.18.252.24` = Your VPS public IP
- `8000` = Port where this callback server listens
- This is the ONLY manual setup needed

### Step 2: Start Callback Server on VPS

```bash
# SSH to VPS
ssh -i ~/.ssh/trading_vps root@178.18.252.24

# Navigate to scripts
cd ~/ai-trading-brain/scripts

# Make executable
chmod +x dhan_callback_server.py

# Start server (runs in foreground, press Ctrl+C to stop)
python3 dhan_callback_server.py
```

Output should show:

```
============================================================
DHAN OAUTH CALLBACK SERVER
============================================================

✓ Server listening on: http://0.0.0.0:8000
✓ Public URL: http://178.18.252.24:8000
✓ Token file: /root/ai-trading-brain/config/api_tokens.json

Step 1: Login to Dhan at: https://api.dhan.co/
Step 2: Dhan will redirect to: http://178.18.252.24:8000/?code=...
Step 3: This script will capture the code automatically

Waiting for Dhan redirect...
```

### Step 3: Login to Dhan (Manual)

In your **local browser**:

1. Open: https://api.dhan.co/
2. Click "Login" (or "Connect Account")
3. Enter your Dhan credentials
4. Follow any 2FA prompts

### Step 4: Authorization Redirect (Automatic)

After login, Dhan redirects your browser to:

```
http://178.18.252.24:8000/?code=ABC123DEF456...
```

The callback server:
- Captures the code automatically ✅
- Saves it to `config/api_tokens.json`
- Shows success page in browser
- Logs to console: "✅ DHAN TOKEN CAPTURED"

**You will see:**

```
✅ DHAN TOKEN CAPTURED
   Code: ABC123DEF456...
   Saved: /root/ai-trading-brain/config/api_tokens.json
   Time: 2026-03-18T09:45:30.123456
   
   Next step: Exchange code for session token
```

### Step 5: Verify Token Captured

On the VPS, check the token file was created:

```bash
cat /root/ai-trading-brain/config/api_tokens.json
```

Expected output:

```json
{
  "dhan_request_code": "ABC123DEF456...",
  "captured_at": "2026-03-18T09:45:30.123456",
  "status": "pending_exchange"
}
```

## Firewall Configuration

**For callback to work, port 8000 must be open on your VPS.**

Add this rule to UFW:

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

You should see:

```
22/tcp                          ALLOW       Anywhere
8000/tcp                        ALLOW       Anywhere
8501/tcp                        ALLOW       Anywhere
```

If port 8000 is not open, Dhan's redirect will timeout. Add it:

```bash
sudo ufw allow 8000/tcp
```

## Running in Background (Production)

Once you've tested the callback, run it as a background service:

```bash
# Stop current process (Ctrl+C)

# Run in background (survives if SSH disconnects)
cd ~/ai-trading-brain/scripts
nohup python3 dhan_callback_server.py > ~/callback_server.log 2>&1 &

# Verify it's running
ps aux | grep dhan_callback_server

# Check logs
tail -f ~/callback_server.log
```

To stop:

```bash
pkill -f dhan_callback_server
```

## What Happens Next

Once the code is captured in `config/api_tokens.json`:

1. Trading system reads the file
2. Exchanges code for a session token (via Dhan API)
3. Stores session token securely
4. Trading begins using the authenticated session

**You never manually copy/paste anything.**

## Security Notes

✅ **Only authorization code is captured** (not credentials)  
✅ **Short-lived** (code expires after ~5 min, must exchange immediately)  
✅ **Port 8000 is internal-use only** (can be restricted to SSH tunnel if needed)  
✅ **Code is saved locally** (no external service involvement)  

## Troubleshooting

### Port 8000 already in use

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Then restart callback server
python3 dhan_callback_server.py
```

### Callback times out

Check:
1. UFW allows port 8000: `sudo ufw allow 8000/tcp`
2. Dhan dashboard has correct callback URL: `http://178.18.252.24:8000/`
3. VPS is reachable: `curl http://178.18.252.24:8000/health`

### Code expires before exchange

Codes are valid for ~5 minutes. If trading system doesn't read the file immediately, the code may expire.

Solution: Re-login and trigger the redirect again.

## Example Complete Session

```bash
# Terminal 1: Start callback server
ssh -i ~/.ssh/trading_vps root@178.18.252.24
cd ~/ai-trading-brain/scripts
python3 dhan_callback_server.py

# Output: Waiting for Dhan redirect...

# Terminal 2 (Your Browser): Login to Dhan
# Open: https://api.dhan.co/
# Login with credentials
# ← Browser auto-redirected to http://178.18.252.24:8000/?code=...

# Terminal 1 Output: 
# ✅ DHAN TOKEN CAPTURED
#    Code: ABC123DEF456...
#    Saved: /root/ai-trading-brain/config/api_tokens.json

# Token is now ready for trading system to use
```

---

**Bottom line:** You login once manually. Everything else is automatic. No copy-paste tokens.
