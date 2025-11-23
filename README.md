# Pantallita 2.1.0

A dual RGB matrix weather display system running on MatrixPortal S3, showing real-time weather, forecasts, stock prices, events, and scheduled activities for family use.

## Overview

Pantallita displays weather information, 12-hour forecasts, stock market data, family events (birthdays, special occasions), and scheduled activities (morning/evening routines) on two 64×32 RGB LED matrices. The system runs continuously with automatic daily restarts, defensive error handling, and smart caching to manage CircuitPython's memory and socket constraints.

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
  - Twelve Data API (real-time stock prices)
  - GitHub raw content (remote events/schedules/stocks)
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
├── code.py                    # Main program (~4500 lines)
├── settings.toml              # Environment variables (not in repo)
├── events.csv                 # Local events database
├── schedules.csv              # Local schedules database
├── stocks.csv                 # Local stocks database
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

# Twelve Data Stock API
TWELVE_DATA_API_KEY = "your-twelve-data-api-key"

# Timezone
TIMEZONE = "America/Chicago"

# Device IDs (last 3 bytes of CPU UID in hex)
MATRIX1 = "abc123"
MATRIX2 = "def456"

# GitHub (optional - for remote events/schedules/stocks)
GITHUB_REPO_URL = "https://raw.githubusercontent.com/user/repo/main/ephemeral_events.csv"
STOCKS_CSV_URL = "https://raw.githubusercontent.com/user/repo/main/stocks.csv"
```

### Getting AccuWeather Location Key
1. Visit AccuWeather and search for your location
2. Look at the URL: `accuweather.com/en/us/city/12345/weather-forecast/12345`
3. The number (12345) is your location key

### Getting Twelve Data API Key
1. Visit [Twelve Data](https://twelvedata.com/) and create a free account
2. Navigate to your API dashboard
3. Copy your API key
4. **Free tier limits:** 800 API calls/day, 8 calls/minute
5. Each stock symbol = 1 API credit (batch requests supported)

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

**5. Display Functions (Lines 2480-3800)**
- `show_weather_display()` - Current conditions with UV/humidity bars
- `show_forecast_display()` - 3-column hourly forecast
- `show_stocks_display()` - Real-time stock prices (3 stocks per rotation)
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

**AccuWeather Budget:** 15,000 calls/month per device = ~500 calls/day

**AccuWeather Usage Pattern:**
- Weather: Every cycle (5 min) = ~288 calls/day
- Forecast: Every 3 cycles (15 min) = ~96 calls/day
- **Total:** ~384 calls/day (77% of budget)

**Twelve Data Budget (Free Tier):** 800 calls/day, 8 calls/minute

**Twelve Data Usage Pattern:**
- Stocks: 3 symbols per rotation during market hours (9:30 AM - 4:00 PM ET)
- Market hours: 6.5 hours/day, weekdays only
- Calls: ~12 calls/hour × 6.5 hours = ~78 calls/day
- After-hours: Uses cached data (1 hour grace period)
- Weekends: No API calls, display skipped
- Rate limiting: 65-second minimum between fetches
- **Total:** ~78 calls/day (10% of budget)

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

### stocks.csv
```csv
# Format: symbol,name
CRM,Salesforce
AAPL,Apple Inc
MSFT,Microsoft
GOOGL,Alphabet Inc
```

**Fields:**
- `symbol`: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)
- `name`: Company name (for reference, not displayed)
- Displays 3 stocks at a time with rotation
- Supports unlimited stocks (no hard limit)
- Can be overridden by remote GitHub CSV via `STOCKS_CSV_URL`

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

### Stock Market Display
- Real-time stock prices from Twelve Data API
- Displays 3 stocks at a time with automatic rotation
- Shows: ticker symbol, price change indicator (+/-), percentage change
- Color-coded: Green for gains, Red for losses
- **Market Hours Aware:**
  - Only fetches during US market hours (9:30 AM - 4:00 PM ET, weekdays)
  - Shows cached data for 1 hour after close (until 5:00 PM ET)
  - Skips display on weekends and outside market hours
  - Automatically converts user's timezone to Eastern Time
  - Falls back to clock display when stocks unavailable
- Rate-limited to respect API limits (65s minimum between fetches)
- Supports unlimited stocks with rotation
- Works with both local CSV and remote GitHub configuration
- Automatic timezone conversion (works from any US timezone)

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

### Image Sizes and Format
- .bmp optimized images in 8-bit format. (Screen has 4-bit depth)
- Stored on device and on Github Repository pantallita-events: https://github.com/strategeekal/pantallita-events/tree/main
- Current Weather images:
  - 32 x 64 full screen images
  - 44 icons with some skipped [ICON#.bmp]
  - 0.bmp is blank
- Forecast Weather images:
  - 13 x 13 pixels
  - 44 icons with some skipped [ICON#.bmp]
  - 0.bmp is blank
- Events images:
  - 25 x 28 pixels
  - blank.bmp is blank
- Schedule images:
  - 40 x 28 pixels
  - blank.bmp is blank
  
## Display Configuration

Toggle features in `DisplayConfig` class (lines 357-447):

```python
def __init__(self):
    # Core displays
    self.show_weather = True
    self.show_forecast = True
    self.show_stocks = True
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

### Socket Exhaustion (FULLY FIXED in 2.0.6)
**Symptom:** "Out of sockets" errors after extended operation (1-2 hours)

**Root Causes - Journey to the Fix:**
1. **v2.0.2:** Runtime weather API responses not closed → Added `response.close()`
2. **v2.0.3:** Startup HTTP requests (timezone, GitHub) not closed → Fixed 4 startup leaks
3. **v2.0.4:** Mid-schedule cleanup never triggered for short schedules → Added global segment counter
4. **v2.0.5:** **THE REAL BUG:** Socket pool was recreated every cleanup, creating orphaned pools!
5. **v2.0.6:** **SIMPLIFICATION:** Removed unnecessary mid-schedule cleanup entirely

**The Critical Bugs:**
- **v2.0.2-v2.0.3:** HTTP responses not closed → Fixed with `response.close()` in try/finally blocks
- **v2.0.5:** Socket pool recreated every cleanup → Fixed with global `_global_socket_pool`
- **v2.0.6:** Cleanup was unnecessary workaround → Removed, matches regular cycle behavior

**Final Solution (v2.0.6):**
- Global `_global_socket_pool` created ONCE and reused forever (v2.0.5 fix)
- All HTTP responses properly closed in try/finally blocks (v2.0.2-v2.0.3 fixes)
- NO mid-schedule cleanup needed - matches regular weather cycle pattern
- Regular cycles prove this works: 100+ iterations without cleanup, zero socket issues
- Daily restart provides natural cleanup boundary
- **Scheduled displays now work identically to regular cycles**

### Stack Exhaustion (FIXED in 2.0.1)
**Symptom:** "pystack exhausted" error during forecast display

**Root Cause:** CircuitPython cannot handle more than 1 level of nested try/except blocks. The forecast image loading loop had 3 levels of nested exception handling, causing guaranteed crashes.

**Fix Applied:**
- Flattened nested try/except blocks to sequential try blocks
- Reduced exception nesting from 3 levels to 1 level maximum
- No helper functions added (which would increase stack depth)

**Stack Capacity Testing Results:**
- Pure recursion limit: 25 levels
- Application recursion depth: 12 levels (52% headroom available)
- Nested exception handling: Max 1 level deep (CircuitPython limitation)

**Development Guidelines:**
- ✅ Use sequential try blocks (not nested)
- ✅ Early returns to reduce nesting
- ✅ Avoid nesting exception handlers
- ❌ Never nest try/except more than 1 level deep
- zfill() is not supported by CircuitPython

**Technical Details:** See `STACK_TEST_ANALYSIS.md` for complete testing methodology and findings.

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

## Code Modularization

### Current Structure: Monolithic (4117 lines)

The entire codebase currently resides in a single `code.py` file. This is a common pattern for CircuitPython projects due to memory constraints.

**Advantages:**
- Minimal import overhead (no module loading costs)
- Simple deployment (one file)
- No module caching/lookup overhead
- Current memory usage: 10-20% (good headroom)

**Disadvantages:**
- Hard to navigate and maintain
- Difficult to test components in isolation
- Challenging for AI agents to parse context
- No clear separation of concerns

### Modularization Considerations

**CircuitPython Memory Tradeoff:**
- Each `import` loads a module into RAM permanently
- Module overhead: ~50-200KB depending on split approach
- ESP32-S3 has 2MB SRAM, currently using 200-400KB

**Best Practices by Project Size:**
- < 500 lines: Single file ✅
- 500-1500 lines: Consider 2-3 modules
- 1500-3000 lines: Should split into modules
- **> 3000 lines: Definitely modularize** ⚠️ (current: 4117 lines)

---

## Future Enhancements

### High Priority

1. **Testing environment**
   - Test mode flag to prevent API calls
   - Mock data generators
   - Unit test framework for CircuitPython
   - Separate test/production configurations

### Planned Features

2. **Stock display variations**
   - **Single stock view:** Full-screen display with detailed stock info (price, change, volume, high/low)
   - **Command center:** Hybrid view showing time, compact weather, and horizontally scrolling stock ticker
   - **Stock charts:** Mini price trend visualization using line graphs or sparklines

3. **Sports scores** (World Cup 2026!)
   - Game schedule tracking
   - Live score updates during matches
   - Team logos and match status

4. **News headlines**
   - RSS feed integration
   - Scrolling news ticker
   - Category filtering (tech, sports, finance)

## Version History

### 2.1.0 (Current)
- **Stock Market Integration:** Added real-time stock price display using Twelve Data API
  - Displays 3 stocks at a time with automatic rotation
  - Color-coded price changes (green/red) with percentage indicators
  - **Market Hours Awareness:** Only fetches during market hours (9:30 AM - 4:00 PM ET, weekdays)
  - Shows cached data for 1 hour after close (until 5:00 PM ET)
  - Skips display on weekends and outside market/grace hours
  - Automatic timezone conversion from user's local time to Eastern Time
  - Falls back to clock display when stocks unavailable
  - Rate-limited API calls (65s minimum between fetches)
  - Supports unlimited stocks via local CSV or remote GitHub configuration
  - Smart rotation leverages natural display cycle timing
  - Added `stocks.csv` for local stock symbols
  - Added `fetch_stock_prices()` with batch request support
  - Added `show_stocks_display()` with 3-row vertical layout and caching
  - Added `is_market_hours_or_cache_valid()` for market hours detection
  - Integration with display rotation cycle
  - Reduced API usage from ~288 calls/day to ~78 calls/day (73% savings)

### 2.0.9
- Added remote display control via CSV parsing, allowing users to remotely control what is shown on each display
- Added logic to show or hide weather icon and weekday indicator during night mode

### 2.0.8
- Split fetch_current_and_forecast_weather() into separate functions
- Extract success/failure tracking
- Night mode using schedule displays and blank image running when a minimal display is needed

### 2.0.7
- Removed logic for feels like temperature for forecast
- Simplified missing image handling for weather, forecast, events and schedule
- Simplified hour formatting and raised to module level
- Simplify load_all_events() with dictionary approach
- Maximize helper reuse in parse_events_csv_content()
- Remove parse_event_line() wrapper for simpler code flow
- HOTFIX: Replace zfill() with manual padding for CircuitPython
- Apply same simplification pattern to schedule loading
- Split fetch_github_data() with helper function
- Display Rendering Optimizatio - use Bitmaps in stead of lines for UV/Humidity and day indicator
- Result: ~150 fewer lines with better display performance and code reusage

### 2.0.6
- **SIMPLIFIED:** Removed mid-schedule cleanup entirely - matches proven regular cycle behavior
- Regular weather cycles run for hundreds of iterations without ANY cleanup - they just work!
- Root insight: Mid-schedule cleanup was a workaround for missing `response.close()` (now fixed)
- With v2.0.5 socket pool fix + all `response.close()` in place, cleanup is unnecessary
- Scheduled displays now work identically to regular cycles: session stays alive, responses close properly
- Benefits: Simpler code, zero overhead, no session recreation, matches proven pattern
- Daily restart provides natural cleanup boundary (sessions never open for days)
- Result: ~200 lines of complexity removed, same reliability as regular cycles  

### 2.0.5
- **FIXED:** CRITICAL socket pool exhaustion - the root cause of ALL socket issues!
- Previous cleanups were creating NEW socket pools every time, never releasing them
- Root cause: `SocketPool(wifi.radio)` was created locally in `get_requests_session()`
- Each cleanup cycle created orphaned socket pools consuming system resources
- Solution: Created global `_global_socket_pool` that is created ONCE and reused forever
- Session cleanup now destroys sessions but preserves the socket pool for reuse
- Tested: v2.0.4 crashed at 1h35m even with cleanups running
- This was the underlying issue causing socket exhaustion in v2.0.2, v2.0.3, and v2.0.4

### 2.0.4
- **FIXED:** Socket exhaustion during rapid short schedules (< 20 minutes each)
- Root cause: Per-schedule segment counter was resetting, preventing cleanup from running
- Solution: Added global_segment_count that persists across all schedules
- Mid-schedule cleanup now triggers every 4 GLOBAL segments (~20 min), not per-schedule
- Added socket health monitoring (HTTP request tracking)
- NOTE: Still had socket pool bug - fixed in v2.0.5

### 2.0.3
- **FIXED:** Socket exhaustion from startup HTTP requests (timezone API, GitHub data)
- Added response.close() to get_timezone_from_location_api() - fixed 1 socket leak
- Added response.close() to fetch_github_data() - fixed 3 socket leaks (events + 2 schedules)
- All HTTP requests now properly close responses in try/finally blocks
- Eliminates 3-4 permanent socket leaks that were causing exhaustion after 2.5 hours
- Tested with varied schedule cycles including back-to-back 1-hour displays

### 2.0.2
- **FIXED:** Socket exhaustion during long schedule displays (partial fix)
- Added response.close() to fetch_weather_with_retries() in try/finally blocks
- Implemented smart weather caching (15-minute refresh, 66% reduction in API calls)
- Added mid-schedule cleanup every 4 segments (~20 minutes)
- NOTE: v2.0.2 fixed runtime leaks but missed startup leaks (completed in v2.0.3)

### 2.0.1
- **FIXED:** Stack exhaustion crashes during forecast display
- Flattened nested try/except blocks (3 levels → 1 level)
- Established CircuitPython stack limits through testing
- 52% stack headroom available for future features
- Documented safe coding patterns for CircuitPython

### 2.0.0
- Stable 25+ hour uptime in normal cycles
- Dual matrix support with device-specific configs
- Segmented schedule displays (up to 2 hours)
- Smart forecast column selection
- Defensive error handling and recovery
- Memory monitoring and optimization
- API budget tracking with preventive restart

### Known Limitations
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
