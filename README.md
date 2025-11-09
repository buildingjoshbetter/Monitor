# Raspberry Pi 5 A/V Monitor with IR Trigger

A self-contained presence-detection recording system that automatically captures synchronized audio and video when a human is detected via IR thermal sensing.

## Overview

This system monitors an AMG8833 IR thermal sensor for human presence and automatically:
- **Starts recording** audio+video when presence is detected
- **Continues recording** as long as presence remains
- **Stops recording** 60 seconds after person leaves frame
- **Saves** timestamped MP4 files to local storage

## Hardware Requirements

### Required Components

1. **Raspberry Pi 5**
   - Running Raspberry Pi OS Bookworm (64-bit)
   - Minimum 32GB microSD card (fast Class 10/UHS-I recommended)
   - 5V/3A USB-C power supply

2. **Camera: Arducam 12MP IMX708** (or Raspberry Pi Camera Module 3)
   - Same sensor class as official Pi Camera Module 3
   - Must use **22-pin → 15-pin CAMERA ribbon cable** for Pi 5
   - Must connect to **CAMERA port** (not DISP/display port)

3. **Audio: Waveshare WM8960 Audio HAT**
   - I²S audio codec with built-in MEMS microphones
   - Attaches directly to GPIO header
   - Provides ALSA capture device

4. **IR Sensor: Panasonic AMG8833** (Grid-EYE)
   - 8×8 thermal array for presence detection
   - I²C interface (address 0x69)
   - Used only as trigger (not for imaging)

### Hardware Connections

#### Camera
```
IMX708 Camera → Pi 5 CAMERA port
(via 22-pin → 15-pin ribbon cable)
```

#### Audio
```
WM8960 HAT → Pi 5 GPIO header (40-pin)
```

#### IR Sensor (AMG8833)
```
VCC → Pin 1  (3.3V)
GND → Pin 6  (Ground)
SDA → Pin 3  (GPIO2 / I2C SDA)
SCL → Pin 5  (GPIO3 / I2C SCL)
```

## Software Stack

### Camera System
- **libcamera** backend (modern camera stack)
- **rpicam-apps** tooling (`rpicam-vid`, `rpicam-hello`)
- ❌ **DO NOT USE**: `raspivid`, `raspistill`, Picamera v1 (deprecated)

### Audio System
- **ALSA** capture from WM8960 HAT
- Built-in MEMS microphones only
- No external mic support

### Video Output
- **Format**: MP4 container
- **Video codec**: H.264 or HEVC
- **Audio codec**: AAC
- **Resolution**: 1080p30 (default) or 4K optional
- **Duration**: Variable (trigger-based)

## Installation

### Quick Install

1. **Clone this repository** on your Raspberry Pi:
   ```bash
   git clone <repository-url>
   cd Monitor
   ```

2. **Run the installation script**:
   ```bash
   chmod +x install.sh validate.sh
   sudo ./install.sh
   ```

3. **Reboot** to activate all drivers:
   ```bash
   sudo reboot
   ```

4. **Validate hardware** after reboot:
   ```bash
   ./validate.sh
   ```

5. **Start the service**:
   ```bash
   sudo systemctl start av-monitor.service
   ```

### Manual Installation

If you prefer manual setup:

#### 1. Enable I2C Interface
```bash
sudo raspi-config nonint do_i2c 0
```

Or manually edit `/boot/firmware/config.txt`:
```
dtparam=i2c_arm=on
```

#### 2. Enable Camera
```bash
sudo raspi-config nonint do_camera 0
```

Or ensure `/boot/firmware/config.txt` contains:
```
camera_auto_detect=1
```

#### 3. Install WM8960 Driver
```bash
git clone https://github.com/waveshare/WM8960-Audio-HAT
cd WM8960-Audio-HAT
sudo ./install.sh
cd ..
```

#### 4. Install Python Dependencies
```bash
sudo apt-get update
sudo apt-get install python3-pip i2c-tools alsa-utils
pip3 install --break-system-packages -r requirements.txt
```

#### 5. Configure System
```bash
sudo mkdir -p /etc/av_monitor
sudo cp config.json /etc/av_monitor/
mkdir -p ~/captures
```

#### 6. Install Systemd Service
```bash
sudo cp av-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable av-monitor.service
```

## Configuration

Edit `/etc/av_monitor/config.json`:

```json
{
  "capture_dir": "/home/pi/captures",
  "temperature_threshold": 28.0,
  "presence_pixels_required": 3,
  "stop_delay_seconds": 60,
  "poll_interval_seconds": 0.5,
  "video_resolution": "1920x1080",
  "video_framerate": 30,
  "audio_samplerate": 48000,
  "audio_channels": 1,
  "video_codec": "h264",
  "audio_device": "plughw:1,0"
}
```

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `capture_dir` | Directory for recorded files | `~/captures` |
| `temperature_threshold` | Temperature (°C) for detection | `28.0` |
| `presence_pixels_required` | Min hot pixels for detection | `3` |
| `stop_delay_seconds` | Delay before stopping recording | `60` |
| `poll_interval_seconds` | IR sensor polling rate | `0.5` |
| `video_resolution` | Video resolution | `1920x1080` |
| `video_framerate` | Frames per second | `30` |
| `audio_samplerate` | Audio sample rate (Hz) | `48000` |
| `audio_channels` | Mono (1) or Stereo (2) | `1` |
| `video_codec` | `h264` or `h265` | `h264` |
| `audio_device` | ALSA device string | `plughw:1,0` |

## Usage

### Service Management

**Start service:**
```bash
sudo systemctl start av-monitor.service
```

**Stop service:**
```bash
sudo systemctl stop av-monitor.service
```

**Check status:**
```bash
sudo systemctl status av-monitor.service
```

**Enable auto-start on boot:**
```bash
sudo systemctl enable av-monitor.service
```

**Disable auto-start:**
```bash
sudo systemctl disable av-monitor.service
```

### View Logs

**Systemd journal:**
```bash
sudo journalctl -u av-monitor.service -f
```

**Log file:**
```bash
tail -f /var/log/av_monitor.log
```

### Manual Testing

Run the application directly (useful for debugging):
```bash
python3 ~/Monitor/av_monitor.py
```

Stop with `Ctrl+C`.

### Retrieve Recordings

Recordings are saved to the configured `capture_dir` (default: `~/captures`).

**List recordings:**
```bash
ls -lh ~/captures/
```

**Copy to another computer via SCP:**
```bash
scp pi@<raspberry-pi-ip>:~/captures/*.mp4 ./
```

**Or use rsync:**
```bash
rsync -avz pi@<raspberry-pi-ip>:~/captures/ ./recordings/
```

## Validation Tests

### Hardware Validation Script

Run `validate.sh` to check all hardware:
```bash
./validate.sh
```

This checks:
- ✓ I2C interface enabled
- ✓ AMG8833 sensor detected at 0x69
- ✓ Camera device available
- ✓ rpicam-vid working
- ✓ WM8960 audio device detected
- ✓ Python dependencies installed

### Manual Hardware Tests

#### Test I2C and AMG8833
```bash
i2cdetect -y 1
# Should show "69" in the grid
```

#### Test Camera
```bash
rpicam-hello -t 3000
# Should show camera preview for 3 seconds
```

#### Test Audio Device
```bash
arecord -l
# Should list wm8960-soundcard

arecord -D plughw:1,0 -d 5 -f cd test.wav
# Records 5 seconds of audio
```

#### Test A/V Recording
```bash
rpicam-vid -t 10000 --width 1920 --height 1080 \
  --codec h264 --audio --audio-device plughw:1,0 \
  -o test.mp4
# Records 10 seconds of video+audio
```

### Adjust Microphone Gain

If audio is too quiet or distorted:
```bash
alsamixer
```

- Select the WM8960 sound card (F6)
- Adjust **"Mic PGA"** (input gain)
- Recommended: 10-20 (moderate gain)
- Avoid: >30 (excessive noise)

Press `Esc` to exit.

## System Behavior

### State Machine

```
┌─────────────┐
│    IDLE     │ ◄─────────────────┐
└──────┬──────┘                   │
       │                          │
       │ Presence Detected        │
       │                          │
       ▼                          │
┌─────────────┐                   │
│  RECORDING  │                   │
└──────┬──────┘                   │
       │                          │
       │ Presence Lost            │
       │                          │
       ▼                          │
┌─────────────┐                   │
│  WAITING    │                   │
│  (60 sec)   │                   │
└──────┬──────┘                   │
       │                          │
       │ Still Absent             │
       │                          │
       └──────────────────────────┘
       
       (If presence returns during
        WAITING, returns to RECORDING)
```

### Recording Behavior

1. **IDLE**: System monitors IR sensor continuously
2. **Presence Detected**: Immediately starts `rpicam-vid` recording
3. **Recording**: Continues as long as presence remains
4. **Presence Lost**: Starts 60-second countdown
5. **Countdown**: If presence returns, cancels countdown and continues recording
6. **Stop**: After 60 seconds of absence, stops recording gracefully
7. **Save**: MP4 file saved with timestamp (e.g., `rec_20251107_143022.mp4`)
8. **Return to IDLE**: Ready for next trigger

### Filename Format

```
rec_YYYYMMDD_HHMMSS.mp4

Examples:
rec_20251107_143022.mp4  → 2025-11-07 at 14:30:22
rec_20251108_091545.mp4  → 2025-11-08 at 09:15:45
```

## Troubleshooting

### Camera Not Detected

**Problem**: `rpicam-hello` fails or shows no camera

**Solutions**:
1. Verify ribbon cable is in **CAMERA port** (not DISP)
2. Check cable orientation (blue side toward board)
3. Enable camera: `sudo raspi-config` → Interface Options → Camera
4. Ensure `/boot/firmware/config.txt` has `camera_auto_detect=1`
5. Reboot after changes
6. Try: `vcgencmd get_camera` (should show `detected=1`)

### Audio Device Not Found

**Problem**: `arecord -l` doesn't show wm8960

**Solutions**:
1. Verify WM8960 HAT is properly seated on GPIO header
2. Re-run WM8960 installer:
   ```bash
   git clone https://github.com/waveshare/WM8960-Audio-HAT
   cd WM8960-Audio-HAT
   sudo ./install.sh
   sudo reboot
   ```
3. Check `/boot/firmware/config.txt` for WM8960 dtoverlay

### IR Sensor Not Detected

**Problem**: `i2cdetect -y 1` doesn't show 0x69

**Solutions**:
1. Enable I2C: `sudo raspi-config` → Interface Options → I2C
2. Check wiring:
   - VCC → 3.3V (Pin 1)
   - GND → Ground (Pin 6)
   - SDA → GPIO2 (Pin 3)
   - SCL → GPIO3 (Pin 5)
3. Verify AMG8833 has power (some boards have power LED)
4. Try alternate I2C address if jumper modified (default: 0x69)

### Recording Starts But No Audio

**Problem**: MP4 file created but silent

**Solutions**:
1. Test audio separately:
   ```bash
   arecord -D plughw:1,0 -d 5 -f cd test.wav
   aplay test.wav
   ```
2. Check audio device in config.json matches `arecord -l` output
3. Adjust mic gain: `alsamixer` → "Mic PGA"
4. Verify WM8960 driver loaded: `lsmod | grep snd`

### Service Won't Start

**Problem**: `systemctl status av-monitor.service` shows failed

**Solutions**:
1. Check logs: `journalctl -u av-monitor.service -n 50`
2. Test manually: `python3 ~/Monitor/av_monitor.py`
3. Verify permissions: user must be in `video`, `audio`, `i2c` groups
4. Check Python dependencies: `pip3 list | grep adafruit`

### False Triggers / No Triggers

**Problem**: Recording starts randomly or never starts

**Solutions**:
1. Adjust `temperature_threshold` in config.json (try 26-30°C)
2. Adjust `presence_pixels_required` (try 2-5)
3. Test IR sensor manually:
   ```python
   import board, busio, adafruit_amg88xx
   i2c = busio.I2C(board.SCL, board.SDA)
   sensor = adafruit_amg88xx.AMG88XX(i2c)
   print(sensor.pixels)  # View 8x8 thermal array
   ```
4. Keep AMG8833 away from hot components (CPU, voltage regulators)
5. Ensure sensor has clear line-of-sight to detection area

### High CPU Usage / Dropped Frames

**Problem**: Pi runs hot or video is choppy

**Solutions**:
1. Lower resolution: `1280x720` instead of `1920x1080`
2. Use H.264 instead of H.265 (less CPU intensive)
3. Add heatsink/fan to Raspberry Pi 5
4. Use faster microSD card (UHS-I/UHS-II)
5. Reduce framerate to 24 or 25fps

## Performance Notes

### Expected Specifications

- **Video quality**: 1080p30 or 720p60
- **Audio quality**: 48kHz mono (raw, no DSP)
- **Detection latency**: <1 second
- **Recording start time**: ~2 seconds
- **File size**: ~1-2 GB per hour (1080p, H.264)
- **CPU usage**: 40-60% during recording
- **Power consumption**: ~3-4W typical

### Limitations

- **Audio**: WM8960 built-in mics capture room audio but lack smartphone-level DSP
- **IR resolution**: 8×8 grid is very coarse; suitable for presence only, not tracking
- **No real-time processing**: This is a data capture system, not an inference system
- **Local storage only**: No automatic cloud upload (add separately if needed)

## Future Enhancements

Potential additions (not currently implemented):

- Cloud upload (S3, Google Drive, Dropbox)
- Day/night IR camera (NoIR module)
- Advanced presence logic (tracking, dwell time)
- Visual motion detection (OpenCV)
- Multi-channel audio (stereo/array)
- Real-time ML inference (person detection, face recognition)
- Web interface for configuration/viewing
- MQTT integration for IoT systems

## System Requirements

- **OS**: Raspberry Pi OS Bookworm (64-bit)
- **Python**: 3.11+ (included in Bookworm)
- **Disk space**: 
  - System: ~8GB
  - Recordings: 1-2GB per hour
  - Recommended: 32GB+ microSD
- **Memory**: 4GB+ recommended (8GB for 4K)
- **Network**: Optional (for remote retrieval)

## File Structure

```
Monitor/
├── av_monitor.py          # Main application
├── config.json            # Configuration template
├── requirements.txt       # Python dependencies
├── av-monitor.service     # Systemd service file
├── install.sh             # Installation script
├── validate.sh            # Hardware validation script
└── README.md              # This file

After installation:
├── /etc/av_monitor/
│   └── config.json        # Active configuration
├── /home/pi/captures/     # Recorded files
└── /var/log/av_monitor.log # Application log
```

## License

MIT License - See LICENSE file for details

## Support

For issues specific to hardware:
- **WM8960 HAT**: [Waveshare Wiki](https://www.waveshare.com/wiki/WM8960_Audio_HAT)
- **IMX708 Camera**: [Arducam Documentation](https://docs.arducam.com/)
- **AMG8833**: [Adafruit Guide](https://learn.adafruit.com/adafruit-amg8833-8x8-thermal-camera-sensor)
- **rpicam-apps**: [Official Documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)

## Credits

- Built for Raspberry Pi 5 with Bookworm OS
- Uses Adafruit CircuitPython libraries
- rpicam-apps from Raspberry Pi Foundation
- WM8960 driver from Waveshare

---

**Project Status**: Ready for deployment  
**Last Updated**: November 2025  
**Tested On**: Raspberry Pi 5, Bookworm 64-bit

