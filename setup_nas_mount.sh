#!/bin/bash
#
# NAS Mount Setup Script
# This script configures automatic mounting of the Ugreen NAS at boot
#
# NAS Details:
#   IP: 192.168.1.82
#   Share: dt
#   Mount Point: /mnt/nas
#   Username: dt_writer
#   Password: Bunny$

set -e

echo "================================================"
echo "NAS Mount Setup for AV Monitoring System"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install required packages
echo "[1/5] Installing CIFS utilities..."
apt-get update -qq
apt-get install -y cifs-utils

# Create mount point
echo "[2/5] Creating mount point /mnt/nas..."
mkdir -p /mnt/nas

# Create credentials file (secure)
echo "[3/5] Creating secure credentials file..."
cat > /etc/.nascreds << 'EOF'
username=dt_writer
password=Bunny$
EOF
chmod 600 /etc/.nascreds
echo "Credentials saved to /etc/.nascreds (read-only for root)"

# Add to /etc/fstab for automatic mounting at boot
echo "[4/5] Adding NAS mount to /etc/fstab..."

# Remove any existing NAS mount entries to avoid duplicates
sed -i '/192.168.1.82/d' /etc/fstab

# Add new mount entry
cat >> /etc/fstab << 'EOF'

# Ugreen NAS mount for AV recordings
//192.168.1.82/dt /mnt/nas cifs credentials=/etc/.nascreds,uid=1000,gid=1000,file_mode=0664,dir_mode=0775,iocharset=utf8,vers=3.0 0 0
EOF

echo "Added to /etc/fstab"

# Mount the NAS
echo "[5/5] Mounting NAS..."
mount /mnt/nas

# Verify mount
if mountpoint -q /mnt/nas; then
    echo ""
    echo "✅ SUCCESS! NAS mounted successfully"
    echo ""
    echo "Mount details:"
    df -h /mnt/nas
    echo ""
    echo "Testing write access..."
    
    # Test write access
    TEST_FILE="/mnt/nas/test_pi_write_$(date +%s).txt"
    if echo "Test write from Raspberry Pi" > "$TEST_FILE" 2>/dev/null; then
        echo "✅ Write test successful!"
        rm -f "$TEST_FILE"
        echo ""
        echo "NAS is ready for recordings!"
        echo "Files will be saved to: /mnt/nas/dt/raw/YYYY/MM/DD/"
    else
        echo "⚠️  WARNING: Could not write to NAS"
        echo "Check NAS permissions for user 'dt_writer'"
    fi
else
    echo "❌ ERROR: Failed to mount NAS"
    echo "Please check:"
    echo "  1. NAS is powered on and accessible"
    echo "  2. Network connectivity: ping 192.168.1.82"
    echo "  3. Share name 'dt' exists on NAS"
    echo "  4. Credentials are correct"
    exit 1
fi

echo ""
echo "================================================"
echo "NAS Mount Setup Complete!"
echo "================================================"
echo ""
echo "The NAS will automatically mount at boot."
echo "To manually unmount: sudo umount /mnt/nas"
echo "To manually mount: sudo mount /mnt/nas"
echo ""

