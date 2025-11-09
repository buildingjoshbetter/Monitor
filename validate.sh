#!/bin/bash
#
# Hardware validation script for Raspberry Pi 5 A/V Monitor
#
# This script checks:
# 1. I2C interface and AMG8833 sensor
# 2. Camera interface and IMX708
# 3. Audio device (WM8960)
# 4. rpicam-vid availability
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

echo "================================================"
echo "Hardware Validation for A/V Monitor System"
echo "================================================"
echo ""

# ============================================
# Check 1: I2C Interface
# ============================================
echo -e "${YELLOW}[1/5] Checking I2C interface...${NC}"
if [ -e /dev/i2c-1 ]; then
    echo -e "${GREEN}✓${NC} I2C interface /dev/i2c-1 exists"
    ((PASS++))
    
    # Check for AMG8833 at address 0x69
    echo "Scanning for AMG8833 sensor (address 0x69)..."
    if i2cdetect -y 1 | grep -q "69"; then
        echo -e "${GREEN}✓${NC} AMG8833 sensor detected at address 0x69"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} AMG8833 sensor NOT detected"
        echo "  Expected at I2C address 0x69"
        echo "  Check wiring: SDA→GPIO2, SCL→GPIO3, VCC→3.3V, GND→GND"
        ((FAIL++))
    fi
else
    echo -e "${RED}✗${NC} I2C interface not available"
    echo "  Run: sudo raspi-config → Interface Options → I2C → Enable"
    ((FAIL++))
fi
echo ""

# ============================================
# Check 2: Camera Interface
# ============================================
echo -e "${YELLOW}[2/5] Checking camera interface...${NC}"
if [ -e /dev/video0 ]; then
    echo -e "${GREEN}✓${NC} Camera device /dev/video0 exists"
    ((PASS++))
    
    # Test camera with rpicam-hello
    echo "Testing camera with rpicam-hello (3 seconds)..."
    if timeout 5 rpicam-hello -t 3000 --nopreview > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Camera test successful"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Camera test failed"
        echo "  Ensure IMX708 is connected to CAMERA port (not DISP)"
        echo "  Use 22-pin→15-pin ribbon cable"
        echo "  Try: rpicam-hello -t 3000"
        ((FAIL++))
    fi
else
    echo -e "${RED}✗${NC} Camera device not found"
    echo "  Run: sudo raspi-config → Interface Options → Camera → Enable"
    echo "  Ensure camera is properly connected"
    ((FAIL++))
fi
echo ""

# ============================================
# Check 3: rpicam-vid availability
# ============================================
echo -e "${YELLOW}[3/5] Checking rpicam-vid...${NC}"
if command -v rpicam-vid > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} rpicam-vid is installed"
    ((PASS++))
    
    VERSION=$(rpicam-vid --version 2>&1 | head -n 1)
    echo "  Version: $VERSION"
else
    echo -e "${RED}✗${NC} rpicam-vid not found"
    echo "  Install with: sudo apt install rpicam-apps"
    ((FAIL++))
fi
echo ""

# ============================================
# Check 4: Audio Device (WM8960)
# ============================================
echo -e "${YELLOW}[4/5] Checking audio device...${NC}"
if arecord -l | grep -q "wm8960"; then
    echo -e "${GREEN}✓${NC} WM8960 audio device detected"
    ((PASS++))
    
    # Show audio device info
    echo "Audio capture devices:"
    arecord -l | grep "wm8960"
    
    # Check if plughw:1,0 is available
    if arecord -D plughw:1,0 -d 1 -f cd /dev/null 2> /dev/null; then
        echo -e "${GREEN}✓${NC} Audio device plughw:1,0 is working"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠${NC} Audio device may need configuration"
        echo "  Try: alsamixer (adjust 'Mic PGA' gain)"
    fi
else
    echo -e "${RED}✗${NC} WM8960 audio device not found"
    echo "  Install WM8960 driver:"
    echo "  git clone https://github.com/waveshare/WM8960-Audio-HAT"
    echo "  cd WM8960-Audio-HAT"
    echo "  sudo ./install.sh"
    ((FAIL++))
fi
echo ""

# ============================================
# Check 5: Python Dependencies
# ============================================
echo -e "${YELLOW}[5/5] Checking Python dependencies...${NC}"
if python3 -c "import adafruit_amg88xx" 2> /dev/null; then
    echo -e "${GREEN}✓${NC} adafruit_amg88xx library installed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} adafruit_amg88xx library not found"
    echo "  Install with: pip3 install -r requirements.txt"
    ((FAIL++))
fi

if python3 -c "import board, busio" 2> /dev/null; then
    echo -e "${GREEN}✓${NC} Adafruit Blinka libraries installed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Adafruit Blinka libraries not found"
    echo "  Install with: pip3 install -r requirements.txt"
    ((FAIL++))
fi
echo ""

# ============================================
# Summary
# ============================================
echo "================================================"
echo "Validation Summary"
echo "================================================"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You can now start the monitoring system:"
    echo "  sudo systemctl start av-monitor.service"
    echo ""
    echo "Or test manually:"
    echo "  python3 ~/Monitor/av_monitor.py"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo "Please fix the issues above before starting the system."
    exit 1
fi

