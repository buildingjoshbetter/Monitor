#!/usr/bin/env python3
"""
Raspberry Pi 5 A/V Capture Monitor with IR Trigger

This script monitors an AMG8833 IR thermal sensor for human presence and
automatically starts/stops synchronized audio+video recording using rpicam-vid.

Hardware Requirements:
- Raspberry Pi 5 (Bookworm 64-bit)
- Arducam IMX708 camera (via 22→15 pin ribbon to CAMERA port)
- Waveshare WM8960 Audio HAT (built-in MEMS mics)
- Panasonic AMG8833 IR sensor (I²C address 0x69)

Recording Behavior:
- Detects human presence → starts recording immediately
- Human leaves frame → waits 60 seconds → stops recording
- Outputs timestamped MP4 files with H.264 video + AAC audio
"""

import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from enum import Enum
import signal
import sys

try:
    import board
    import busio
    import adafruit_amg88xx
except ImportError as e:
    print("Error: Required libraries not installed.")
    print("Please run: pip3 install adafruit-circuitpython-amg88xx")
    sys.exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """System configuration parameters"""
    
    # Storage
    CAPTURE_DIR = Path.home() / "captures"
    
    # IR Sensor Thresholds
    IR_PRESENCE_TEMP_MIN = 28.0  # Celsius - minimum temp to consider human
    IR_PRESENCE_PIXEL_COUNT = 3   # Number of pixels above threshold to trigger
    IR_POLL_INTERVAL = 0.5        # Seconds between IR sensor reads
    
    # Recording Timing
    STOP_DELAY_SECONDS = 60       # Wait time after person leaves before stopping
    
    # Video Settings
    VIDEO_WIDTH = 1920
    VIDEO_HEIGHT = 1080
    VIDEO_FPS = 30
    VIDEO_CODEC = "h264"          # h264 or hevc
    
    # Audio Settings
    AUDIO_SAMPLE_RATE = 48000
    AUDIO_CHANNELS = 1            # mono
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = Path.home() / "capture_monitor.log"


# ============================================================================
# STATE MACHINE
# ============================================================================

class RecordingState(Enum):
    """Recording states"""
    IDLE = "idle"                 # Not recording, waiting for presence
    RECORDING = "recording"       # Actively recording
    COOLDOWN = "cooldown"        # Person left, counting down to stop


# ============================================================================
# IR SENSOR HANDLER
# ============================================================================

class IRSensor:
    """Handles AMG8833 IR thermal sensor operations"""
    
    def __init__(self):
        self.logger = logging.getLogger("IRSensor")
        self.sensor = None
        self._initialize()
    
    def _initialize(self):
        """Initialize I²C connection to AMG8833"""
        try:
            i2c_bus = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_amg88xx.AMG88XX(i2c_bus)
            self.logger.info("AMG8833 IR sensor initialized (address 0x69)")
        except Exception as e:
            self.logger.error(f"Failed to initialize AMG8833: {e}")
            self.logger.error("Check I²C connection and run: i2cdetect -y 1")
            raise
    
    def detect_presence(self) -> bool:
        """
        Detect human presence based on thermal signature.
        
        Returns:
            True if human-like heat signature detected, False otherwise
        """
        try:
            # Read 8x8 thermal array
            pixels = self.sensor.pixels
            
            # Count pixels above human body temperature threshold
            hot_pixel_count = 0
            max_temp = 0
            
            for row in pixels:
                for temp in row:
                    if temp > max_temp:
                        max_temp = temp
                    if temp >= Config.IR_PRESENCE_TEMP_MIN:
                        hot_pixel_count += 1
            
            presence = hot_pixel_count >= Config.IR_PRESENCE_PIXEL_COUNT
            
            if presence:
                self.logger.debug(
                    f"Presence detected: {hot_pixel_count} hot pixels, "
                    f"max temp: {max_temp:.1f}°C"
                )
            
            return presence
            
        except Exception as e:
            self.logger.error(f"Error reading IR sensor: {e}")
            return False


# ============================================================================
# VIDEO RECORDER
# ============================================================================

class AVRecorder:
    """Manages rpicam-vid recording process"""
    
    def __init__(self):
        self.logger = logging.getLogger("AVRecorder")
        self.process = None
        self.current_filename = None
    
    def start_recording(self) -> str:
        """
        Start A/V recording using rpicam-vid.
        
        Returns:
            Filename of the recording being created
        """
        if self.is_recording():
            self.logger.warning("Already recording, ignoring start request")
            return self.current_filename
        
        # Create capture directory if it doesn't exist
        Config.CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rec_{timestamp}.mp4"
        filepath = Config.CAPTURE_DIR / filename
        
        # Build rpicam-vid command
        # Using timeout 0 means record indefinitely until killed
        cmd = [
            "rpicam-vid",
            "-t", "0",  # No timeout, record until stopped
            "-o", str(filepath),
            "--width", str(Config.VIDEO_WIDTH),
            "--height", str(Config.VIDEO_HEIGHT),
            "--framerate", str(Config.VIDEO_FPS),
            "--codec", Config.VIDEO_CODEC,
            # Audio parameters
            "--audio",
            "--audio-codec", "aac",
            "--audio-samplerate", str(Config.AUDIO_SAMPLE_RATE),
            "--audio-channels", str(Config.AUDIO_CHANNELS),
            # Disable preview (headless operation)
            "-n",
        ]
        
        try:
            self.logger.info(f"Starting recording: {filename}")
            self.logger.debug(f"Command: {' '.join(cmd)}")
            
            # Start recording process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.current_filename = filename
            self.logger.info(f"Recording started: {filename}")
            
            return filename
            
        except FileNotFoundError:
            self.logger.error(
                "rpicam-vid not found. Ensure rpicam-apps is installed."
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            raise
    
    def stop_recording(self):
        """Stop current recording gracefully"""
        if not self.is_recording():
            self.logger.warning("Not recording, ignoring stop request")
            return
        
        try:
            self.logger.info(f"Stopping recording: {self.current_filename}")
            
            # Send SIGINT for graceful shutdown (allows rpicam-vid to finalize MP4)
            self.process.send_signal(signal.SIGINT)
            
            # Wait for process to complete (with timeout)
            try:
                stdout, stderr = self.process.communicate(timeout=10)
                
                if self.process.returncode == 0:
                    self.logger.info(
                        f"Recording stopped successfully: {self.current_filename}"
                    )
                else:
                    self.logger.warning(
                        f"Recording stopped with code {self.process.returncode}"
                    )
                    if stderr:
                        self.logger.debug(f"stderr: {stderr}")
                        
            except subprocess.TimeoutExpired:
                self.logger.warning("Recording process did not stop gracefully, forcing kill")
                self.process.kill()
                self.process.wait()
            
            # Get file size for confirmation
            filepath = Config.CAPTURE_DIR / self.current_filename
            if filepath.exists():
                size_mb = filepath.stat().st_size / (1024 * 1024)
                self.logger.info(
                    f"Saved: {self.current_filename} ({size_mb:.1f} MB)"
                )
            else:
                self.logger.error(f"Recording file not found: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}")
        finally:
            self.process = None
            self.current_filename = None
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.process is not None and self.process.poll() is None


# ============================================================================
# MAIN MONITOR
# ============================================================================

class CaptureMonitor:
    """Main monitoring and control logic"""
    
    def __init__(self):
        self.logger = logging.getLogger("CaptureMonitor")
        self.ir_sensor = IRSensor()
        self.recorder = AVRecorder()
        
        self.state = RecordingState.IDLE
        self.cooldown_start_time = None
        self.running = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def run(self):
        """Main monitoring loop"""
        self.logger.info("=== Capture Monitor Started ===")
        self.logger.info(f"Capture directory: {Config.CAPTURE_DIR}")
        self.logger.info(f"Video: {Config.VIDEO_WIDTH}x{Config.VIDEO_HEIGHT}@{Config.VIDEO_FPS}fps")
        self.logger.info(f"Audio: {Config.AUDIO_SAMPLE_RATE}Hz, {Config.AUDIO_CHANNELS}ch")
        self.logger.info(f"Stop delay: {Config.STOP_DELAY_SECONDS}s")
        self.logger.info("=" * 40)
        
        self.running = True
        
        try:
            while self.running:
                self._update()
                time.sleep(Config.IR_POLL_INTERVAL)
                
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self._cleanup()
    
    def _update(self):
        """Single iteration of the monitoring loop"""
        presence = self.ir_sensor.detect_presence()
        
        if self.state == RecordingState.IDLE:
            if presence:
                self.logger.info("Presence detected → Starting recording")
                self.recorder.start_recording()
                self.state = RecordingState.RECORDING
        
        elif self.state == RecordingState.RECORDING:
            if not presence:
                self.logger.info(
                    f"Presence lost → Cooldown started ({Config.STOP_DELAY_SECONDS}s)"
                )
                self.cooldown_start_time = time.time()
                self.state = RecordingState.COOLDOWN
        
        elif self.state == RecordingState.COOLDOWN:
            if presence:
                # Person returned, resume recording
                self.logger.info("Presence detected again → Resuming recording")
                self.state = RecordingState.RECORDING
                self.cooldown_start_time = None
            else:
                # Check if cooldown period has elapsed
                elapsed = time.time() - self.cooldown_start_time
                if elapsed >= Config.STOP_DELAY_SECONDS:
                    self.logger.info("Cooldown complete → Stopping recording")
                    self.recorder.stop_recording()
                    self.state = RecordingState.IDLE
                    self.cooldown_start_time = None
    
    def _cleanup(self):
        """Cleanup on shutdown"""
        self.logger.info("Cleaning up...")
        
        if self.recorder.is_recording():
            self.logger.info("Stopping active recording...")
            self.recorder.stop_recording()
        
        self.logger.info("=== Capture Monitor Stopped ===")


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging to file and console"""
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler (detailed)
    file_handler = logging.FileHandler(Config.LOG_FILE)
    file_handler.setLevel(Config.LOG_LEVEL)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler (simpler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(Config.LOG_LEVEL)
    console_handler.setFormatter(simple_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(Config.LOG_LEVEL)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    setup_logging()
    
    logger = logging.getLogger("Main")
    
    # Pre-flight checks
    logger.info("Running pre-flight checks...")
    
    # Check if capture directory is writable
    try:
        Config.CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        test_file = Config.CAPTURE_DIR / ".test"
        test_file.touch()
        test_file.unlink()
        logger.info(f"✓ Capture directory writable: {Config.CAPTURE_DIR}")
    except Exception as e:
        logger.error(f"✗ Cannot write to capture directory: {e}")
        return 1
    
    # Check if rpicam-vid is available
    try:
        result = subprocess.run(
            ["rpicam-vid", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        logger.info(f"✓ rpicam-vid found: {result.stdout.strip()}")
    except FileNotFoundError:
        logger.error("✗ rpicam-vid not found. Install rpicam-apps.")
        return 1
    except Exception as e:
        logger.error(f"✗ Error checking rpicam-vid: {e}")
        return 1
    
    logger.info("Pre-flight checks complete\n")
    
    # Start monitoring
    try:
        monitor = CaptureMonitor()
        monitor.run()
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

