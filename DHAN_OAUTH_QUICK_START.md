# Dhan OAuth Token Capture — Quick Reference

**Status:** ✅ **LIVE & OPERATIONAL**  
**Deployment Date:** 2026-03-18  
**Service:** dhan-oauth (port 8000)  
**VPS IP:** 178.18.252.24

---

## 🚀 Quick Start (5 Minutes)

### 1️⃣ Get Your Dhan Client ID

Visit: **https://dhan.co**
1. Login
2. My Profile → API → Create App
3. Copy: **CLIENT_ID** (e.g., `0d725eed`)

### 2️⃣ Visit OAuth URL in Your Browser

```
https://api.dhan.co/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://178.18.252.24:8000/callback&response_type=code&state=trading-brain
```

*(Replace `YOUR_CLIENT_ID` with your actual ID from step 1)*

### 3️⃣ Login & Authorize

1. Enter Dhan credentials
2. Enter TOTP code (Google Authenticator/Authy)
3. Click Authorize

### 4️⃣ Automatic Capture

✅ Dhan redirects to OAuth server  
✅ Server captures code automatically  
✅ Browser shows: **"Authentication Successful ✓"**  
✅ Token saved to `config/api_tokens.json`

### 5️⃣ Verify Capture

```bash
# SSH to VPS
ssh -i ~/.ssh/trading_vps root@178.18.252.24

# Check token file
cat /root/ai-trading-brain/config/api_tokens.json
```

Expected output:
```json
{
  "dhan_request_code": "CODE_VALUE_HERE",
  "captured_at": "2026-03-18T11:41:00Z",
  "status": "captured"
}
```

---

## 🎮 Service Management

### Start OAuth Server
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo systemctl start dhan-oauth
```

### Stop OAuth Server
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo systemctl stop dhan-oauth
```

### Restart OAuth Server
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo systemctl restart dhan-oauth
```

### Check Status
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo systemctl status dhan-oauth
```

### View Logs (Live)
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo tail -f /root/ai-trading-brain/data/logs/oauth-callback.log
```

---

## 🔍 Verification Commands

### Test Health Endpoint
```bash
curl http://178.18.252.24:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-18T...",
  "listening_on": "0.0.0.0:8000",
  "callback_uri": "/callback"
}
```

### Check OAuth Server Process
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "ps aux | grep 'dhan_oauth_server' | grep -v grep"
```

### Verify Port 8000 Listening
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "ss -tuln | grep 8000"
```

### Check Token File Permissions
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "ls -la /root/ai-trading-brain/config/api_tokens.json"
```

Should show: `-rw-------` (600 permissions) ✓

---

## 📊 Monitoring

### Real-Time Log Monitoring
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  "tail -f /root/ai-trading-brain/data/logs/oauth-callback.log"
```

### Check Last 20 Log Entries
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  "tail -20 /root/ai-trading-brain/data/logs/oauth-callback.log"
```

### Token Status Dashboard
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 << 'EOF'
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/root/ai-trading-brain')
from utils.dhan_token_manager import get_token_status
import json
print(json.dumps(get_token_status(), indent=2))
PYEOF
EOF
```

---

## ⚠️ Common Issues & Fixes

### Port 8000 Not Open?
```bash
# Check firewall
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo ufw status | grep 8000

# Add rule if missing
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo ufw allow 8000/tcp
```

### Service Won't Start?
```bash
# Check errors
ssh -i ~/.ssh/trading_vps root@178.18.252.24 sudo journalctl -u dhan-oauth -n 50

# Clear cache & restart
ssh -i ~/.ssh/trading_vps root@178.18.252.24 << 'EOF'
find /root/ai-trading-brain -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
sudo systemctl restart dhan-oauth
EOF
```

### Token Not Loading in Trading Engine?
```bash
# Verify token file exists
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  cat /root/ai-trading-brain/config/api_tokens.json

# Check if watcher is running
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  "grep 'Token file watcher' /root/ai-trading-brain/data/logs/trading-brain.log"
```

---

## 🔐 Security Notes

✅ **Token stored with 600 permissions** (rw-------)  
✅ **Token never logged in plain text**  
✅ **Automatic expiration detection** (90 days)  
✅ **Warnings before expiry** (7 days)  
✅ **Auto-restart on crash** (systemd)  
✅ **Port restricted to firewall** (UFW)  

---

## 🔄 Token Lifecycle

| Event | Action | When |
|-------|--------|------|
| **Token Captured** | Save to config/api_tokens.json | User authorizes |
| **Token Loaded** | Trading engine uses token | On cycle start |
| **Token Watched** | Monitor for changes | Every 30s |
| **Expiry Warning** | Log alert | 7 days before |
| **Token Expired** | Emit critical alert | >90 days old |
| **Re-capture** | User logs in again | On expiry |

---

## 📞 Support

### Check OAuth Server Logs
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  tail -100 /root/ai-trading-brain/data/logs/oauth-callback.log
```

### Check Error Logs
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 \
  tail -100 /root/ai-trading-brain/data/logs/oauth-callback-error.log
```

### Full Diagnostics
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24 << 'EOF'
echo "=== OAuth Service ==="
sudo systemctl status dhan-oauth --no-pager | head -10
echo ""
echo "=== Health Check ==="
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
echo "=== Token File ==="
cat /root/ai-trading-brain/config/api_tokens.json | python3 -m json.tool
echo ""
echo "=== Recent Logs ==="
tail -10 /root/ai-trading-brain/data/logs/oauth-callback.log
EOF
```

---

## 📚 Files

| File | Purpose |
|------|---------|
| `scripts/dhan_oauth_server.py` | OAuth callback server |
| `utils/dhan_token_manager.py` | Token lifecycle manager |
| `config/api_tokens.json` | Captured token storage |
| `/etc/systemd/system/dhan-oauth.service` | Systemd service file |
| `data/logs/oauth-callback.log` | Server logs |
| `data/logs/oauth-callback-error.log` | Error logs |

---

## ✅ Deployment Status

- ✅ **OAuth Server:** Running (port 8000)
- ✅ **Health Check:** Passing
- ✅ **File Permissions:** 600 (secure)
- ✅ **Auto-start:** Enabled
- ✅ **Firewall:** Open (port 8000)
- ✅ **Monitoring:** Active (30s watcher)

---

**Next Step:** Follow the Quick Start above to capture your first token!
