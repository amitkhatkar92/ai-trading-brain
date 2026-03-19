# Dhan OAuth System — Reference Card

**Quick access to all commands and checks. Print and keep handy.**

---

## 🚀 QUICK START (First Time)

```bash
# 1. Verify deployment
python3 scripts/test_dhan_oauth.py

# 2. Start monitoring
python3 scripts/monitor_dhan_oauth.py --vps &

# 3. Get OAuth URL
# Use: https://api.dhan.co/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://178.18.252.24:8000/callback&response_type=code&state=trading-brain

# 4. Login and let server capture token automatically
# Result: Token saved to config/api_tokens.json

# 5. Verify token captured
python3 -c "import json; print(json.dumps(json.load(open('config/api_tokens.json')), indent=2))"
```

---

## 🔍 SERVICE STATUS

```bash
# Check service is running
sudo systemctl status dhan-oauth

# Check service is listening on port 8000
ss -tuln | grep 8000

# Test health endpoint
curl http://localhost:8000/health | python3 -m json.tool

# Restart service
sudo systemctl restart dhan-oauth

# View service logs
sudo journalctl -eu dhan-oauth -n 50
tail -f /root/ai-trading-brain/data/logs/oauth-callback.log
```

---

## 📊 MONITORING

```bash
# Real-time dashboard (local)
python3 scripts/monitor_dhan_oauth.py

# Real-time dashboard (VPS)
python3 scripts/monitor_dhan_oauth.py --vps

# Follow logs in real-time
python3 scripts/monitor_dhan_oauth.py --follow-logs

# One-time comprehensive check
python3 scripts/test_dhan_oauth.py --verbose
```

---

## 🔑 TOKEN MANAGEMENT

```bash
# View captured token
cat config/api_tokens.json

# Check token file permissions
ls -la config/api_tokens.json
# Should be: -rw------- (600)

# Fix permissions if needed
chmod 600 config/api_tokens.json

# Check token age
python3 -c "
import json
from datetime import datetime
data = json.load(open('config/api_tokens.json'))
captured = datetime.fromisoformat(data['captured_at'])
age = (datetime.now() - captured).days
print(f'Token age: {age} days')
print(f'Expires in: {90 - age} days')
"

# Test token loading in code
python3 -c "
import sys; sys.path.insert(0, '.')
from utils.dhan_token_manager import get_dhan_token, get_token_status
token = get_dhan_token()
status = get_token_status()
print(f'Token: {token}')
print(f'Status: {status}')
"
```

---

## 🧪 TESTING & VERIFICATION

```bash
# Full system diagnostic
python3 scripts/test_dhan_oauth.py --verbose

# Test OAuth server is responding
curl -v http://localhost:8000/callback?code=test&state=test

# Test token capture manually
curl -X POST http://localhost:8000/callback -d "code=TEST123&state=trading-brain"

# Verify imports work
python3 -c "from utils.dhan_token_manager import get_dhan_token; print('OK')"

# Watch token file for changes in real-time
python3 -c "
import time, os
from pathlib import Path
token_file = Path('config/api_tokens.json')
last_mtime = 0
while True:
    if token_file.exists():
        mtime = token_file.stat().st_mtime
        if mtime > last_mtime:
            last_mtime = mtime
            print(f'✓ Token file changed at {time.ctime(mtime)}')
    time.sleep(1)
"
```

---

## 🚨 EMERGENCY PROCEDURES

```bash
# Restart everything
sudo systemctl stop dhan-oauth && sleep 1 && sudo systemctl start dhan-oauth

# Kill any stuck processes
pkill -f dhan_oauth_server.py

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Reset logs (keep last 100 lines)
tail -100 data/logs/oauth-callback.log > /tmp/oauth.log.tmp
mv /tmp/oauth.log.tmp data/logs/oauth-callback.log

# Full diagnostic snapshot
{
  echo "=== SERVICE STATUS ===" && sudo systemctl status dhan-oauth --no-pager
  echo -e "\n=== PORT STATUS ===" && ss -tuln | grep 8000
  echo -e "\n=== HEALTH CHECK ===" && curl -s http://localhost:8000/health | python3 -m json.tool
  echo -e "\n=== TOKEN FILE ===" && cat config/api_tokens.json 2>/dev/null
  echo -e "\n=== RECENT LOGS ===" && tail -20 data/logs/oauth-callback.log
} | tee /tmp/oauth_diagnostic.txt
```

---

## 📁 KEY FILES & LOCATIONS

| File | Purpose | Edit? |
|------|---------|-------|
| `scripts/dhan_oauth_server.py` | OAuth callback handler | ✋ Only if fixing bugs |
| `utils/dhan_token_manager.py` | Token lifecycle manager | ✋ Only if fixing bugs |
| `scripts/dhan-oauth.service` | Systemd service config | ✋ Only to change ports/dirs |
| `config/api_tokens.json` | Captured Dhan token | ❌ Auto-generated |
| `data/logs/oauth-callback.log` | OAuth server logs | 📖 For debugging |
| `DHAN_OAUTH_SETUP.md` | Full setup guide | 📖 Read for details |
| `DHAN_OAUTH_QUICK_START.md` | 5-min quick start | 📖 First time? Start here |
| `DHAN_OAUTH_INTEGRATION.md` | Trading engine integration | 📖 For developers |
| `DHAN_OAUTH_TROUBLESHOOTING.md` | Fix common issues | 📖 When stuck |

---

## 🔧 SYSTEM INTERNALS

| Component | Configuration | Notes |
|-----------|---|---|
| **OAuth Server Port** | 8000 | Listening on 0.0.0.0:8000 |
| **Token TTL** | 90 days | Standard Dhan token validity |
| **Expiry Warning** | 7 days before | Alert when token < 7 days old |
| **File Watcher** | 30 seconds | Checks for file changes every 30s |
| **File Permissions** | 600 (rw-------) | Only root can read token |
| **Auto-restart** | Enabled | Service auto-restarts on crash |
| **Boot Startup** | Enabled | Service starts at system boot |

---

## 🌐 NETWORK CONFIGURATION

| Item | Value | Verify |
|------|-------|--------|
| **VPS IP** | 178.18.252.24 | `ssh root@178.18.252.24` |
| **OAuth Port** | 8000 | `curl http://localhost:8000/health` |
| **Firewall** | UFW Allow | `sudo ufw status` |
| **Redirect URI** | http://178.18.252.24:8000/callback | Matches Dhan portal |
| **SSH Key** | ~/.ssh/trading_vps | `ls -la ~/.ssh/trading_vps` |

---

## 📋 SETUP CHECKLIST

- [ ] OAuth server deployed: `ls -la scripts/dhan_oauth_server.py`
- [ ] Token manager deployed: `ls -la utils/dhan_token_manager.py`
- [ ] Systemd service installed: `systemctl status dhan-oauth`
- [ ] Service running: `sudo systemctl is-active dhan-oauth`
- [ ] Port 8000 listening: `ss -tuln | grep 8000`
- [ ] Health endpoint: `curl http://localhost:8000/health`
- [ ] Firewall allow 8000: `sudo ufw status | grep 8000`
- [ ] .gitignore updated: `grep api_tokens.json .gitignore`
- [ ] Dhan Client ID available: Yes ☐
- [ ] OAuth URL ready: Yes ☐
- [ ] Token captured: `[ -f config/api_tokens.json ] && echo "OK"`

---

## 📞 SUPPORT

| Issue | Next Step |
|-------|-----------|
| Service won't start | [Troubleshooting](./DHAN_OAUTH_TROUBLESHOOTING.md#problem-oauth-service-not-running) |
| Port not listening | [Troubleshooting](./DHAN_OAUTH_TROUBLESHOOTING.md#problem-port-8000-not-listening) |
| Token not captured | [Troubleshooting](./DHAN_OAUTH_TROUBLESHOOTING.md#problem-oauth-code-not-being-captured) |
| Health endpoint fails | [Troubleshooting](./DHAN_OAUTH_TROUBLESHOOTING.md#problem-health-endpoint-not-responding) |
| Import errors | [Troubleshooting](./DHAN_OAUTH_TROUBLESHOOTING.md#problem-token-manager-cant-import) |
| Integration help | [Integration Guide](./DHAN_OAUTH_INTEGRATION.md) |
| Full setup | [Setup Guide](./DHAN_OAUTH_SETUP.md) |

---

## 💾 BACKUP & RECOVERY

```bash
# Backup token file
cp config/api_tokens.json config/api_tokens.json.backup

# Restore token file
cp config/api_tokens.json.backup config/api_tokens.json

# Backup OAuth logs
tar czf ~/oauth_logs_$(date +%Y%m%d).tar.gz data/logs/oauth-callback*.log

# Verify service can start from scratch
sudo systemctl stop dhan-oauth
rm -rf config/api_tokens.json
sudo systemctl start dhan-oauth
echo "Ready for new token capture"
```

---

## 🎯 COMMON COMMANDS

```bash
# Three essential commands:

# 1. VERIFY: Is everything running?
python3 scripts/test_dhan_oauth.py

# 2. MONITOR: Watch it in real-time
python3 scripts/monitor_dhan_oauth.py --vps

# 3. DEBUG: See what's happening
tail -f data/logs/oauth-callback.log
```

---

**For more details, see complete guides above. This card covers 95% of common needs.**

*Last updated: 2026-03-18*
