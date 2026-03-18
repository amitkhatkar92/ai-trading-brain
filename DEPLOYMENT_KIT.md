# 🚀 AI Trading Brain — DEPLOYMENT KIT
# Generated: March 18, 2026
# Run these commands in order

# ============================================================================
# STEP 1: ENSURE GIT IS INSTALLED
# ============================================================================
# Manual: Download from https://git-scm.com/download/win
# OR use this:
curl -L https://github.com/git-for-windows/git/releases/download/v2.53.0.windows.1/Git-2.53.0-64-bit.exe -o git-installer.exe
# Double-click to install, choose: Use Git from PowerShell

# After Git installed, verify:
git --version

# ============================================================================
# STEP 2: CREATE SSH KEYS FOR VPS ACCESS
# ============================================================================
# Run in PowerShell (as regular user, not admin):

mkdir -Force $env:USERPROFILE\.ssh
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\trading_vps" -N ""

# View private key (you'll need to paste to GitHub secret):
Get-Content "$env:USERPROFILE\.ssh\trading_vps"

# View public key (you'll paste to VPS ~/.ssh/authorized_keys):
Get-Content "$env:USERPROFILE\.ssh\trading_vps.pub"

# ============================================================================
# STEP 3: INITIALIZE GIT AND PREPARE FOR GITHUB
# ============================================================================

cd c:\Users\UCIC\OneDrive\Desktop\ai_trading_brain

# Check if git repo exists
git status

# If error: repository not found, initialize:
git init
git config user.name "Amit Khatkar"
git config user.email "amitkhatkar92@gmail.com"

# Add all files
git add --all

# Create initial commit
git commit -m "Initial: AI Trading Brain with Docker + CI/CD setup"

# ============================================================================
# STEP 4: GITHUB SETUP (BROWSER - MANUAL)
# ============================================================================
# 1. Go to https://github.com/new
# 2. Create repository:
#    - Name: ai-trading-brain
#    - Description: Hierarchical Multi-Agent Trading System
#    - Visibility: Public
#    - Do NOT initialize with README
# 3. Click "Create repository"
# 4. GitHub will show you: "git remote add origin..." command
#    Copy that URL (should be: https://github.com/amitkhatkar92/ai-trading-brain.git)

# ============================================================================
# STEP 5: ADD REMOTE AND PUSH TO GITHUB
# ============================================================================

# Add remote (replace with your actual GitHub repo URL if different):
git remote add origin https://github.com/amitkhatkar92/ai-trading-brain.git

# Rename branch to main
git branch -M main

# Push to GitHub (will prompt for credentials)
git push -u origin main
# You'll be asked to authenticate. Use:
#   - Username: amitkhatkar92
#   - Password: [your GitHub personal access token]
#     Get token from: https://github.com/settings/tokens

# ============================================================================
# STEP 6: ADD GITHUB SECRETS (BROWSER - MANUAL)
# ============================================================================
# Go to: https://github.com/amitkhatkar92/ai-trading-brain/settings/secrets/actions
# Click "New repository secret" and add:

# Secret 1: DOCKER_USERNAME
# Value: amitkhatkar92

# Secret 2: DOCKER_PASSWORD
# Value: [get from Docker Hub at https://hub.docker.com/settings/security]
# - Click "New Access Token"
# - Name it: "ai-trading-brain"
# - Copy the token

# Secret 3: VPS_HOST
# Value: 178.18.252.24

# Secret 4: VPS_SSH_KEY
# Value: [paste your ENTIRE private SSH key from Step 2]
# Include the -----BEGIN OPENSSH PRIVATE KEY----- header

# ============================================================================
# STEP 7: SETUP VPS (SSH - MANUAL)
# ============================================================================

# SSH into VPS:
ssh -i "$env:USERPROFILE\.ssh\trading_vps" root@178.18.252.24

# Once logged in, run setup:
cd /root
curl -O https://raw.githubusercontent.com/amitkhatkar92/ai-trading-brain/main/scripts/setup-vps.sh
bash setup-vps.sh

# This auto-installs: Docker, Docker Compose, Git, directories

# ============================================================================
# STEP 8: ADD YOUR SSH PUBLIC KEY TO VPS
# ============================================================================
# Still on VPS, create SSH directory if not exists:
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key from Step 2:
echo "YOUR_PUBLIC_KEY_CONTENT_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Test SSH connection from local (exit VPS first):
exit
ssh -i "$env:USERPROFILE\.ssh\trading_vps" root@178.18.252.24 "echo 'SSH works!'"

# ============================================================================
# STEP 9: CONFIGURE .ENV ON VPS
# ============================================================================
# SSH back in:
ssh -i "$env:USERPROFILE\.ssh\trading_vps" root@178.18.252.24

# Edit config:
nano /root/ai-trading-brain/.env

# Add your broker credentials:
# ACTIVE_BROKER=zerodha
# ZERODHA_API_KEY=your_key
# ZERODHA_API_SECRET=your_secret
# ZERODHA_ACCESS_TOKEN=your_token

# Save: Ctrl+O → Enter → Ctrl+X

# ============================================================================
# STEP 10: FIRST MANUAL DEPLOYMENT
# ============================================================================
# On VPS:
cd /root/ai-trading-brain

# Clone code from GitHub:
git clone https://github.com/amitkhatkar92/ai-trading-brain.git .

# Start containers:
docker-compose up -d

# Verify running:
docker ps

# Check logs:
docker logs ai-trading-brain

# ============================================================================
# STEP 11: VERIFY DEPLOYMENT
# ============================================================================
# Monitor:
bash /root/ai-trading-brain/monitor.sh

# Access dashboard:
# Open browser: http://178.18.252.24:8501

# Check paper trades:
tail -20 /root/ai-trading-brain/data/paper_trades.csv

# ============================================================================
# STEP 12: TEST AUTO-DEPLOYMENT
# ============================================================================
# Make a test change locally:
cd c:\Users\UCIC\OneDrive\Desktop\ai_trading_brain
echo "# Auto-deployment test $(date)" >> README.md
git add README.md
git commit -m "Test: verify GitHub Actions auto-deploy"
git push origin main

# Watch workflow:
# https://github.com/amitkhatkar92/ai-trading-brain/actions

# Should complete in 3-5 minutes, VPS updated automatically ✅

# ============================================================================
# DONE! 🎉
# ============================================================================
