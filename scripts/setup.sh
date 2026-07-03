#!/bin/bash
# VPS Setup Script for Cloudflare Auto Signup
# Run as root on Ubuntu 22.04+

set -e

echo "🔧 Setting up Cloudflare Auto Signup environment..."

# Update system
apt update -y

# Install Chrome
if ! command -v google-chrome-stable &> /dev/null; then
    echo "📦 Installing Google Chrome..."
    apt install -y wget gnupg
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
    apt update -y
    apt install -y google-chrome-stable
fi

# Install Xvfb (virtual display)
echo "📦 Installing Xvfb..."
apt install -y xvfb

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install nodriver opencv-python-headless httpx Pillow

# Install project requirements
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Create config if not exists
if [ ! -f config.json ]; then
    cp config.example.json config.json
    echo "⚙️  Created config.json from template — edit with your settings"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  xvfb-run --auto-servernum python main.py --accounts 1"
echo ""
echo "With proxy:"
echo "  xvfb-run --auto-servernum python main.py --accounts 5 --proxy http://user:pass@host:port"
