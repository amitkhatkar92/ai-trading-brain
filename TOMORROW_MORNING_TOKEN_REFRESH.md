# 🚀 TOMORROW MORNING: Token Capture Action Plan

**Status:** ✅ All systems ready  
**Date:** March 20, 2026  
**Time:** Between 07:00 IST and 09:15 IST (before market open)  
**Duration:** 2-3 minutes  

---

## Current Token Status
- **Current Token**: Valid until 2026-03-19 at **16:51 UTC** (TODAY ~5.5 hours)
- **Tomorrow Status**: ⏰ WILL EXPIRE at market open (09:15 IST)
- **Action Required**: Capture new token tomorrow between 07:00-09:15 IST

**Tomorrow at 09:15 IST when market opens:**
- If token NOT refreshed → ❌ Trading BLOCKED
- If token IS refreshed → ✅ Trading proceeds normally

---

## 📋 TOMORROW'S STEPS (Copy & Paste Ready)

### ⏰ Time: 07:15 AM IST tomorrow (or any time between 07:00-09:15 IST)

### Step 1: Open Your Browser
Paste this URL into your browser address bar:
```
https://api.dhan.co/oauth2/authorize?client_id=2603183256&redirect_uri=http://178.18.252.24:8000&response_type=code&state=trading-brain
```

### Step 2: Login with Dhan Credentials
- Enter your Dhan login (email/phone + password)
- Complete any 2FA if prompted

### Step 3: Authorize the Request
- Click the **"Authorize"** or **"Allow"** button
- Dhan will redirect to your VPS

### Step 4: Success Confirmation
You should see a **GREEN PAGE** with:
- ✓ "Authentication Successful"
- "Your Dhan credentials have been captured"
- "You may close this window"

### Step 5: Verify Token Saved
Wait 2 seconds, then check:
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
# On VPS, run:
tail -5 /root/ai-trading-brain/data/logs/oauth-callback.log
```

You should see:
```
✅ Authorization code captured
✅ Token saved to config/api_tokens.json
```

---

## ✅ WHAT HAPPENS AUTOMATICALLY

Once you complete Step 3 (click Authorize):

1. **OAuth server captures the code** from Dhan
2. **Exchanges it for access token** (automatic)
3. **Saves token to file** with:
   - Expiry: March 20, 2026 at 16:51 UTC (market close tomorrow)
   - Format: DAILY_SESSION
   - Status: active
4. **Displays success page** (Step 4 above)

---

## 🆘 If Something Goes Wrong

### Issue: Browser shows "404 Not Found" instead of success page
**Action:** Restart the OAuth server:
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
systemctl restart dhan-oauth
systemctl status dhan-oauth
```
Then try Step 1 again.

### Issue: Browser shows "Authorization Failed"
**Action:** Check the logs:
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
tail -20 /root/ai-trading-brain/data/logs/oauth-callback.log
```
Look for error messages and report them.

### Issue: Can't access http://178.18.252.24:8000
**Action:** Test connectivity:
```bash
ping 178.18.252.24
curl http://178.18.252.24:8000/health
```
If both fail, VPS is unreachable. Check internet/firewall.

### Issue: Success page appears but token doesn't load in trading engine
**Action:** Check if trading engine is reading the token:
```bash
ssh -i ~/.ssh/trading_vps root@178.18.252.24
cat /root/ai-trading-brain/config/api_tokens.json | grep expires_at
```
Should show today's date (Mar 20) with 16:51 UTC expiry.

---

## 📊 Timeline

| Time | What Happens |
|------|--------------|
| **Now** | Current token valid until 16:51 UTC today |
| **Tomorrow 07:00 IST** | OAuth server ready, waiting for your authorization |
| **Tomorrow 07:15 IST** | ⭐ YOU: Visit OAuth URL, login, authorize |
| **Tomorrow 07:16 IST** | ✅ OAuth server captures token automatically |
| **Tomorrow 07:17 IST** | ✅ Token saved to config/api_tokens.json |
| **Tomorrow 09:15 IST** | Market opens, trading engine loads token |
| **Tomorrow 16:51 UTC** | Token expires (same-day session token) |
| **Tomorrow overnight** | Repeat this process before next market open |

---

## 🔐 Security Notes

- Token contains your authentication to Dhan
- Saved with strict file permissions (600 = read-write only for root)
- Never logged in full (only first 20 chars visible in logs for verification)
- File location: `/root/ai-trading-brain/config/api_tokens.json`

---

## ✨ After Tomorrow

**Important:** This token is DAILY only.

Every trading day, you either:
- **Option A** (Recommended): Do this same process before 09:15 IST
- **Option B** (Planned): Implement automated daily refresh (in development)

Daily token requirement is because Dhan uses session-based tokens (like a browser cookie), not long-lived OAuth tokens.

---

## 📞 Quick Reference

| Item | Value |
|------|-------|
| OAuth URL | `https://api.dhan.co/oauth2/authorize?...` (see Step 1) |
| Callback endpoint | `http://178.18.252.24:8000/` (root, no /callback suffix) |
| Token file | `/root/ai-trading-brain/config/api_tokens.json` |
| Logs | `/root/ai-trading-brain/data/logs/oauth-callback.log` |
| VPS SSH | `ssh -i ~/.ssh/trading_vps root@178.18.252.24` |
| Health check | `curl http://178.18.252.24:8000/health` |

---

## ✅ Ready? 

All systems are configured and tested. OAuth server is running and responding correctly.

**You are GO for tomorrow morning.**

When you're ready, just:
1. Visit the OAuth URL (Step 1)
2. Login & Authorize (Steps 2-3)
3. See the success page (Step 4)
4. ✅ Done!

