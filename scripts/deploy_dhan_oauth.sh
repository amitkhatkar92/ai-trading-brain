#!/bin/bash
#
# Dhan OAuth System — Automated VPS Deployment
# ==============================================
#
# Deploys complete OAuth token capture system to VPS in one command.
#
# Usage:
#   bash scripts/deploy_dhan_oauth.sh
#
# What it does:
#   1. Copies OAuth server to VPS
#   2. Copies token manager to VPS
#   3. Installs systemd service
#   4. Enables auto-start
#   5. Starts OAuth server
#   6. Verifies installation
#

set -e  # Exit on any error

# ─────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────

VPS_HOST="root@178.18.252.24"
VPS_SSH_KEY="~/.ssh/trading_vps"
VPS_HOME="/root/ai-trading-brain"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

# ─────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_header() {
    echo -e "\n${BOLD}$1${NC}"
    echo "─────────────────────────────────────────────────────────────────"
}

ssh_cmd() {
    ssh -i "$VPS_SSH_KEY" "$VPS_HOST" "$@"
}

scp_cmd() {
    scp -i "$VPS_SSH_KEY" "$@"
}

# ─────────────────────────────────────────────────────────────────────────
# Pre-flight Checks
# ─────────────────────────────────────────────────────────────────────────

log_header "🔍 Pre-flight Checks"

# Check local files exist
if [ ! -f "$LOCAL_DIR/scripts/dhan_oauth_server.py" ]; then
    log_error "OAuth server script not found: $LOCAL_DIR/scripts/dhan_oauth_server.py"
    exit 1
fi
log_info "OAuth server script found"

if [ ! -f "$LOCAL_DIR/utils/dhan_token_manager.py" ]; then
    log_error "Token manager not found: $LOCAL_DIR/utils/dhan_token_manager.py"
    exit 1
fi
log_info "Token manager found"

if [ ! -f "$LOCAL_DIR/scripts/dhan-oauth.service" ]; then
    log_error "Systemd service not found: $LOCAL_DIR/scripts/dhan-oauth.service"
    exit 1
fi
log_info "Systemd service definition found"

# Test SSH connection
if ! ssh_cmd "echo 'SSH OK'" > /dev/null 2>&1; then
    log_error "Cannot connect to VPS via SSH"
    exit 1
fi
log_info "SSH connection to VPS OK"

# Check VPS directories
if ! ssh_cmd "[ -d '$VPS_HOME' ]"; then
    log_error "Project directory not found on VPS: $VPS_HOME"
    exit 1
fi
log_info "Project directory exists on VPS"

# Check venv
if ! ssh_cmd "[ -d '$VPS_HOME/venv' ]"; then
    log_error "Python venv not found on VPS: $VPS_HOME/venv"
    exit 1
fi
log_info "Python venv exists on VPS"

# ─────────────────────────────────────────────────────────────────────────
# Deploy Files
# ─────────────────────────────────────────────────────────────────────────

log_header "📦 Deploying Files to VPS"

# OAuth server
log_info "Copying OAuth server script..."
scp_cmd -i "$VPS_SSH_KEY" \
    "$LOCAL_DIR/scripts/dhan_oauth_server.py" \
    "$VPS_HOST:$VPS_HOME/scripts/"

# Token manager
log_info "Copying token manager module..."
scp_cmd -i "$VPS_SSH_KEY" \
    "$LOCAL_DIR/utils/dhan_token_manager.py" \
    "$VPS_HOST:$VPS_HOME/utils/"

# Systemd service (to temp first)
log_info "Copying systemd service definition..."
scp_cmd -i "$VPS_SSH_KEY" \
    "$LOCAL_DIR/scripts/dhan-oauth.service" \
    "$VPS_HOST:/tmp/dhan-oauth.service"

log_info "All files copied successfully"

# ─────────────────────────────────────────────────────────────────────────
# Install Systemd Service
# ─────────────────────────────────────────────────────────────────────────

log_header "⚙️  Installing Systemd Service"

ssh_cmd << 'EOFSH'
    # Copy service file to systemd directory
    sudo cp /tmp/dhan-oauth.service /etc/systemd/system/
    
    # Set permissions
    sudo chmod 644 /etc/systemd/system/dhan-oauth.service
    
    # Refresh systemd daemon
    sudo systemctl daemon-reload
    
    # Enable auto-start on boot
    sudo systemctl enable dhan-oauth
    
    echo "Systemd service installed"
EOFSH

log_info "Systemd service installed"

# ─────────────────────────────────────────────────────────────────────────
# Start OAuth Server
# ─────────────────────────────────────────────────────────────────────────

log_header "🚀 Starting OAuth Server"

ssh_cmd "sudo systemctl start dhan-oauth"
log_info "OAuth server started"

# Wait for server to be ready
sleep 2

# ─────────────────────────────────────────────────────────────────────────
# Verification & Health Check
# ─────────────────────────────────────────────────────────────────────────

log_header "✔️  Verification & Health Checks"

# Check service status
STATUS=$(ssh_cmd "sudo systemctl is-active dhan-oauth" || echo "inactive")
if [ "$STATUS" = "active" ]; then
    log_info "Service status: ACTIVE"
else
    log_error "Service status: $STATUS"
    log_error "Checking error logs..."
    ssh_cmd "sudo systemctl status dhan-oauth --no-pager"
    exit 1
fi

# Check port 8000 is listening
if ssh_cmd "sudo netstat -tuln | grep -q ':8000'"; then
    log_info "Port 8000 is listening"
else
    log_warn "Port 8000 not yet listening (may need a few seconds)"
fi

# Test health endpoint (with retries)
log_info "Testing health endpoint..."
for i in {1..5}; do
    if ssh_cmd "curl -s http://localhost:8000/health | grep -q 'healthy'" 2>/dev/null; then
        log_info "Health check: PASSED ✓"
        break
    fi
    if [ $i -lt 5 ]; then
        sleep 1
    fi
done

# Check log files exist
if ssh_cmd "[ -f '$VPS_HOME/data/logs/oauth-callback.log' ]"; then
    log_info "OAuth log file created"
fi

# ─────────────────────────────────────────────────────────────────────────
# Display Configuration Info
# ─────────────────────────────────────────────────────────────────────────

log_header "📋 Configuration & Next Steps"

VPS_IP=$(ssh_cmd "curl -s https://ifconfig.me" || echo "178.18.252.24")

echo -e "\n${BOLD}OAuth Server Details:${NC}"
echo "  Listening on: http://$VPS_IP:8000"
echo "  Health endpoint: http://$VPS_IP:8000/health"
echo "  Callback URI: http://$VPS_IP:8000/callback"
echo ""

echo -e "${BOLD}Log Files:${NC}"
echo "  OAuth logs: ssh -i $VPS_SSH_KEY $VPS_HOST tail -f $VPS_HOME/data/logs/oauth-callback.log"
echo "  Error logs: ssh -i $VPS_SSH_KEY $VPS_HOST tail -f $VPS_HOME/data/logs/oauth-callback-error.log"
echo ""

echo -e "${BOLD}Service Management:${NC}"
echo "  Start:   ssh -i $VPS_SSH_KEY $VPS_HOST sudo systemctl start dhan-oauth"
echo "  Stop:    ssh -i $VPS_SSH_KEY $VPS_HOST sudo systemctl stop dhan-oauth"
echo "  Restart: ssh -i $VPS_SSH_KEY $VPS_HOST sudo systemctl restart dhan-oauth"
echo "  Status:  ssh -i $VPS_SSH_KEY $VPS_HOST sudo systemctl status dhan-oauth"
echo ""

echo -e "${BOLD}Next Steps:${NC}"
echo "  1. Get Dhan Client ID from: https://dhan.co → My Profile → API"
echo "  2. Visit OAuth URL in your browser:"
echo "     https://api.dhan.co/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://$VPS_IP:8000/callback&response_type=code&state=trading-brain"
echo "  3. Login with Dhan credentials + TOTP code"
echo "  4. Dhan redirects to your OAuth server"
echo "  5. Token automatically captured and saved"
echo ""
echo -e "${BOLD}Verify Token Capture:${NC}"
echo "  ssh -i $VPS_SSH_KEY $VPS_HOST cat $VPS_HOME/config/api_tokens.json"
echo ""

# ─────────────────────────────────────────────────────────────────────────
# Final Status
# ─────────────────────────────────────────────────────────────────────────

log_header "✅ Deployment Complete!"

echo -e "\n${GREEN}🎉 Dhan OAuth System deployed successfully!${NC}\n"

echo "System Status:"
ssh_cmd "sudo systemctl status dhan-oauth --no-pager | head -5"

echo ""
log_info "Ready to capture Dhan tokens automatically"
log_info "See DHAN_OAUTH_SETUP.md for full documentation"
