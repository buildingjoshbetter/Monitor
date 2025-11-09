#!/usr/bin/env python3
"""
Component Testing Script

Tests each hardware component individually to help debug issues.
Run this script to verify your hardware setup.
"""

import sys
import time

def test_imports():
    """Test Python library imports"""
    print("=" * 60)
    print("Testing Python Dependencies")
    print("=" * 60)
    
    tests = [
        ("board", "GPIO board support"),
        ("busio", "I2C/SPI support"),
        ("adafruit_amg88xx", "AMG8833 sensor library"),
    ]
    
    passed = 0
    for module, description in tests:
        try:
            __import__(module)
            print(f"✓ {description} ({module})")
            passed += 1
        except ImportError as e:
            print(f"✗ {description} ({module}) - {e}")
    
    print(f"\nPassed: {passed}/{len(tests)}")
    return passed == len(tests)


def test_ir_sensor():
    """Test AMG8833 IR thermal sensor"""
    print("\n" + "=" * 60)
    print("Testing AMG8833 IR Sensor")
    print("=" * 60)
    
    try:
        import board
        import busio
        import adafruit_amg88xx
        
        print("Initializing I2C...")
        i2c = busio.I2C(board.SCL, board.SDA)
        
        print("Connecting to AMG8833...")
        sensor = adafruit_amg88xx.AMG88XX(i2c)
        
        print("✓ AMG8833 initialized successfully\n")
        
        # Read temperature grid
        print("Reading thermal grid (8x8)...")
        pixels = sensor.pixels
        
        print("\nThermal Map (°C):")
        print("-" * 60)
        
        temps = []
        for row_idx, row in enumerate(pixels):
            row_str = f"Row {row_idx}: "
            for temp in row:
                row_str += f"{temp:5.1f} "
                temps.append(temp)
            print(row_str)
        
        print("-" * 60)
        print(f"Min Temperature: {min(temps):.1f}°C")
        print(f"Max Temperature: {max(temps):.1f}°C")
        print(f"Avg Temperature: {sum(temps)/len(temps):.1f}°C")
        
        # Test presence detection
        threshold = 28.0
        hot_pixels = sum(1 for t in temps if t >= threshold)
        print(f"\nPixels above {threshold}°C threshold: {hot_pixels}")
        
        if hot_pixels >= 3:
            print("✓ Potential human presence detected")
        else:
            print("✓ No presence detected (expected if no one nearby)")
        
        return True
        
    except Exception as e:
        print(f"✗ IR sensor test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check I2C is enabled: i2cdetect -y 1")
        print("  2. Verify wiring: SDA→GPIO2, SCL→GPIO3, VCC→3.3V, GND→GND")
        print("  3. Default address is 0x69")
        return False


def test_camera():
    """Test camera with rpicam-hello"""
    print("\n" + "=" * 60)
    print("Testing Camera (IMX708)")
    print("=" * 60)
    
    import subprocess
    
    try:
        print("Running rpicam-hello for 2 seconds...")
        result = subprocess.run(
            ['rpicam-hello', '-t', '2000', '--nopreview'],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✓ Camera test successful")
            return True
        else:
            print(f"✗ Camera test failed with code {result.returncode}")
            print(f"Error: {result.stderr.decode()}")
            return False
            
    except FileNotFoundError:
        print("✗ rpicam-hello not found")
        print("  Install with: sudo apt install rpicam-apps")
        return False
    except subprocess.TimeoutExpired:
        print("✗ Camera test timed out")
        return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check camera is connected to CAMERA port (not DISP)")
        print("  2. Enable camera: sudo raspi-config → Interface → Camera")
        print("  3. Verify cable orientation (blue side toward board)")
        print("  4. Try: rpicam-hello -t 3000")
        return False


def test_audio():
    """Test audio recording"""
    print("\n" + "=" * 60)
    print("Testing Audio (WM8960)")
    print("=" * 60)
    
    import subprocess
    
    try:
        # List audio devices
        print("Checking for WM8960 audio device...")
        result = subprocess.run(
            ['arecord', '-l'],
            capture_output=True,
            text=True
        )
        
        if 'wm8960' in result.stdout.lower():
            print("✓ WM8960 audio device found")
            print("\nAudio devices:")
            for line in result.stdout.split('\n'):
                if 'wm8960' in line.lower() or 'card' in line.lower():
                    print(f"  {line}")
        else:
            print("✗ WM8960 audio device not found")
            print("  Install WM8960 driver from Waveshare")
            return False
        
        # Test recording
        print("\nTesting 2-second audio capture...")
        result = subprocess.run(
            ['arecord', '-D', 'plughw:1,0', '-d', '2', '-f', 'cd', '/tmp/test_audio.wav'],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✓ Audio recording successful")
            print("  Test file: /tmp/test_audio.wav")
            print("  Play with: aplay /tmp/test_audio.wav")
            return True
        else:
            print(f"✗ Audio recording failed")
            print(f"  Error: {result.stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"✗ Audio test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify WM8960 HAT is seated on GPIO header")
        print("  2. Install driver: https://github.com/waveshare/WM8960-Audio-HAT")
        print("  3. Adjust gain: alsamixer → 'Mic PGA'")
        return False


def test_av_recording():
    """Test combined A/V recording with rpicam-vid"""
    print("\n" + "=" * 60)
    print("Testing A/V Recording (5 seconds)")
    print("=" * 60)
    
    import subprocess
    import os
    
    output_file = '/tmp/test_av.mp4'
    
    try:
        print("Recording 5 seconds of video+audio...")
        print("(This is the actual capture method used by the system)")
        
        cmd = [
            'rpicam-vid',
            '-t', '5000',
            '--width', '1920',
            '--height', '1080',
            '--framerate', '30',
            '--codec', 'h264',
            '--audio',
            '--audio-device', 'plughw:1,0',
            '--audio-samplerate', '48000',
            '--audio-channels', '1',
            '-o', output_file,
            '--nopreview'
        ]
        
        print(f"Command: {' '.join(cmd)}\n")
        
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✓ A/V recording successful")
            print(f"  Output: {output_file}")
            print(f"  Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            print(f"\nYou can copy this file to view it:")
            print(f"  scp pi@<this-pi>:{output_file} ./")
            return True
        else:
            print(f"✗ A/V recording failed")
            if result.stderr:
                print(f"Error: {result.stderr.decode()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Recording timed out")
        return False
    except Exception as e:
        print(f"✗ A/V recording failed: {e}")
        return False


def main():
    """Run all component tests"""
    print("\n" + "=" * 60)
    print("Raspberry Pi 5 A/V Monitor - Component Tests")
    print("=" * 60)
    print()
    
    results = {}
    
    # Test dependencies
    results['dependencies'] = test_imports()
    
    # Test IR sensor
    results['ir_sensor'] = test_ir_sensor()
    
    # Test camera
    results['camera'] = test_camera()
    
    # Test audio
    results['audio'] = test_audio()
    
    # Test combined A/V
    if results['camera'] and results['audio']:
        results['av_recording'] = test_av_recording()
    else:
        print("\n" + "=" * 60)
        print("Skipping A/V test (camera or audio failed)")
        print("=" * 60)
        results['av_recording'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready.")
        print("\nYou can now:")
        print("  1. Adjust configuration: /etc/av_monitor/config.json")
        print("  2. Start the service: sudo systemctl start av-monitor.service")
        print("  3. Monitor logs: sudo journalctl -u av-monitor.service -f")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix issues before starting the service.")
        print("\nSee README.md for detailed troubleshooting.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)

