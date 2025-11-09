# NAS Integration Setup Guide

This guide explains how to configure your Raspberry Pi to automatically save recordings to your Ugreen NAS.

---

## 📋 Overview

**NAS Details:**
- **Model:** Ugreen DXP4800 Plus (4-bay)
- **IP Address:** `192.168.1.82`
- **Share Name:** `dt`
- **Mount Point:** `/mnt/nas`
- **Username:** `dt_writer`
- **Password:** `Bunny$`

**File Structure:**
```
/mnt/nas/dt/raw/
├── 2025/
│   ├── 11/
│   │   ├── 09/
│   │   │   ├── 11092025_sauron-unit-1_143022.mp4
│   │   │   ├── 11092025_sauron-unit-1_150134.mp4
│   │   │   └── 11092025_sauron-unit-1_152445.mp4
│   │   └── 10/
│   │       └── 11102025_sauron-unit-1_091523.mp4
│   └── 12/
│       └── ...
```

**Filename Format:** `MMDDYYYY_hostname_HHMMSS.mp4`
- `MMDDYYYY` - Date (e.g., 11092025 for November 9, 2025)
- `hostname` - Raspberry Pi hostname (e.g., sauron-unit-1)
- `HHMMSS` - Time (e.g., 143022 for 2:30:22 PM)

---

## 🚀 Quick Setup

### Step 1: Verify Network Connectivity

On your Raspberry Pi:

```bash
ping -c 4 192.168.1.82
```

You should see successful ping responses. If not, check network cables and NAS power.

---

### Step 2: Pull Latest Code

```bash
cd ~/Monitor
git pull origin main
```

---

### Step 3: Run NAS Mount Setup

```bash
cd ~/Monitor
chmod +x setup_nas_mount.sh
sudo ./setup_nas_mount.sh
```

This script will:
1. Install required CIFS utilities
2. Create mount point `/mnt/nas`
3. Create secure credentials file
4. Add NAS mount to `/etc/fstab` (auto-mount at boot)
5. Mount the NAS and verify write access

---

### Step 4: Update AV Monitor Configuration

The `config.json` has been updated to point to the NAS:

```bash
sudo cp config.json /etc/av_monitor/config.json
```

---

### Step 5: Restart AV Monitor Service

```bash
sudo systemctl restart av-monitor.service
sudo systemctl status av-monitor.service
```

---

### Step 6: Watch the Logs

```bash
sudo journalctl -u av-monitor.service -f
```

Wave your hand in front of the IR sensor and watch for:
- "Presence detected! Starting recording..."
- "Stopping recording..."
- "Merging audio and video..."
- "Recording saved: /mnt/nas/dt/raw/2025/11/09/..."

---

## 🔍 Verification

### Check NAS Mount

```bash
# Verify NAS is mounted
mountpoint /mnt/nas

# Check available space
df -h /mnt/nas

# List recordings
ls -lh /mnt/nas/dt/raw/$(date +%Y)/$(date +%m)/$(date +%d)/
```

---

### Test Recording Manually

```bash
# Stop the service temporarily
sudo systemctl stop av-monitor.service

# Run in foreground to see output
cd ~/Monitor
python3 av_monitor.py
```

Trigger presence detection and watch for file creation on NAS.

---

## 🛠️ Troubleshooting

### NAS Not Mounting

```bash
# Check mount status
mount | grep nas

# Try manual mount
sudo mount /mnt/nas

# Check system logs
dmesg | tail -20
```

**Common Issues:**
- NAS offline → Check power and network
- Permission denied → Verify credentials in `/etc/.nascreds`
- Share not found → Verify share name "dt" exists on NAS

---

### Permission Errors

If you see "Permission denied" when writing:

```bash
# Check mount options
mount | grep nas

# Verify user ownership
ls -ld /mnt/nas

# Test write access
echo "test" > /mnt/nas/test.txt
rm /mnt/nas/test.txt
```

---

### Service Fails to Start

```bash
# Check service status
sudo systemctl status av-monitor.service

# View detailed logs
sudo journalctl -u av-monitor.service -n 50

# Check if NAS is mounted
mountpoint /mnt/nas
```

---

## 🔐 Security Notes

**Credentials File:** `/etc/.nascreds`
- Permissions: `600` (root read-only)
- Contains NAS username and password
- Never commit this file to git (already in .gitignore)

**NAS Access:**
- Uses dedicated `dt_writer` account
- Limit permissions to `dt` share only
- Consider setting up read-only accounts for viewing

---

## 📊 Monitoring NAS Storage

### Check Disk Usage

```bash
# On Raspberry Pi
df -h /mnt/nas

# Total recording size
du -sh /mnt/nas/dt/raw/
```

### Cleanup Old Recordings (Optional)

To automatically delete recordings older than 30 days:

```bash
# Add to crontab
sudo crontab -e

# Add this line (runs daily at 3 AM)
0 3 * * * find /mnt/nas/dt/raw -name "*.mp4" -mtime +30 -delete
```

---

## 🔄 Adding More Pi Units

When setting up additional Raspberry Pi units:

1. **Set unique hostname during OS setup:**
   ```bash
   sudo raspi-config
   # System Options → Hostname → sauron-unit-2
   ```

2. **Clone this repository:**
   ```bash
   cd ~
   git clone https://github.com/buildingjoshbetter/Monitor.git
   ```

3. **Run installation:**
   ```bash
   cd Monitor
   sudo ./install.sh
   sudo ./setup_nas_mount.sh
   ```

4. **Verify hostname in logs:**
   ```bash
   hostname  # Should show: sauron-unit-2
   ```

All recordings will automatically include the correct unit name!

---

## 📁 File Organization Benefits

✅ **Scalable:** Easy to add more Pi units  
✅ **Organized:** Year/Month/Day hierarchy  
✅ **Identifiable:** Filename shows date, unit, and time  
✅ **Searchable:** Easy to find recordings by date or unit  
✅ **Centralized:** All recordings in one NAS location

**Example search for all Unit 1 recordings on Nov 9:**
```bash
find /mnt/nas/dt/raw/2025/11/09/ -name "*sauron-unit-1*"
```

---

## 🎯 Next Steps

- ✅ NAS mounted and accessible
- ✅ Recordings saving to structured folders
- ✅ Hostname-based identification working
- 🔜 Set up automatic cleanup of old recordings
- 🔜 Configure NAS backup/redundancy
- 🔜 Add web interface for viewing recordings

---

**Need Help?** Check logs with:
```bash
sudo journalctl -u av-monitor.service -f
```

