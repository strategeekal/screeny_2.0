# Complete List of Tracking Call Sites

This document maps every location where success/failure tracking occurs for use during refactoring.

## State Variable Initialization

**File:** `/home/user/screeny_2.0/code.py`  
**Class:** `WeatherDisplayState`  
**Lines:** 782-843

```python
Line 791:  self.api_call_count = 0
Line 792:  self.current_api_calls = 0
Line 793:  self.forecast_api_calls = 0
Line 794:  self.consecutive_failures = 0
Line 795:  self.last_successful_weather = 0
Line 819:  self.wifi_reconnect_attempts = 0
Line 820:  self.last_wifi_attempt = 0
Line 821:  self.system_error_count = 0
Line 823:  self.in_extended_failure_mode = False
Line 824:  self.scheduled_display_error_count = 0
Line 825:  self.has_permanent_error = False
Line 828:  self.http_requests_total = 0
Line 829:  self.http_requests_success = 0
Line 830:  self.http_requests_failed = 0
Line 831:  self.session_cleanup_count = 0
Line 834:  self.ephemeral_event_count = 0
Line 835:  self.permanent_event_count = 0
Line 836:  self.total_event_count = 0
```

---

## Tracking Functions

### track_api_call_success() - API Success Tracking
**Lines:** 1507-1515
```python
def track_api_call_success(call_type):
    """Track successful API call"""
    if call_type == "current":
        state.current_api_calls += 1
    elif call_type == "forecast":
        state.forecast_api_calls += 1
    state.api_call_count += 1
    log_debug(f"API Stats: Total={state.api_call_count}...")
```

**Call Sites:**
- Line 1605: `track_api_call_success("current")` after successful current weather fetch
- Line 1658: `track_api_call_success("forecast")` after successful forecast fetch

### handle_weather_success() - Reset All Failure Counters
**Lines:** 1517-1527
```python
def handle_weather_success():
    """Handle successful weather fetch"""
    if state.in_extended_failure_mode:
        recovery_time = int((time.monotonic() - state.last_successful_weather) / System.SECONDS_PER_MINUTE)
        log_info(f"Weather API recovered after {recovery_time} minutes of failures")
    
    state.consecutive_failures = 0
    state.last_successful_weather = time.monotonic()
    state.wifi_reconnect_attempts = 0
    state.system_error_count = 0
```

**Call Sites:**
- Line 1615: After successful current weather fetch
- Line 1665: After successful forecast fetch

### handle_weather_failure() - Increment Failure Counters & Trigger Resets
**Lines:** 1529-1556
```python
def handle_weather_failure():
    """Handle failed weather fetch"""
    state.consecutive_failures += 1
    state.system_error_count += 1
    log_warning(f"Consecutive failures: {state.consecutive_failures}, System errors: {state.system_error_count}")
    
    # Soft reset threshold
    if state.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD:
        log_warning("Soft reset: clearing network session")
        cleanup_global_session()
        state.consecutive_failures = 0
        was_in_extended_mode = state.in_extended_failure_mode
        state.in_extended_failure_mode = True
        log_info("Cooling down for 30 seconds...")
        show_clock_display(state.rtc_instance, 30)
        state.in_extended_failure_mode = was_in_extended_mode
    
    # Hard reset threshold
    if state.system_error_count >= Recovery.HARD_RESET_THRESHOLD:
        log_error(f"Hard reset after {state.system_error_count} system errors")
        supervisor.reload()
```

**Call Sites:**
- Line 1593: After failed current weather fetch
- Line 1624: Exception in current weather fetch
- Line 1630: Timeout in current weather fetch
- Line 1646: Exception in forecast fetch
- Line 1670: Exception in forecast fetch
- Line 1675: Timeout in forecast fetch
- Line 1681: Exception in forecast fetch

---

## Network Error Handling

### _handle_network_error() - Categorize Network Errors
**Lines:** 1311-1337
```python
def _handle_network_error(error, context, attempt, max_retries):
    """Helper: Handle network errors"""
    error_msg = str(error)
    
    if "pystack exhausted" in error_msg.lower():
        log_error(f"{context}: Stack exhausted - forcing cleanup")
    elif "already connected" in error_msg.lower():
        log_error(f"{context}: Socket stuck - forcing cleanup")
    elif "ETIMEDOUT" in error_msg or "104" in error_msg or "32" in error_msg:
        log_warning(f"{context}: Network timeout on attempt {attempt + 1}")
    else:
        log_warning(f"{context}: Network error on attempt {attempt + 1}: {error_msg}")
    
    # Cleanup for critical errors
    if "pystack exhausted" in error_msg.lower() or "already connected" in error_msg.lower():
        cleanup_global_session()
        cleanup_sockets()
        gc.collect()
        time.sleep(2)
    
    # Retry delay
    if attempt < max_retries:
        delay = API.RETRY_BASE_DELAY * (2 ** attempt)
        log_verbose(f"Retrying in {delay}s...")
        time.sleep(delay)
```

**Call Sites:**
- Line 1401: Exception handler in `fetch_weather_with_retries()`

### _process_response_status() - Classify HTTP Responses
**Lines:** 1339-1373
```python
def _process_response_status(response, context):
    """Helper: Process HTTP response status"""
    status = response.status_code
    
    if status == API.HTTP_OK:
        log_verbose(f"{context}: Success")
        return response.json()
    
    # Permanent errors
    permanent_errors = {
        API.HTTP_UNAUTHORIZED: "Unauthorized (401)",
        API.HTTP_NOT_FOUND: "Not found (404)",
        API.HTTP_BAD_REQUEST: "Bad request (400)",
        API.HTTP_FORBIDDEN: "Forbidden (403)"
    }
    
    if status in permanent_errors:
        log_error(f"{context}: {permanent_errors[status]}")
        state.has_permanent_error = True
        return None
    
    # Retryable errors
    if status == API.HTTP_SERVICE_UNAVAILABLE:
        log_warning(f"{context}: Service unavailable (503)")
        return False
    elif status == API.HTTP_INTERNAL_SERVER_ERROR:
        log_warning(f"{context}: Server error (500)")
        return False
    elif status == API.HTTP_TOO_MANY_REQUESTS:
        log_warning(f"{context}: Rate limited (429)")
        return False
    else:
        log_error(f"{context}: HTTP {status}")
        return False
```

**Call Sites:**
- Line 1414: In `fetch_weather_with_retries()` response processing

---

## HTTP Request Tracking

### fetch_weather_with_retries() - Main Retry Loop with Counters
**Lines:** 1375-1449

**Counter Increments:**
- Line 1398: `state.http_requests_total += 1` (all attempts)
- Line 1402: `state.http_requests_failed += 1` (on exception)
- Line 1418: `state.http_requests_success += 1` (on 200 response)

**Status Handling:**
- Lines 1427-1440: Rate limiting (429) with 3x delay
- Lines 1433-1440: Standard exponential backoff for retryable errors

---

## Error State & UI Management

### get_current_error_state() - Determine System State
**Lines:** 1742-1777

```python
def get_current_error_state():
    """Determine current error state based on system status"""
    if state.startup_time == 0:
        return None
    
    if state.in_extended_failure_mode:
        return "extended"  # PURPLE
    
    if hasattr(state, 'has_permanent_error') and state.has_permanent_error:
        return "general"  # WHITE
    
    if not is_wifi_connected():
        return "wifi"  # RED
    
    if state.scheduled_display_error_count >= 3:
        return "general"  # WHITE
    
    time_since_success = time.monotonic() - state.last_successful_weather
    if state.last_successful_weather > 0 and time_since_success > 600:
        return "weather"  # YELLOW
    
    if state.consecutive_failures >= 3:
        return "weather"  # YELLOW
    
    return None  # MINT
```

**Call Sites:**
- Used throughout display functions to determine UI error indicator color

---

## Extended Failure Mode

### handle_extended_failure_mode() - Degraded UI & Recovery
**Lines:** 3942-3960

```python
def handle_extended_failure_mode(rtc, time_since_success):
    """Handle extended failure mode"""
    if not state.in_extended_failure_mode:
        log_warning(f"ENTERING extended failure mode after {int(time_since_success/System.SECONDS_PER_MINUTE)} min")
        state.in_extended_failure_mode = True
    
    log_debug(f"Extended failure mode active ({int(time_since_success/System.SECONDS_PER_MINUTE)}min since success)")
    show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
    
    # Every ~30 minutes attempt recovery
    if int(time_since_success) % Timing.API_RECOVERY_RETRY_INTERVAL < Timing.DEFAULT_CYCLE:
        log_verbose("Attempting API recovery...")
        current_data, forecast_data = fetch_current_and_forecast_weather()
        if current_data:
            log_info("API recovery successful!")
            return True
    
    return False
```

**Call Sites:**
- Line 4028: In `_check_failure_mode()` when in failure mode

### Extended Failure Entry/Exit
**Entry:**
- Line 3947: `state.in_extended_failure_mode = True` in `handle_extended_failure_mode()`
- Line 1543: `state.in_extended_failure_mode = True` in `handle_weather_failure()` soft reset

**Exit:**
- Line 4024: `state.in_extended_failure_mode = False` in `_check_failure_mode()`
- Line 1550: `state.in_extended_failure_mode = was_in_extended_mode` (restore state)

**Checks:**
- Line 1520: `if state.in_extended_failure_mode:` (log recovery message)
- Line 1751: `if state.in_extended_failure_mode:` (error state)
- Line 3945: `if not state.in_extended_failure_mode:` (entry logging)
- Line 4022: `if not in_failure_mode and state.in_extended_failure_mode:` (exit)

---

## Scheduled Display Error Tracking

### Schedule Image Loading
**Lines:** 3620-3632

```python
try:
    bitmap, palette = load_bmp_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
    schedule_img = displayio.TileGrid(bitmap, pixel_shader=palette)
    state.main_group.append(schedule_img)
    state.scheduled_display_error_count = 0  # Reset on success
except Exception as e:
    log_warning(f"Failed to load schedule image")
    state.scheduled_display_error_count += 1
    if state.scheduled_display_error_count >= 3:
        log_error(f"Too many schedule errors, disabling schedules")
        display_config.show_scheduled_displays = False
    return
```

**Additional References:**
- Line 3625: Reset on success
- Line 3628: Increment on failure
- Line 3629: Check threshold (3)
- Line 1763: Check in `get_current_error_state()`

---

## Display Loop Error Handling

### Main Display Cycle Exception Handler
**Lines:** 4220-4248

```python
cycle_count = 0
while True:
    try:
        cycle_count += 1
        log_info(f"## CYCLE {cycle_count} ##")
        run_display_cycle(rtc, cycle_count)
        
    except Exception as e:
        log_error(f"Display loop error: {e}")
        state.memory_monitor.check_memory("display_loop_error")
        
        # Add delay based on consecutive failures
        state.consecutive_failures += 1
        
        if state.consecutive_failures >= 3:
            log_error(f"Multiple consecutive failures ({state.consecutive_failures})")
            interruptible_sleep(30)
        else:
            interruptible_sleep(Timing.SLEEP_BETWEEN_ERRORS)
```

**Notable:**
- Line 4232: Increments `consecutive_failures` (also used for soft reset logic)
- Line 4234: Checks threshold (3)

---

## Cycle Completion Logging

### Weather Display Cycle Logging
**Lines:** 4078-4140

```python
# Line 4080 (SCHEDULED)
log_info(f"Cycle #{cycle_count} (SCHEDULED) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | API: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}")

# Line 4140 (NORMAL)
log_info(f"Cycle #{cycle_count} complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | Mem: {mem_stats['usage_percent']:.1f}% | API: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}")
```

---

## Cache Statistics

### Image Cache Tracking
**Lines:** 620-658

```python
class ImageCache:
    def __init__(self, max_size=10):
        self.cache = {}
        self.max_size = max_size
        self.hit_count = 0       # Line 623
        self.miss_count = 0      # Line 624
    
    def get_image(self, filepath):
        if filepath in self.cache:
            self.hit_count += 1  # Line 628
            return self.cache[filepath]
        
        try:
            self.miss_count += 1  # Line 634
            # ... load image ...
            return bitmap, palette
    
    def get_stats(self):
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        return f"Cache: {len(self.cache)} items, {hit_rate:.1f}% hit rate"
```

### Text Width Cache Tracking
**Lines:** 660-695

```python
class TextWidthCache:
    def __init__(self, max_size=50):
        self.cache = {}
        self.max_size = max_size
        self.hit_count = 0       # Line 664
        self.miss_count = 0      # Line 665
    
    def get_text_width(self, text, font):
        cache_key = (text, id(font))
        
        if cache_key in self.cache:
            self.hit_count += 1   # Line 674
            return self.cache[cache_key]
        
        # Calculate width
        self.miss_count += 1      # Line 682
        self.cache[cache_key] = width
        return width
    
    def get_stats(self):
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        return f"Text cache: {len(self.cache)} items, {hit_rate:.1f}% hit rate"
```

**Logging Location:**
- Line 4129: `log_debug(state.image_cache.get_stats())` every `Timing.CYCLES_FOR_CACHE_STATS`

---

## Memory Monitoring

### MemoryMonitor Class
**Lines:** 697-777

```python
class MemoryMonitor:
    def __init__(self):
        self.baseline_memory = gc.mem_free()      # Line 699
        self.startup_time = time.monotonic()      # Line 700
        self.peak_usage = 0                       # Line 701
        self.measurements = []                    # Line 702
    
    def check_memory(self, checkpoint_name=""):
        stats = self.get_memory_stats()
        
        if stats["used_bytes"] > self.peak_usage:
            self.peak_usage = stats["used_bytes"]  # Line 733
        
        self.measurements.append({                # Line 735
            "name": checkpoint_name,
            "used_percent": stats["usage_percent"],
            "runtime": runtime
        })
        
        if stats["usage_percent"] > 50:
            log_warning(f"High memory: {stats['usage_percent']:.1f}% at {checkpoint_name}")
```

**Checkpoint Call Sites (20+ locations):**
- Line 1582: `state.memory_monitor.check_memory("current_fetch_start")`
- Line 1620: `state.memory_monitor.check_memory("current_fetch_complete")`
- Line 1629: `state.memory_monitor.check_memory("current_fetch_error")`
- Line 1635: `state.memory_monitor.check_memory("forecast_fetch_start")`
- Line 1664: `state.memory_monitor.check_memory("forecast_data_complete")`
- Line 1680: `state.memory_monitor.check_memory("forecast_fetch_error")`
- Line 2590: `state.memory_monitor.check_memory("weather_display_start")`
- Line 2721: `state.memory_monitor.check_memory(f"weather_display_gc_...")`
- Line 2723: `state.memory_monitor.check_memory(f"weather_display_loop_...")`
- Line 2747: `state.memory_monitor.check_memory("weather_display_complete")`
- Line 2815: `state.memory_monitor.check_memory("event_display_start")`
- Line 2865: `state.memory_monitor.check_memory(f"event_{i+1}_start")`
- Line 2869: `state.memory_monitor.check_memory("event_display_complete")`
- Line 2878: `state.memory_monitor.check_memory("single_event_start")`
- Line 2973: `state.memory_monitor.check_memory(f"event_display_allday_...")`
- Line 2977: `state.memory_monitor.check_memory("single_event_error")`
- Line 2981: `state.memory_monitor.check_memory("single_event_complete")`
- Line 3142: `state.memory_monitor.check_memory("forecast_display_start")`
- Line 3336: `state.memory_monitor.check_memory(f"forecast_display_loop_...")`
- Line 3360: `state.memory_monitor.check_memory(f"forecast_display_gc_...")`
- Line 3362: `state.memory_monitor.check_memory(f"forecast_display_loop_...")`
- Line 3368: `state.memory_monitor.check_memory("forecast_display_error")`
- Line 3372: `state.memory_monitor.check_memory("forecast_display_complete")`
- Line 3849: `state.memory_monitor.check_memory("hardware_init_complete")`
- Line 4229: `state.memory_monitor.check_memory("display_loop_error")`

**Reporting:**
- Line 4242: `state.memory_monitor.log_report()` on KeyboardInterrupt
- Line 4246: `state.memory_monitor.log_report()` on exception
- Line 4252: `state.memory_monitor.log_report()` in finally block

---

## Event Tracking

### Event Count Assignments
**Lines:** 1989-2007

```python
# Line 1989
state.permanent_event_count = permanent_count

# Line 1999
state.ephemeral_event_count = ephemeral_count

# Line 2007
state.total_event_count = sum(len(events) for events in merged.values())
log_debug(f"Events merged: {permanent_count} permanent + {ephemeral_count} ephemeral = {state.total_event_count} total")
```

**UI Display Usage:**
- Line 3917: `f"({state.ephemeral_event_count} imported)"` if event count > 0

---

## API Call Limit Handling

### reset_api_counters()
**Lines:** 845-851

```python
def reset_api_counters(self):
    """Reset API call tracking"""
    old_total = self.api_call_count
    self.api_call_count = 0
    self.current_api_calls = 0
    self.forecast_api_calls = 0
    log_debug(f"API counters reset (was {old_total} total calls)")
```

### API Call Limit Threshold Check
**Lines:** 1560-1561

```python
if state.api_call_count >= API.MAX_CALLS_BEFORE_RESTART:
    log_warning(f"Preventive restart after {state.api_call_count} API calls")
    supervisor.reload()
```

---

## WiFi Reconnection Tracking

### WiFi Reset on Success
**Lines:** 1526

```python
state.wifi_reconnect_attempts = 0  # Reset WiFi counter on success
```

**Increment (during initialization):**
- Part of WiFi connection retry logic (lines 1052-1084)

---

## Session Cleanup Tracking

### Session Cleanup Count
**Lines:** 1286

```python
state.session_cleanup_count += 1  # Track cleanups
```

**Status:**
- Incremented but never read/logged anywhere
- Dead data collection

---

## Exception Handlers Summary

Total of 35 `except Exception as e:` handlers:
- Lines: 647, 917, 1026, 1104, 1201, 1227, 1241, 1267, 1304, 1404, 1627, 1678, 1729, 1737, 1900, 1926, 1975, 1981, 2104, 2148, 2175, 2237, 2289, 2975, 3008, 3111, 3133, 3240, 3366, 3559, 3626, 3714, 3828, 4227, 4244

**Pattern:** All log errors but only:
- Lines 1627, 1678: Log in weather fetch functions
- Line 2976: Log in event display
- Line 3715: Log in schedule display
- Line 4228: Log in main loop with consecutive_failures increment

---

## Summary Table

| Component | Tracking Variables | Init | Increment | Reset | Check | Log |
|-----------|-------------------|------|-----------|-------|-------|-----|
| **API Calls** | 3 vars | 791-793 | 1514-1512 | 848 | 1560 | 1515,4080,4140 |
| **Consecutive Failures** | 1 var | 794 | 1531,4232 | 1524,1539,3662,4054 | 1536,1772,2810,3720,4234 | 1533 |
| **System Errors** | 1 var | 821 | 1532 | 1527 | 1553 | 1533 |
| **Extended Failure** | 1 flag | 823 | 1543,3947 | 1550,4024 | 1520,1751,3945,4022 | 1521,3946,4023 |
| **Permanent Errors** | 1 flag | 825 | 1358 | - | 1755 | 1357 |
| **Schedule Errors** | 1 var | 824 | 3628 | 3625 | 1763,3629 | 3627,3630 |
| **HTTP Requests** | 3 vars | 828-830 | 1398,1402,1418 | - | - | NEVER |
| **Cache** | hit/miss counters | 623,664 | 628,634,674,682 | - | - | 4129(conditional) |
| **Memory** | peak/measurements | 699,702 | 733,735 | - | - | 1745+ (40+) |
| **WiFi** | 1 var | 819 | - | 1526 | - | - |
| **Session Cleanup** | 1 var | 831 | 1286 | - | - | NEVER |
| **Events** | 2 vars | 835-836 | 1989,1999,2007 | - | - | 3917 |

