# Phase 0: Bootstrap - Foundation Testing

## Goal
Get the bare minimum system running on CircuitPython 10:
- WiFi connection
- Display initialization
- RTC sync
- Simple display (clock or "Hello World")
- Button stop functionality

**Success Criteria:** System runs for 1 hour, displays current time, responds to button press.

## Step-by-Step Implementation

### Step 0.1: Upgrade to CircuitPython 10

1. **Backup your current working system:**
   ```
   # On your computer, copy entire CIRCUITPY drive
   cp -r /Volumes/CIRCUITPY ~/pantallita_v2_backup
   ```

2. **Flash TinyUF2 0.33.0+ bootloader:**
   - Download from: https://github.com/adafruit/tinyuf2/releases
   - Find: `tinyuf2-adafruit_matrixportal_s3-0.33.0.bin`
   - Use esptool: `esptool.py write_flash 0x0 tinyuf2-*.bin`
   - OR use Adafruit's web-based flasher: https://adafruit.github.io/Adafruit_WebSerial_ESPTool/

3. **Install CircuitPython 10.0.1:**
   - Download from: https://circuitpython.org/board/adafruit_matrixportal_s3/
   - Find: `adafruit-circuitpython-adafruit_matrixportal_s3-en_US-10.0.1.uf2`
   - Copy to BOOT drive when MatrixPortal is in bootloader mode
   - Wait for device to restart

4. **Verify installation:**
   ```python
   # Connect to serial console
   import sys
   print(sys.implementation)
   # Should show: (name='circuitpython', version=(10, 0, 1))
   ```

5. **Copy back libraries:**
   ```
   # Copy lib folder from backup
   cp -r ~/pantallita_v2_backup/lib /Volumes/CIRCUITPY/lib
   ```

6. **Copy settings.toml:**
   ```
   cp ~/pantallita_v2_backup/settings.toml /Volumes/CIRCUITPY/settings.toml
   ```

### Step 0.2: Create Minimal Module Structure

Create these files with minimal content:

#### 1. config.py (Minimal)

```python
"""Minimal config for bootstrap test"""
import os

class Display:
    WIDTH = 64
    HEIGHT = 32
    BIT_DEPTH = 4

class Colors:
    BLACK = 0x000000
    WHITE = 0xF5F5DC
    GREEN = 0x00FF00
    RED = 0xFF0000

class Env:
    WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
    WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")

class Paths:
    FONT_LARGE = "/fonts/bigbit10-16.bdf"

class LogLevel:
    ERROR = 1
    INFO = 3

CURRENT_LOG_LEVEL = LogLevel.INFO
```

#### 2. state.py (Minimal)

```python
"""Global state for bootstrap test"""

# Display objects (initialized by hardware.py)
display = None
main_group = None
font_large = None

# RTC object (initialized by hardware.py)
rtc = None

# Button objects
button_up = None
button_down = None

# Session (initialized by hardware.py)
session = None
```

#### 3. hardware.py (Minimal)

```python
"""Hardware initialization for bootstrap test"""
import board
import displayio
import digitalio
import framebufferio
import rgbmatrix
import busio
import wifi
import socketpool
import ssl
import adafruit_requests
import adafruit_ds3231
import adafruit_ntp
from adafruit_bitmap_font import bitmap_font
import time

import config
import state

def log(msg):
    if config.CURRENT_LOG_LEVEL >= config.LogLevel.INFO:
        print(f"[HW] {msg}")

def init_display():
    """Initialize RGB matrix display"""
    log("Initializing display...")

    displayio.release_displays()

    matrix = rgbmatrix.RGBMatrix(
        width=config.Display.WIDTH,
        height=config.Display.HEIGHT,
        bit_depth=config.Display.BIT_DEPTH,
        rgb_pins=[
            board.MTX_R1, board.MTX_G1, board.MTX_B1,
            board.MTX_R2, board.MTX_G2, board.MTX_B2
        ],
        addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
        clock_pin=board.MTX_CLK,
        latch_pin=board.MTX_LAT,
        output_enable_pin=board.MTX_OE
    )

    state.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
    state.main_group = displayio.Group()
    state.display.root_group = state.main_group

    # Load font
    state.font_large = bitmap_font.load_font(config.Paths.FONT_LARGE)

    log("Display initialized")

def init_rtc():
    """Initialize RTC module"""
    log("Initializing RTC...")

    i2c = busio.I2C(board.SCL, board.SDA)
    state.rtc = adafruit_ds3231.DS3231(i2c)

    log("RTC initialized")
    return state.rtc

def init_buttons():
    """Initialize MatrixPortal buttons"""
    log("Initializing buttons...")

    try:
        state.button_up = digitalio.DigitalInOut(board.BUTTON_UP)
        state.button_up.switch_to_input(pull=digitalio.Pull.UP)

        state.button_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
        state.button_down.switch_to_input(pull=digitalio.Pull.UP)

        log("Buttons initialized")
    except Exception as e:
        log(f"Button init failed: {e}")
        state.button_up = None
        state.button_down = None

def button_up_pressed():
    """Check if UP button is pressed"""
    if state.button_up:
        return not state.button_up.value  # Button is active LOW
    return False

def connect_wifi():
    """Connect to WiFi"""
    log(f"Connecting to WiFi: {config.Env.WIFI_SSID}...")

    wifi.radio.connect(config.Env.WIFI_SSID, config.Env.WIFI_PASSWORD)
    log(f"Connected! IP: {wifi.radio.ipv4_address}")

    # Create HTTP session
    pool = socketpool.SocketPool(wifi.radio)
    state.session = adafruit_requests.Session(pool, ssl.create_default_context())

    log("HTTP session created")

def is_wifi_connected():
    """Check if WiFi is connected"""
    return wifi.radio.connected

def reconnect_wifi():
    """Attempt to reconnect WiFi"""
    try:
        connect_wifi()
        return True
    except Exception as e:
        log(f"WiFi reconnect failed: {e}")
        return False

def sync_time(rtc):
    """Sync RTC with NTP"""
    log("Syncing time with NTP...")

    try:
        ntp = adafruit_ntp.NTP(state.session.socket_pool, tz_offset=0)
        rtc.datetime = ntp.datetime
        log(f"Time synced: {rtc.datetime}")
    except Exception as e:
        log(f"NTP sync failed: {e}")
```

#### 4. code.py (Bootstrap Test)

```python
"""
Pantallita 3.0 - Bootstrap Test
Tests basic system functionality before implementing features
"""

import time
import gc
import traceback
from adafruit_display_text import bitmap_label

import config
import state
import hardware

def log(msg):
    if config.CURRENT_LOG_LEVEL >= config.LogLevel.INFO:
        print(f"[MAIN] {msg}")

def show_message(text, color=config.Colors.GREEN):
    """Show a simple text message on display"""
    # Clear display
    while len(state.main_group) > 0:
        state.main_group.pop()

    # Create label
    label = bitmap_label.Label(
        state.font_large,
        text=text,
        color=color,
        x=2,
        y=16
    )
    state.main_group.append(label)

def show_clock(rtc):
    """Show current time from RTC"""
    # Clear display
    while len(state.main_group) > 0:
        state.main_group.pop()

    # Get time
    now = rtc.datetime
    hour = now.tm_hour
    minute = now.tm_min

    # Format as 12-hour
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12
    ampm = "AM" if hour < 12 else "PM"

    # Create time label
    time_text = f"{hour_12}:{minute:02d}"
    time_label = bitmap_label.Label(
        state.font_large,
        text=time_text,
        color=config.Colors.WHITE,
        x=5,
        y=12
    )
    state.main_group.append(time_label)

    # Create AM/PM label
    ampm_label = bitmap_label.Label(
        state.font_large,
        text=ampm,
        color=config.Colors.GREEN,
        x=5,
        y=24
    )
    state.main_group.append(ampm_label)

def run_test_cycle(rtc, cycle_count):
    """Run one test cycle"""
    log(f"=== Cycle {cycle_count} ===")

    # Check WiFi
    if not hardware.is_wifi_connected():
        log("WiFi disconnected!")
        show_message("NO WIFI", config.Colors.RED)
        time.sleep(5)
        hardware.reconnect_wifi()
        return

    # Show clock for 10 seconds
    show_clock(rtc)

    # Sleep with button check
    for _ in range(100):  # 100 * 0.1s = 10s
        if hardware.button_up_pressed():
            log("Button pressed - exiting")
            raise KeyboardInterrupt
        time.sleep(0.1)

    # Memory check
    if cycle_count % 10 == 0:
        free = gc.mem_free()
        log(f"Memory: {free} bytes free")
        gc.collect()

def main():
    """Bootstrap test main function"""
    log("=== Pantallita 3.0 Bootstrap Test ===")
    log(f"CircuitPython version: {import sys; sys.implementation.version}")

    try:
        # Initialize hardware
        show_message("INIT...", config.Colors.GREEN)

        hardware.init_display()
        rtc = hardware.init_rtc()
        hardware.init_buttons()

        show_message("WIFI...", config.Colors.GREEN)
        hardware.connect_wifi()

        show_message("SYNC...", config.Colors.GREEN)
        hardware.sync_time(rtc)

        show_message("READY!", config.Colors.GREEN)
        time.sleep(2)

        log("=== Bootstrap test starting ===")
        log("Press UP button to stop")

        # Main test loop
        cycle_count = 0
        while True:
            cycle_count += 1
            run_test_cycle(rtc, cycle_count)

    except KeyboardInterrupt:
        log("=== Bootstrap test stopped ===")
        show_message("STOPPED", config.Colors.RED)
        time.sleep(2)
    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exception(e)
        show_message("ERROR!", config.Colors.RED)
        time.sleep(10)

if __name__ == "__main__":
    main()
```

### Step 0.3: Deploy and Test

1. **Copy files to MatrixPortal:**
   ```
   cp config.py /Volumes/CIRCUITPY/
   cp state.py /Volumes/CIRCUITPY/
   cp hardware.py /Volumes/CIRCUITPY/
   cp code.py /Volumes/CIRCUITPY/
   ```

2. **Watch serial console:**
   ```
   screen /dev/tty.usbmodem* 115200
   # or use Mu Editor
   ```

3. **Expected output:**
   ```
   [MAIN] === Pantallita 3.0 Bootstrap Test ===
   [HW] Initializing display...
   [HW] Display initialized
   [HW] Initializing RTC...
   [HW] RTC initialized
   [HW] Initializing buttons...
   [HW] Buttons initialized
   [HW] Connecting to WiFi: YourNetwork...
   [HW] Connected! IP: 192.168.1.123
   [HW] HTTP session created
   [HW] Syncing time with NTP...
   [HW] Time synced: time.struct_time(...)
   [MAIN] === Bootstrap test starting ===
   [MAIN] Press UP button to stop
   [MAIN] === Cycle 1 ===
   [MAIN] === Cycle 2 ===
   ...
   ```

4. **Display should show:**
   - Brief messages: "INIT...", "WIFI...", "SYNC...", "READY!"
   - Then clock updates every 10 seconds: "12:34" with "PM"

5. **Test button:**
   - Press UP button
   - Should see "STOPPED" on display
   - Serial shows: "[MAIN] === Bootstrap test stopped ==="

### Step 0.4: Validation Checklist

Run for 1 hour and verify:

- [ ] Display shows correct time
- [ ] Time updates every 10 seconds
- [ ] WiFi stays connected (check logs)
- [ ] Memory doesn't leak (check every 10th cycle)
- [ ] Button stops program cleanly
- [ ] No error messages in serial console
- [ ] No crashes or resets

### Step 0.5: Troubleshooting

**"Module not found" errors:**
- Verify files are at root of CIRCUITPY drive
- Check file names match exactly (case-sensitive)

**WiFi connection fails:**
- Check settings.toml has correct SSID/password
- Verify WiFi is 2.4GHz (ESP32 doesn't support 5GHz)

**Display stays black:**
- Check power supply (needs 5V 2A minimum)
- Verify lib folder has adafruit_display_text
- Check fonts folder exists with bigbit10-16.bdf

**Time doesn't sync:**
- Verify WiFi is connected first
- Check firewall isn't blocking NTP (port 123)
- May take 30-60 seconds for first sync

**Button doesn't work:**
- Board might not have BUTTON_UP/BUTTON_DOWN pins
- Check hardware.py logs: "Button init failed" means pins not available
- Can skip button testing if not available

### Step 0.6: Success Criteria

Once you have:
- ✅ 1 hour of stable operation
- ✅ No crashes or resets
- ✅ WiFi staying connected
- ✅ Memory stable (not increasing)
- ✅ Display updating correctly
- ✅ Button working (if available)

**You're ready for Phase 1: Weather Display**

## What This Bootstrap Test Validates

1. **CircuitPython 10 compatibility** - Ensures new version works
2. **Hardware initialization** - Display, RTC, buttons all functional
3. **WiFi stability** - Network connection reliable
4. **Module architecture** - Your new structure compiles and runs
5. **Memory baseline** - Establishes normal memory usage
6. **Button functionality** - Can stop program cleanly

This gives you a **known-good foundation** before adding complexity.

## Next Steps After Bootstrap

Once bootstrap test passes 1 hour:

1. **Create weather_api.py** - Add weather fetching
2. **Create display_weather.py** - Add weather rendering
3. **Update code.py** - Replace clock with weather display
4. **Test for 24 hours** - Ensure weather display is stable
5. **Repeat for forecast** - Add next feature
6. **And so on...**

Each phase builds on the previous known-good state.
