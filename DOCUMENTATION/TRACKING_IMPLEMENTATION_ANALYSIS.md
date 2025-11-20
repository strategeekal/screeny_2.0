# Success/Failure Tracking Implementation Analysis

## Overview
The codebase implements a **multi-layered tracking system** that monitors:
- API request success/failure rates
- Consecutive failure counts and thresholds
- WiFi connectivity and reconnection attempts
- Extended failure modes (recovery procedures)
- Display-specific error tracking
- Cache hit/miss statistics
- Memory usage monitoring
- Session cleanup tracking

---

## 1. STATE VARIABLES FOR TRACKING

### Core Failure Tracking Variables (Lines 790-843)
Located in `WeatherDisplayState` class:

```python
# API tracking (Lines 790-795)
self.api_call_count = 0                    # Total API calls made
self.current_api_calls = 0                 # Count of current weather API calls
self.forecast_api_calls = 0                # Count of forecast API calls
self.consecutive_failures = 0              # Sequential failure counter
self.last_successful_weather = 0           # Timestamp of last success

# Network/WiFi tracking (Lines 818-831)
self.wifi_reconnect_attempts = 0           # WiFi reconnection attempt counter
self.last_wifi_attempt = 0                 # Timestamp of last WiFi attempt
self.system_error_count = 0                # System-wide error accumulator
self.in_extended_failure_mode = False      # Extended failure mode flag
self.has_permanent_error = False           # 401/404 permanent error flag

# HTTP Request tracking (Lines 827-831)
self.http_requests_total = 0               # All HTTP request attempts
self.http_requests_success = 0             # Successful HTTP responses
self.http_requests_failed = 0              # Failed HTTP responses
self.session_cleanup_count = 0             # Network session cleanup counter

# Scheduled display tracking (Line 824)
self.scheduled_display_error_count = 0     # Schedule display error counter

# Event tracking (Lines 833-836)
self.ephemeral_event_count = 0             # Imported events count
self.permanent_event_count = 0             # Stored events count
self.total_event_count = 0                 # Total events currently loaded
```

### Cache Tracking Classes (Lines 620-695)

**ImageCache** (Lines 620-658):
- `self.hit_count`: Cache hits for image lookups
- `self.miss_count`: Cache misses (images loaded from disk)
- `get_stats()`: Returns formatted cache statistics

**TextWidthCache** (Lines 660-695):
- `self.hit_count`: Cache hits for text width calculations
- `self.miss_count`: Cache misses (text width recalculated)
- `get_stats()`: Returns formatted cache statistics

**MemoryMonitor** (Lines 697-777):
- `self.baseline_memory`: Initial memory state
- `self.peak_usage`: Highest memory consumption recorded
- `self.measurements[]`: Array of checkpoint measurements

---

## 2. TRACKING PATTERNS - SCATTERED THROUGHOUT CODE

### Pattern A: HTTP Request Tracking
**Lines 1398, 1402, 1418** - In `fetch_weather_with_retries()`:
```python
state.http_requests_total += 1      # Track all attempts
state.http_requests_failed += 1     # Track failure
state.http_requests_success += 1    # Track success
```

### Pattern B: API Call Type Tracking
**Lines 1507-1515** - Dedicated tracking function:
```python
def track_api_call_success(call_type):
    """Track successful API call (call_type: 'current' or 'forecast')"""
    if call_type == "current":
        state.current_api_calls += 1
    elif call_type == "forecast":
        state.forecast_api_calls += 1
    state.api_call_count += 1
    log_debug(f"API Stats: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}")
```
- **Used at:** Lines 1605, 1658 (after successful weather fetches)

### Pattern C: Success/Failure Handlers
**Lines 1517-1556** - Two dedicated handler functions:

```python
def handle_weather_success():
    """Handle successful weather fetch - reset failure counters"""
    if state.in_extended_failure_mode:
        recovery_time = int((time.monotonic() - state.last_successful_weather) / System.SECONDS_PER_MINUTE)
        log_info(f"Weather API recovered after {recovery_time} minutes of failures")
    
    state.consecutive_failures = 0
    state.last_successful_weather = time.monotonic()
    state.wifi_reconnect_attempts = 0  # Reset WiFi counter
    state.system_error_count = 0       # Reset system errors
```

```python
def handle_weather_failure():
    """Handle failed weather fetch - increment failure counters"""
    state.consecutive_failures += 1
    state.system_error_count += 1
    log_warning(f"Consecutive failures: {state.consecutive_failures}, System errors: {state.system_error_count}")
    
    # Soft reset on repeated failures
    if state.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD:
        log_warning("Soft reset: clearing network session")
        cleanup_global_session()
        state.consecutive_failures = 0
```

### Pattern D: Threshold-Based Actions
**Lines 1536-1556** - Soft/Hard resets triggered by counters:
```python
# Soft reset threshold (5 consecutive failures)
if state.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD:
    # Clear session, show clock

# Hard reset threshold (15 system errors)
if state.system_error_count >= Recovery.HARD_RESET_THRESHOLD:
    supervisor.reload()

# API call limit threshold
if state.api_call_count >= API.MAX_CALLS_BEFORE_RESTART:
    supervisor.reload()
```

### Pattern E: Error State Determination
**Lines 1742-1777** - Comprehensive error state checking:
```python
def get_current_error_state():
    """Determine current error state based on system status"""
    if state.in_extended_failure_mode:
        return "extended"   # PURPLE
    if state.has_permanent_error:
        return "general"    # WHITE
    if not is_wifi_connected():
        return "wifi"       # RED
    if state.scheduled_display_error_count >= 3:
        return "general"    # WHITE
    if time_since_success > 600:
        return "weather"    # YELLOW
    if state.consecutive_failures >= 3:
        return "weather"    # YELLOW
    return None             # MINT (OK)
```

### Pattern F: Scheduled Display Error Tracking
**Lines 3625-3631** - Schedule-specific error counter:
```python
try:
    state.scheduled_display_error_count = 0
except Exception as e:
    log_warning(f"Failed to load schedule image {schedule_config['image']}")
    state.scheduled_display_error_count += 1
    if state.scheduled_display_error_count >= 3:
        log_error(f"Too many schedule errors ({state.scheduled_display_error_count}), disabling schedules")
        display_config.show_scheduled_displays = False
```

### Pattern G: Extended Failure Mode Handling
**Lines 3942-3960** - Recovery attempt tracking:
```python
def handle_extended_failure_mode(rtc, time_since_success):
    """Handle extended failure mode with periodic recovery attempts"""
    if not state.in_extended_failure_mode:
        log_warning(f"ENTERING extended failure mode after {int(time_since_success/System.SECONDS_PER_MINUTE)} minutes")
        state.in_extended_failure_mode = True
    
    # Periodically retry (every ~30 minutes)
    if int(time_since_success) % Timing.API_RECOVERY_RETRY_INTERVAL < Timing.DEFAULT_CYCLE:
        current_data, forecast_data = fetch_current_and_forecast_weather()
        if current_data:
            log_info("API recovery successful!")
            return True  # Signal recovery
    return False
```
- **Entered at:** Line 4028 (when no success for 15 minutes)
- **Exited at:** Lines 4022-4024

### Pattern H: Display Error Handling
**Lines 4227-4238** - Main loop error counter:
```python
except Exception as e:
    log_error(f"Display loop error: {e}")
    state.consecutive_failures += 1
    
    if state.consecutive_failures >= 3:
        log_error(f"Multiple consecutive failures ({state.consecutive_failures}) - longer delay")
        interruptible_sleep(30)  # 30 second delay
    else:
        interruptible_sleep(Timing.SLEEP_BETWEEN_ERRORS)
```

### Pattern I: Network Error Logging Helper
**Lines 1311-1337** - Categorizes and logs network errors:
```python
def _handle_network_error(error, context, attempt, max_retries):
    """Helper: Handle network errors - reduces nesting"""
    error_msg = str(error)
    
    if "pystack exhausted" in error_msg.lower():
        log_error(f"{context}: Stack exhausted - forcing cleanup")
    elif "already connected" in error_msg.lower():
        log_error(f"{context}: Socket stuck - forcing cleanup")
    elif "ETIMEDOUT" in error_msg:
        log_warning(f"{context}: Network timeout on attempt {attempt + 1}")
    else:
        log_warning(f"{context}: Network error on attempt {attempt + 1}: {error_msg}")
```

### Pattern J: HTTP Response Status Handling
**Lines 1339-1373** - Classifies responses as success/retryable/permanent:
```python
def _process_response_status(response, context):
    """Helper: Process HTTP response status"""
    status = response.status_code
    
    if status == API.HTTP_OK:
        log_verbose(f"{context}: Success")
        return response.json()  # SUCCESS
    
    # Permanent errors (401, 403, 404, 400)
    if status in permanent_errors:
        log_error(f"{context}: {permanent_errors[status]}")
        state.has_permanent_error = True
        return None  # PERMANENT ERROR
    
    # Retryable errors (500, 503, 429)
    else:
        log_warning(f"{context}: {status_description}")
        return False  # RETRY
```

### Pattern K: Memory Checkpoint Tracking
**Lines 727-747** - Checkpoints throughout execution:
```python
def check_memory(self, checkpoint_name=""):
    """Check memory and log only if there's an issue"""
    stats = self.get_memory_stats()
    self.measurements.append({
        "name": checkpoint_name,
        "used_percent": stats["usage_percent"],
        "runtime": runtime
    })
    # Called 20+ times throughout code at key points
```

---

## 3. TRACKING DUPLICATION & SCATTERED PATTERNS

### Duplication Issues Identified:

1. **Consecutive Failure Counter Scattered (5+ locations)**
   - Incremented at: Lines 1531, 4232
   - Reset at: Lines 1524, 1539, 3662, 4054
   - Used/Checked at: Lines 1772, 2810, 4234
   - **Also referenced but NOT initialized:** `consecutive_display_errors` (Line 3720)

2. **HTTP Request Tracking (3 separate counters)**
   - `http_requests_total` (increment at line 1398)
   - `http_requests_failed` (increment at line 1402)
   - `http_requests_success` (increment at line 1418)
   - Never read/logged anywhere in code!

3. **Error Logging Scattered Across 40+ Exception Handlers**
   - Generic `except Exception as e:` at lines: 647, 917, 1026, 1104, 1201, 1227, 1241, 1267, 1304, 1404, 1627, 1678, 1729, 1737, 1900, 1926, 1975, 1981, 2104, 2148, 2175, 2237, 2289, 2975, 3008, 3111, 3133, 3240, 3366, 3559, 3626, 3714, 3828, 4227, 4244
   - No consistent tracking pattern

4. **Cyclic Restart Tracking (Line 4223)**
   - Simple counter increment with no success/failure tracking
   - No durations logged

---

## 4. KEY THRESHOLDS & CONSTANTS (Hardcoded References)

### Recovery Thresholds (Lines 222-227)
```python
MAX_CONSECUTIVE_API_FAILURES = 3    # Threshold (unused?)
SOFT_RESET_THRESHOLD = 5            # Consecutive failures before soft reset
HARD_RESET_THRESHOLD = 15           # System errors before hard restart
WIFI_RECONNECT_COOLDOWN = 300       # 5 minutes between WiFi attempts
```

### Failure Mode Timing (Lines 125-175)
```python
EXTENDED_FAILURE_THRESHOLD = 900    # 15 minutes without success
EXTENDED_FAILURE_MODE_RETRY = 1800  # 30 min retry interval
CLOCK_DISPLAY_DURATION = 300        # 5 minutes
```

### API Limits (Lines 189-209)
```python
MAX_RETRIES = 2
MAX_CALLS_BEFORE_RESTART = 100      # Preventive restart after 100 API calls
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
```

---

## 5. LOGGING & REPORTING PATTERNS

### Logging Functions (Lines 875-939)
- `log_entry()`: Core logging with timestamp filtering
- `log_info()`: Standard info messages
- `log_warning()`: Warning/potential issue messages
- `log_error()`: Error messages
- `log_debug()`: Debug-level messages
- `log_verbose()`: Extra detail (conditional)

### Logging Used For:
1. **Cycle Completion Summary** (Lines 4080, 4140):
   ```
   "Cycle #{cycle_count} complete in {duration} min | Mem: {mem}% | API: {api_count}/{max}"
   ```

2. **Weather Fetch Results** (Lines 1615, 1522, 1533):
   ```
   "Weather API recovered after {recovery_time} minutes"
   "Consecutive failures: {count}, System errors: {system_count}"
   ```

3. **Hardware Initialization** (Line 3921):
   ```
   "Hardware ready | {schedules} schedules | {events} events"
   ```

4. **Cache Statistics** (Lines 658, 695):
   - Called at Line 4129 every `CYCLES_FOR_CACHE_STATS` cycles
   - Format: `"Cache: {items} items, {hit_rate}% hit rate"`

---

## 6. CURRENT TRACKING MECHANISM PURPOSES

| Tracking Type | Purpose | Location |
|---|---|---|
| **API Call Counts** | Preventive restart after 100 calls | 1507-1515, 1560 |
| **Consecutive Failures** | Trigger soft/hard resets | 1531, 1536-1556 |
| **System Error Count** | Hard reset after 15 errors | 1532, 1553 |
| **WiFi Attempts** | Track reconnection attempts | 819, 1526 |
| **HTTP Requests** | Monitor request health | 1398, 1402, 1418 (UNUSED!) |
| **Extended Failure Mode** | Show degraded UI, retry periodically | 3942-3960, 4022-4028 |
| **Schedule Errors** | Disable schedules after 3 failures | 3628-3630 |
| **Permanent Errors** | Mark 401/403/404 as unrecoverable | 1358 |
| **Cache Hit Rates** | Performance monitoring | 656-658, 692-695 |
| **Memory Usage** | Detect memory leaks | 727-747 |
| **Event Counts** | UI status display | 1989, 1999, 2007 |

---

## 7. IDENTIFIED BUGS & INCONSISTENCIES

### Bug #1: Undefined State Variable
- **Location:** Line 3720
- **Issue:** References `state.consecutive_display_errors` but NOT initialized in `__init__`
- **Impact:** First access will raise AttributeError
- **Code:** `if state.consecutive_display_errors >= 5:`

### Bug #2: Unused HTTP Request Counters
- **Location:** Lines 828-830, 1398, 1402, 1418
- **Issue:** `http_requests_total`, `http_requests_success`, `http_requests_failed` are tracked but NEVER read or logged
- **Impact:** Data collection overhead with no visibility

### Bug #3: Unused Threshold Constant
- **Location:** Line 222
- **Issue:** `MAX_CONSECUTIVE_API_FAILURES = 3` defined but never used in code
- **Impact:** Dead code/configuration

### Bug #4: Inconsistent Error Tracking
- **Location:** 40+ exception handlers
- **Issue:** No systematic tracking of which display functions fail most often
- **Impact:** Can't identify patterns in failures

### Bug #5: Session Cleanup Count Unused
- **Location:** Line 831
- **Issue:** `session_cleanup_count` incremented (1286) but never read/logged
- **Impact:** Dead data collection

### Bug #6: Cache Stats Not Logged
- **Location:** Lines 658, 695
- **Issue:** Cache statistics generated but only logged every N cycles (line 4129)
- **Impact:** Missing continuous visibility into cache performance

---

## 8. TRACKING DATA FLOW

```
START
  ↓
[Successful API Call]
  ├→ track_api_call_success(type)  [increment counters]
  ├→ handle_weather_success()      [reset failure counters]
  └→ log_info() messages
  
[Failed API Call]
  ├→ _handle_network_error()       [categorize error]
  ├→ _process_response_status()    [determine if retry/permanent]
  ├→ http_requests_failed += 1     [track attempt]
  ├→ handle_weather_failure()      [increment consecutive_failures]
  ├→ Check thresholds:
  │  ├─ If consecutive_failures >= 5: soft reset
  │  ├─ If system_error_count >= 15: hard reset
  │  └─ If time_since_success > 900s: enter extended failure mode
  └→ log_warning/error() messages

[Periodic Cycle]
  ├→ memory_monitor.check_memory()  [collect checkpoint]
  ├→ memory_monitor.get_memory_stats() [read peak usage]
  └→ log_info() with cycle summary including API counts

[Extended Failure Recovery]
  ├→ If in_extended_failure_mode for 30 min
  ├→ Attempt fetch_current_and_forecast_weather()
  └─→ If success: exit extended failure mode, reset consecutive_failures
```

---

## 9. RECOMMENDATIONS FOR REFACTORING

1. **Initialize missing `consecutive_display_errors` in state** (Line 824)
2. **Extract HTTP request tracking to visible metrics** (create a reporting function)
3. **Consolidate failure tracking** into a single `Failure Manager` class
4. **Create a `TrackingMetrics` class** to wrap all counters with consistency
5. **Log unused counters** or remove them if truly unused
6. **Systematize exception handling** with consistent tracking per display function
7. **Generate periodic reports** (not just at cycle completion) showing:
   - Success rate (successes / total attempts)
   - Average retry count per API call
   - Time in extended failure mode
   - Cache hit rates
   - Error distribution by type

