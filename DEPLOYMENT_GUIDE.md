# Deployment Guide

## Two Implementation Options

This project includes **two versions** of the monitoring application:

### Option 1: `av_monitor.py` (Recommended)
**Full-featured version with external configuration**

✓ JSON configuration file (`/etc/av_monitor/config.json`)  
✓ Detailed logging to `/var/log/av_monitor.log`  
✓ Systemd service integration  
✓ Runtime adjustable settings (no code changes needed)  
✓ Better error handling and recovery  

**Best for**: Production deployment, long-term operation

### Option 2: `capture_monitor.py` (Simple)
**Self-contained version with embedded configuration**

✓ All settings in Python code (Config class)  
✓ Simpler codebase (~450 lines)  
✓ Fewer dependencies (no JSON parsing)  
✓ Easier to understand and modify  

**Best for**: Learning, prototyping, single-use deployment

---

## Quick Deployment (Option 1 - Recommended)

### 1. Install System

```bash
cd /Users/j/Monitor
sudo ./install.sh
sudo reboot
```

### 2. Validate Hardware

```bash
cd /Users/j/Monitor
./validate.sh
```

Expected: All checks pass ✓

### 3. Test Components (Optional)

```bash
python3 test_components.py
```

This tests each component individually.

### 4. Start Service

```bash
sudo systemctl start av-monitor.service
sudo systemctl enable av-monitor.service  # Auto-start on boot
```

### 5. Monitor Operation

```bash
# Watch logs in real-time
sudo journalctl -u av-monitor.service -f

# Or check log file
tail -f /var/log/av_monitor.log

# Check service status
sudo systemctl status av-monitor.service
```

### 6. Verify Recording

1. Wave hand in front of IR sensor
2. Wait for "Presence detected" message in logs
3. Wait 60+ seconds after removing hand
4. Check for MP4 file:

```bash
ls -lh ~/captures/
```

---

## Manual Testing (Option 2)

If you want to use the simpler version or test manually:

```bash
# Edit configuration directly in the file
nano capture_monitor.py
# Modify the Config class at the top

# Run directly
python3 capture_monitor.py

# Stop with Ctrl+C
```

---

## Configuration Comparison

### Option 1 Configuration
Edit `/etc/av_monitor/config.json`:
```json
{
  "capture_dir": "/home/pi/captures",
  "temperature_threshold": 28.0,
  "stop_delay_seconds": 60
}
```
Then restart service: `sudo systemctl restart av-monitor.service`

### Option 2 Configuration
Edit `capture_monitor.py` directly:
```python
class Config:
    CAPTURE_DIR = Path.home() / "captures"
    IR_PRESENCE_TEMP_MIN = 28.0
    STOP_DELAY_SECONDS = 60
```
No restart needed (if running manually).

---

## Common Deployment Scenarios

### Scenario 1: Home Security Camera
**Setup:**
- Place Pi near entry door
- Aim IR sensor at door
- Set threshold to 29°C (reduce false triggers)
- Set stop delay to 120s (longer capture)

**Configuration (`/etc/av_monitor/config.json`):**
```json
{
  "temperature_threshold": 29.0,
  "stop_delay_seconds": 120,
  "video_resolution": "1920x1080"
}
```

### Scenario 2: Meeting Room Auto-Capture
**Setup:**
- Mount Pi on wall facing conference table
- IR sensor detects when people sit down
- Lower threshold for seated people (farther away)
- Longer stop delay for breaks

**Configuration:**
```json
{
  "temperature_threshold": 26.0,
  "presence_pixels_required": 5,
  "stop_delay_seconds": 300,
  "video_resolution": "1920x1080",
  "audio_channels": 1
}
```

### Scenario 3: Wildlife Observation
**Setup:**
- Outdoor weatherproof enclosure
- IR detects warm-blooded animals
- Lower threshold for animals
- Shorter stop delay to save storage

**Configuration:**
```json
{
  "temperature_threshold": 25.0,
  "presence_pixels_required": 2,
  "stop_delay_seconds": 30,
  "video_resolution": "1280x720",
  "video_framerate": 30
}
```

### Scenario 4: Low-Storage Mode
**Setup:**
- Limited SD card space
- Lower resolution and framerate
- Shorter recordings

**Configuration:**
```json
{
  "video_resolution": "1280x720",
  "video_framerate": 24,
  "stop_delay_seconds": 45,
  "video_codec": "h264"
}
```

---

## Post-Deployment Checklist

- [ ] **Day 1**: Monitor logs for any crashes
- [ ] **Day 1**: Check recording quality (video/audio sync)
- [ ] **Day 3**: Verify IR threshold is not too sensitive
- [ ] **Week 1**: Check disk space usage: `df -h`
- [ ] **Week 1**: Set up recording retrieval workflow
- [ ] **Month 1**: Consider log rotation: `/etc/logrotate.d/av-monitor`
- [ ] **Month 1**: Backup important recordings off-device

---

## Service Management Commands

```bash
# Start service
sudo systemctl start av-monitor.service

# Stop service
sudo systemctl stop av-monitor.service

# Restart service (after config changes)
sudo systemctl restart av-monitor.service

# Enable auto-start on boot
sudo systemctl enable av-monitor.service

# Disable auto-start
sudo systemctl disable av-monitor.service

# View status
sudo systemctl status av-monitor.service

# View recent logs
sudo journalctl -u av-monitor.service -n 100

# View logs in real-time
sudo journalctl -u av-monitor.service -f

# View logs from specific time
sudo journalctl -u av-monitor.service --since "2025-11-07 14:00"
```

---

## Retrieving Recordings

### Local Access
```bash
ls -lh ~/captures/
```

### Remote Access via SCP
```bash
# From another computer
scp pi@<raspberry-pi-ip>:~/captures/*.mp4 ./recordings/
```

### Remote Access via Rsync
```bash
# Sync all recordings
rsync -avz --progress pi@<raspberry-pi-ip>:~/captures/ ./recordings/

# Delete source files after successful transfer
rsync -avz --progress --remove-source-files pi@<raspberry-pi-ip>:~/captures/ ./recordings/
```

### Automated Retrieval Script
Create on your computer:

```bash
#!/bin/bash
# retrieve_recordings.sh

PI_IP="192.168.1.100"  # Change to your Pi's IP
LOCAL_DIR="./recordings"

mkdir -p "$LOCAL_DIR"
rsync -avz --progress pi@$PI_IP:~/captures/ "$LOCAL_DIR/"

echo "Retrieved $(ls -1 $LOCAL_DIR/*.mp4 2>/dev/null | wc -l) recordings"
```

Run daily via cron:
```bash
# Edit crontab
crontab -e

# Add line (runs at 2 AM daily)
0 2 * * * /home/user/retrieve_recordings.sh
```

---

## Monitoring Disk Space

### Check Available Space
```bash
df -h /home
```

### Check Capture Directory Size
```bash
du -sh ~/captures/
du -h ~/captures/ | sort -h
```

### Automatic Cleanup Script
Create `~/cleanup_old_recordings.sh`:

```bash
#!/bin/bash
# Delete recordings older than 30 days

CAPTURE_DIR="$HOME/captures"
DAYS_TO_KEEP=30

find "$CAPTURE_DIR" -name "rec_*.mp4" -type f -mtime +$DAYS_TO_KEEP -delete

echo "Cleaned recordings older than $DAYS_TO_KEEP days"
```

Schedule via cron:
```bash
crontab -e

# Add line (runs daily at 3 AM)
0 3 * * * /home/pi/cleanup_old_recordings.sh
```

---

## Performance Optimization

### For Lower CPU Usage
```json
{
  "video_resolution": "1280x720",
  "video_framerate": 24,
  "video_codec": "h264"
}
```

### For Better Quality (More CPU)
```json
{
  "video_resolution": "1920x1080",
  "video_framerate": 60,
  "video_codec": "h264"
}
```

### For 4K (High CPU, Large Files)
```json
{
  "video_resolution": "3840x2160",
  "video_framerate": 30,
  "video_codec": "h265"
}
```

**Note**: H.265 has better compression but higher CPU usage than H.264.

---

## Security Considerations

### SSH Access
```bash
# Change default password
passwd

# Optional: Set up SSH key authentication
ssh-keygen -t ed25519
ssh-copy-id pi@<raspberry-pi-ip>
```

### File Permissions
```bash
# Ensure only pi user can access recordings
chmod 700 ~/captures/
```

### Network Isolation
- Consider placing Pi on isolated VLAN
- Use VPN for remote access instead of exposing SSH
- Disable unused services: `sudo systemctl disable <service>`

### Encrypt Recordings (Optional)
```bash
# Install encryption tools
sudo apt install ecryptfs-utils

# Set up encrypted directory
# (Advanced - see eCryptfs documentation)
```

---

## Troubleshooting Common Issues

### Service Won't Start
```bash
# Check logs
sudo journalctl -u av-monitor.service -n 50

# Test manually
python3 ~/Monitor/av_monitor.py

# Check permissions
ls -la /etc/av_monitor/config.json
ls -la ~/captures/
```

### No Audio in Recordings
```bash
# Test audio device
arecord -D plughw:1,0 -d 5 test.wav
aplay test.wav

# Adjust mic gain
alsamixer
# Select WM8960 (F6), adjust "Mic PGA"
```

### False Triggers
```bash
# Increase threshold and pixel count
sudo nano /etc/av_monitor/config.json
```
Change:
```json
{
  "temperature_threshold": 30.0,
  "presence_pixels_required": 5
}
```
```bash
sudo systemctl restart av-monitor.service
```

### Recordings Stop Too Soon
```bash
# Increase stop delay
sudo nano /etc/av_monitor/config.json
```
Change:
```json
{
  "stop_delay_seconds": 120
}
```

### High CPU Usage
Monitor with:
```bash
top
htop  # Install with: sudo apt install htop
```

Lower resolution or framerate in config.

### Disk Full
```bash
# Check space
df -h

# Find large files
du -h ~/captures/ | sort -h | tail -20

# Clean old recordings
rm ~/captures/rec_202511*.mp4
```

---

## Advanced Features

### Web Interface (Future Enhancement)
Consider adding Flask/FastAPI server for:
- Remote viewing of status
- Configuration changes via web UI
- Download recordings via browser

### Cloud Upload (Future Enhancement)
Add automatic upload to:
- AWS S3
- Google Drive
- Dropbox
- Custom SFTP server

### Multi-Camera Support
Run multiple instances:
```bash
# Copy service file
sudo cp /etc/systemd/system/av-monitor.service /etc/systemd/system/av-monitor-cam2.service

# Edit new service to use different config file
sudo nano /etc/systemd/system/av-monitor-cam2.service
```

---

## Support

- **Full Documentation**: [README.md](README.md)
- **Quick Setup**: [QUICKSTART.md](QUICKSTART.md)  
- **Hardware Validation**: Run `./validate.sh`
- **Component Tests**: Run `python3 test_components.py`
- **Project Overview**: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)

---

**Last Updated**: November 2025  
**Deployment Target**: Raspberry Pi 5, Bookworm 64-bit

