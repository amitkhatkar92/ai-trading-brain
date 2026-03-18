#!/bin/bash
#
# Contabo VPS Setup Script for AI Trading Brain
# Run this once on the cloud server to prepare for Docker deployment
#
# Usage: bash /root/setup-vps.sh
#

set -e  # Exit on error

echo "🔧 AI Trading Brain - VPS Setup"
echo "================================"

# Update system
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
echo "📦 Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
echo "📦 Installing Git..."
apt-get install -y git

# Create project directory
PROJECT_DIR="/root/ai-trading-brain"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 Creating project directory..."
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    git init
else
    echo "📁 Project directory already exists"
    cd "$PROJECT_DIR"
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p "$PROJECT_DIR/data/logs"
mkdir -p "$PROJECT_DIR/data/live"
mkdir -p "$PROJECT_DIR/data/historical"
mkdir -p "$PROJECT_DIR/logs"

# Set permissions
chmod -R 755 "$PROJECT_DIR/data" "$PROJECT_DIR/logs"

# Create .env file (with placeholder values)
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "🔐 Creating .env file..."
    cat > "$PROJECT_DIR/.env" << 'EOF'
# Active broker
ACTIVE_BROKER=zerodha

# Zerodha credentials (fill in your actual values)
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
ZERODHA_ACCESS_TOKEN=your_access_token

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Paper trading mode
PAPER_TRADING=true
EOF
    echo "⚠️  Please edit .env with your broker credentials!"
fi

# Create docker-compose override file for cloud
if [ ! -f "$PROJECT_DIR/docker-compose.override.yml" ]; then
    echo "🐳 Creating docker-compose override for cloud..."
    cat > "$PROJECT_DIR/docker-compose.override.yml" << 'EOF'
version: '3.9'

services:
  ai-trading-brain:
    mem_limit: 4g
    cpus: '2.0'
    
  streamlit-dashboard:
    ports:
      - "8501:8501"
EOF
fi

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > "$PROJECT_DIR/monitor.sh" << 'EOF'
#!/bin/bash
# Monitor trading system health

echo "🔍 AI Trading Brain Health Check"
echo "=================================="

# Check if container is running
echo "Container Status:"
docker ps | grep ai-trading-brain && echo "✅ Trading engine is running" || echo "❌ Trading engine is stopped"

# Show container logs (last 20 lines)
echo ""
echo "Latest Logs:"
docker logs --tail 20 ai-trading-brain 2>/dev/null || echo "No logs available"

# Disk usage
echo ""
echo "Disk Usage:"
df -h /root/ai-trading-brain

# Memory usage
echo ""
echo "Memory Usage:"
docker stats --no-stream ai-trading-brain 2>/dev/null || echo "Container stats unavailable"

# Check paper trades
echo ""
echo "Latest Paper Trades:"
if [ -f "/root/ai-trading-brain/data/paper_trades.csv" ]; then
    tail -5 /root/ai-trading-brain/data/paper_trades.csv
else
    echo "No trade file found"
fi
EOF

chmod +x "$PROJECT_DIR/monitor.sh"

# Start Docker daemon
echo "🚀 Starting Docker daemon..."
systemctl start docker
systemctl enable docker

# Verify installation
echo ""
echo "✅ Verification:"
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo "Git version: $(git --version)"

echo ""
echo "✨ VPS Setup Complete!"
echo "=================================="
echo "Next steps:"
echo "1. cd /root/ai-trading-brain"
echo "2. Edit .env with your broker credentials: nano .env"
echo "3. Clone repository: git clone https://github.com/amitkhatkar92/ai-trading-brain.git ."
echo "4. Start containers: docker-compose up -d"
echo "5. Monitor: bash monitor.sh"
echo ""
