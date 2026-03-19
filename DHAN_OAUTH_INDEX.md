# Dhan OAuth System — Documentation Index

**Complete reference to all documentation, guides, and tools.**

---

## 🎯 START HERE

### First Time? (New users)
👉 **[DHAN_OAUTH_QUICK_START.md](./DHAN_OAUTH_QUICK_START.md)** (5 min read)
- Step-by-step OAuth login flow
- How to verify token captured
- Common issues & quick fixes

### Want Full Details? (Setup/Installation)
👉 **[DHAN_OAUTH_SETUP.md](./DHAN_OAUTH_SETUP.md)** (15 min read)
- Complete system architecture
- Installation procedure
- Security checklist
- Troubleshooting gallery

### Integrating with Trading Engine? (Developers)
👉 **[DHAN_OAUTH_INTEGRATION.md](./DHAN_OAUTH_INTEGRATION.md)** (20 min read)
- Code examples
- Orchestrator integration
- Dhan feed integration
- Testing procedures

### Something's Broken? (Troubleshooting)
👉 **[DHAN_OAUTH_TROUBLESHOOTING.md](./DHAN_OAUTH_TROUBLESHOOTING.md)** (Reference)
- 12 common problems
- Diagnosis & fixes for each
- Emergency procedures
- Support resources

### Need Quick Commands? (Operators)
👉 **[DHAN_OAUTH_REFERENCE.md](./DHAN_OAUTH_REFERENCE.md)** (1-page cheat sheet)
- All key commands
- File locations
- Service management
- Setup checklist

### Want Project Overview? (Everyone)
👉 **[DHAN_OAUTH_README.md](./DHAN_OAUTH_README.md)** (10 min read)
- Project overview
- Architecture diagram
- Feature summary
- Integration roadmap

### See What Was Delivered? (Project managers)
👉 **[DHAN_OAUTH_DELIVERY_MANIFEST.md](./DHAN_OAUTH_DELIVERY_MANIFEST.md)** (5 min read)
- Complete file listing
- Feature checklist
- Current status
- Quality assurance summary

---

## 📚 FULL DOCUMENTATION MAP

```
DHAN OAuth System Documentation
├── 🟢 START HERE
│   ├── DHAN_OAUTH_QUICK_START.md          ← 5-minute quick start
│   └── DHAN_OAUTH_README.md               ← Project overview
│
├── 📖 DETAILED GUIDES
│   ├── DHAN_OAUTH_SETUP.md                ← Complete installation
│   ├── DHAN_OAUTH_INTEGRATION.md          ← Developer guide
│   └── DHAN_OAUTH_TROUBLESHOOTING.md      ← Problem solving
│
├── 🔧 REFERENCE
│   ├── DHAN_OAUTH_REFERENCE.md            ← Quick commands
│   └── DHAN_OAUTH_IMPLEMENTATION_SUMMARY.md ← Technical details
│
├── 📋 PROJECT DOCS
│   └── DHAN_OAUTH_DELIVERY_MANIFEST.md    ← What was delivered
│
└── 🛠️ TOOLS
    ├── scripts/test_dhan_oauth.py         ← Verification tool
    ├── scripts/monitor_dhan_oauth.py      ← Monitoring tool
    ├── scripts/dhan_oauth_server.py       ← OAuth server code
    └── utils/dhan_token_manager.py        ← Token manager code
```

---

## 🎯 CHOOSE YOUR PATH

### Path 1: I Want to Use It NOW (5 minutes)

1. Read: [DHAN_OAUTH_QUICK_START.md](./DHAN_OAUTH_QUICK_START.md)
2. Run: `python3 scripts/test_dhan_oauth.py`
3. Visit OAuth URL to login
4. Done!

### Path 2: I Need Full Setup Details (30 minutes)

1. Read: [DHAN_OAUTH_SETUP.md](./DHAN_OAUTH_SETUP.md)
2. Follow installation steps
3. Review security checklist
4. Verify deployment with tools

### Path 3: I'm Integrating with Trading Engine (1 hour)

1. Read: [DHAN_OAUTH_INTEGRATION.md](./DHAN_OAUTH_INTEGRATION.md)
2. Add code to orchestrator
3. Update Dhan feed
4. Run integration tests
5. Restart service

### Path 4: Something's Not Working (As needed)

1. Run: `python3 scripts/test_dhan_oauth.py --verbose`
2. See: [DHAN_OAUTH_TROUBLESHOOTING.md](./DHAN_OAUTH_TROUBLESHOOTING.md)
3. Follow diagnosis & fixes
4. Verify fix: `python3 scripts/monitor_dhan_oauth.py --vps`

### Path 5: I Need Quick Reference (Ongoing)

1. Bookmark: [DHAN_OAUTH_REFERENCE.md](./DHAN_OAUTH_REFERENCE.md)
2. Print the page (it's one sheet)
3. Keep handy for common commands

---

## 📖 DOCUMENT DESCRIPTIONS

### DHAN_OAUTH_QUICK_START.md
**Purpose:** Get started in 5 minutes  
**Audience:** End users wanting to capture their first token  
**Content:**
- OAuth login flow (step-by-step)
- Token verification
- Service management commands
- Common quick fixes

### DHAN_OAUTH_README.md
**Purpose:** Project overview & architecture  
**Audience:** Everyone - understand what the system does  
**Content:**
- System overview
- How it works (3-step flow)
- Architecture diagram
- Features & benefits

### DHAN_OAUTH_SETUP.md
**Purpose:** Complete setup & installation guide  
**Audience:** Administrators & operators  
**Content:**
- Full architecture with diagrams
- 7-step installation procedure
- 3 usage scenarios
- Security verification (8-point checklist)
- Troubleshooting gallery

### DHAN_OAUTH_INTEGRATION.md
**Purpose:** Application developer guide  
**Audience:** Python developers integrating with trading engine  
**Content:**
- Integration points in code
- Orchestrator integration example
- Dhan feed integration example
- Token health monitoring
- Testing & verification steps

### DHAN_OAUTH_TROUBLESHOOTING.md
**Purpose:** Problem diagnosis & resolution  
**Audience:** Anyone experiencing issues  
**Content:**
- 12 problem categories
- Diagnosis steps for each
- Multiple fix options
- Emergency procedures
- Quick support checklist

### DHAN_OAUTH_REFERENCE.md
**Purpose:** Quick command reference (print-friendly)  
**Audience:** Operators & DevOps engineers  
**Content:**
- All key commands
- File locations & purposes
- System configuration details
- Setup checklist
- Support matrix

### DHAN_OAUTH_IMPLEMENTATION_SUMMARY.md
**Purpose:** Technical implementation details  
**Audience:** Technical architects & lead developers  
**Content:**
- What was delivered (component breakdown)
- How each component works
- Integration checklist
- Learning resources
- Quality assurance summary

### DHAN_OAUTH_DELIVERY_MANIFEST.md
**Purpose:** Project sign-off & delivery confirmation  
**Audience:** Project managers & stakeholders  
**Content:**
- Complete deliverables checklist
- File listing & locations
- Features delivered
- Current deployment status
- Quality assurance results

---

## 🛠️ TOOLS PROVIDED

### Test Script (`scripts/test_dhan_oauth.py`)

**Purpose:** Comprehensive health verification

**Usage:**
```bash
# Quick check
python3 scripts/test_dhan_oauth.py

# Verbose diagnostic
python3 scripts/test_dhan_oauth.py --verbose

# Auto-fix permissions
python3 scripts/test_dhan_oauth.py --fix-perms

# Restart service
python3 scripts/test_dhan_oauth.py --restart
```

**Output:** Colored ✓/✗ for 4 verification sections
- Local deployment
- VPS deployment
- Token file status
- Trading engine integration

### Monitor Script (`scripts/monitor_dhan_oauth.py`)

**Purpose:** Real-time system monitoring

**Usage:**
```bash
# Dashboard (local)
python3 scripts/monitor_dhan_oauth.py

# Dashboard (VPS remote)
python3 scripts/monitor_dhan_oauth.py --vps

# Follow logs
python3 scripts/monitor_dhan_oauth.py --follow-logs

# Custom interval
python3 scripts/monitor_dhan_oauth.py --check-interval 10
```

**Output:** Live dashboard with:
- Service status & memory
- Health endpoint status
- Token file information
- Quick command reference

---

## 🔑 KEY CONCEPTS

### OAuth Flow
1. User visits: `https://api.dhan.co/oauth2/authorize?...`
2. Logs in with Dhan credentials + TOTP
3. Dhan redirects to: `http://178.18.252.24:8000/callback?code=ABC123`
4. OAuth server captures code
5. **Token saved automatically** ✓

### Token Manager
- Location: `utils/dhan_token_manager.py`
- Polls: Every 30 seconds
- Monitors: `config/api_tokens.json`
- TTL: 90 days (Dhan standard)
- Warning: 7 days before expiry

### Token Usage
- Loaded: From file (new)
- Fallback: Environment variable
- No restart needed
- Auto-reload on change

---

## 📋 COMMON TASKS QUICK LINKS

| Task | Where | Time |
|------|-------|------|
| **Capture first token** | [Quick Start](./DHAN_OAUTH_QUICK_START.md) | 5 min |
| **Verify deployment** | Run `test_dhan_oauth.py` | 1 min |
| **Monitor system** | Run `monitor_dhan_oauth.py` | ongoing |
| **View logs** | `tail -f data/logs/oauth-callback.log` | ongoing |
| **Integrate with code** | [Integration](./DHAN_OAUTH_INTEGRATION.md) | 1 hour |
| **Fix service issue** | [Troubleshooting](./DHAN_OAUTH_TROUBLESHOOTING.md) | varies |
| **Get quick commands** | [Reference Card](./DHAN_OAUTH_REFERENCE.md) | 2 min |
| **Understand system** | [README](./DHAN_OAUTH_README.md) | 10 min |

---

## 🚀 QUICK START PATHS

### User (I want to use it)
```
START: DHAN_OAUTH_QUICK_START.md
  → Run: python3 scripts/test_dhan_oauth.py
  → Do: Visit OAuth URL to login
  → Done ✓
```

### Operator (I need to maintain it)
```
START: DHAN_OAUTH_REFERENCE.md (bookmark this)
  → Run daily: python3 scripts/monitor_dhan_oauth.py --vps
  → Run weekly: python3 scripts/test_dhan_oauth.py
  → Keep handy for troubleshooting
```

### Developer (I need to integrate it)
```
START: DHAN_OAUTH_INTEGRATION.md
  → Read: Code examples
  → Add: imports to orchestrator
  → Update: dhan_feed.py
  → Test: Integration tests
  → Done ✓
```

### Architect (I need full details)
```
START: DHAN_OAUTH_README.md
  → Read: DHAN_OAUTH_SETUP.md (complete details)
  → Review: DHAN_OAUTH_IMPLEMENTATION_SUMMARY.md
  → Check: DHAN_OAUTH_DELIVERY_MANIFEST.md
```

### Troubleshooter (Something's wrong)
```
START: python3 scripts/test_dhan_oauth.py --verbose
  → See failure details
  → Go to: DHAN_OAUTH_TROUBLESHOOTING.md
  → Find: Your problem
  → Follow: Diagnosis & fixes
```

---

## 📞 GETTING HELP

### Problem Finding the Right Doc?
👉 **[DHAN_OAUTH_README.md](./DHAN_OAUTH_README.md)** — General overview with links

### Quick Commands?
👉 **[DHAN_OAUTH_REFERENCE.md](./DHAN_OAUTH_REFERENCE.md)** — One-page cheat sheet

### Something Broken?
👉 **[DHAN_OAUTH_TROUBLESHOOTING.md](./DHAN_OAUTH_TROUBLESHOOTING.md)** — Problem gallery

### Need Code Examples?
👉 **[DHAN_OAUTH_INTEGRATION.md](./DHAN_OAUTH_INTEGRATION.md)** — Integration guide

### Want Full Details?
👉 **[DHAN_OAUTH_SETUP.md](./DHAN_OAUTH_SETUP.md)** — Complete guide

### Just Starting?
👉 **[DHAN_OAUTH_QUICK_START.md](./DHAN_OAUTH_QUICK_START.md)** — 5-minute guide

---

## 🎯 FILE ORGANIZATION

### By User Role

**End Users:** QUICK_START → README → REFERENCE

**Operators:** REFERENCE → MONITOR → TROUBLESHOOTING

**Developers:** INTEGRATION → SETUP → IMPLEMENTATION_SUMMARY

**Architects:** README → SETUP → IMPLEMENTATION_SUMMARY → DELIVERY_MANIFEST

### By Task

**Initial Setup:** QUICK_START → SETUP

**Daily Use:** REFERENCE (bookmark it)

**Troubleshooting:** TROUBLESHOOTING

**Integration:** INTEGRATION

**Understanding System:** README → SETUP

---

## ✅ VERIFICATION CHECKLIST

- [ ] Found your starting document
- [ ] Read the appropriate guide
- [ ] Ran verification tools
- [ ] System is working or issue is fixed
- [ ] Bookmarked REFERENCE.md for daily use

---

## 📚 COMPLETE FILE LIST

### Documentation
```
DHAN_OAUTH_QUICK_START.md               ← 5-minute quick start
DHAN_OAUTH_README.md                    ← Project overview
DHAN_OAUTH_SETUP.md                     ← Complete setup
DHAN_OAUTH_INTEGRATION.md               ← Developer guide
DHAN_OAUTH_TROUBLESHOOTING.md           ← Problem solving
DHAN_OAUTH_REFERENCE.md                 ← Quick reference
DHAN_OAUTH_IMPLEMENTATION_SUMMARY.md    ← Technical details
DHAN_OAUTH_DELIVERY_MANIFEST.md         ← Delivery confirmation
DHAN_OAUTH_INDEX.md                     ← This file
```

### Tools
```
scripts/test_dhan_oauth.py              ← Verification tool
scripts/monitor_dhan_oauth.py           ← Monitoring tool
```

### Source Code (Already Deployed)
```
scripts/dhan_oauth_server.py            ← OAuth server (deployed)
utils/dhan_token_manager.py             ← Token manager (deployed)
scripts/dhan-oauth.service              ← Systemd config (deployed)
```

---

**All documentation is linked from here for easy navigation.**

**Start with the document matching your role above.** ✓

