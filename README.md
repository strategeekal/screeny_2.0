# Pantallita 2.5.0

A dual RGB matrix weather display system running on MatrixPortal S3, showing real-time weather, forecasts, stock prices with intraday charts, CTA transit arrivals, events, and scheduled activities for family use. Features built-in button control for easy stop/exit.

## Overview

Pantallita displays weather information, 12-hour forecasts, stock market data, CTA transit arrival times, family events (birthdays, special occasions), and scheduled activities (morning/evening routines) on two 64×32 RGB LED matrices. The system runs continuously with automatic daily restarts, defensive error handling, and smart caching to manage CircuitPython's memory and socket constraints.

## Hardware

- **Controller:** Adafruit MatrixPortal S3 (ESP32-S3, 8MB flash, 2MB SRAM)
- **Displays:** 2× RGB LED matrices (64×32 pixels, 4-bit color depth)
- **RTC:** DS3231 real-time clock module
- **Buttons:** 2× built-in buttons on MatrixPortal S3 (UP/DOWN)
- **Power:** 5V power supply
- **Firmware:** Adafruit CircuitPython 9.2.8

## Software Stack

- **Language:** CircuitPython 9.2.8
- **APIs:**
  - AccuWeather API (current conditions & 12-hour forecast)
  - Twelve Data API (real-time stock prices)
  - CTA Transit APIs (Train Tracker & Bus Tracker for real-time arrivals)
  - GitHub raw content (remote events/schedules/stocks)
- **Libraries:**
  - `adafruit_requests` - HTTP client
  - `adafruit_ntp` - Time synchronization
  - `adafruit_ds3231` - RTC module
  - `digitalio` - Built-in button control (GPIO)
  - `adafruit_imageload` - BMP image loading
  - `adafruit_bitmap_font` - Text rendering
  - `adafruit_display_shapes` - Line shapes for chart rendering
  - `displayio` / `rgbmatrix` - Display control

## Project Structure

```
screeny_2.0/
├── code.py                    # Main program (~6200 lines)
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

**Twelve Data Usage Pattern (Multi-Stock Rotation Mode):**
- Stocks: 4 symbols per rotation (3 displayed + 1 buffer) during market hours (9:30 AM - 4:00 PM ET)
- Market hours: 6.5 hours/day, weekdays only
- Calls: ~16 calls/hour × 6.5 hours = ~104 calls/day
- After-hours: Uses cached data (1.5 hour grace period, 4:00 PM - 5:30 PM ET)
- Holidays: 1 call to detect, then cached for day (~770 calls/year saved)
- Weekends: No API calls (default), or always-on for testing
- Rate limiting: 65-second minimum between fetches
- **Total:** ~112 calls/day (14% of budget, includes grace period + buffer)

**Twelve Data Usage Pattern (Single Stock Chart Mode - NEW in 2.2.0):**
- Intraday chart: 1 time_series call every 15 minutes during market hours
- Market hours: 6.5 hours/day = 390 minutes
- Time series calls: 390 ÷ 15 = ~26 calls/day
- Quote calls: 1 per chart display (every 5 min) = ~78 calls/day
- 15-minute cache prevents redundant time_series fetches
- **Total:** ~52 calls/day (6.5% of budget) with caching
- **Without cache:** ~104 calls/day (13% of budget)
- More efficient than multi-stock rotation for single ticker monitoring

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
# Format: symbol,name,type,display_name,highlight
CRM,Salesforce,stock,,1
AAPL,Apple,stock,,0
USDMXN,USD to Mexican Peso,forex,MXN,0
BTC/USD,Bitcoin,crypto,BTC,0
GC=F,Gold Futures,commodity,GLD,0
```

**Fields:**
- `symbol`: Ticker, forex pair, crypto, or commodity symbol (required)
- `name`: Full name for reference/web app (required)
- `type`: "stock", "forex", "crypto", or "commodity" (optional, default: stock)
- `display_name`: Short name for 64×32 display (optional, default: symbol)
- `highlight`: 0 or 1 to show as chart (optional, default: 0)

**Display Behavior:**
- **highlight=1:** Shows as full-screen intraday chart
- **highlight=0:** Shows in multi-stock rotation (3 at a time)
- **Stocks:** Show percentage change with colored triangle arrows
- **Forex/Crypto/Commodities:** Show price with colored $ indicator
- Prices >= $1000: Comma separators, no cents (e.g., 86,932)
- Prices < $1000: Show 2 decimals (e.g., 18.49)
- Smart rotation: Charts when offset lands on highlighted stock, multi-stock otherwise
- Supports unlimited tickers (no hard limit)
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

### Stock, Forex, Crypto & Commodity Display
- Real-time prices from Twelve Data API
- **Two Display Modes:**
  - **Multi-Stock Rotation:** Displays 3 items at a time with automatic rotation
  - **Single Stock Chart:** Full-screen view with intraday price chart
- **Multiple Asset Types:**
  - **Stocks:** Triangle arrows (▲▼) + ticker + percentage change
  - **Forex:** $ indicator + ticker + exchange rate (e.g., "$ MXN 18.49")
  - **Crypto:** $ indicator + ticker + price with comma separator (e.g., "$ BTC 86,932")
  - **Commodities:** $ indicator + ticker + price with comma separator (e.g., "$ GLD 2,341")
- **Smart Price Formatting:**
  - Prices >= $1000: No cents, comma separators (86,932)
  - Prices < $1000: Show cents (18.49)
- **Color-coded:** Green for gains, Red for losses (all types)
- **Single Stock Chart Display (NEW in 2.2.0, Enhanced in 2.4.0):**
  - **Full-screen intraday chart** showing price movement throughout trading day
  - **Layout:**
    - Row 1: Display name + daily percentage change (color-coded)
    - Row 2: Current price with smart formatting ($1,234 or $226.82)
    - Chart area: 16-pixel tall line graph (64 pixels wide)
  - **Progressive Chart Loading (NEW in 2.4.0):**
    - **5-minute intervals:** 1-78 data points (vs previous 15-min/26 points)
    - **During market hours:** Chart fills progressively as day advances
      - First point: Market open price (9:30 AM ET)
      - Last point: Market close (4:00 PM ET) = 78 intervals (6.5 hours × 12/hour)
      - Updates every 5 minutes with new data point
      - Visual feedback shows how much trading day remains
    - **Outside market hours:** Full 78-point chart for complete visualization
    - **Smart caching:** Remembers each stock's chart data outside market hours
  - **Accurate percentage:** Uses actual market open price (9:30 AM) from quote API
  - **Smart caching:** 15-minute cache reduces API usage during market hours
  - **Efficient API usage:** Single time_series call per 15 minutes
  - **Visual feedback:** Line graph scales automatically to price range
  - **Smart Rotation:** Control via `highlight` column in stocks.csv
    - `highlight=1`: Shows as full-screen chart
    - `highlight=0`: Shows in multi-stock rotation
    - Rotation automatically switches between chart and multi-stock modes
    - Chart advances by 1, multi-stock advances by 3
  - **API Tracking:** Stock API calls tracked separately (Total X/800)
  - **Cache Indicators:** Logs show "(cached)" or "(fresh)" status
- **Resilient 4-Ticker Buffer (Multi-Stock Mode):**
  - Fetches 4 items but displays 3 (protects against invalid tickers)
  - Progressive degradation: Shows 3→2→skip based on API successes
  - Logs warnings for failed tickers (e.g., typos like "IBT" instead of "IBIT")
  - Never crashes from bad ticker symbols
  - Proper rotation with buffer overlap (no skipped tickers)
- **Market Hours Aware (Enhanced in 2.4.0):**
  - **During market hours (9:30 AM - 4:00 PM ET, weekdays):**
    - Fetches fresh data every cycle (with rate limiting)
    - Progressive chart updates every 5 minutes
  - **Outside market hours (weekends, before/after close):**
    - Uses cached data if available
    - Fetches once per stock/batch to create cache if none exists
    - Displays full 78-point chart for complete visualization
  - **Smart caching per rotation batch:**
    - Multi-stock mode: Each batch of 3-4 stocks cached independently
    - Single stock chart: Each ticker cached separately
    - Enables smooth rotation through all stocks on weekends
  - **Timezone handling:** Automatically converts user's timezone to Eastern Time
  - **Configurable:** `stocks_respect_market_hours` toggle (1=prod, 0=testing)
  - Logs market status (e.g., "Outside market hours with no cache - fetching once")
  - Falls back to clock display when stocks unavailable
- **Flexible Configuration:**
  - Unlimited tickers supported (no hard limit)
  - Custom display names for long tickers (USDMXN → MXN)
  - Type-specific display behavior (stock/forex/crypto/commodity)
  - Rate-limited to respect API limits (65s minimum between fetches)
  - Works with both local CSV and remote GitHub configuration
  - Automatic timezone conversion (works from any US timezone)

### Built-in Button Control (NEW in 2.3.0)

The **MatrixPortal S3's built-in buttons** provide simple, hardware-integrated control for stopping the program.

**Hardware:**
- **UP Button:** Physical button on the side of MatrixPortal S3
- **DOWN Button:** Physical button on the side of MatrixPortal S3 (reserved for future use)
- **No additional hardware required** - buttons are built into the controller
- **Direct GPIO access** - simple, lightweight implementation

**Button Functions:**
- **UP Button (Stop):** Press to immediately stop the program
  - Raises `KeyboardInterrupt` for clean shutdown
  - Exits gracefully with memory report
  - Equivalent to ctrl+c
  - Checked once per display cycle (minimal overhead)

- **DOWN Button:** Reserved for future manual display advance feature

**Implementation:**
- Uses built-in `digitalio` library (no external dependencies)
- Simple GPIO reading with pull-up resistors
- Button check in main loop only (not in hot path)
- Graceful degradation if buttons unavailable
- Zero pystack impact - no nested functions or complex logic

**Setup:**
- Auto-initialized during system startup
- Logs "MatrixPortal buttons initialized - UP=stop, DOWN=advance" if successful
- No configuration required
- Works immediately after deployment

**Advantages:**
- ✅ No extra hardware needed
- ✅ No library dependencies beyond built-in
- ✅ Simple implementation (~40 lines of code)
- ✅ Zero stack depth issues
- ✅ Fast response time

### CTA Transit Display (NEW in 2.4.0)

Real-time CTA (Chicago Transit Authority) train and bus arrival tracking for morning commute.

**Display Features:**
- Shows **3 arrivals at a time** (trains + buses combined, sorted by time)
- **Visual Indicators:**
  - **Trains:** Colored circles (🔴 Red line, 🟤 Brown line, 🟣 Purple line)
  - **Buses:** White squares (⬜ for bus routes)
- **Layout:** Route name on left, arrival time on right
- **Time Format:** "DUE", "1 min", or "X min"
- Automatically sorts all arrivals by time (earliest first)

**Configured Stations:**
- **Diversey Station (40530):** Brown & Purple lines to Loop
- **Fullerton Station (41220):** Red line southbound
- **Halsted & Wrightwood Stop (1446):** 8 bus southbound

**API Integration:**
- **Train Tracker API:** Fetches train arrivals with route colors
- **Bus Tracker API:** Fetches bus predictions
- Single `CTA_API_KEY` for both APIs (from settings.toml)
- **60-second caching** to minimize API calls
- Calculates arrival times in minutes from prediction data

**Smart Display Control:**
- **Commute Hours Only (default):** Shows 9-11 AM only
- **Configurable Toggle:** `transit_respect_commute_hours` (1=commute only, 0=all day)
- **Display Frequency:** `transit_display_frequency=3` (shows every 3rd cycle)
- **Smart Frequency:** Always shows if only display enabled (prevents clock fallback)
- Works with display rotation system

**Configuration:**
```csv
# In display_config.csv
show_transit,transit_display_frequency,transit_respect_commute_hours
1,3,1
```

**API Setup:**
1. Get free CTA API key from: https://www.transitchicago.com/developers/
2. Add to `settings.toml`: `CTA_API_KEY = "your-key-here"`
3. Enable in `display_config.csv`: `show_transit=1`

**How It Works:**
- Fetches arrivals from all configured stations/stops
- Combines trains and buses into single list
- Sorts by arrival time (earliest first)
- Shows top 3 arrivals with route colors
- Respects commute hours (if enabled)
- Caches for 60 seconds to reduce API usage
- Integrates seamlessly with other displays

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

### Current Structure: Monolithic (5538 lines)

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

2. **Enhanced stock displays**
   - **Command center:** Hybrid view showing time, compact weather, and horizontally scrolling stock ticker
   - **Volume indicators:** Show trading volume alongside price
   - **High/Low indicators:** Show daily high/low on chart view

3. **Sports scores** (World Cup 2026!)
   - Game schedule tracking
   - Live score updates during matches
   - Team logos and match status

4. **News headlines**
   - RSS feed integration
   - Scrolling news ticker
   - Category filtering (tech, sports, finance)

## Version History

### 2.5.0 (Current - December 2025)
- **Progressive 5-Min Interval Charts (Major Feature):**
  - **Granular Intraday Data:**
    - Changed from 15-min to 5-min intervals (3× more granular)
    - Fetches up to 78 data points (full trading day coverage)
    - API returns available data progressively throughout the day
  - **Progressive Chart Fill:**
    - Early morning: Sparse chart with few points (shows market just opened)
    - Mid-day: Partial fill (visual indicator of time elapsed)
    - Market close: Full 78-point chart (complete day coverage)
    - Honest visualization (only shows available data, not interpolated)
  - **Anchored to Market Open:**
    - Chart scaling includes actual market open price
    - Visual chart now matches percentage display
    - Fixes misleading charts where % was negative but chart looked positive
  - **Uniform Sampling:**
    - 78 data points mapped to 64 pixels (1.22 points per pixel)
    - Minimal compression with even distribution
    - Preserves accurate price movement representation
  - **Same API Cost:**
    - 1 API credit regardless of outputsize parameter
    - No additional cost for 3× more data

- **Simplified Market State Logic (Major Refactor):**
  - **Time-Based Logic (Replaces Complex State Transitions):**
    - Weekend: Markets never open → use cache if available (no fetching)
    - Pre-market (before 8:30 AM ET weekdays): Markets never open yet → use cache
    - Market hours (8:30 AM - 4:00 PM ET weekdays): Might be open → let API decide
    - After hours (after 4:00 PM ET weekdays): Market closed → use cache
    - Holidays: No detection logic → API says closed, we use cache
  - **Removed Complex State Tracking:**
    - Eliminated `last_market_state` variable (no more open→closed transitions)
    - Eliminated `market_holiday_date` variable (no more false holiday detection)
    - Eliminated catch-22 bugs where bad state blocked corrections
    - Net reduction: -48 lines of code while adding new features
  - **Visual Cache Indicator:**
    - 4 lilac pixels at top center (x=30-33, y=0) when displaying cached data
    - Uses displayio.Bitmap + TileGrid (proper CircuitPython approach)
    - Shows in both stock rotation and single stock chart modes
    - Clear visual feedback for debugging and testing
  - **Testing Mode Respects Market Hours:**
    - `stocks_respect_market_hours=0` now only affects DISPLAY (not fetching)
    - Testing mode displays stocks anytime but still optimizes API calls
    - Weekend/pre-market: Uses cache instead of fetching every cycle
    - Reduces API usage while maintaining 24/7 display capability
  - **Cache Management:**
    - Per-stock cache checking (supports gradual rotation through 4+ stocks)
    - 15-minute intraday cache during market hours
    - Indefinite cache when market closed (weekend/pre-market/holidays)
    - Empty cache detection after restart (3am or weekends)
  - **Bug Fixes:**
    - Fixed missing `open_price` field in cached stock data
    - Fixed false holiday detection (December 2 cached as holiday)
    - Fixed market hours missing upper bound (was fetching at 10:54 PM ET)
    - Fixed pystack exhausted from complex diagnostic f-strings
    - Fixed pystack exhausted from timezone calculations (simplified to use API)
    - Fixed cache indicator using nonexistent state.matrix attribute
    - Fixed stock chart color/percentage calculations

- **Removed Obsolete Features:**
  - **350 API Call Restart:**
    - Removed MAX_CALLS_BEFORE_RESTART constant
    - Removed should_preventive_restart() method
    - Removed check_preventive_restart() function
    - Removed all function calls and references
    - Updated logging to remove /350 reference (now shows "Total=X")
    - No longer needed for weather API management

- **Transit Display Enhancements:**
  - **Interruptible Sleep:**
    - Transit display now uses `interruptible_sleep()`
    - UP button works to stop board during transit display
    - Consistent behavior across all displays
  - **Two-Column Time Layout:**
    - First arrival time: Right-aligned to column 1 (x=49)
    - Second arrival time: Right-aligned to column 2 (x=63)
    - Removed comma separator (visual spacing sufficient)
    - Cleaner, more readable layout
  - **Code Optimization:**
    - Created `add_transit_times()` helper function
    - Eliminated 36 lines of duplicate code
    - Added Layout constants: `TRANSIT_ICON_X`, `TRANSIT_LABEL_X`, `TRANSIT_START_Y`, `TRANSIT_ROW_HEIGHT`, `TRANSIT_TIME_COL1_END`, `TRANSIT_TIME_COL2_END`

- **Forecast Display Improvements:**
  - **12-Hour Precipitation Analysis:**
    - Extended from 6 to 12 hours of forecast data
    - Smart rain duration logic with 3-hour threshold
    - If raining > 3 hours: Show next hour + when rain stops
    - If raining ≤ 3 hours: Show when stops + hour after
    - If rain never stops in 12h: Show next hour + last available
  - **Color Indicators:**
    - MINT (green): Non-consecutive future hours (visual indicator)
    - DIMMEST_WHITE: Current or consecutive hours
    - If col2 is MINT (non-consecutive), col3 is always MINT (future indicator)
    - Improved readability for time gaps

- **Code Architecture Improvements:**
  - **Layout Constants:**
    - Added `DISPLAY_WIDTH` and `DISPLAY_HEIGHT` (replaced ambiguous `RIGHT_EDGE`)
    - Stock chart constants: `STOCK_ROW1_Y`, `STOCK_ROW2_Y`, `STOCK_CHART_Y_START`, `STOCK_CHART_HEIGHT`
    - Transit constants for all positioning values
    - Removed all magic numbers from display code
  - **Helper Functions:**
    - `add_transit_times()`: Two-column time display
    - Reduced code duplication
    - Improved maintainability
  - **Refactoring:**
    - Consistent use of Layout constants throughout codebase
    - Cleaner code structure without functionality impact
    - No increase in stack depth

### 2.4.0 (November 2025)
- **CTA Transit Display:**
  - **Real-Time Arrival Tracking:**
    - Shows 3 arrivals at a time (trains + buses combined)
    - Sorts all arrivals by time (earliest first)
    - Visual indicators: Colored circles for trains, white squares for buses
    - Time format: "DUE", "1 min", or "X min"
  - **Configured Stations:**
    - Diversey Station (40530): Brown & Purple lines to Loop
    - Fullerton Station (41220): Red line southbound
    - Halsted & Wrightwood Stop (1446): 8 bus southbound
  - **API Integration:**
    - Train Tracker API for train arrivals with route colors
    - Bus Tracker API for bus predictions
    - Single `CTA_API_KEY` for both APIs
    - 60-second caching to minimize API calls
  - **Smart Display Control:**
    - Commute hours filtering (9-11 AM only by default)
    - `transit_respect_commute_hours` toggle (1=commute only, 0=all day)
    - `transit_display_frequency` for rotation control (default: every 3rd cycle)
    - Smart frequency: always shows if only display enabled
  - **Technical Implementation:**
    - `fetch_cta_train_arrivals()`: Train Tracker API integration
    - `fetch_cta_bus_arrivals()`: Bus Tracker API integration
    - `fetch_all_transit_arrivals()`: Combined fetcher with sorting
    - `show_transit_display()`: Display function with Circle and Rect shapes
    - Integrated into `_run_normal_cycle()` with frequency control
  - **Configuration:**
    - `show_transit` toggle (disabled by default)
    - Works with both local and remote display_config.csv
    - Respects commute hours for morning commute use case

### 2.3.0 (November 2025)
- **Built-in Button Control:**
  - **Hardware Integration:**
    - Uses MatrixPortal S3's built-in UP and DOWN buttons
    - No additional hardware required
    - Direct GPIO access via `digitalio` library
    - Auto-detection at startup with graceful degradation
  - **Button Functions:**
    - **UP Button (Stop):** Press to immediately stop program (ctrl+c equivalent)
    - **DOWN Button:** Reserved for future manual display advance feature
  - **Technical Implementation:**
    - `setup_buttons()`: Initialize GPIO pins with pull-up resistors
    - `check_button_stop()`: Simple GPIO read in main loop
    - Button check once per cycle (not in hot path)
    - Raises `KeyboardInterrupt` for clean shutdown
    - ~40 lines of code total
  - **Integration Details:**
    - Checked at start of each display cycle
    - No nested function calls or try/except in hot path
    - Zero pystack impact
    - Graceful degradation if buttons unavailable
    - No library dependencies (digitalio is built-in)
  - **Advantages:**
    - Simple, lightweight implementation
    - Fast response time
    - No I2C communication overhead
    - Works immediately after deployment

### 2.2.0 (November 2025)
- **Single Stock Chart Display:** Full-screen intraday price chart view
  - **Visual Chart Display:**
    - Row 1: Display name + daily percentage change (color-coded green/red)
    - Row 2: Current price with smart formatting ($1,234 or $226.82)
    - Chart area: 16-pixel tall line graph showing price movement
    - 64-pixel wide display utilizes full screen width
  - **Technical Implementation:**
    - `fetch_intraday_time_series()`: Fetches time series data from Twelve Data API
    - `show_single_stock_chart()`: Renders chart with bitmap labels and line shapes
    - Uses `adafruit_display_shapes.line.Line` for chart rendering
    - State caching: `cached_intraday_data` and `last_intraday_fetch_time`
    - Helper functions: `format_price_with_dollar()`, `get_stock_display_name()`
  - **Data & Accuracy:**
    - 26 data points at 15-minute intervals (covers 6.5-hour trading day)
    - Uses actual market open price (9:30 AM) for percentage calculation
    - Prevents incorrect color/percentage when recent trend differs from daily trend
    - Example: Stock down 2% for day but up in last 2 hours correctly shows red/-2%
  - **Caching & Efficiency:**
    - 15-minute cache for time series data
    - Reduces API usage: ~26 calls/day (chart mode) vs ~104 calls/day (multi-stock rotation)
    - Combined with quote API: ~52 calls/day total in chart mode
    - Still well within 800/day free tier limit (6.5% usage)
- **Smart Stock Rotation with Highlight Flag:**
  - **New CSV Format:** Added 5th column `highlight` (0 or 1) to stocks.csv
  - **Intelligent Display Selection:**
    - `get_stock_display_mode()`: Determines chart vs multi-stock based on highlight flag
    - When offset lands on highlighted stock (highlight=1): Show full-screen chart
    - When offset lands on non-highlighted (highlight=0): Show multi-stock rotation
    - Chart mode advances offset by 1, multi-stock advances by 3
  - **Edge Cases Handled:**
    - All highlighted: Shows all as charts
    - None highlighted: Shows all in multi-stock rotation
    - Mixed: Seamlessly switches between modes during rotation
  - **Backward Compatible:** Defaults to 0 if highlight column missing
- **Stock API Call Tracking:**
  - **Separate Counter:** `stock_api_calls` tracked independently from weather
  - **Accurate Counting:** Batch requests count each symbol (4 symbols = 4 credits)
  - **End-of-Cycle Logging:** Shows "Total=X/350, Current=Y, Forecast=Z, Stocks=W/800"
  - **Verbose Logging:** Individual API calls show running total
  - **Budget Monitoring:** Helps stay within 800 calls/day free tier limit
- **Cache Status Indicators:**
  - **Chart Logs:** "Chart: CRM -0.13% ($226.82) with 26 data points (cached)"
  - **Multi-Stock Logs:** "Stocks (3/4): AAPL +2.3%, MSFT +1.5% (fresh)"
  - **Transparency:** Users can see when data is from cache vs fresh API call
- **Code Optimization & Refactoring:**
  - **Extracted Helper Functions:**
    - `format_price_with_dollar()`: Price formatting with $ prefix and commas
    - `get_stock_display_name()`: Display name lookup from stocks.csv
  - **Simplified Logic:** Reduced `get_stock_display_mode()` from 39 to 32 lines
  - **Improved Maintainability:** DRY principle, better separation of concerns
  - **No Functional Changes:** Pure refactoring for code quality
- **Bug Fixes & Improvements:**
  - Fixed CSV config parser to auto-convert numeric values to integers
  - Fixed `stocks_display_frequency` type error (string vs int in modulo operation)
  - Fixed color key names (uppercase: GREEN, RED, WHITE)
  - Fixed label rendering (bitmap_label with font, state.main_group)
  - Fixed percentage calculation to use actual day open price from quote API
  - Uses display_name from stocks.csv in chart view
  - Smart price formatting (commas for >= $1000)

### 2.1.0
- **Multi-Asset Market Data Integration:** Real-time prices for stocks, forex, crypto, and commodities
  - **Supports 4 Asset Types:**
    - **Stocks:** Triangle arrows (▲▼) + percentage change
    - **Forex:** $ indicator + exchange rate (e.g., USDMXN → MXN)
    - **Crypto:** $ indicator + price with comma formatting (e.g., BTC → 86,932)
    - **Commodities:** $ indicator + price (e.g., Gold, Oil, Silver)
  - **Smart Price Formatting:**
    - Prices >= $1000: Comma separators, no cents (86,932)
    - Prices < $1000: Show 2 decimals (18.49)
    - Optimized for 64×32 pixel display constraints
  - **Flexible CSV Format:** `symbol,name,type,display_name`
    - Custom display names for long tickers
    - Type-specific rendering (stock/forex/crypto/commodity)
    - Backward compatible with old format
  - Displays 3 items at a time with automatic rotation
  - **Triangle Arrow Indicators:** Visual up ▲ / down ▼ arrows (5×4px) for stocks
  - Color-coded: Green for gains, Red for losses (all asset types)
  - **4-Ticker Buffer System:** Fetches 4 items but displays 3 for resilience
    - Progressive degradation: 3/4 or 4/4 → show 3, 2/4 → show 2, <2 → skip
    - Handles invalid tickers gracefully (no crashes)
    - Clear warning logs for failed symbols (e.g., "IBT" typo)
    - Proper rotation with buffer overlap (no skipped tickers)
    - API cost: ~112 calls/day (14% of 800/day limit)
  - **Market Hours Awareness:** Only fetches during US market hours (9:30 AM - 4:00 PM ET, weekdays)
  - Shows cached data for 1.5 hours after close (until 5:30 PM ET)
  - **Configurable Market Hours Toggle:** `stocks_respect_market_hours` in display_config.csv
    - Set to 1 (default): Respects market hours, skips weekends/holidays
    - Set to 0 (testing): Always displays regardless of time/day
    - Allows weekend testing of display and visual elements
  - **Automatic Holiday Detection:** Detects market holidays via API (no extra cost)
    - Caches holiday status for entire day after first detection
    - Saves ~770 API calls/year on 10 market holidays
    - Skips display on Thanksgiving, Christmas, MLK Day, etc.
    - Respects market hours toggle when holiday detected
  - **Enhanced Startup Messages:** Context-aware market status at boot
    - "markets closed - weekend" (Saturday/Sunday)
    - "markets closed - holiday" (detected holidays)
    - "markets open 9:30 AM ET" (early morning weekdays)
    - "markets closed today" (after grace period)
  - Logs market status (e.g., "markets closed, displaying cached data")
  - Automatic timezone conversion from user's local time to Eastern Time
  - Falls back to clock display when data unavailable
  - Rate-limited API calls (65s minimum between fetches)
  - **Supports unlimited tickers** via local CSV or remote GitHub configuration
  - Smart rotation leverages natural display cycle timing
  - Added `stocks.csv` for local ticker symbols
  - Added `fetch_stock_prices()` with batch request support
  - Added `show_stocks_display()` with 3-row vertical layout and caching
  - Added `is_market_hours_or_cache_valid()` for market hours detection
  - Added `format_price_with_suffix()` for smart price formatting
  - Integration with display rotation cycle

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
