#!/bin/bash
# Dhan OAuth Token Management — Deployment to VPS
# Date: March 19, 2026
# April 17, 2026 token expiry tracking

set -e

echo "════════════════════════════════════════════════"
echo "  DEPLOYING DHAN OAUTH UPDATES TO VPS"
echo "════════════════════════════════════════════════"
echo ""

# Configuration
VPS_IP="178.18.252.24"
VPS_USER="root"
SSH_KEY="$HOME/.ssh/trading_vps"
PROJECT_ROOT="/root/ai-trading-brain"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Verify local changes
echo -e "${BLUE}Step 1: Checking local changes...${NC}"
if ! git status --porcelain | grep -E '(utils/dhan_token|scripts/dhan_oauth|DHAN_OAUTH|config/dhan_oauth)' > /dev/null; then
    echo -e "${YELLOW}⚠️  No changes detected in OAuth-related files${NC}"
fi
echo ""

# Step 2: Commit changes
echo -e "${BLUE}Step 2: Committing changes...${NC}"
git add -A
git commit -m "feat: April 17, 2026 token expiry tracking

- Add utils/dhan_token_exchange.py for automatic code→token exchange
- Update utils/dhan_token_manager.py to support explicit expiry dates
- Enhance scripts/dhan_oauth_server.py with automatic token exchange
- Add config/dhan_oauth_config.json for centralized token settings
- Add scripts/validate_dhan_oauth.py for token validation
- Document April 17, 2026 expiry date in DHAN_OAUTH_30DAY_SETUP.md

Token management:
- Client ID: 2603183256
- Token expires: April 17, 2026 (~29 days)
- Refresh alert: April 14 (3-day warning)
- Format: access_token with explicit expires_at field"

echo -e "${GREEN}✅ Changes committed${NC}"
echo ""

# Step 3: Push to GitHub
echo -e "${BLUE}Step 3: Pushing to GitHub...${NC}"
git push origin main
echo -e "${GREEN}✅ Pushed to GitHub${NC}"
echo ""

# Step 4: Pull on VPS
echo -e "${BLUE}Step 4: Pulling changes on VPS...${NC}"
ssh -i "$SSH_KEY" $VPS_USER@$VPS_IP "cd $PROJECT_ROOT && git pull origin main"
echo -e "${GREEN}✅ VPS code updated${NC}"
echo ""

# Step 5: Verify files exist
echo -e "${BLUE}Step 5: Verifying deployed files...${NC}"
ssh -i "$SSH_KEY" $VPS_USER@$VPS_IP bash << 'EOF'
echo "Checking files..."
test -f /root/ai-trading-brain/utils/dhan_token_exchange.py && echo "  ✅ dhan_token_exchange.py" || echo "  ❌ dhan_token_exchange.py MISSING"
test -f /root/ai-trading-brain/config/dhan_oauth_config.json && echo "  ✅ dhan_oauth_config.json" || echo "  ❌ dhan_oauth_config.json MISSING"
test -f /root/ai-trading-brain/scripts/validate_dhan_oauth.py && echo "  ✅ validate_dhan_oauth.py" || echo "  ❌ validate_dhan_oauth.py MISSING"
echo ""
echo "OAuth server status:"
sudo systemctl is-active dhan-oauth && echo "  🟢 OAuth service running" || echo "  🔴 OAuth service not running"
EOF
echo ""

# Step 6: Restart OAuth service
echo -e "${BLUE}Step 6: Restarting OAuth service...${NC}"
ssh -i "$SSH_KEY" $VPS_USER@$VPS_IP "sudo systemctl restart dhan-oauth && sleep 2 && sudo systemctl status dhan-oauth"
echo -e "${GREEN}✅ OAuth service restarted${NC}"
echo ""

# Step 7: Test token validation script
echo -e "${BLUE}Step 7: Testing token validation...${NC}"
ssh -i "$SSH_KEY" $VPS_USER@$VPS_IP "cd $PROJECT_ROOT && python3 scripts/validate_dhan_oauth.py"
echo ""

echo "════════════════════════════════════════════════"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo "════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Login to Dhan OAuth:"
echo "     https://api.dhan.co/oauth2/authorize?client_id=2603183256&redirect_uri=http://178.18.252.24:8000/callback"
echo ""
echo "  2. Verify token captured:"
echo "     ssh -i ~/.ssh/trading_vps root@178.18.252.24 'cat /root/ai-trading-brain/config/api_tokens.json | python3 -m json.tool'"
echo ""
echo "  3. Monitor expiry (April 14, 2026):"
echo "     System will alert at 3-day threshold"
echo ""
