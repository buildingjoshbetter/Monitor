#!/usr/bin/env python3
"""
Raspberry Pi 5 A/V Monitoring System with IR Trigger

Hardware Requirements:
- Raspberry Pi 5 (Bookworm OS)
- Arducam 64MP OwlSight camera (via CAMERA port)
- Waveshare WM8960 Audio HAT (ALSA)
- AMG8833 IR thermal sensor (I2C)

This application monitors the AMG8833 IR sensor and automatically
starts/stops A/V recording based on human presence detection.
"""

import board
import busio
import adafruit_amg88xx
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from enum import Enum
import signal
import sys
import json
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/av_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class RecordingState(Enum):
    """State machine for recording logic"""
    IDLE = "idle"
    RECORDING = "recording"
    WAITING_TO_STOP = "waiting_to_stop"


class Config:
    """Configuration settings"""
    def __init__(self, config_path: str = "/etc/av_monitor/config.json"):
        self.config_path = config_path
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or use defaults"""
        defaults = {
            "capture_dir": str(Path.home() / "captures"),
            "temperature_threshold": 28.0,  # Celsius for human detection
            "presence_pixels_required": 3,  # Min pixels above threshold
            "stop_delay_seconds": 60,
            "poll_interval_seconds": 0.5,
            "video_resolution": "1920x1080",
            "video_framerate": 30,
            "audio_samplerate": 48000,
            "audio_channels": 1,
            "video_codec": "h264",  # or "h265"
            "audio_device": "plughw:1,0",  # WM8960 ALSA device
            "autofocus_mode": "auto",  # auto, continuous, or manual
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    defaults.update(user_config)
                logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not load config file, using defaults: {e}")
        
        # Set attributes
        for key, value in defaults.items():
            setattr(self, key, value)
        
        # Ensure capture directory exists
        Path(self.capture_dir).mkdir(parents=True, exist_ok=True)


class IRSensor:
    """AMG8833 IR thermal sensor interface"""
    def __init__(self, threshold: float = 28.0, min_pixels: int = 3):
        self.threshold = threshold
        self.min_pixels = min_pixels
        self.sensor = None
        self.initialize()
    
    def initialize(self):
        """Initialize I2C connection to AMG8833"""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_amg88xx.AMG88XX(i2c)
            logger.info("AMG8833 IR sensor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AMG8833: {e}")
            raise
    
    def detect_presence(self) -> bool:
        """
        Detect human presence based on thermal signature
        
        Returns:
            True if human-like heat signature detected, False otherwise
        """
        try:
            # Read 8x8 thermal grid
            pixels = self.sensor.pixels
            
            # Count pixels above threshold
            hot_pixels = 0
            for row in pixels:
                for temp in row:
                    if temp >= self.threshold:
                        hot_pixels += 1
            
            presence = hot_pixels >= self.min_pixels
            
            if presence:
                logger.debug(f"Presence detected: {hot_pixels} pixels above {self.threshold}°C")
            
            return presence
            
        except Exception as e:
            logger.error(f"Error reading IR sensor: {e}")
            return False


class AVRecorder:
    """Manages audio/video recording using rpicam-vid"""
    def __init__(self, config: Config):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.current_file: Optional[Path] = None
    
    def generate_filename(self) -> Path:
        """Generate timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rec_{timestamp}.mp4"
        return Path(self.config.capture_dir) / filename
    
    def start_recording(self) -> bool:
        """
        Start rpicam-vid recording with audio
        
        Returns:
            True if recording started successfully, False otherwise
        """
        if self.process is not None:
            logger.warning("Recording already in progress")
            return False
        
        self.current_file = self.generate_filename()
        
        # Build rpicam-vid command
        # Format: rpicam-vid -t 0 --width 1920 --height 1080 --framerate 30 \
        #         --codec h264 --audio --audio-device plughw:1,0 --audio-samplerate 48000 \
        #         --audio-channels 1 -o output.mp4
        
        width, height = self.config.video_resolution.split('x')
        
        cmd = [
            'rpicam-vid',
            '-t', '0',  # Infinite duration (we'll stop manually)
            '--width', width,
            '--height', height,
            '--framerate', str(self.config.video_framerate),
            '--codec', self.config.video_codec,
            '--autofocus-mode', self.config.autofocus_mode,  # Autofocus mode for 64MP camera
            '--audio-codec', 'aac',  # Audio codec (AAC for MP4)
            '--audio-device', self.config.audio_device,
            '--audio-samplerate', str(self.config.audio_samplerate),
            '--audio-channels', str(self.config.audio_channels),
            '-o', str(self.current_file),
            '--nopreview',  # No preview window
        ]
        
        try:
            logger.info(f"Starting recording: {self.current_file}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            )
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Check if process started successfully
            if self.process.poll() is not None:
                # Process already terminated
                _, stderr = self.process.communicate()
                logger.error(f"rpicam-vid failed to start: {stderr.decode()}")
                self.process = None
                self.current_file = None
                return False
            
            logger.info("Recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.process = None
            self.current_file = None
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop recording gracefully
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.process is None:
            logger.warning("No recording in progress")
            return False
        
        try:
            logger.info("Stopping recording...")
            
            # Send SIGINT to rpicam-vid for graceful shutdown
            self.process.send_signal(signal.SIGINT)
            
            # Wait for process to finish (with timeout)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't stop gracefully, forcing termination")
                self.process.kill()
                self.process.wait()
            
            # Check if file was created successfully
            if self.current_file and self.current_file.exists():
                file_size = self.current_file.stat().st_size
                logger.info(f"Recording saved: {self.current_file} ({file_size} bytes)")
            else:
                logger.error(f"Recording file not found: {self.current_file}")
            
            self.process = None
            self.current_file = None
            return True
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.process = None
            self.current_file = None
            return False
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.process is not None and self.process.poll() is None


class MonitorSystem:
    """Main monitoring system coordinator"""
    def __init__(self, config: Config):
        self.config = config
        self.ir_sensor = IRSensor(
            threshold=config.temperature_threshold,
            min_pixels=config.presence_pixels_required
        )
        self.recorder = AVRecorder(config)
        self.state = RecordingState.IDLE
        self.absence_timer: Optional[float] = None
        self.running = True
    
    def handle_signal(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.recorder.is_recording():
            self.recorder.stop_recording()
        sys.exit(0)
    
    def run(self):
        """Main monitoring loop"""
        # Register signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        logger.info("=== A/V Monitoring System Started ===")
        logger.info(f"Configuration:")
        logger.info(f"  Capture directory: {self.config.capture_dir}")
        logger.info(f"  Temperature threshold: {self.config.temperature_threshold}°C")
        logger.info(f"  Stop delay: {self.config.stop_delay_seconds}s")
        logger.info(f"  Video: {self.config.video_resolution} @ {self.config.video_framerate}fps")
        logger.info(f"  Audio: {self.config.audio_samplerate}Hz, {self.config.audio_channels}ch")
        logger.info("Monitoring for presence...")
        
        try:
            while self.running:
                presence = self.ir_sensor.detect_presence()
                current_time = time.time()
                
                # State machine logic
                if self.state == RecordingState.IDLE:
                    if presence:
                        logger.info("Presence detected! Starting recording...")
                        if self.recorder.start_recording():
                            self.state = RecordingState.RECORDING
                            self.absence_timer = None
                
                elif self.state == RecordingState.RECORDING:
                    if not presence:
                        logger.info("Presence lost, starting countdown...")
                        self.state = RecordingState.WAITING_TO_STOP
                        self.absence_timer = current_time
                
                elif self.state == RecordingState.WAITING_TO_STOP:
                    if presence:
                        # Presence returned, cancel countdown
                        logger.info("Presence returned, canceling stop countdown")
                        self.state = RecordingState.RECORDING
                        self.absence_timer = None
                    elif self.absence_timer is not None:
                        elapsed = current_time - self.absence_timer
                        if elapsed >= self.config.stop_delay_seconds:
                            logger.info(f"No presence for {self.config.stop_delay_seconds}s, stopping recording")
                            self.recorder.stop_recording()
                            self.state = RecordingState.IDLE
                            self.absence_timer = None
                
                # Poll interval
                time.sleep(self.config.poll_interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            if self.recorder.is_recording():
                logger.info("Stopping recording before exit...")
                self.recorder.stop_recording()
            logger.info("=== A/V Monitoring System Stopped ===")


def main():
    """Entry point"""
    try:
        # Load configuration
        config = Config()
        
        # Create and run monitor system
        monitor = MonitorSystem(config)
        monitor.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

