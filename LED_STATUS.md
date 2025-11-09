# Status LED Indicators

Visual feedback system for the AV Monitoring System.

---

## 🔌 Hardware Setup

### LED Connections

| LED Color | GPIO Pin | State | Meaning |
|-----------|----------|-------|---------|
| 🟠 Orange | GPIO 6 | Monitoring | System is running and searching for presence |
| 🔴 Red | GPIO 26 | Recording | Camera and microphone are actively recording |

### Wiring Diagram

```
Raspberry Pi GPIO
├─ GPIO 6  ──[220Ω]──┤>├── GND  (Orange LED)
└─ GPIO 26 ──[220Ω]──┤>├── GND  (Red LED)
```

**Note:** Use 220-330Ω current-limiting resistors to protect the LEDs.

---

## 🚦 LED States

### 🟠 **Orange LED ON, Red LED OFF**
**State:** `IDLE` (Monitoring)
- System is running normally
- IR sensor is actively monitoring for presence
- No recording in progress
- Waiting for someone to enter the frame

### 🔴 **Red LED ON, Orange LED OFF**
**State:** `RECORDING` or `WAITING_TO_STOP`
- Camera and microphone are recording
- Either:
  * Person detected and recording ongoing, OR
  * Person left frame, 60-second countdown active

### ⚫ **Both LEDs OFF**
**State:** System offline
- Service not running
- System shutdown
- Power loss

---

## 📊 State Transitions

```
┌──────────────┐
│  POWER ON    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  🟠 ORANGE   │ ◄─────────────┐
│   (Idle)     │                │
└──────┬───────┘                │
       │                        │
   Presence                     │
   Detected                     │
       │                        │
       ▼                        │
┌──────────────┐                │
│   🔴 RED     │                │
│ (Recording)  │                │
└──────┬───────┘                │
       │                        │
   Presence                     │
    Lost                        │
       │                        │
       ▼                        │
┌──────────────┐                │
│   🔴 RED     │                │
│  (Waiting)   │                │
│  60 seconds  │                │
└──────┬───────┘                │
       │                        │
       │    Timeout             │
       └────────────────────────┘
```

---

## 🛠️ Troubleshooting

### LEDs Not Working

```bash
# Check if gpiozero is installed
python3 -c "import gpiozero; print('OK')"

# Verify GPIO pins are not in use
cat /sys/kernel/debug/gpio

# Test LEDs manually
python3 << EOF
from gpiozero import LED
from time import sleep

orange = LED(6)
red = LED(26)

print("Testing Orange LED...")
orange.on()
sleep(2)
orange.off()

print("Testing Red LED...")
red.on()
sleep(2)
red.off()

print("Test complete")
EOF
```

### LED Always On

- Check for stuck process: `ps aux | grep av_monitor`
- Restart service: `sudo systemctl restart av-monitor.service`
- Manual cleanup: `sudo pkill -f av_monitor.py`

### Wrong LED Behavior

Check the logs to see state transitions:
```bash
sudo journalctl -u av-monitor.service -f | grep "LED"
```

---

## ⚙️ Configuration

The LED GPIO pins are hardcoded in the `StatusLEDs` class:

```python
class StatusLEDs:
    def __init__(self, orange_pin: int = 6, red_pin: int = 26):
        ...
```

To change pins, edit `av_monitor.py` and modify the `StatusLEDs.__init__()` method.

---

## 🎯 Design Rationale

**Why Orange for Idle?**
- Warm, non-alarming color
- Indicates "system is awake and watching"
- Low-key presence

**Why Red for Recording?**
- Universal "recording" indicator
- High visibility
- Clear distinction from idle state

**Why keep Red on during wait period?**
- Recording hasn't actually stopped yet
- 60-second countdown is still part of the recording session
- Switching back to orange could be confusing

---

## 📝 Future Enhancements

Possible LED improvements:

- **Blinking during wait period:** Red LED blinks to show countdown
- **Dual-color LED:** Single RGB LED instead of two separate LEDs
- **Brightness control:** PWM for dimming at night
- **Error indication:** Rapid blinking for errors
- **Network status:** Additional LED for NAS connectivity

---

## 🔐 Safety Notes

- Always use current-limiting resistors (220-330Ω)
- LEDs draw minimal power (~20mA max)
- GPIO pins are 3.3V tolerant
- No risk to Pi hardware with proper resistors

---

**Status:** Implemented in v1.0
**Last Updated:** 2025-11-09

