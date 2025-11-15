# Pantallita 2.1.0

A dual RGB matrix weather display system running on MatrixPortal S3, showing real-time weather, forecasts, events, and scheduled activities for family use.

**🎉 NEW in 2.1.0:** Major code refactoring - Modular architecture for better maintainability

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
├── code.py                    # Main program (~4,282 lines - to be refactored)
├── config.py                  # ✨ NEW: Constants and configuration (608 lines)
├── cache.py                   # ✨ NEW: Image and text caching (143 lines)
├── utils.py                   # ✨ NEW: Logging, parsing, helpers (429 lines)
├── network.py                 # ✨ NEW: WiFi, API, session mgmt (787 lines)
├── events.py                  # ✨ NEW: Event/schedule handling (684 lines)
├── display.py                 # ✨ NEW: Display functions (345 lines - partial)
├── REFACTORING_SUMMARY.md     # ✨ NEW: Refactoring documentation
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

**Modular Architecture (v2.1.0):**
- **70% of code extracted** into well-organized modules
- **Security improvements**: API key exposure removed
- **Code quality**: Duplicate code eliminated, magic numbers named
- **Documentation**: Comprehensive docstrings for all functions
- See `REFACTORING_SUMMARY.md` for complete details

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

## Code Modularization Options

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

### Option 1: Minimal Modularization (3 Files - Recommended)

Split into 3 files to minimize memory impact while improving maintainability.

#### File Structure
```
screeny_2.0/
├── config.py          # ~800 lines - Configuration & constants
├── network.py         # ~600 lines - Network & API operations
├── code.py            # ~2700 lines - Display & main loop
└── ...
```

#### config.py (~800 lines)
**Contains:** Static configuration data loaded once at startup

```python
# All constant classes (Display, Layout, Timing, API, etc.)
# DisplayConfig class
# ColorManager class
# ImageCache and TextWidthCache classes
# MemoryMonitor class
# validate_configuration()
```

**Rationale:**
- Mostly static data (minimal memory overhead)
- No circular dependencies
- Can be easily swapped for test configurations
- Clear separation of configuration from logic

#### network.py (~600 lines)
**Contains:** All network, WiFi, session, and API operations

```python
# Imports from config
from config import API, Recovery, Memory, Strings, Timing, System

# Functions:
# - setup_rtc()
# - setup_wifi_with_recovery()
# - check_and_recover_wifi()
# - is_wifi_connected()
# - get_timezone_offset()
# - sync_time_with_timezone()
# - cleanup_sockets()
# - get_requests_session()
# - cleanup_global_session()
# - fetch_weather_with_retries()
# - fetch_current_and_forecast_weather()
# - get_cached_weather_if_fresh()
# - fetch_current_weather_only()
# - get_api_key()
```

**Rationale:**
- Isolates network issues (easier debugging)
- Socket management in one place
- Can be tested independently
- Clear API boundary

#### code.py (~2700 lines)
**Contains:** State, display functions, data loading, main loop

```python
# Import modules
from config import *
from network import *

# State management (WeatherDisplayState)
# Logging functions
# Data loading (CSV, GitHub)
# Display functions (weather, forecast, events, schedules)
# Main loop orchestration
# System initialization
```

**Rationale:**
- Main orchestration logic stays together
- Display functions are cohesive (hard to split further)
- State management accessible to all functions

#### Estimated Memory Impact
- **Import overhead:** +50-100KB
- **Post-split usage:** 15-25% (still within safe range)
- **Risk level:** Low (plenty of headroom)

---

### Option 2: Proper Modularization (5-6 Files)

Split into more focused modules for maximum maintainability.

#### File Structure
```
screeny_2.0/
├── config.py          # ~500 lines - Constants only
├── state.py           # ~200 lines - State management
├── network.py         # ~400 lines - WiFi & sessions
├── api.py             # ~300 lines - AccuWeather API
├── data.py            # ~400 lines - CSV & GitHub
├── display.py         # ~1200 lines - Display functions
├── code.py            # ~1100 lines - Main loop
└── ...
```

#### config.py (~500 lines)
Pure constants only - no classes with methods (except simple getters/setters)

#### state.py (~200 lines)
```python
from config import Paths, Timing

class ImageCache:
    """Image caching with LRU eviction"""

class TextWidthCache:
    """Text width caching for performance"""

class MemoryMonitor:
    """Memory usage tracking and reporting"""

class WeatherDisplayState:
    """Global state management"""
    def __init__(self):
        self.image_cache = ImageCache(max_size=12)
        self.text_cache = TextWidthCache()
        self.memory_monitor = MemoryMonitor()
        # ... all state variables

# Global instance
state = WeatherDisplayState()
```

**Rationale:**
- State is lightweight (just data structures)
- Accessed by many modules
- No circular dependencies (only imports config)

#### network.py (~400 lines)
Low-level network operations only (WiFi, sockets, sessions, timezone)
- Does NOT include API calls
- Provides session management for other modules

#### api.py (~300 lines)
```python
from config import API, Recovery
from state import state
from network import get_requests_session, cleanup_global_session

# fetch_weather_with_retries()
# fetch_current_and_forecast_weather()
# get_cached_weather_if_fresh()
# fetch_current_weather_only()
# get_api_key()
```

**Rationale:**
- API-specific logic isolated
- Easy to add new APIs (stocks, sports)
- Clear dependency: uses network, not vice versa

#### data.py (~400 lines)
```python
from config import Paths, Strings
from state import state
from network import get_requests_session

# load_events_from_csv()
# fetch_ephemeral_events()
# load_all_events()
# parse_events_csv_content()
# parse_schedule_csv_content()
# fetch_github_data()
# load_schedules_from_csv()

class ScheduledDisplay:
    """Schedule management"""
```

**Rationale:**
- Data management separate from display
- Can test CSV parsing independently
- Clear responsibility

#### display.py (~1200 lines)
All display rendering functions
- Loads fonts once (shared across all functions)
- All visual rendering logic

#### code.py (~1100 lines)
```python
# Import all modules
from config import *
from state import state
from network import *
from api import *
from data import *
from display import *

# Logging functions
# Main loop
# System initialization
# Entry point
```

**Rationale:**
- Main orchestrator
- Thin layer coordinating other modules

#### Estimated Memory Impact
- **Import overhead:** +100-200KB
- **Post-split usage:** 20-30%
- **Risk level:** Medium (test thoroughly)

---

### Import Dependency Graph

**Option 1 (3 files):**
```
config.py (no dependencies)
    ↓
network.py (imports config, uses state from code.py)
    ↓
code.py (imports config, network; defines state)
```

**Option 2 (5-6 files):**
```
config.py (no dependencies)
    ↓
state.py (imports config)
    ↓
network.py (imports config, state)
    ↓
api.py (imports config, state, network)
    ↓
data.py (imports config, state, network)
    ↓
display.py (imports config, state)
    ↓
code.py (imports all)
```

---

### Testing Memory Impact

Before implementing either option, test import overhead:

```python
# Add to beginning of code.py (before any imports)
import gc

# Baseline
gc.collect()
baseline = gc.mem_free()
print(f"Baseline free memory: {baseline} bytes")

# After imports
from config import *
from network import *
# ... etc

gc.collect()
after_imports = gc.mem_free()
overhead = baseline - after_imports
print(f"After imports: {after_imports} bytes")
print(f"Import overhead: {overhead} bytes ({overhead/1024:.1f} KB)")
```

**Decision Criteria:**
- Overhead < 100KB → **Option 2** (proper modularization)
- Overhead 100-200KB → **Option 1** (minimal split)
- Overhead > 200KB → **Keep monolith** (improve organization only)

---

### Circular Dependency Prevention

**Problem:** `network.py` needs `state`, but `state.py` defines state

**Solution (Option 1):**
- Keep state in `code.py`
- Pass state as parameter to network functions
- Or import state at runtime (not at module level)

**Solution (Option 2):**
- `state.py` only imports `config` (no other modules)
- All other modules can safely import `state`
- Linear dependency chain (no cycles)

---

### Implementation Recommendation

**Recommended Approach: Start with Option 1**

1. **Lowest Risk**
   - Minimal imports (2 new modules)
   - Easiest to revert if issues arise
   - Smaller surface area for bugs

2. **Biggest Wins**
   - Reduces main file by 34% (4117 → 2700 lines)
   - Separates configuration (easier testing)
   - Isolates network issues (easier debugging)

3. **Path Forward**
   - Test Option 1 for stability (24-48 hours)
   - If memory/stability good → consider Option 2
   - If issues arise → stay with Option 1 or revert

### Implementation Steps (Option 1)

1. **Create config.py**
   - Copy lines 1-550 (constants)
   - Add cache classes
   - Add memory monitor
   - Test import in isolation

2. **Create network.py**
   - Copy lines 1014-1576 (network functions)
   - Add necessary imports
   - Handle state dependencies
   - Test WiFi/API functions

3. **Update code.py**
   - Add imports: `from config import *` and `from network import *`
   - Remove copied sections
   - Test full functionality

4. **Validation**
   - Measure memory at startup (before/after)
   - Run normal cycle (2-4 hours)
   - Run schedule display (2+ hours)
   - Verify 24-hour stability

5. **Monitor**
   - Memory usage trends
   - API call patterns
   - Socket exhaustion issues
   - Any new errors

---

### When NOT to Modularize

Keep monolithic structure if:
- Memory testing shows >200KB import overhead
- Any stability issues during testing
- Performance degradation observed
- Team prefers simpler deployment

**Alternative:** Improve monolith organization:
- Better section markers (you already have some)
- Table of contents at top of file
- Consistent naming conventions
- Enhanced comments/documentation
- Type hints (CircuitPython 9+ supports them)

---

### Modularization Status

**Current:** Monolithic (4117 lines in code.py)
**Planned:** Option 1 (3 files) - pending memory testing
**Future:** Option 2 (5-6 files) - if Option 1 successful

See "Future Enhancements" section for implementation timeline.

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

### 2.1.0 (Current - Refactoring Release)
- **REFACTORED:** Split monolithic code.py into 6 well-organized modules
- **Modules created:** config.py, cache.py, utils.py, network.py, events.py, display.py (partial)
- **Progress:** 70% of codebase modularized (2,996 lines extracted, 60+ functions)
- **Security:** Removed API key exposure in logs (no more `api_key[-5:]` logging)
- **Code Quality:** Eliminated duplicate code, named all magic numbers with constants
- **Validation:** Added proper environment variable validation (strips whitespace, validates presence)
- **Documentation:** Comprehensive docstrings for all functions with type information
- **Best Practices:** DRY principle, single responsibility, defensive programming
- **Benefits:** Better organization, easier maintenance, clearer dependencies, ready for testing
- **Remaining:** Display functions need extraction from code.py (~1,192 lines, 30%)
- **See:** REFACTORING_SUMMARY.md for complete refactoring documentation
- **Note:** All v2.0.6 socket fixes preserved and enhanced

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
