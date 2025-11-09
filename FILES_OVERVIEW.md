# Project Files Overview

## Complete File Listing

```
/Users/j/Monitor/
├── Core Application Files
│   ├── av_monitor.py              ⭐ Main application (recommended)
│   ├── capture_monitor.py         Simple self-contained version
│   └── config.json                Configuration template
│
├── Installation & Setup
│   ├── install.sh                 ⭐ Automated installation script
│   ├── validate.sh                ⭐ Hardware validation script
│   └── test_components.py         Individual component testing
│
├── System Integration
│   ├── av-monitor.service         Systemd service definition
│   └── requirements.txt           Python dependencies
│
├── Documentation
│   ├── README.md                  ⭐ Complete documentation (START HERE)
│   ├── QUICKSTART.md              5-minute setup guide
│   ├── PROJECT_OVERVIEW.md        Architecture and design
│   ├── DEPLOYMENT_GUIDE.md        Deployment scenarios
│   └── FILES_OVERVIEW.md          This file
│
└── Project Management
    ├── LICENSE                    MIT License
    ├── .gitignore                 Git ignore patterns
    └── .git/                      Git repository

⭐ = Essential files for deployment
```

---

## File Descriptions

### `av_monitor.py` (13 KB) ⭐
**Main application - Full-featured version**

- Complete state machine for presence detection
- JSON configuration support
- Detailed logging
- Signal handling for graceful shutdown
- Production-ready

**Key Classes:**
- `Config` - Loads settings from `/etc/av_monitor/config.json`
- `IRSensor` - AMG8833 interface
- `AVRecorder` - rpicam-vid controller
- `MonitorSystem` - Main coordinator

**When to use:** Production deployment, systemd service

---

### `capture_monitor.py` (15 KB)
**Simple self-contained version**

- All configuration in Python code
- Same functionality as av_monitor.py
- Easier to understand for learning
- No external config file needed

**Key Classes:**
- `Config` - Settings embedded in code
- `IRSensor` - AMG8833 interface
- `AVRecorder` - rpicam-vid controller
- `CaptureMonitor` - Main coordinator

**When to use:** Testing, learning, prototyping

---

### `config.json` (337 B) ⭐
**Configuration template**

Default settings for all adjustable parameters:
- Detection thresholds
- Recording settings
- Video/audio quality
- File paths

**Deployed to:** `/etc/av_monitor/config.json` by install.sh

---

### `install.sh` (5.7 KB) ⭐
**Automated installation script**

Performs:
1. System package updates
2. I2C interface enable
3. Camera enable
4. WM8960 driver installation
5. Python dependency installation
6. Directory creation
7. Systemd service setup

**Usage:** `sudo ./install.sh`

---

### `validate.sh` (5.3 KB) ⭐
**Hardware validation script**

Checks:
- ✓ I2C interface enabled
- ✓ AMG8833 detected at 0x69
- ✓ Camera working (rpicam-hello test)
- ✓ rpicam-vid available
- ✓ WM8960 audio device present
- ✓ Python dependencies installed

**Usage:** `./validate.sh`

---

### `test_components.py` (9.3 KB)
**Individual component testing**

Tests each component separately:
1. Python library imports
2. IR sensor (reads thermal grid)
3. Camera (rpicam-hello test)
4. Audio (2-second recording)
5. A/V combined (5-second test recording)

**Usage:** `python3 test_components.py`

---

### `av-monitor.service` (514 B)
**Systemd service definition**

Configures:
- Service name and description
- User/group (pi/pi)
- Working directory
- Restart behavior
- Logging

**Deployed to:** `/etc/systemd/system/av-monitor.service`

---

### `requirements.txt` (348 B)
**Python dependencies**

Lists required packages:
- `adafruit-circuitpython-amg88xx` - IR sensor library
- `adafruit-blinka` - CircuitPython compatibility layer

**Install with:** `pip3 install -r requirements.txt`

---

### `README.md` (14 KB) ⭐
**Complete project documentation**

Comprehensive guide covering:
- Hardware requirements
- Hardware connections
- Software stack
- Installation (quick & manual)
- Configuration options
- Usage instructions
- Validation tests
- Troubleshooting
- Performance notes

**Read this first!**

---

### `QUICKSTART.md` (2.0 KB)
**5-minute setup guide**

Condensed installation and testing procedure:
1. One-command installation
2. Quick validation
3. Start system
4. Test recording
5. Retrieve files

For users who want to get running quickly.

---

### `PROJECT_OVERVIEW.md` (12 KB)
**Architecture and design documentation**

Deep dive into:
- System architecture diagram
- Component descriptions
- State machine flow
- Data flow sequences
- Design decisions
- Performance characteristics
- Extension points

For understanding how the system works.

---

### `DEPLOYMENT_GUIDE.md` (9.7 KB)
**Deployment scenarios and operations**

Covers:
- Two implementation options (comparison)
- Common deployment scenarios
- Service management commands
- Recording retrieval methods
- Disk space monitoring
- Performance optimization
- Security considerations
- Advanced features

For production deployments.

---

### `LICENSE` (1.0 KB)
**MIT License**

Open source license allowing free use, modification, and distribution.

---

### `.gitignore` (356 B)
**Git ignore patterns**

Excludes from version control:
- Python bytecode
- Virtual environments
- Log files
- Recorded MP4 files
- Local config overrides
- OS and IDE files

---

## Documentation Reading Order

### For Quick Deployment
1. **README.md** (skim hardware section)
2. **QUICKSTART.md** (follow steps)
3. **DEPLOYMENT_GUIDE.md** (post-deployment)

### For Understanding the System
1. **README.md** (full read)
2. **PROJECT_OVERVIEW.md** (architecture)
3. **Browse source code** (av_monitor.py)

### For Troubleshooting
1. **README.md** (troubleshooting section)
2. **Run validate.sh** (check hardware)
3. **Run test_components.py** (isolate issues)
4. **DEPLOYMENT_GUIDE.md** (common issues)

---

## Directory Structure After Installation

```
Raspberry Pi Filesystem:

/home/pi/
├── Monitor/                      # Application directory
│   ├── av_monitor.py
│   ├── capture_monitor.py
│   └── ...
│
├── captures/                     # Recorded files
│   ├── rec_20251107_143022.mp4
│   ├── rec_20251107_145831.mp4
│   └── ...
│
└── capture_monitor.log           # Legacy log (if using capture_monitor.py)

/etc/
└── av_monitor/
    └── config.json               # Active configuration

/var/log/
└── av_monitor.log                # Application logs (av_monitor.py)

/etc/systemd/system/
└── av-monitor.service            # Service definition
```

---

## Configuration File Locations

### Development/Testing
- Template: `/Users/j/Monitor/config.json`
- Used by: Manual runs

### Production (after installation)
- Active config: `/etc/av_monitor/config.json`
- Used by: Systemd service

**To modify production config:**
```bash
sudo nano /etc/av_monitor/config.json
sudo systemctl restart av-monitor.service
```

---

## Log File Locations

### av_monitor.py (recommended)
- File: `/var/log/av_monitor.log`
- Journal: `journalctl -u av-monitor.service`

### capture_monitor.py (simple)
- File: `~/capture_monitor.log`
- Stdout: Terminal output

---

## Which Files to Transfer to Raspberry Pi

### Minimum (for manual operation)
- `av_monitor.py` or `capture_monitor.py`
- `requirements.txt`

### Recommended (for production)
- **All files** (entire Monitor directory)

Use git clone or scp:

```bash
# Option 1: Git clone (if hosted)
ssh pi@<raspberry-pi-ip>
git clone <repository-url> Monitor

# Option 2: SCP transfer
scp -r /Users/j/Monitor pi@<raspberry-pi-ip>:~/
```

---

## File Size Summary

| File | Size | Type |
|------|------|------|
| av_monitor.py | 13 KB | Python |
| capture_monitor.py | 15 KB | Python |
| test_components.py | 9.3 KB | Python |
| install.sh | 5.7 KB | Shell |
| validate.sh | 5.3 KB | Shell |
| README.md | 14 KB | Markdown |
| PROJECT_OVERVIEW.md | 12 KB | Markdown |
| DEPLOYMENT_GUIDE.md | 9.7 KB | Markdown |
| QUICKSTART.md | 2.0 KB | Markdown |
| LICENSE | 1.0 KB | Text |
| config.json | 337 B | JSON |
| requirements.txt | 348 B | Text |
| av-monitor.service | 514 B | Systemd |
| .gitignore | 356 B | Text |
| **TOTAL** | **~88 KB** | |

Very lightweight project!

---

## Quick Command Reference

```bash
# Installation
sudo ./install.sh
sudo reboot

# Validation
./validate.sh
python3 test_components.py

# Service Control
sudo systemctl start av-monitor.service
sudo systemctl stop av-monitor.service
sudo systemctl status av-monitor.service

# Logs
tail -f /var/log/av_monitor.log
sudo journalctl -u av-monitor.service -f

# Configuration
sudo nano /etc/av_monitor/config.json
sudo systemctl restart av-monitor.service

# Manual Testing
python3 ~/Monitor/av_monitor.py
python3 ~/Monitor/capture_monitor.py

# View Recordings
ls -lh ~/captures/
```

---

**Last Updated**: November 2025  
**Project Status**: Complete and ready for deployment

