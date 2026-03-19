# Dhan OAuth System — Troubleshooting Guide

## Quick Diagnostics

Run the verification script to identify issues instantly:

```bash
python3 scripts/test_dhan_oauth.py --verbose
```

Run the real-time monitor to watch system health:

```bash
python3 scripts/monitor_dhan_oauth.py --vps
```

---

## Problem: OAuth Service Not Running

### Symptom
```bash
$ systemctl status dhan-oauth
● dhan-oauth.service - Dhan OAuth Callback Server
   Loaded: loaded
   Active: inactive (dead)
```

### Diagnosis

1. **Check service status**
   ```bash
   sudo systemctl status dhan-oauth --no-pager
   ```

2. **Check system journal for errors**
   ```bash
   sudo journalctl -eu dhan-oauth -n 20
   ```

3. **Check OAuth log file**
   ```bash
   tail -f /root/ai-trading-brain/data/logs/oauth-callback.log
   ```

### Fixes

**Fix 1: Restart service**
```bash
sudo systemctl restart dhan-oauth
sleep 2
sudo systemctl status dhan-oauth --no-pager
```

**Fix 2: Check Python path**
```bash
# Verify Python executable exists
ls -lh /root/ai-trading-brain/venv/bin/python3

# If not, reinstall venv
cd /root/ai-trading-brain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Fix 3: Clear Python cache and restart**
```bash
find /root/ai-trading-brain -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
sudo systemctl restart dhan-oauth
```

**Fix 4: Reinstall systemd service**
```bash
cd /root/ai-trading-brain
sudo cp scripts/dhan-oauth.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/dhan-oauth.service
sudo systemctl daemon-reload
sudo systemctl enable dhan-oauth
sudo systemctl start dhan-oauth
```

---

## Problem: Port 8000 Not Listening

### Symptom
```bash
$ curl http://localhost:8000/health
curl: (7) Failed to connect to localhost port 8000
```

### Diagnosis

1. **Check port status**
   ```bash
   ss -tuln | grep 8000
   ```
   
   Expected output:
   ```
   tcp    LISTEN   0.0.0.0:8000   0.0.0.0:*
   ```

2. **Check firewall**
   ```bash
   sudo ufw status | grep 8000
   ```
   
   Expected output:
   ```
   8000/tcp                   ALLOW       Anywhere
   ```

3. **Check if service is actually running**
   ```bash
   sudo systemctl status dhan-oauth
   ps aux | grep python3 | grep oauth
   ```

### Fixes

**Fix 1: Open firewall port**
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

**Fix 2: Check if another service is using port 8000**
```bash
# Find what's using port 8000
sudo lsof -i :8000
# OR
sudo ss -tuln | grep 8000
```

**Fix 3: Manually start OAuth server to see errors**
```bash
cd /root/ai-trading-brain
source venv/bin/activate
python3 scripts/dhan_oauth_server.py
```

---

## Problem: Health Endpoint Not Responding

### Symptom
```bash
$ curl http://localhost:8000/health
curl: (52) Empty reply from server
```

### Diagnosis

1. **Check service is responding**
   ```bash
   curl -v http://localhost:8000/health
   ```

2. **Check service logs**
   ```bash
   tail -30 /root/ai-trading-brain/data/logs/oauth-callback.log
   tail -30 /root/ai-trading-brain/data/logs/oauth-callback-error.log
   ```

### Fixes

**Fix 1: Service crash from import error**
```bash
# Check for Python errors
sudo journalctl -eu dhan-oauth -n 50 | grep -i error

# Clear cache and restart
find /root/ai-trading-brain -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
sudo systemctl restart dhan-oauth
sleep 2
curl http://localhost:8000/health
```

**Fix 2: Service hanging**
```bash
# Kill service and restart
sudo systemctl stop dhan-oauth
sleep 1
sudo systemctl start dhan-oauth
sleep 2
curl http://localhost:8000/health
```

---

## Problem: OAuth Code Not Being Captured

### Symptom

Token file not created after logging into Dhan OAuth:
```bash
$ ls -la /root/ai-trading-brain/config/api_tokens.json
ls: cannot access config/api_tokens.json: No such file or directory
```

### Diagnosis

1. **Check if request reached server**
   ```bash
   tail -20 /root/ai-trading-brain/data/logs/oauth-callback.log
   ```
   
   Look for lines like:
   ```
   [timestamp] OAuth server received callback from [IP]
   [timestamp] Authorization code: abcd1234...
   ```

2. **Check OAuth service is actually listening**
   ```bash
   curl -v http://localhost:8000/callback?code=test123&state=trading-brain
   ```

3. **Check file permissions**
   ```bash
   ls -la /root/ai-trading-brain/config/
   ```

### Fixes

**Fix 1: Verify OAuth URL is correct**

Make sure you're using:
```
https://api.dhan.co/oauth2/authorize?\
  client_id=YOUR_CLIENT_ID&\
  redirect_uri=http://178.18.252.24:8000/callback&\
  response_type=code&\
  state=trading-brain
```

⚠️ Common mistakes:
- Wrong redirect URI (should match exactly in Dhan portal)
- Using HTTPS instead of HTTP
- Port mismatch
- Missing query parameters

**Fix 2: Check config directory exists**
```bash
mkdir -p /root/ai-trading-brain/config
chmod 755 /root/ai-trading-brain/config
```

**Fix 3: Manual token capture for testing**
```bash
# Test the callback manually
curl "http://localhost:8000/callback?code=test123&state=trading-brain"

# Check if file was created
cat /root/ai-trading-brain/config/api_tokens.json
```

**Fix 4: Check firewall/VPN blocking callback**

If you're behind a VPN or firewall that blocks incoming HTTP:
- Verify port 8000 is open: `sudo ufw status | grep 8000`
- Try from different network if behind corporate firewall
- Check if ISP blocks port 8000

---

## Problem: Token File Has Wrong Permissions

### Symptom
```bash
$ ls -la /root/ai-trading-brain/config/api_tokens.json
-rw-rw-rw- 1 root root 234 Mar 18 10:30 api_tokens.json
```

Should be `600` (rw-------), not `666`.

### Diagnosis

1. **Check file permissions**
   ```bash
   stat /root/ai-trading-brain/config/api_tokens.json | grep Access
   ```

### Fixes

**Fix 1: Correct permissions manually**
```bash
chmod 600 /root/ai-trading-brain/config/api_tokens.json
ls -la /root/ai-trading-brain/config/api_tokens.json
```

**Fix 2: Use verification script with auto-fix**
```bash
python3 scripts/test_dhan_oauth.py --fix-perms
```

**Fix 3: Fix service ownership**
```bash
sudo chown root:root /root/ai-trading-brain/config/api_tokens.json
sudo chmod 600 /root/ai-trading-brain/config/api_tokens.json
```

---

## Problem: Token Manager Can't Import

### Symptom
```python
>>> from utils.dhan_token_manager import get_dhan_token
ModuleNotFoundError: No module named 'utils'
```

### Diagnosis

1. **Run from correct directory**
   ```bash
   cd /root/ai-trading-brain
   python3 -c "from utils.dhan_token_manager import get_dhan_token; print('OK')"
   ```

2. **Check Python path**
   ```bash
   python3 -c "import sys; print(sys.path)"
   ```

### Fixes

**Fix 1: Run from project root**
```bash
cd /root/ai-trading-brain
python3 scripts/test_dhan_oauth.py
```

**Fix 2: Use absolute imports in code**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.dhan_token_manager import get_dhan_token
```

**Fix 3: Reinstall package in editable mode**
```bash
cd /root/ai-trading-brain
pip install -e .
```

---

## Problem: OAuth Service Memory Leak

### Symptom

Memory usage continuously grows:
```bash
$ watch -n 5 'systemctl status dhan-oauth | grep Memory'
Memory: 50.5M (peak: 51.2M)    # Was 12.3M initially
Memory: 75.3M (peak: 80.1M)    # Growing...
```

### Diagnosis

1. **Monitor memory over time**
   ```bash
   watch -n 10 'ps aux | grep dhan_oauth | grep -v grep'
   ```

2. **Check for open file handles**
   ```bash
   lsof -p $(pgrep -f dhan_oauth_server.py)
   ```

### Fixes

**Fix 1: Restart service periodically**
```bash
# Add daily restart to crontab
0 4 * * * /bin/systemctl restart dhan-oauth

# Or manually restart
sudo systemctl restart dhan-oauth
```

**Fix 2: Check logs for stuck connections**
```bash
tail -100 /root/ai-trading-brain/data/logs/oauth-callback.log | grep -i error
```

**Fix 3: Monitor and kill if too high**
```bash
# Create monitoring script
#!/bin/bash
THRESHOLD=100  # MB
MEMORY=$(ps aux | grep dhan_oauth_server.py | grep -v grep | awk '{print $6}')
if [ "$MEMORY" -gt "$THRESHOLD" ]; then
  sudo systemctl restart dhan-oauth
fi
```

---

## Problem: SSH Connection to VPS Failed

### Symptom
```bash
$ ssh -i ~/.ssh/trading_vps root@178.18.252.24
Permission denied (publickey)
```

### Diagnosis

1. **Check SSH key exists**
   ```bash
   ls -la ~/.ssh/trading_vps
   ```

2. **Check SSH key permissions**
   ```bash
   ls -la ~/.ssh/
   # Should be drwx------ (700)
   ```

### Fixes

**Fix 1: Fix SSH key permissions**
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/trading_vps
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "echo test"
```

**Fix 2: Verify key passphrase**
```bash
ssh-keygen -y -f ~/.ssh/trading_vps
# If prompted for passphrase, enter it correctly
```

**Fix 3: Check SSH config**
```bash
cat ~/.ssh/config | grep -A 5 trading_vps
```

---

## Quick Emergency Procedures

### Restart Everything
```bash
# Kill and restart OAuth service
sudo systemctl stop dhan-oauth
sleep 1
sudo systemctl start dhan-oauth
sleep 2
sudo systemctl status dhan-oauth

# Test health
curl http://localhost:8000/health | python3 -m json.tool
```

### Full System Reset
```bash
# Clear cache
find /root/ai-trading-brain -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Kill any stray processes
pkill -f dhan_oauth_server.py

# Restart service
sudo systemctl restart dhan-oauth
sleep 3
sudo systemctl status dhan-oauth

# Verify
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Emergency Log Cleanup
```bash
# Reset logs (keep last 100 lines)
tail -100 /root/ai-trading-brain/data/logs/oauth-callback.log > /tmp/oauth.log.tmp
mv /tmp/oauth.log.tmp /root/ai-trading-brain/data/logs/oauth-callback.log
```

### Disable/Re-enable Auto-Start
```bash
# Disable
sudo systemctl disable dhan-oauth
sudo systemctl stop dhan-oauth

# Re-enable
sudo systemctl enable dhan-oauth
sudo systemctl start dhan-oauth
```

---

## Getting Help

**Collect diagnostic information:**
```bash
python3 scripts/test_dhan_oauth.py --verbose > /tmp/oauth_diag.txt 2>&1
python3 scripts/monitor_dhan_oauth.py --vps > /tmp/oauth_monitor.txt 2>&1 &
sleep 10
kill %1

cat /tmp/oauth_diag.txt
cat /tmp/oauth_monitor.txt
```

**Share these files when asking for help:**
1. `test_dhan_oauth.py --verbose` output
2. `journalctl -eu dhan-oauth -n 50` output
3. `/root/ai-trading-brain/data/logs/oauth-callback.log` (last 50 lines)
4. Service status: `sudo systemctl status dhan-oauth --no-pager`

---

## Still Stuck?

Check these resources:

1. **Full Setup Guide:** [DHAN_OAUTH_SETUP.md](./DHAN_OAUTH_SETUP.md)
2. **Quick Start:** [DHAN_OAUTH_QUICK_START.md](./DHAN_OAUTH_QUICK_START.md)
3. **OAuth Server Code:** [scripts/dhan_oauth_server.py](./scripts/dhan_oauth_server.py)
4. **Token Manager Code:** [utils/dhan_token_manager.py](./utils/dhan_token_manager.py)

