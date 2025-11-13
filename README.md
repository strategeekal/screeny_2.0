# Pantallita 2.0.0

A dual RGB matrix weather display system running on MatrixPortal S3, showing real-time weather, forecasts, events, and scheduled activities for family use.

## Overview

Pantallita displays weather information, 12-hour forecasts, family events (birthdays, special occasions), and scheduled activities (morning/evening routines) on two 64×32 RGB LED matrices. The system runs continuously with automatic daily restarts, defensive error handling, and smart caching to manage CircuitPython's memory and socket constraints.

## Hardware

- **Controller:** Adafruit MatrixPortal S3 (ESP32-S3, 8MB flash, 2MB SRAM)
- **Displays:** 2× RGB LED matrices (64×32 pixels, 4-bit color depth)
- **RTC:** DS3231 real-time clock module
- **Power:** 5V power supply
- **Firmware:** Adafruit CircuitPython 9.2.8

## Software Stack

- **Language:** CircuitPython 9.2.8
- **APIs:**
  - AccuWeather API (current conditions & 12-hour forecast)
  - GitHub raw content (remote events/schedules)
- **Libraries:**
  - `adafruit_requests` - HTTP client
  - `adafruit_ntp` - Time synchronization
  - `adafruit_ds3231` - RTC module
  - `adafruit_imageload` - BMP image loading
  - `adafruit_bitmap_font` - Text rendering
  - `displayio` / `rgbmatrix` - Display control

## Project Structure

```
screeny_2.0/
├── code.py                    # Main program (4117 lines)
├── settings.toml              # Environment variables (not in repo)
├── events.csv                 # Local events database
├── schedules.csv              # Local schedules database
├── fonts/
│   ├── bigbit10-16.bdf       # Large font (16pt)
│   └── tinybit6-16.bdf       # Small font (6pt)
├── img/
│   ├── weather/              # Weather icons (1-44.bmp)
│   │   └── columns/          # Forecast column icons
│   ├── events/               # Event images (cake.bmp, heart.bmp, etc.)
│   └── schedules/            # Schedule images (breakfast.bmp, etc.)
└── lib/                      # CircuitPython libraries
```

## Configuration

All configuration is done via `settings.toml` (environment variables):

```toml
# WiFi
CIRCUITPY_WIFI_SSID = "your-ssid"
CIRCUITPY_WIFI_PASSWORD = "your-password"

# AccuWeather API
ACCUWEATHER_API_KEY_TYPE1 = "key-for-matrix-1"
ACCUWEATHER_API_KEY_TYPE2 = "key-for-matrix-2"
ACCUWEATHER_LOCATION_KEY = "location-code"

# Timezone
TIMEZONE = "America/Chicago"

# Device IDs (last 3 bytes of CPU UID in hex)
MATRIX1 = "abc123"
MATRIX2 = "def456"

# GitHub (optional - for remote events/schedules)
GITHUB_REPO_URL = "https://raw.githubusercontent.com/user/repo/main/ephemeral_events.csv"
```

### Getting AccuWeather Location Key
1. Visit AccuWeather and search for your location
2. Look at the URL: `accuweather.com/en/us/city/12345/weather-forecast/12345`
3. The number (12345) is your location key

### Determining Device ID
The device ID is automatically detected from the ESP32-S3's unique CPU UID. Check logs at startup to see your device ID, then add it to `settings.toml`.

## Code Architecture

### Main Components

**1. Configuration & Constants (Lines 1-550)**
- `DisplayConfig` class controls feature toggles
- Constants organized in classes: `Display`, `Layout`, `Timing`, `API`, `Recovery`, `Memory`, `Paths`, `Visual`, `System`
- `ColorManager` handles color palette with dynamic bit depth support

**2. State Management (Lines 767-847)**
- `WeatherDisplayState` class maintains global state
- Tracks API calls, failures, cached data, timing
- Image and text width caching
- Memory monitoring

**3. Network & API (Lines 1014-1576)**
- WiFi connection with exponential backoff retry
- Global session management (single session reused)
- `fetch_weather_with_retries()` with detailed error handling
- `fetch_current_and_forecast_weather()` fetches both in one cycle
- Weather caching with age tracking

**4. Data Loading (Lines 1804-2244)**
- `load_events_from_csv()` - Local events
- `fetch_ephemeral_events()` - GitHub events (startup only)
- `load_schedules_from_csv()` - Local schedules
- `fetch_github_data()` - Remote schedules (startup only)

**5. Display Functions (Lines 2480-3625)**
- `show_weather_display()` - Current conditions with UV/humidity bars
- `show_forecast_display()` - 3-column hourly forecast
- `show_event_display()` - Birthday/event cards
- `show_scheduled_display()` - Time-based activities (segmented for long displays)
- `show_clock_display()` - Fallback/error mode

**6. Main Loop (Lines 3879-4117)**
- `run_display_cycle()` orchestrates all displays
- Checks for scheduled displays first (priority)
- Falls back to weather → forecast → events rotation
- Fast cycle detection prevents runaway errors
- Memory monitoring and cleanup

### Display Cycle Logic

**Normal Cycle (5 minutes):**
1. Check WiFi connectivity
2. Check if schedule is active → show schedule (priority)
3. Otherwise: Fetch weather/forecast data
4. Display forecast (60 seconds)
5. Display weather (240 seconds)
6. Display events (if any remaining time)
7. Memory cleanup

**Schedule Display (segmented, up to 2 hours):**
1. Break into 5-minute segments
2. Each segment fetches weather (or uses cache)
3. Display schedule image + weather + clock + progress bar
4. Repeat until schedule window ends
5. Check for events between schedules

**Error Modes:**
- No WiFi → Clock display
- API failures → Use cached data (up to 15 min old)
- Extended failures (15+ min) → Clock-only mode
- Permanent errors (401/404) → Stop API calls

### API Call Management

**Budget:** 15,000 calls/month per device = ~500 calls/day

**Current Usage Pattern:**
- Weather: Every cycle (5 min) = ~288 calls/day
- Forecast: Every 3 cycles (15 min) = ~96 calls/day
- **Total:** ~384 calls/day (77% of budget)

**Call Tracking:**
- `state.api_call_count` tracks total calls
- Automatic restart at 350 calls (preventive)
- Daily 3am restart resets counters

### Socket Management

**Critical Constraint:** ESP32-S3 has ~8-10 socket descriptors

**Current Strategy:**
- Single global session reused for all requests
- Aggressive cleanup after errors
- `cleanup_global_session()` destroys/recreates session
- `cleanup_sockets()` + `gc.collect()` after operations

**Known Issue:** Response objects not explicitly closed, leading to socket accumulation during long schedule displays (see CODE_REVIEW_REVISED.md for fixes)

### Memory Management

**Available:** ~2MB SRAM
**Typical Usage:** 10-20% (200-400KB)

**Optimization Strategies:**
- Image cache (max 12 images)
- Text width cache (max 50 entries)
- Strategic `gc.collect()` calls
- Cached weather/forecast data
- Single font loading (not per-display)

**Memory Monitoring:**
- `MemoryMonitor` class tracks usage
- Reports every 100 cycles
- Identifies memory spikes at checkpoints

### Timing & Scheduling

**Daily Restart:** 3am automatic restart
- Resets API counters
- Refreshes GitHub data
- Clears accumulated errors
- Prevents memory fragmentation

**Schedule Detection:**
- `ScheduledDisplay` class checks current time against CSV
- Weekday filtering (0=Monday, 6=Sunday)
- Exact minute matching for start/end times
- Supports overlapping schedules (first match wins)

## CSV File Formats

### events.csv
```csv
# Format: MM-DD,TopLine,BottomLine,ImageFile,Color[,StartHour,EndHour]
01-01,Happy,New Year,new_year.bmp,BUGAMBILIA
02-14,Dia,Didiculo,heart.bmp,RED,8,20
```

**Optional Time Range:**
- If omitted: Event shows all day (0-24)
- If specified: Event only shows during those hours (24-hour format)

### schedules.csv
```csv
# Format: name,enabled,days,start_hour,start_min,end_hour,end_min,image,progressbar
Get Dressed,1,0123456,7,0,7,15,get_dressed.bmp,1
Sleep,1,0123456,20,45,21,30,bed.bmp,0
```

**Fields:**
- `enabled`: 1=active, 0=disabled
- `days`: String of digits (0=Mon, 6=Sun), e.g., "0123456" for all days
- `progressbar`: 1=show progress bar, 0=hide

## Features

### Weather Display
- Current temperature (feels-like or feels-shade based on threshold)
- Weather icon (AccuWeather icon numbers 1-44)
- UV index bar (color-coded: green→yellow→red)
- Humidity bar (0-100%, with spacing indicators)
- Weather condition text
- Last update timestamp

### 12-Hour Forecast
- 3-column layout showing different time periods
- Smart column selection:
  - Shows next 3 different hours
  - Prioritizes precipitation hours
  - Skips redundant times
- Each column: Time, icon, temperature
- "NOW" indicator for current hour

### Events
- Date-based display (MM-DD format)
- Two-line text with customizable colors
- Image support (25×28px BMPs)
- Optional time filtering (show only during specific hours)
- Bottom-aligned text positioning
- Supports both local (events.csv) and remote (GitHub) events

### Schedules
- Time-based activity reminders
- Weekday filtering
- 40×28px schedule images
- Side-mounted weather display (optional)
- Progress bar showing completion
- Segmented display for long schedules (breaks into 5-min chunks)
- Clock display with minute updates

### Error Recovery
- WiFi reconnection with cooldown (5 min between attempts)
- API retry with exponential backoff
- Cached data fallback (up to 15 min old)
- Clock-only mode for extended failures
- Fast cycle detection and restart
- Socket cleanup on RuntimeError/OSError

### Visual Features
- Weekday color indicator (4×4px square, top-right corner)
- Color-coded error states (clock display color)
- Cached data indicator (LILAC color for stale data)
- Multiple color schemes for text

## Display Configuration

Toggle features in `DisplayConfig` class (lines 357-447):

```python
def __init__(self):
    # Core displays
    self.show_weather = True
    self.show_forecast = True
    self.show_events = True

    # Display elements
    self.show_weekday_indicator = True
    self.show_scheduled_displays = True
    self.show_events_in_between_schedules = True

    # API controls
    self.use_live_weather = True
    self.use_live_forecast = True

    # Test modes
    self.use_test_date = False
    self.show_color_test = False
    self.show_icon_test = False
```

## Known Issues

### Socket Exhaustion During Long Schedules
**Symptom:** Socket errors after 8-10 segments of 2-hour schedule displays

**Root Cause:** HTTP response objects not explicitly closed, accumulating in global session

**Workaround:** Current cleanup strategy handles normal cycles (300+ cycles), but struggles with 24-segment schedules

**Fix:** See `CODE_REVIEW_REVISED.md` and `QUICK_FIX_GUIDE.md` for implementation details
- Add `response.close()` in `try/finally` blocks (5 locations)
- Add mid-schedule cleanup every 4 segments
- Implement smarter weather caching (15 min for schedules)

### Stack Exhaustion
**Symptom:** "pystack exhausted" error

**Cause:** Deep nesting in CircuitPython's limited stack

**Mitigation:**
- Use early returns to reduce nesting
- Minimize nested conditionals
- Avoid recursive calls

### Memory Fragmentation
**Symptom:** Gradual memory increase over many hours

**Mitigation:**
- Daily 3am restart
- Strategic `gc.collect()` calls
- Limit string concatenation (use f-strings sparingly in hot paths)

## Debugging

### Log Levels
Set `CURRENT_DEBUG_LEVEL` (line 355):
- `DebugLevel.ERROR` (1) - Errors only
- `DebugLevel.WARNING` (2) - Errors + warnings
- `DebugLevel.INFO` (3) - Key events (DEFAULT)
- `DebugLevel.DEBUG` (4) - Troubleshooting details
- `DebugLevel.VERBOSE` (5) - Everything

### Common Debug Tasks

**Check API calls:**
```python
log_debug(f"API Stats: Total={state.api_call_count}, Current={state.current_api_calls}")
```

**Monitor memory:**
```python
state.memory_monitor.check_memory("checkpoint_name")
```

**Test without API:**
```python
display_config.use_live_weather = False
display_config.use_live_forecast = False
# Uses TestData.DUMMY_WEATHER_DATA
```

## Future Enhancements

### High Priority
1. **Implement socket exhaustion fixes** (see CODE_REVIEW_REVISED.md)
   - Add response.close() to 5 locations
   - Mid-schedule cleanup every 4 segments
   - 15-minute weather caching during schedules

2. **Testing environment**
   - Test mode flag to prevent API calls
   - Mock data generators
   - Unit test framework for CircuitPython
   - Separate test/production configurations

### Planned Features
3. **GitHub-based config control**
   - Remote feature toggles without USB connection
   - JSON config file fetched at startup
   - Validation and fallback to local config

4. **Stock prices module**
   - Ticker symbols from config
   - Update frequency: 5-15 minutes
   - Rotating display with multiple stocks

5. **Minimal display mode**
   - Time-based activation (e.g., 10pm-6am)
   - Clock + temperature only
   - Reduced brightness
   - Lower API frequency

6. **Sports scores** (World Cup 2026!)
   - Game schedule tracking
   - Live score updates during matches
   - Team logos and match status

## Version History

### 2.0.0 (Current)
- Stable 25+ hour uptime in normal cycles
- Dual matrix support with device-specific configs
- Segmented schedule displays (up to 2 hours)
- Smart forecast column selection
- Defensive error handling and recovery
- Memory monitoring and optimization
- API budget tracking with preventive restart

### Known Limitations
- Socket exhaustion during multi-hour schedules
- Response objects not explicitly closed
- No remote configuration updates
- Manual CSV editing required

## License

Personal project - All rights reserved

## Credits

- **Hardware:** Adafruit MatrixPortal S3, RGB matrices
- **Firmware:** Adafruit CircuitPython 9.2.8
- **Weather Data:** AccuWeather API
- **Fonts:** Custom BDF fonts (bigbit, tinybit)
- **Remote Storage:** GitHub raw content hosting
- **Web App:** Separate CloudFlare-hosted CSV editor (see web app repository)

---

**For detailed code review and optimization recommendations, see:**
- `CODE_REVIEW_REVISED.md` - Complete technical analysis
- `QUICK_FIX_GUIDE.md` - Step-by-step implementation guide
- `README_SETTINGS.md` - Settings configuration details
