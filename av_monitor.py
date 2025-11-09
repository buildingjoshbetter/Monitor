#!/usr/bin/env python3
"""
Raspberry Pi 5 A/V Monitoring System with IR Trigger

Hardware Requirements:
- Raspberry Pi 5 (Bookworm OS)
- Arducam 64MP OwlSight camera (via CAMERA port)
- Waveshare WM8960 Audio HAT (ALSA)
- AMG8833 IR thermal sensor (I2C)
- Status LEDs:
  * Orange LED on GPIO 19 (monitoring/idle state)
  * Red LED on GPIO 26 (active recording)

This application monitors the AMG8833 IR sensor and automatically
starts/stops A/V recording based on human presence detection.
Visual status indicators via LEDs provide real-time feedback.
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
import socket
from typing import Optional
from gpiozero import LED

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
            "audio_channels": 2,
            "video_codec": "h264",  # or "h265"
            "audio_device": "plughw:2,0",  # WM8960 ALSA device
            "autofocus_mode": "auto",  # Autofocus mode for camera
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


class StatusLEDs:
    """Status LED controller for visual feedback"""
    def __init__(self, orange_pin: int = 19, red_pin: int = 26):
        """
        Initialize status LEDs
        
        Args:
            orange_pin: GPIO pin for orange LED (monitoring/idle)
            red_pin: GPIO pin for red LED (recording)
        """
        self.orange_led = LED(orange_pin)
        self.red_led = LED(red_pin)
        logger.info(f"Status LEDs initialized (Orange: GPIO{orange_pin}, Red: GPIO{red_pin})")
        
        # Start with orange LED on (system idle/monitoring)
        self.set_idle()
    
    def set_idle(self):
        """Set LEDs to idle state (orange on, red off)"""
        self.orange_led.on()
        self.red_led.off()
        logger.debug("LED Status: IDLE (orange)")
    
    def set_recording(self):
        """Set LEDs to recording state (orange off, red on)"""
        self.orange_led.off()
        self.red_led.on()
        logger.debug("LED Status: RECORDING (red)")
    
    def set_waiting(self):
        """Set LEDs to waiting state (red blinking)"""
        # Keep red on during waiting period
        self.orange_led.off()
        self.red_led.on()
        logger.debug("LED Status: WAITING (red)")
    
    def cleanup(self):
        """Turn off all LEDs"""
        self.orange_led.off()
        self.red_led.off()
        logger.debug("LED Status: OFF")


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
    """Manages audio/video recording (separate streams, merged on stop)"""
    def __init__(self, config: Config):
        self.config = config
        self.video_process: Optional[subprocess.Popen] = None
        self.audio_process: Optional[subprocess.Popen] = None
        self.current_file: Optional[Path] = None
        self.temp_video_file: Optional[Path] = None
        self.temp_audio_file: Optional[Path] = None
        self.hostname = socket.gethostname()  # Get device hostname
    
    def generate_filename(self) -> Path:
        """
        Generate timestamped filename with hierarchical folder structure
        
        Structure: /mnt/nas/dt/raw/YYYY/MM/DD/MMDDYYYY_hostname_HHMMSS.mp4
        Example: /mnt/nas/dt/raw/2025/11/09/11092025_sauron-unit-1_143022.mp4
        """
        now = datetime.now()
        
        # Create year/month/day folder structure
        year_folder = now.strftime("%Y")
        month_folder = now.strftime("%m")
        day_folder = now.strftime("%d")
        
        capture_path = Path(self.config.capture_dir) / year_folder / month_folder / day_folder
        
        # Create directories if they don't exist
        capture_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: MMDDYYYY_hostname_HHMMSS.mp4
        date_str = now.strftime("%m%d%Y")
        time_str = now.strftime("%H%M%S")
        filename = f"{date_str}_{self.hostname}_{time_str}.mp4"
        
        return capture_path / filename
    
    def start_recording(self) -> bool:
        """
        Start audio and video recording (separate processes)
        
        Returns:
            True if recording started successfully, False otherwise
        """
        if self.video_process is not None or self.audio_process is not None:
            logger.warning("Recording already in progress")
            return False
        
        self.current_file = self.generate_filename()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Store temp files in /tmp to avoid cluttering NAS
        self.temp_video_file = Path(f"/tmp/temp_video_{timestamp}.mp4")
        self.temp_audio_file = Path(f"/tmp/temp_audio_{timestamp}.wav")
        
        width, height = self.config.video_resolution.split('x')
        
        # Build audio recording command (arecord)
        audio_cmd = [
            'arecord',
            '-D', self.config.audio_device,
            '-f', 'S16_LE',
            '-r', str(self.config.audio_samplerate),
            '-c', str(self.config.audio_channels),
            str(self.temp_audio_file)
        ]
        
        # Build video recording command (rpicam-vid, NO audio)
        video_cmd = [
            'rpicam-vid',
            '-t', '0',  # Infinite duration (we'll stop manually)
            '--width', width,
            '--height', height,
            '--framerate', str(self.config.video_framerate),
            '--codec', self.config.video_codec,
            '--autofocus-mode', self.config.autofocus_mode,
            '-o', str(self.temp_video_file),
            '--nopreview',
        ]
        
        try:
            logger.info(f"Starting recording: {self.current_file}")
            logger.debug(f"Audio command: {' '.join(audio_cmd)}")
            logger.debug(f"Video command: {' '.join(video_cmd)}")
            
            # Start audio recording first
            self.audio_process = subprocess.Popen(
                audio_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            )
            
            # Start video recording immediately after
            self.video_process = subprocess.Popen(
                video_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            )
            
            # Give them a moment to start
            time.sleep(0.5)
            
            # Check if processes started successfully
            if self.audio_process.poll() is not None:
                _, stderr = self.audio_process.communicate()
                logger.error(f"arecord failed to start: {stderr.decode()}")
                self._cleanup_failed_start()
                return False
            
            if self.video_process.poll() is not None:
                _, stderr = self.video_process.communicate()
                logger.error(f"rpicam-vid failed to start: {stderr.decode()}")
                self._cleanup_failed_start()
                return False
            
            logger.info("Audio and video recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._cleanup_failed_start()
            return False
    
    def _cleanup_failed_start(self):
        """Clean up after failed recording start"""
        if self.audio_process:
            try:
                self.audio_process.kill()
                self.audio_process.wait()
            except:
                pass
            self.audio_process = None
        
        if self.video_process:
            try:
                self.video_process.kill()
                self.video_process.wait()
            except:
                pass
            self.video_process = None
        
        self.current_file = None
        self.temp_audio_file = None
        self.temp_video_file = None
    
    def stop_recording(self) -> bool:
        """
        Stop recording gracefully and merge audio/video
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.video_process is None and self.audio_process is None:
            logger.warning("No recording in progress")
            return False
        
        try:
            logger.info("Stopping recording...")
            
            # Stop video process (SIGINT for graceful shutdown)
            if self.video_process:
                self.video_process.send_signal(signal.SIGINT)
                try:
                    self.video_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("Video process didn't stop gracefully, forcing termination")
                    self.video_process.kill()
                    self.video_process.wait()
            
            # Stop audio process (SIGTERM for arecord)
            if self.audio_process:
                self.audio_process.terminate()
                try:
                    self.audio_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Audio process didn't stop gracefully, forcing termination")
                    self.audio_process.kill()
                    self.audio_process.wait()
            
            # Check if temp files exist
            if not self.temp_video_file or not self.temp_video_file.exists():
                logger.error(f"Temporary video file not found: {self.temp_video_file}")
                self._cleanup_recording()
                return False
            
            if not self.temp_audio_file or not self.temp_audio_file.exists():
                logger.error(f"Temporary audio file not found: {self.temp_audio_file}")
                self._cleanup_recording()
                return False
            
            # Merge audio and video with ffmpeg
            logger.info("Merging audio and video...")
            merge_success = self._merge_av_files()
            
            if merge_success:
                # Delete temporary files
                try:
                    self.temp_video_file.unlink()
                    self.temp_audio_file.unlink()
                    logger.info("Temporary files cleaned up")
                except Exception as e:
                    logger.warning(f"Could not delete temporary files: {e}")
                
                file_size = self.current_file.stat().st_size
                logger.info(f"Recording saved: {self.current_file} ({file_size} bytes)")
            else:
                logger.error("Failed to merge audio and video")
            
            self._cleanup_recording()
            return merge_success
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self._cleanup_recording()
            return False
    
    def _merge_av_files(self) -> bool:
        """
        Merge audio and video files using ffmpeg
        
        Returns:
            True if merge successful, False otherwise
        """
        merge_cmd = [
            'ffmpeg',
            '-i', str(self.temp_video_file),
            '-i', str(self.temp_audio_file),
            '-c:v', 'copy',  # Copy video stream (no re-encode)
            '-c:a', 'aac',   # Encode audio to AAC
            '-shortest',     # Match shortest stream duration
            '-y',            # Overwrite output file
            str(self.current_file)
        ]
        
        try:
            logger.debug(f"Merge command: {' '.join(merge_cmd)}")
            result = subprocess.run(
                merge_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Audio/video merge successful")
                return True
            else:
                logger.error(f"ffmpeg merge failed: {result.stderr.decode()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg merge timed out")
            return False
        except Exception as e:
            logger.error(f"Error running ffmpeg: {e}")
            return False
    
    def _cleanup_recording(self):
        """Clean up recording state"""
        self.video_process = None
        self.audio_process = None
        self.current_file = None
        self.temp_video_file = None
        self.temp_audio_file = None
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        video_active = self.video_process is not None and self.video_process.poll() is None
        audio_active = self.audio_process is not None and self.audio_process.poll() is None
        return video_active or audio_active


class MonitorSystem:
    """Main monitoring system coordinator"""
    def __init__(self, config: Config):
        self.config = config
        self.status_leds = StatusLEDs()  # Initialize LED indicators
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
        self.status_leds.cleanup()  # Turn off LEDs
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
                
                # State machine logic with LED indicators
                if self.state == RecordingState.IDLE:
                    if presence:
                        logger.info("Presence detected! Starting recording...")
                        if self.recorder.start_recording():
                            self.state = RecordingState.RECORDING
                            self.status_leds.set_recording()  # Turn on red LED
                            self.absence_timer = None
                
                elif self.state == RecordingState.RECORDING:
                    if not presence:
                        logger.info("Presence lost, starting countdown...")
                        self.state = RecordingState.WAITING_TO_STOP
                        self.status_leds.set_waiting()  # Keep red LED on during wait
                        self.absence_timer = current_time
                
                elif self.state == RecordingState.WAITING_TO_STOP:
                    if presence:
                        # Presence returned, cancel countdown
                        logger.info("Presence returned, canceling stop countdown")
                        self.state = RecordingState.RECORDING
                        self.status_leds.set_recording()  # Back to red LED
                        self.absence_timer = None
                    elif self.absence_timer is not None:
                        elapsed = current_time - self.absence_timer
                        if elapsed >= self.config.stop_delay_seconds:
                            logger.info(f"No presence for {self.config.stop_delay_seconds}s, stopping recording")
                            self.recorder.stop_recording()
                            self.state = RecordingState.IDLE
                            self.status_leds.set_idle()  # Back to orange LED
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
            self.status_leds.cleanup()  # Turn off LEDs on exit
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

