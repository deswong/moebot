#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== MoeBot Service Installer ===${NC}"

# 1. Detect User and Group
CURRENT_USER=$(id -un)
CURRENT_GROUP=$(id -gn)
WORKING_DIR=$(pwd)

echo "Detected User:  $CURRENT_USER"
echo "Detected Group: $CURRENT_GROUP"
echo "Working Dir:    $WORKING_DIR"

# 2. Ensure UV is installed
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to path for this session so we can use it immediately
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        echo "Error: Failed to install uv. Please install it manually."
        exit 1
    fi
else
    echo "uv is already installed."
fi

# 3. Generate Systemd Service File
SERVICE_FILE="moebot.service"
echo "Generating $SERVICE_FILE..."

cat > $SERVICE_FILE <<EOF
[Unit]
Description=MoeBot MQTT Bridge Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_GROUP
WorkingDirectory=$WORKING_DIR
ExecStart=$(which uv) run main.py mqtt
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created:"
cat $SERVICE_FILE

# 4. Install Service
echo -e "${GREEN}Installing service to /etc/systemd/system/... (requires gb_sudo)${NC}"

if [ "$EUID" -eq 0 ]; then
  mv $SERVICE_FILE /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable moebot
  systemctl restart moebot
else
  sudo mv $SERVICE_FILE /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable moebot
  sudo systemctl restart moebot
fi

echo -e "${GREEN}Success! MoeBot service installed and started.${NC}"
echo "Check status directly with: systemctl status moebot"
echo "View logs with: journalctl -u moebot -f"
