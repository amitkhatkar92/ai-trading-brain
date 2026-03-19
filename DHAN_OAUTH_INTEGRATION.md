# Dhan OAuth System — Trading Engine Integration Guide

## Overview

The OAuth token capture system allows your trading engine to automatically load captured Dhan tokens **without service restart**.

This guide shows exactly where and how to integrate the token manager into your trading system.

---

## Integration Points

### 1. Master Orchestrator (Start Token Watcher)

**File:** `orchestrator/master_orchestrator.py`

**What to do:** Start the token file watcher when the orchestrator initializes.

**Current code structure:**
```python
from orchestrator.master_orchestrator import MasterOrchestrator

class MasterOrchestrator:
    def __init__(self, ...):
        # ... other initialization ...
        self.feed_manager = get_feed_manager()
        # ... more initialization ...
```

**Add these lines in `__init__` method (after feed manager initialization):**

```python
from utils.dhan_token_manager import watch_token_file_start, get_token_status

class MasterOrchestrator:
    def __init__(self, ...):
        # ... existing initialization ...
        
        # START TOKEN WATCHER ← ADD THIS
        try:
            watch_token_file_start(poll_interval=30)
            logger.info("✓ Token file watcher started (polling every 30s)")
        except Exception as e:
            logger.warning(f"Could not start token watcher: {e}")
        
        # ... rest of initialization ...
```

**Effect:** Token manager will:
- Start background thread monitoring `config/api_tokens.json`
- Auto-detect when token is captured
- Emit alerts when token is about to expire (7 days before 90-day TTL)
- No need to restart trading engine after login

---

### 2. Dhan Feed (Load Dynamic Token)

**File:** `data_feeds/dhan_feed.py`

**What to do:** Replace static token with dynamic loader.

**Find this section:**

```python
class DhanFeed:
    def __init__(self, ...):
        self.client_id = os.getenv("DHAN_CLIENT_ID")
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN")  # ← STATIC
        self.base_url = "https://api.dhan.co"
```

**Replace with:**

```python
from utils.dhan_token_manager import get_dhan_token

class DhanFeed:
    def __init__(self, ...):
        self.client_id = os.getenv("DHAN_CLIENT_ID")
        # DYNAMIC TOKEN LOADING ← CHANGE THIS
        self.access_token = get_dhan_token()
        if not self.access_token:
            logger.warning("No Dhan token available. Using fallback feed.")
        self.base_url = "https://api.dhan.co"
```

**Also update token refresh in any periodic methods:**

```python
def periodic_token_refresh(self):
    """Refresh token from file (called periodically)."""
    new_token = get_dhan_token()
    if new_token and new_token != self.access_token:
        self.access_token = new_token
        logger.info(f"✓ Token updated (loaded from file)")
```

**Effect:**
- Dhan feed automatically loads latest token
- If token is re-captured, feed uses new token without restart
- Fallback to yfinance if no token available

---

### 3. Status Monitoring (Optional)

**File:** `orchestrator/master_orchestrator.py` or `control_tower/agent_status_monitor.py`

**What to do:** Add periodic token status checks to monitoring.

**Add to your monitoring loop:**

```python
from utils.dhan_token_manager import get_token_status

def check_token_health(self):
    """Check if Dhan token is healthy."""
    try:
        status = get_token_status()
        if status:
            expires_in = status.get("expires_in_days", 0)
            if expires_in < 7:
                logger.warning(f"Dhan token expires in {expires_in} days!")
            return {
                "token_available": True,
                "age_days": status.get("age_days"),
                "expires_in_days": expires_in,
            }
    except Exception as e:
        logger.error(f"Could not check token status: {e}")
    return {"token_available": False}
```

---

## Complete Integration Example

Here's a complete minimal integration showing all three pieces:

### Step 1: Update Orchestrator Init

**File:** `orchestrator/master_orchestrator.py`

```python
#!/usr/bin/env python3
"""Master Orchestrator — coordinates all AI agents."""

import logging
from utils.logger import get_logger
from data_feeds.data_feed_manager import get_feed_manager
from utils.dhan_token_manager import watch_token_file_start  # ADD THIS IMPORT

logger = get_logger(__name__)

class MasterOrchestrator:
    """Main orchestration engine."""

    def __init__(self):
        """Initialize orchestrator."""
        logger.info("Initializing MasterOrchestrator...")
        
        # Initialize feed manager
        self.feed_manager = get_feed_manager()
        
        # START TOKEN WATCHER ← ADD THIS SECTION
        try:
            watch_token_file_start(poll_interval=30)
            logger.info("✓ Dhan token file watcher started")
        except Exception as e:
            logger.warning(f"Could not start token watcher: {e}")
        
        # ... rest of initialization ...
        logger.info("MasterOrchestrator initialized ✓")

    def run_full_cycle(self):
        """Run complete trading cycle."""
        # ... existing cycle code ...
        pass
```

### Step 2: Update Dhan Feed

**File:** `data_feeds/dhan_feed.py`

```python
#!/usr/bin/env python3
"""Dhan broker feed — dynamic token loading."""

import os
import logging
from typing import Optional, Dict, List
from utils.logger import get_logger
from utils.dhan_token_manager import get_dhan_token  # ADD THIS IMPORT

logger = get_logger(__name__)

class DhanFeed:
    """Dhan broker data feed."""

    def __init__(self, env: str = "sandbox"):
        """Initialize Dhan feed with dynamic token."""
        self.env = env
        self.client_id = os.getenv("DHAN_CLIENT_ID")
        
        # DYNAMIC TOKEN LOADING ← CHANGE THIS
        self.access_token = get_dhan_token()
        if not self.access_token:
            logger.warning("No Dhan token in config/api_tokens.json. "
                         "Complete OAuth login first. Fallback to yfinance.")
        
        self.base_url = (
            "https://api.sandbox.dhan.co" if env == "sandbox"
            else "https://api.dhan.co"
        )

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get live quote for symbol."""
        if not self.access_token:
            logger.debug(f"Dhan token not available for {symbol}, skipping")
            return None
        
        # Use self.access_token for API calls
        # ... existing implementation ...
        pass

    def refresh_token_if_updated(self):
        """Check if token was updated in file."""
        new_token = get_dhan_token()
        if new_token and new_token != self.access_token:
            old = self.access_token[:10] + "..." if self.access_token else "None"
            new = new_token[:10] + "..."
            logger.info(f"Token updated: {old} → {new}")
            self.access_token = new_token
```

### Step 3: Add Token Health Monitoring (Optional)

**File:** `control_tower/agent_status_monitor.py` (or equivalent)

```python
#!/usr/bin/env python3
"""Agent status monitoring."""

import logging
from utils.logger import get_logger
from utils.dhan_token_manager import get_token_status  # ADD THIS IMPORT

logger = get_logger(__name__)

class SystemMonitor:
    """Monitor system and agent health."""

    def check_system_health(self) -> Dict:
        """Check overall system health including token."""
        health = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "token": self._check_token_health(),  # ADD THIS
        }
        return health

    def _check_token_health(self) -> Dict:
        """Check Dhan token health."""
        try:
            status = get_token_status()
            if status:
                expires_in = status.get("expires_in_days", 0)
                warning = expires_in < 7
                
                if warning:
                    logger.warning(f"⚠ Dhan token expires in {expires_in} days")
                
                return {
                    "available": True,
                    "age_days": status.get("age_days"),
                    "expires_in_days": expires_in,
                    "warning": warning,
                }
        except Exception as e:
            logger.debug(f"Could not check token status: {e}")
        
        return {"available": False}
```

---

## Testing the Integration

### Test 1: Verify Token Manager Imports

```bash
cd /root/ai-trading-brain
python3 -c "from utils.dhan_token_manager import get_dhan_token, watch_token_file_start; print('✓ Imports OK')"
```

### Test 2: Start Orchestrator and Monitor Token

```bash
cd /root/ai-trading-brain
python3 -c "
from orchestrator.master_orchestrator import MasterOrchestrator
import time

# Initialize (starts token watcher)
orch = MasterOrchestrator()

# Monitor token status for 10 seconds
for i in range(10):
    from utils.dhan_token_manager import get_token_status
    status = get_token_status()
    print(f'[{i}] Token status: {status}')
    time.sleep(1)
"
```

### Test 3: Simulate Token Capture

```bash
# 1. Manually create a test token
cat > /root/ai-trading-brain/config/api_tokens.json << 'EOF'
{
  "dhan_request_code": "test_code_12345",
  "captured_at": "2026-03-18T11:30:00",
  "status": "captured"
}
EOF

# 2. Set proper permissions
chmod 600 /root/ai-trading-brain/config/api_tokens.json

# 3. Verify token manager loads it
python3 -c "
from utils.dhan_token_manager import get_dhan_token, get_token_status
token = get_dhan_token()
status = get_token_status()
print(f'Token loaded: {token}')
print(f'Status: {status}')
"
```

### Test 4: Monitor Token Changes in Real-time

```bash
# Terminal 1: Start watcher
python3 -c "
from utils.dhan_token_manager import watch_token_file_start
import time
watch_token_file_start(poll_interval=5)
print('Watcher running... watching for changes')
time.sleep(120)
"

# Terminal 2: Simulate new token capture
sleep 30
cat > /root/ai-trading-brain/config/api_tokens.json << 'EOF'
{
  "dhan_request_code": "new_token_67890",
  "captured_at": "2026-03-18T11:40:00",
  "status": "captured"
}
EOF
```

Watch Terminal 1 for "Token file changed" log message.

---

## Full System Integration Checklist

- [ ] **OAuth Server Running:** `sudo systemctl status dhan-oauth`
- [ ] **Token Watcher Started:** Add to `MasterOrchestrator.__init__`
- [ ] **Dynamic Token Loading:** Update `DhanFeed.__init__`
- [ ] **Optional: Token Health Monitoring:** Add to `SystemMonitor`
- [ ] **Restart Trading Engine:** `sudo systemctl restart trading-brain`
- [ ] **Verify Logs:** No import errors in trading engine logs
- [ ] **Test Token Capture:** Login via OAuth URL, verify file appears
- [ ] **Test Dynamic Loading:** Verify feed uses new token without restart

---

## Workflow After Integration

### First-Time Setup (Once)
1. ✅ OAuth server deployed and running (`systemctl status dhan-oauth`)
2. ✅ Token watcher started in orchestrator
3. ✅ Dhan feed uses dynamic loader
4. ✅ Trading engine restarted

### Token Capture (User-Initiated)
1. Get Dhan Client ID from Dhan portal
2. Visit OAuth URL: `https://api.dhan.co/oauth2/authorize?client_id=...`
3. Login with credentials + TOTP
4. OAuth server auto-captures code
5. Token saved to `config/api_tokens.json` ✓

### Trading Engine (Automatic)
1. Orchestrator starts → token watcher begins monitoring
2. Dhan feed loads token from file (or env fallback)
3. Trading cycle runs → uses fresh token
4. If token is re-captured → feed auto-detects and updates
5. No restart needed!

### Token Expiration (Automatic)
- 7 days before expiry: Warning alert
- At expiry: Critical alert + fallback to yfinance
- Re-login: Capture new token, system auto-loads

---

## Rollback (If Needed)

To revert to static environment-based tokens:

```python
# In dhan_feed.py, change back to:
self.access_token = os.getenv("DHAN_ACCESS_TOKEN")

# In master_orchestrator.py, remove:
watch_token_file_start(poll_interval=30)
```

---

## Verification

After integration, verify everything is working:

```bash
# Check integration is complete
python3 scripts/test_dhan_oauth.py

# Monitor in real-time
python3 scripts/monitor_dhan_oauth.py --vps

# Tail logs
tail -f /root/ai-trading-brain/data/logs/oauth-callback.log
```

Expected output when trading engine starts:
```
[orchestrator] ✓ Dhan token file watcher started
[dhan_feed] Token loaded from config/api_tokens.json (age: 2 days)
[trading_engine] Ready to trade with Dhan broker
```

---

## Support

For troubleshooting, see: [DHAN_OAUTH_TROUBLESHOOTING.md](./DHAN_OAUTH_TROUBLESHOOTING.md)

For complete setup, see: [DHAN_OAUTH_SETUP.md](./DHAN_OAUTH_SETUP.md)
