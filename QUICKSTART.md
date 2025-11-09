# Quick Start Guide

Get your A/V monitoring system running in 5 minutes.

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS Bookworm (64-bit)
- All hardware connected (camera, audio HAT, IR sensor)
- Internet connection for installation

## Installation (One Command)

```bash
# Clone and install
git clone <repository-url> Monitor
cd Monitor
chmod +x install.sh validate.sh
sudo ./install.sh

# Reboot
sudo reboot
```

## Validation (After Reboot)

```bash
cd Monitor
./validate.sh
```

Expected output: All checks pass ✓

## Start System

```bash
sudo systemctl start av-monitor.service
sudo systemctl status av-monitor.service
```

## Monitor Activity

```bash
# Watch logs
sudo journalctl -u av-monitor.service -f

# Or
tail -f /var/log/av_monitor.log
```

## Test Recording

1. Wave your hand in front of the IR sensor
2. Check logs for "Presence detected! Starting recording..."
3. Remove hand and wait 60 seconds
4. Check for MP4 file: `ls -lh ~/captures/`

## Retrieve Recordings

```bash
# From another computer
scp pi@<raspberry-pi-ip>:~/captures/*.mp4 ./
```

## Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| Camera not found | Check CAMERA port connection, run `rpicam-hello -t 3000` |
| Audio not working | Run `alsamixer`, adjust "Mic PGA" gain |
| IR not detected | Run `i2cdetect -y 1`, should show `69` |
| Service won't start | Check logs: `journalctl -u av-monitor.service -n 50` |

## Configuration

Edit `/etc/av_monitor/config.json` and restart service:

```bash
sudo systemctl restart av-monitor.service
```

## Common Adjustments

**Too many false triggers:**
```json
{
  "temperature_threshold": 30.0,
  "presence_pixels_required": 5
}
```

**Recordings stop too soon:**
```json
{
  "stop_delay_seconds": 120
}
```

**Better video quality:**
```json
{
  "video_resolution": "3840x2160",
  "video_framerate": 30
}
```

## Next Steps

- Adjust microphone gain for your environment
- Tune IR threshold for your space
- Set up automatic recording retrieval
- Monitor disk space: `df -h`

See [README.md](README.md) for complete documentation.

