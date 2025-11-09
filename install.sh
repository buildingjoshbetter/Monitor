#!/bin/bash
#
# Installation script for Raspberry Pi 5 A/V Monitor System
#
# This script will:
# 1. Check system requirements
# 2. Install Python dependencies
# 3. Configure audio (WM8960)
# 4. Enable I2C for IR sensor
# 5. Set up systemd service
# 6. Validate hardware connections
#

set -e  # Exit on error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "Raspberry Pi 5 A/V Monitor Installation"
echo "================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${RED}Error: This doesn't appear to be a Raspberry Pi${NC}"
    exit 1
fi

MODEL=$(cat /proc/device-tree/model)
echo "Detected: $MODEL"
echo ""

# Check for root/sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Please run with sudo:${NC}"
    echo "  sudo ./install.sh"
    exit 1
fi

# Get the actual user (not root when using sudo)
ACTUAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo "Home directory: $USER_HOME"
echo ""

# ============================================
# Step 1: Update system and install dependencies
# ============================================
echo -e "${GREEN}[1/7] Updating system packages...${NC}"
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    i2c-tools \
    alsa-utils \
    git

# ============================================
# Step 2: Enable I2C
# ============================================
echo -e "${GREEN}[2/7] Enabling I2C interface...${NC}"
raspi-config nonint do_i2c 0
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/firmware/config.txt
fi

# ============================================
# Step 3: Enable Camera (libcamera)
# ============================================
echo -e "${GREEN}[3/7] Enabling camera interface...${NC}"
raspi-config nonint do_camera 0

# Ensure camera is enabled in config.txt
if ! grep -q "^camera_auto_detect=1" /boot/firmware/config.txt; then
    echo "camera_auto_detect=1" >> /boot/firmware/config.txt
fi

# ============================================
# Step 4: Install WM8960 Audio HAT driver
# ============================================
echo -e "${GREEN}[4/7] Installing WM8960 audio HAT driver...${NC}"
echo "This will install the Waveshare WM8960 driver..."

# Clone and install WM8960 driver
WM8960_DIR="/tmp/WM8960-Audio-HAT"
if [ -d "$WM8960_DIR" ]; then
    rm -rf "$WM8960_DIR"
fi

git clone https://github.com/waveshare/WM8960-Audio-HAT "$WM8960_DIR"
cd "$WM8960_DIR"
./install.sh

# Return to original directory
cd - > /dev/null

echo "WM8960 driver installed. May require reboot to take effect."
echo ""

# ============================================
# Step 5: Install Python dependencies
# ============================================
echo -e "${GREEN}[5/7] Installing Python dependencies...${NC}"

# Install system-wide for simplicity (can use venv if preferred)
pip3 install --break-system-packages -r requirements.txt

# ============================================
# Step 6: Create directories and copy files
# ============================================
echo -e "${GREEN}[6/7] Setting up directories and configuration...${NC}"

# Create capture directory
CAPTURE_DIR="$USER_HOME/captures"
mkdir -p "$CAPTURE_DIR"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$CAPTURE_DIR"

# Create config directory
CONFIG_DIR="/etc/av_monitor"
mkdir -p "$CONFIG_DIR"

# Copy config file if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cp config.json "$CONFIG_DIR/config.json"
    # Update capture_dir in config to use actual user home
    sed -i "s|/home/pi/captures|$CAPTURE_DIR|g" "$CONFIG_DIR/config.json"
    echo "Configuration created at $CONFIG_DIR/config.json"
else
    echo "Configuration already exists at $CONFIG_DIR/config.json (not overwriting)"
fi

# Create log directory
mkdir -p /var/log
touch /var/log/av_monitor.log
chown "$ACTUAL_USER:$ACTUAL_USER" /var/log/av_monitor.log

# Copy main script to user directory
INSTALL_DIR="$USER_HOME/Monitor"
mkdir -p "$INSTALL_DIR"
cp av_monitor.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/av_monitor.py"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$INSTALL_DIR"

# ============================================
# Step 7: Install systemd service
# ============================================
echo -e "${GREEN}[7/7] Installing systemd service...${NC}"

# Update service file with actual user and paths
cp av-monitor.service /etc/systemd/system/av-monitor.service
sed -i "s|User=pi|User=$ACTUAL_USER|g" /etc/systemd/system/av-monitor.service
sed -i "s|Group=pi|Group=$ACTUAL_USER|g" /etc/systemd/system/av-monitor.service
sed -i "s|/home/pi/Monitor|$INSTALL_DIR|g" /etc/systemd/system/av-monitor.service

# Reload systemd
systemctl daemon-reload

# Enable service (but don't start yet - let user validate first)
systemctl enable av-monitor.service

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo ""
echo "1. REBOOT your Raspberry Pi to activate all drivers:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, run validation tests:"
echo "   ./validate.sh"
echo ""
echo "3. If validation passes, start the service:"
echo "   sudo systemctl start av-monitor.service"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status av-monitor.service"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u av-monitor.service -f"
echo "   or: tail -f /var/log/av_monitor.log"
echo ""
echo "Configuration file: $CONFIG_DIR/config.json"
echo "Capture directory: $CAPTURE_DIR"
echo "================================================"

