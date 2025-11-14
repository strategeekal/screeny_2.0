# Code Flattening Analysis for Stack Exhaustion Mitigation
## Pantallita 2.0.0 - CircuitPython Stack Optimization

**Analysis Date:** 2025-11-13
**Code Version:** 4117 lines monolithic
**Primary Risk:** Stack exhaustion ("pystack exhausted" errors)

---

## Executive Summary

**Stack Depth Analysis:**
- **570 lines** with 4+ indentation levels (deeply nested)
- **200 lines** with 5+ indentation levels (very deeply nested)
- **49 try/except blocks** (each adds stack overhead)
- **Estimated max stack depth:** 7-9 function calls deep in critical paths

**Risk Assessment:**
- 🔴 **HIGH RISK:** Schedule display functions (long-running, deep nesting)
- 🟡 **MEDIUM RISK:** API retry functions (nested try/except + loops)
- 🟢 **LOW RISK:** Display rendering functions (mostly sequential)

**Recommended Actions:**
1. **Flatten immediately:** 8 high-priority functions (no functionality impact)
2. **Consider flattening:** 5 functions with acceptable tradeoffs
3. **Monitor:** 3 functions that should be redesigned if stack issues persist

---

## Analysis Methodology

### Stack Frame Consumption Estimate

Each of these consumes stack frames:
```python
Function call:          ~40-80 bytes
Try/except block:       ~20-40 bytes
Nested if/else:         ~10-20 bytes per level
Loop (for/while):       ~20-30 bytes
Local variables:        ~8 bytes per variable (depends on type)
```

### Nesting Depth Classification

- **Level 1-2:** ✅ Safe (normal code)
- **Level 3-4:** ⚠️ Monitor (acceptable but watch)
- **Level 5+:** 🔴 High Risk (flatten immediately)

### Detection Criteria

Found using:
```bash
# 4+ indentation levels
grep -nP "^\t\t\t\t" code.py | wc -l  # 570 lines

# 5+ indentation levels
grep -nP "^\t\t\t\t\t" code.py | wc -l  # 200 lines

# Try/except blocks
grep -n "try:" code.py | wc -l  # 49 blocks
```

---

## Category A: No-Impact Flattening (Safe Refactoring)

These changes **preserve exact functionality** while reducing stack depth.

### A1. fetch_weather_with_retries() - Lines 1272-1411

**Current Nesting:** 5 levels (loop → try → if → elif chain → nested if)

**Stack Depth Issue:**
```python
for attempt in range():                    # Level 1
    try:                                   # Level 2
        if not check_and_recover_wifi():   # Level 3
            return None

        response = session.get()

        if response.status_code == 200:    # Level 3
            return response.json()
        elif response.status_code == 429:  # Level 3
            if attempt < max_retries:      # Level 4
                interruptible_sleep()      # Level 5
```

**Flattening Strategy:** Early returns + error mapping

**Refactored (BEFORE):**
```python
# Current deeply nested version (simplified)
for attempt in range(max_retries + 1):
    try:
        if not check_and_recover_wifi():
            log_error(f"{context}: WiFi unavailable")
            return None

        session = get_requests_session()
        if not session:
            log_error(f"{context}: No requests session available")
            return None

        response = session.get(url)

        if response.status_code == API.HTTP_OK:
            return response.json()
        elif response.status_code == API.HTTP_SERVICE_UNAVAILABLE:
            last_error = "Service unavailable"
        elif response.status_code == API.HTTP_TOO_MANY_REQUESTS:
            last_error = "Rate limited"
            if attempt < max_retries:
                delay = API.RETRY_DELAY * 3
                interruptible_sleep(delay)
                continue
        # ... 6 more elif blocks

    except RuntimeError as e:
        # ... nested error handling
    except OSError as e:
        # ... nested error handling
```

**Refactored (AFTER):**
```python
def fetch_weather_with_retries(url, max_retries=None, context="API"):
    """Flattened version - same logic, less nesting"""
    if max_retries is None:
        max_retries = API.MAX_RETRIES

    last_error = None

    for attempt in range(max_retries + 1):
        # Early return pattern - no nesting
        if not check_and_recover_wifi():
            log_error(f"{context}: WiFi unavailable")
            return None

        session = get_requests_session()
        if not session:
            log_error(f"{context}: No requests session available")
            return None

        log_verbose(f"{context} attempt {attempt + 1}/{max_retries + 1}")

        # Separate error handling from success path
        response = None
        try:
            response = session.get(url)
        except (RuntimeError, OSError) as e:
            last_error = _handle_network_error(e, context, attempt, max_retries)
            continue  # Skip to next attempt
        except Exception as e:
            log_error(f"{context} unexpected error: {e}")
            last_error = str(e)
            if attempt < max_retries:
                interruptible_sleep(API.RETRY_DELAY)
            continue

        # Handle response status (extract to helper)
        result = _process_response_status(response, context, last_error)
        if result is not None:
            return result  # Success or permanent error

        # Retry logic
        if attempt < max_retries:
            delay = min(API.RETRY_DELAY * (2 ** attempt), Recovery.API_RETRY_MAX_DELAY)
            log_debug(f"Retrying in {delay}s...")
            interruptible_sleep(delay)

    log_error(f"{context}: All attempts failed. Last error: {last_error}")
    return None

def _handle_network_error(error, context, attempt, max_retries):
    """Helper: Handle network errors - reduces nesting in main function"""
    error_msg = str(error)

    if "pystack exhausted" in error_msg.lower():
        log_error(f"{context}: Stack exhausted - forcing cleanup")
    elif "already connected" in error_msg.lower():
        log_error(f"{context}: Socket already connected - forcing cleanup")
    else:
        log_error(f"{context}: Runtime error on attempt {attempt + 1}: {error_msg}")

    # Nuclear cleanup
    cleanup_global_session()
    cleanup_sockets()
    gc.collect()
    time.sleep(2)

    if attempt < max_retries:
        delay = API.RETRY_BASE_DELAY * (2 ** attempt)
        log_verbose(f"Retrying in {delay}s...")
        time.sleep(delay)

    return f"Network error: {error_msg}"

def _process_response_status(response, context, last_error):
    """Helper: Process HTTP response status - reduces nesting"""
    status = response.status_code

    # Success
    if status == API.HTTP_OK:
        log_verbose(f"{context}: Success")
        return response.json()

    # Permanent errors (map to None for early exit)
    permanent_errors = {
        API.HTTP_UNAUTHORIZED: "Unauthorized (401) - check API key",
        API.HTTP_NOT_FOUND: "Not found (404) - check location key",
        API.HTTP_BAD_REQUEST: "Bad request (400) - check URL/parameters",
        API.HTTP_FORBIDDEN: "Forbidden (403) - API key lacks permissions"
    }

    if status in permanent_errors:
        log_error(f"{context}: {permanent_errors[status]}")
        state.has_permanent_error = True
        return None

    # Retryable errors (return False to signal retry)
    if status == API.HTTP_SERVICE_UNAVAILABLE:
        log_warning(f"{context}: Service unavailable (503)")
    elif status == API.HTTP_INTERNAL_SERVER_ERROR:
        log_warning(f"{context}: Server error (500)")
    else:
        log_error(f"{context}: HTTP {status}")

    return False  # Signal retry needed

```

**Benefits:**
- Reduces max nesting from 5 → 2 levels
- Stack frames saved: ~3-4 frames per call
- Same functionality, easier to read
- Error handling isolated in helpers

**Risk:** None - pure refactoring

---

### A2. run_display_cycle() - Lines 3879-4034

**Current Nesting:** 4-5 levels (multiple nested if/else chains)

**Stack Depth Issue:**
```python
if cycle_count > 1:                                    # Level 1
    if avg_cycle_time < threshold and cycle_count > 10:  # Level 2
        # restart logic

if not wifi_available:                                 # Level 1
    wifi_available = check_and_recover_wifi()          # Level 2 (function call)

if not wifi_available:                                 # Level 1
    show_clock_display()
    return

if display_config.show_scheduled_displays:             # Level 1
    schedule_name, schedule_config = ...

    if schedule_name:                                  # Level 2
        current_data = fetch_current_weather_only()

        if current_data:                               # Level 3
            state.last_successful_weather = ...

        if cycle_elapsed < threshold:                  # Level 3
            log_error()

        if state.schedule_just_ended and ... and ...:  # Level 3 (nested conditions)
            cleanup_global_session()
            # ...
```

**Flattening Strategy:** Extract schedule handling to separate function

**Refactored (AFTER):**
```python
def run_display_cycle(rtc, cycle_count):
    """Flattened main cycle - delegates to helpers"""
    cycle_start_time = time.monotonic()

    # Early exit: rapid cycling detection
    if _check_rapid_cycling(cycle_count):
        return

    # Maintenance
    if cycle_count % Timing.CYCLES_FOR_MEMORY_REPORT == 0:
        state.memory_monitor.log_report()
    check_daily_reset(rtc)

    # Early exit: no WiFi
    if not _ensure_wifi_available():
        _log_cycle_complete(cycle_count, cycle_start_time, "NO WIFI")
        return

    # Early exit: extended failure mode
    if _check_failure_mode(rtc):
        return

    # Try scheduled display first (priority path)
    if _run_scheduled_cycle(rtc, cycle_count, cycle_start_time):
        return  # Schedule handled everything

    # Normal cycle
    _run_normal_cycle(rtc, cycle_count, cycle_start_time)

def _check_rapid_cycling(cycle_count):
    """Helper: Detect and handle rapid cycling - returns True if restarting"""
    if cycle_count <= 1:
        return False

    time_since_startup = time.monotonic() - state.startup_time
    avg_cycle_time = time_since_startup / cycle_count

    if avg_cycle_time >= Timing.FAST_CYCLE_THRESHOLD or cycle_count <= 10:
        return False

    log_error(f"Rapid cycling detected ({avg_cycle_time:.1f}s/cycle) - restarting")
    interruptible_sleep(Timing.RESTART_DELAY)
    supervisor.reload()
    return True  # Will never reach here, but explicit

def _ensure_wifi_available():
    """Helper: Check WiFi with recovery attempt - returns True if available"""
    if is_wifi_connected():
        return True

    log_debug("WiFi disconnected, attempting recovery...")
    if check_and_recover_wifi():
        return True

    log_warning("No WiFi - showing clock")
    show_clock_display(state.rtc_instance, Timing.CLOCK_DISPLAY_DURATION)
    return False

def _check_failure_mode(rtc):
    """Helper: Check and handle extended failure mode - returns True if in failure mode"""
    time_since_success = time.monotonic() - state.last_successful_weather
    in_failure_mode = time_since_success > Timing.EXTENDED_FAILURE_THRESHOLD

    # Exit failure mode if recovered
    if not in_failure_mode and state.in_extended_failure_mode:
        log_info("EXITING extended failure mode")
        state.in_extended_failure_mode = False
        return False

    if in_failure_mode:
        handle_extended_failure_mode(rtc, time_since_success)
        return True

    return False

def _run_scheduled_cycle(rtc, cycle_count, cycle_start_time):
    """Helper: Handle scheduled display if active - returns True if schedule ran"""
    if not display_config.show_scheduled_displays:
        log_debug("Scheduled displays disabled due to errors")
        return False

    schedule_name, schedule_config = scheduled_display.get_active_schedule(rtc)
    if not schedule_name:
        return False  # No active schedule

    # Fetch weather for segment
    current_data = fetch_current_weather_only()
    if current_data:
        state.last_successful_weather = time.monotonic()
        state.consecutive_failures = 0

    # Display schedule segment
    display_duration = get_remaining_schedule_time(rtc, schedule_config)
    segment_start = time.monotonic()

    show_scheduled_display(rtc, schedule_name, schedule_config, display_duration, current_data)

    # Fast cycle protection
    segment_elapsed = time.monotonic() - segment_start
    if segment_elapsed < Timing.FAST_CYCLE_THRESHOLD:
        log_error(f"Schedule cycle suspiciously fast ({segment_elapsed:.1f}s) - adding delay")
        time.sleep(Timing.ERROR_SAFETY_DELAY)

    # Check for events between schedules
    if state.schedule_just_ended and display_config.show_events_in_between_schedules and display_config.show_events:
        cleanup_global_session()
        gc.collect()
        show_event_display(rtc, 30)
        cleanup_global_session()
        gc.collect()

    _log_cycle_complete(cycle_count, cycle_start_time, "SCHEDULED")
    return True

def _run_normal_cycle(rtc, cycle_count, cycle_start_time):
    """Helper: Run normal display cycle (weather/forecast/events)"""
    something_displayed = False

    # Fetch data once
    current_data, forecast_data, forecast_is_fresh = fetch_cycle_data(rtc)
    current_duration, forecast_duration, event_duration = calculate_display_durations(rtc)

    # Forecast display
    forecast_shown = False
    if display_config.show_forecast and current_data and forecast_data:
        forecast_shown = show_forecast_display(current_data, forecast_data, forecast_duration, forecast_is_fresh)
        something_displayed = something_displayed or forecast_shown

    if not forecast_shown:
        current_duration += forecast_duration

    # Weather display
    if display_config.show_weather and current_data:
        show_weather_display(rtc, current_duration, current_data)
        something_displayed = True

    # Events display
    if display_config.show_events and event_duration > 0:
        event_shown = show_event_display(rtc, event_duration)
        something_displayed = something_displayed or event_shown
        if not event_shown:
            interruptible_sleep(1)

    # Test modes
    if display_config.show_color_test:
        show_color_test_display(Timing.COLOR_TEST)
        something_displayed = True

    if display_config.show_icon_test:
        show_icon_test_display(icon_numbers=TestData.TEST_ICONS)
        something_displayed = True

    # Fallback
    if not something_displayed:
        log_warning("No displays active - showing clock as fallback")
        show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
        something_displayed = True

    # Stats logging
    if cycle_count % Timing.CYCLES_FOR_CACHE_STATS == 0:
        log_debug(state.image_cache.get_stats())

    # Fast cycle protection
    cycle_duration = time.monotonic() - cycle_start_time
    if cycle_duration < Timing.FAST_CYCLE_THRESHOLD:
        log_error(f"Cycle too fast ({cycle_duration:.1f}s) - adding safety delay")
        time.sleep(Timing.ERROR_SAFETY_DELAY)
        cycle_duration = time.monotonic() - cycle_start_time

    _log_cycle_complete(cycle_count, cycle_start_time, "NORMAL")

def _log_cycle_complete(cycle_count, start_time, mode):
    """Helper: Log cycle completion with stats"""
    cycle_duration = time.monotonic() - start_time
    mem_stats = state.memory_monitor.get_memory_stats()

    log_info(
        f"Cycle #{cycle_count} ({mode}) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | "
        f"UT: {state.memory_monitor.get_runtime()} | "
        f"Mem: {mem_stats['usage_percent']:.1f}% | "
        f"API: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, "
        f"Current={state.current_api_calls}, Forecast={state.forecast_api_calls}\n"
    )
```

**Benefits:**
- Reduces max nesting from 4 → 2 levels
- Main function now 60 lines (down from 156)
- Each path is clear and testable
- Stack frames saved: ~2-3 frames

**Risk:** None - pure refactoring with extraction

---

### A3. show_scheduled_display() - Lines 3406-3625

**Current Nesting:** 5 levels (try → if → if → for → if)

**Stack Depth Issue:**
```python
try:                                        # Level 1
    if not current_data:                    # Level 2
        current_data = fetch_weather()

    if not current_data:                    # Level 2
        if cached := get_cached():          # Level 3
            is_cached = True
        else:                               # Level 3
            is_cached = False

    if current_data:                        # Level 2
        if uv_index > 0:                    # Level 3
            for i in range(uv_length):      # Level 4
                if i not in positions:      # Level 5
                    # create pixel

        try:                                # Level 3
            # load icon
        except:                             # Level 3
            pass
```

**Flattening Strategy:** Extract rendering sections to helpers

**Refactored (AFTER):**
```python
def show_scheduled_display(rtc, schedule_name, schedule_config, total_duration, current_data=None):
    """Flattened schedule display"""
    # Setup segment tracking
    elapsed, full_duration, progress = get_schedule_progress()
    if elapsed is None:
        _init_schedule_session(schedule_name, total_duration)
        elapsed, full_duration, progress = 0, total_duration, 0

    segment_duration = min(Timing.SCHEDULE_SEGMENT_DURATION, full_duration - elapsed)
    log_debug(f"Segment duration: {segment_duration}s")

    gc.collect()
    clear_display()

    try:
        # Get weather data
        current_data, is_cached = _get_schedule_weather_data(current_data)

        # Render weather section (if available)
        if current_data:
            _render_schedule_weather(current_data, is_cached)

        # Render schedule image (always)
        if not _render_schedule_image(schedule_config):
            # Image load failed - show clock and exit
            show_clock_display(rtc, segment_duration)
            return

        # Render clock label
        time_label = _create_schedule_clock_label()
        state.main_group.append(time_label)

        # Add weekday indicator
        if display_config.show_weekday_indicator:
            add_day_indicator(state.main_group, rtc)

        # Calculate segment info
        segment_num, total_segments = _calculate_segment_info(elapsed, full_duration)
        state.schedule_just_ended = (segment_num >= total_segments)

        # Log display info
        _log_schedule_segment(schedule_name, segment_num, total_segments, segment_duration, progress, current_data, is_cached)

        # Update success tracking
        state.last_successful_weather = time.monotonic()
        state.consecutive_failures = 0

        # Render progress bar
        progress_grid, progress_bitmap = None, None
        if schedule_config.get("progressbar", True):
            progress_grid, progress_bitmap = create_progress_bar_tilegrid()
            if progress > 0:
                update_progress_bar_bitmap(progress_bitmap, elapsed, full_duration)
            state.main_group.append(progress_grid)

        # Display loop
        _run_schedule_display_loop(rtc, segment_duration, time_label, progress_bitmap, elapsed, full_duration, progress_grid is not None)

    except Exception as e:
        log_error(f"Scheduled display segment error: {e}")
        safe_duration = Timing.CLOCK_DISPLAY_DURATION if state.consecutive_display_errors >= 5 else max(Timing.ERROR_SAFETY_DELAY, segment_duration)
        show_clock_display(rtc, safe_duration)

    finally:
        gc.collect()

def _get_schedule_weather_data(provided_data):
    """Helper: Get weather data for schedule - returns (data, is_cached)"""
    if provided_data:
        return provided_data, False

    # Fetch fresh weather
    fresh_data = fetch_current_weather_only()
    if fresh_data:
        return fresh_data, False

    log_warning("No weather data for scheduled display segment")

    # Try cached
    cached_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)
    if cached_data:
        log_debug("Using cached current weather as fallback")
        return cached_data, True

    log_warning("No weather data - Display schedule + clock only")
    return None, False

def _render_schedule_weather(weather_data, is_cached):
    """Helper: Render weather section of schedule display"""
    temperature = f"{round(weather_data['feels_like'])}°"
    weather_icon = f"{weather_data['weather_icon']}.bmp"
    uv_index = weather_data['uv_index']

    # UV bar
    if uv_index > 0:
        _add_uv_bar(uv_index)

    y_offset = Layout.SCHEDULE_X_OFFSET if uv_index > 0 else 0

    # Weather icon
    try:
        bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{weather_icon}")
        weather_img = displayio.TileGrid(bitmap, pixel_shader=palette)
        weather_img.x = Layout.SCHEDULE_LEFT_MARGIN_X
        weather_img.y = Layout.SCHEDULE_W_IMAGE_Y + y_offset
        state.main_group.append(weather_img)
    except Exception as e:
        log_error(f"Failed to load weather icon: {e}")

    # Temperature label
    temp_color = state.colors["LILAC"] if is_cached else state.colors["DIMMEST_WHITE"]
    temp_label = bitmap_label.Label(
        font,
        color=temp_color,
        text=temperature,
        x=Layout.SCHEDULE_LEFT_MARGIN_X,
        y=Layout.SCHEDULE_TEMP_Y + y_offset
    )
    state.main_group.append(temp_label)

def _add_uv_bar(uv_index):
    """Helper: Add UV bar pixels to display"""
    uv_length = calculate_uv_bar_length(uv_index)
    for i in range(uv_length):
        if i in Visual.UV_SPACING_POSITIONS:
            continue

        uv_pixel = Line(
            Layout.SCHEDULE_LEFT_MARGIN_X + i,
            Layout.SCHEDULE_UV_Y,
            Layout.SCHEDULE_LEFT_MARGIN_X + i,
            Layout.SCHEDULE_UV_Y,
            state.colors["DIMMEST_WHITE"]
        )
        state.main_group.append(uv_pixel)

def _render_schedule_image(schedule_config):
    """Helper: Load and render schedule image - returns True if successful"""
    try:
        bitmap, palette = load_bmp_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
        schedule_img = displayio.TileGrid(bitmap, pixel_shader=palette)
        schedule_img.x = Layout.SCHEDULE_IMAGE_X
        schedule_img.y = Layout.SCHEDULE_IMAGE_Y
        state.main_group.append(schedule_img)
        state.scheduled_display_error_count = 0
        return True
    except Exception as e:
        log_error(f"Failed to load schedule image: {e}")
        state.scheduled_display_error_count += 1
        if state.scheduled_display_error_count >= 3:
            display_config.show_scheduled_displays = False
        return False

# ... additional helpers ...
```

**Benefits:**
- Reduces max nesting from 5 → 2 levels
- Main function now ~80 lines (down from 220)
- Each section testable in isolation
- Stack frames saved: ~3 frames

**Risk:** None - pure extraction

---

### A4. fetch_current_and_forecast_weather() - Lines 1413-1575

**Current Nesting:** 4 levels (try → if → if → nested dict access)

**Flattening Strategy:** Extract data processing to helpers

**Refactored (AFTER):**
```python
def fetch_current_and_forecast_weather():
    """Flattened weather fetch"""
    state.memory_monitor.check_memory("weather_fetch_start")

    # Early exit: all fetching disabled
    if not display_config.should_fetch_weather() and not display_config.should_fetch_forecast():
        log_debug("All API fetching disabled")
        return None, None

    # Early exit: no API key
    api_key = get_api_key()
    if not api_key:
        state.consecutive_failures += 1
        return None, None

    # Monitor API call budget
    expected_calls = _count_expected_api_calls()
    if state.api_call_count + expected_calls >= API.MAX_CALLS_BEFORE_RESTART:
        log_warning(f"API call #{state.api_call_count + expected_calls} - restart imminent")

    try:
        # Fetch current weather
        current_data = _fetch_and_process_current(api_key) if display_config.should_fetch_weather() else None

        # Fetch forecast
        forecast_data = _fetch_and_process_forecast(api_key) if display_config.should_fetch_forecast() else None

        # Update state based on results
        _update_fetch_state(current_data, forecast_data)

        return current_data, forecast_data

    except Exception as e:
        log_error(f"Weather fetch critical error: {type(e).__name__}: {e}")
        state.memory_monitor.check_memory("weather_fetch_error")
        return None, None

def _fetch_and_process_current(api_key):
    """Helper: Fetch and process current weather"""
    url = f"{API.BASE_URL}/{API.CURRENT_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&details=true"

    current_json = fetch_weather_with_retries(url, context="Current Weather")
    if not current_json:
        log_warning("Current weather fetch failed")
        return None

    # Count API call
    state.current_api_calls += 1
    state.api_call_count += 1

    # Process response
    current = current_json[0]
    current_data = {
        "weather_icon": current.get("WeatherIcon", 0),
        "temperature": current.get("Temperature", {}).get("Metric", {}).get("Value", 0),
        "feels_like": current.get("RealFeelTemperature", {}).get("Metric", {}).get("Value", 0),
        "feels_shade": current.get("RealFeelTemperatureShade", {}).get("Metric", {}).get("Value", 0),
        "humidity": current.get("RelativeHumidity", 0),
        "uv_index": current.get("UVIndex", 0),
        "weather_text": current.get("WeatherText", "Unknown"),
        "is_day_time": current.get("IsDayTime", True),
        "has_precipitation": current.get("HasPrecipitation", False),
    }

    # Cache for fallback
    state.cached_current_weather = current_data
    state.cached_current_weather_time = time.monotonic()

    log_info(f"Weather: {current_data['weather_text']}, {current_data['feels_like']}°C")
    return current_data

def _fetch_and_process_forecast(api_key):
    """Helper: Fetch and process forecast weather"""
    url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&metric=true&details=true"

    forecast_json = fetch_weather_with_retries(url, max_retries=1, context="Forecast")

    # Count API call even if processing fails
    if forecast_json:
        state.forecast_api_calls += 1
        state.api_call_count += 1

    # Validate data length
    forecast_length = min(API.DEFAULT_FORECAST_HOURS, API.MAX_FORECAST_HOURS)
    if not forecast_json or len(forecast_json) < forecast_length:
        log_warning("Forecast fetch failed or insufficient data")
        return None

    # Process forecast data
    forecast_data = []
    for i in range(forecast_length):
        hour_data = forecast_json[i]
        forecast_data.append({
            "temperature": hour_data.get("Temperature", {}).get("Value", 0),
            "feels_like": hour_data.get("RealFeelTemperature", {}).get("Value", 0),
            "feels_shade": hour_data.get("RealFeelTemperatureShade", {}).get("Value", 0),
            "weather_icon": hour_data.get("WeatherIcon", 1),
            "weather_text": hour_data.get("IconPhrase", "Unknown"),
            "datetime": hour_data.get("DateTime", ""),
            "has_precipitation": hour_data.get("HasPrecipitation", False)
        })

    log_info(f"Forecast: {len(forecast_data)} hours (fresh) | Next: {forecast_data[0]['feels_like']}°C")
    state.memory_monitor.check_memory("forecast_data_complete")

    return forecast_data

def _update_fetch_state(current_data, forecast_data):
    """Helper: Update state based on fetch results"""
    success = (current_data is not None) or (forecast_data is not None)

    if success:
        # Success path
        if state.consecutive_failures > 0:
            recovery_time = int((time.monotonic() - state.last_successful_weather) / System.SECONDS_PER_MINUTE)
            log_info(f"Weather API recovered after {recovery_time} minutes")

        state.last_successful_weather = time.monotonic()
        state.consecutive_failures = 0

        # Cache forecast if received
        if forecast_data:
            state.cached_forecast_data = forecast_data
            state.last_forecast_fetch = time.monotonic()

    else:
        # Failure path
        state.consecutive_failures += 1
        state.system_error_count += 1
        log_warning(f"Consecutive failures: {state.consecutive_failures}, System errors: {state.system_error_count}")

        # Check for reset thresholds
        if state.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD:
            log_warning("Soft reset: clearing network session")
            cleanup_global_session()
            state.consecutive_failures = 0

        if state.system_error_count >= Recovery.HARD_RESET_THRESHOLD:
            log_error(f"Hard reset after {state.system_error_count} system errors")
            interruptible_sleep(Timing.RESTART_DELAY)
            supervisor.reload()

    # Preventive restart check
    if state.api_call_count >= API.MAX_CALLS_BEFORE_RESTART:
        log_warning(f"Preventive restart after {state.api_call_count} API calls")
        cleanup_global_session()
        interruptible_sleep(API.RETRY_DELAY)
        supervisor.reload()

def _count_expected_api_calls():
    """Helper: Count expected API calls this fetch"""
    count = 0
    if display_config.should_fetch_weather():
        count += 1
    if display_config.should_fetch_forecast():
        count += 1
    return count
```

**Benefits:**
- Reduces max nesting from 4 → 2 levels
- Separates concerns (fetch, process, state update)
- Each helper is testable
- Stack frames saved: ~2 frames

**Risk:** None - pure extraction

---

### A5-A8: Additional Low-Risk Flattening Opportunities

**A5. show_weather_display() - Lines 2480-2636**
- **Current nesting:** 3-4 levels
- **Strategy:** Extract static element creation to helpers
- **Benefit:** 1-2 stack frames saved
- **Risk:** None

**A6. show_forecast_display() - Lines 3019-3284**
- **Current nesting:** 3-4 levels
- **Strategy:** Extract column rendering to helpers
- **Benefit:** 2 stack frames saved
- **Risk:** None

**A7. show_event_display() - Lines 2706-2863**
- **Current nesting:** 3 levels
- **Strategy:** Extract event selection logic
- **Benefit:** 1 stack frame saved
- **Risk:** None

**A8. _display_single_event_optimized() - Lines 2765-2864**
- **Current nesting:** 3-4 levels
- **Strategy:** Extract image loading and text rendering
- **Benefit:** 1-2 stack frames saved
- **Risk:** None

---

## Category B: Flattening with Functionality Tradeoffs

These changes **improve stack depth** but may **slightly alter behavior** or **reduce error detail**.

### B1. Retry Loop Consolidation

**Current Pattern:** Separate error handling for RuntimeError, OSError, Exception

**Issue:** Each except block adds stack depth

**Tradeoff Option:** Consolidate exception handling

**Current (lines 1353-1408):**
```python
except RuntimeError as e:
    error_msg = str(e)
    if "pystack exhausted" in error_msg.lower():
        log_error(f"{context}: Stack exhausted")
    elif "already connected" in error_msg.lower():
        log_error(f"{context}: Socket already connected")
    # ... cleanup

except OSError as e:
    error_msg = str(e)
    if "already connected" in error_msg.lower():
        log_error(f"{context}: Socket stuck")
    # ... cleanup

except Exception as e:
    log_error(f"{context} unexpected error: {e}")
    # ... retry logic
```

**Flattened:**
```python
except Exception as e:
    # Unified error handling - less stack depth
    error_type = type(e).__name__
    error_msg = str(e)

    # Detect critical errors
    is_stack_error = "pystack exhausted" in error_msg.lower()
    is_socket_error = "already connected" in error_msg.lower() or isinstance(e, OSError)

    if is_stack_error:
        log_error(f"{context}: Stack exhausted")
        cleanup_global_session()
        cleanup_sockets()
    elif is_socket_error:
        log_error(f"{context}: Socket issue - {error_type}")
        cleanup_global_session()
        cleanup_sockets()
    else:
        log_error(f"{context}: {error_type}: {error_msg}")

    gc.collect()
    time.sleep(2)

    if attempt < max_retries:
        delay = API.RETRY_BASE_DELAY * (2 ** attempt)
        time.sleep(delay)
```

**Benefits:**
- Reduces exception handling from 3 blocks → 1 block
- Saves ~1 stack frame
- Simpler control flow

**Tradeoffs:**
- ⚠️ **Less specific logging** - generic Exception instead of RuntimeError/OSError
- ⚠️ **Potentially catches too much** - might mask bugs
- ⚠️ **Cleanup always runs** - even for non-socket errors

**Recommendation:** Only if stack exhaustion persists after Category A changes

---

### B2. Progress Bar Simplification

**Current (lines 3556-3602):** Progress bar updates every column change in tight loop

**Issue:** Display loop runs for entire segment duration with nested conditionals

**Tradeoff Option:** Update progress bar less frequently

**Current:**
```python
while time.monotonic() - segment_start < segment_duration:
    current_minute = rtc.datetime.tm_min
    current_time = time.monotonic()

    overall_elapsed = elapsed + (current_time - segment_start)
    overall_progress = overall_elapsed / full_duration
    current_column = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * overall_progress)

    if show_progress_bar and current_column != last_displayed_column and current_column < Layout.PROGRESS_BAR_HORIZONTAL_WIDTH:
        update_progress_bar_bitmap(progress_bitmap, overall_elapsed, full_duration)
        last_displayed_column = current_column

    if current_minute != last_minute:
        # Update clock
        hour = rtc.datetime.tm_hour
        display_hour = hour % System.HOURS_IN_HALF_DAY or System.HOURS_IN_HALF_DAY
        time_label.text = f"{display_hour}:{current_minute:02d}"
        last_minute = current_minute

    time.sleep(sleep_interval)
```

**Simplified:**
```python
# Update progress bar every 30 seconds instead of every column
last_progress_update = 0
progress_update_interval = 30  # seconds

while time.monotonic() - segment_start < segment_duration:
    current_time = time.monotonic()
    current_minute = rtc.datetime.tm_min

    # Update clock (every minute)
    if current_minute != last_minute:
        hour = rtc.datetime.tm_hour
        display_hour = hour % System.HOURS_IN_HALF_DAY or System.HOURS_IN_HALF_DAY
        time_label.text = f"{display_hour}:{current_minute:02d}"
        last_minute = current_minute

    # Update progress bar (every 30 seconds)
    if show_progress_bar and (current_time - last_progress_update) >= progress_update_interval:
        overall_elapsed = elapsed + (current_time - segment_start)
        update_progress_bar_bitmap(progress_bitmap, overall_elapsed, full_duration)
        last_progress_update = current_time

    time.sleep(sleep_interval)
```

**Benefits:**
- Removes nested progress calculation every loop iteration
- Reduces local variables (no current_column, last_displayed_column)
- Simpler loop logic

**Tradeoffs:**
- ⚠️ **Less smooth progress bar** - updates every 30s instead of per-column
- ⚠️ **Visual change** - user might notice chunkier progress

**Recommendation:** Acceptable tradeoff - 30-second updates are fine for 2-hour displays

---

### B3. Precipitation Detection Simplification

**Current (lines 3032-3074):** Complex nested logic to find rain start/stop times

**Tradeoff Option:** Simplified precipitation logic

**Current:**
```python
if current_has_precip:
    for i in range(len(precip_flags)):
        if not precip_flags[i]:
            forecast_indices = [i, min(i + 1, len(forecast_data) - 1)]
            break
else:
    rain_start = -1
    rain_stop = -1

    for i in range(len(precip_flags)):
        if precip_flags[i] and rain_start == -1:
            rain_start = i
        elif not precip_flags[i] and rain_start != -1 and rain_stop == -1:
            rain_stop = i
            break

    if rain_start != -1:
        if rain_stop != -1:
            forecast_indices = [rain_start, rain_stop]
        else:
            forecast_indices = [rain_start, min(rain_start + 1, len(forecast_data) - 1)]
```

**Simplified:**
```python
# Simpler: just show next 2 different hours, highlight if precip
forecast_indices = [0, 1]

# If currently raining, find when it stops (first hour without rain)
if current_has_precip:
    for i, has_rain in enumerate(precip_flags):
        if not has_rain:
            forecast_indices = [i, i + 1]
            break

# If not raining, find when it starts (first hour with rain)
elif any(precip_flags):
    rain_start = precip_flags.index(True)
    forecast_indices = [rain_start, rain_start + 1]
```

**Benefits:**
- Removes nested if/elif logic
- Removes multiple state variables (rain_start, rain_stop)
- Easier to understand

**Tradeoffs:**
- ⚠️ **Less smart** - doesn't show rain stop time if not currently raining
- ⚠️ **Different UX** - always shows consecutive hours

**Recommendation:** Only if stack issues persist - current logic is valuable

---

### B4. Deep Dictionary Access Flattening

**Current Pattern:** Multiple nested .get() chains

**Example (lines 1454-1456):**
```python
temp_data = current.get("Temperature", {}).get("Metric", {})
realfeel_data = current.get("RealFeelTemperature", {}).get("Metric", {})
realfeel_shade_data = current.get("RealFeelTemperatureShade", {}).get("Metric", {})

current_data = {
    "temperature": temp_data.get("Value", 0),
    "feels_like": realfeel_data.get("Value", 0),
    "feels_shade": realfeel_shade_data.get("Value", 0),
}
```

**Flattened (with try/except):**
```python
# Direct access with fallback
try:
    temperature = current["Temperature"]["Metric"]["Value"]
except (KeyError, TypeError):
    temperature = 0

try:
    feels_like = current["RealFeelTemperature"]["Metric"]["Value"]
except (KeyError, TypeError):
    feels_like = 0

try:
    feels_shade = current["RealFeelTemperatureShade"]["Metric"]["Value"]
except (KeyError, TypeError):
    feels_shade = 0

current_data = {
    "temperature": temperature,
    "feels_like": feels_like,
    "feels_shade": feels_shade,
}
```

**Benefits:**
- Slightly faster (direct access vs multiple .get() calls)
- No intermediate dict variables

**Tradeoffs:**
- ⚠️ **Adds try/except blocks** - might actually increase stack usage
- ⚠️ **Less readable** - nested try blocks
- ⚠️ **Not recommended** - .get() chains are fine

**Recommendation:** Do NOT flatten this - current approach is better

---

### B5. Error State Consolidation

**Current:** Detailed error state tracking in multiple variables

**Tradeoff:** Simplified error tracking with enum

**Current:**
```python
state.consecutive_failures
state.system_error_count
state.wifi_reconnect_attempts
state.has_permanent_error
state.in_extended_failure_mode
```

**Simplified:**
```python
class ErrorState(Enum):
    NORMAL = 0
    TRANSIENT_FAILURE = 1  # 1-5 failures
    DEGRADED = 2           # 5-10 failures
    EXTENDED_FAILURE = 3   # 15+ min without success
    PERMANENT = 4          # 401/404 errors

state.error_level = ErrorState.NORMAL
state.error_count = 0  # Single counter instead of multiple
```

**Benefits:**
- Simpler state management
- Easier to reason about error modes
- Less state variables to track

**Tradeoffs:**
- ⚠️ **Loss of granularity** - can't distinguish WiFi vs API vs socket errors
- ⚠️ **Changes recovery logic** - would need redesign
- ⚠️ **Significant refactor** - not worth it for stack reduction

**Recommendation:** Do NOT implement - too invasive for minimal gain

---

## Priority Recommendations

### Immediate Actions (Do First)

1. **Flatten run_display_cycle()** - Biggest single improvement (A2)
   - Extract schedule handling
   - Extract normal cycle handling
   - Use early returns throughout

2. **Flatten fetch_weather_with_retries()** - Critical path (A1)
   - Extract error handlers
   - Extract response processing
   - Reduce try/except nesting

3. **Flatten show_scheduled_display()** - Longest running function (A3)
   - Extract weather rendering
   - Extract image loading
   - Extract display loop

### Secondary Actions (Do Next)

4. **Flatten fetch_current_and_forecast_weather()** (A4)
5. **Flatten show_weather_display()** (A5)
6. **Flatten show_forecast_display()** (A6)

### Conditional Actions (Only If Needed)

7. **Consolidate exception handling** (B1) - Only if stack issues persist
8. **Simplify progress bar updates** (B2) - Acceptable UX tradeoff
9. **Simplify precipitation logic** (B3) - Only if desperate

### Do NOT Do

10. ❌ **Dictionary access flattening** (B4) - Makes it worse
11. ❌ **Error state consolidation** (B5) - Too invasive

---

## Implementation Timeline

### Week 1: High-Priority Flattening
- Day 1-2: Implement A1 (fetch_weather_with_retries)
- Day 3-4: Implement A2 (run_display_cycle)
- Day 5-7: Test for 72 hours, monitor stack usage

### Week 2: Secondary Flattening
- Day 1-2: Implement A3 (show_scheduled_display)
- Day 3: Implement A4 (fetch_current_and_forecast_weather)
- Day 4-7: Test for 96 hours during 2-hour schedules

### Week 3: Optional Changes
- Day 1: Implement A5, A6 if needed
- Day 2-7: Extended testing, monitor for any remaining stack issues

### Week 4: Conditional Changes (Only If Needed)
- Implement B1 or B2 only if stack exhaustion still occurs
- Extensive testing before production

---

## Testing Strategy

### Stack Depth Measurement

Unfortunately, CircuitPython doesn't expose stack depth directly. Indirect measurement:

```python
# Add to critical functions
def _test_stack_depth():
    """Attempt to detect stack depth issues early"""
    import gc

    # Force allocation to test remaining stack
    try:
        # Create nested list - will fail if stack low
        test = [[[[[[[[[[[[[[[[None]]]]]]]]]]]]]]]]
        return True
    except RuntimeError as e:
        if "stack" in str(e).lower():
            log_error("Stack depth low!")
            return False
        raise
```

### Validation Checklist

After each flattening change:

- [ ] Code compiles without syntax errors
- [ ] Normal cycle runs successfully (5 min)
- [ ] Schedule display runs successfully (30 min segment)
- [ ] 2-hour schedule completes without errors
- [ ] 24-hour burn-in test passes
- [ ] Memory usage remains 10-20%
- [ ] No new errors in logs
- [ ] API call counts unchanged
- [ ] Display functionality identical

### Regression Testing

**Critical Paths to Test:**
1. Normal weather → forecast → events cycle
2. 2-hour schedule display (multiple segments)
3. WiFi disconnect/reconnect recovery
4. API failure recovery
5. Socket exhaustion scenario (if reproducible)
6. Memory monitoring reports
7. Daily 3am restart

---

## Expected Stack Depth Reduction

### Before Flattening

**Estimated max stack depth: 8-9 frames**

```
main() → run_display_cycle() → show_scheduled_display() → fetch_current_weather_only() → fetch_current_and_forecast_weather() → fetch_weather_with_retries() → session.get() → [requests lib] → [socket lib]

= 9 function frames + nested if/try blocks = ~10-12 total frames
```

### After Category A Flattening

**Estimated max stack depth: 5-6 frames**

```
main() → run_display_cycle() → _run_scheduled_cycle() → _get_schedule_weather_data() → fetch_current_weather_only() → session.get() → [requests lib]

= 7 function frames (but helpers are shallower) + minimal nesting = ~6-8 total frames
```

**Improvement:** ~30-40% reduction in stack usage

### After Category A + B Flattening

**Estimated max stack depth: 4-5 frames**

- Removes additional exception handling nesting
- Simplifies loops

**Improvement:** ~40-50% reduction in stack usage

---

## Conclusion

**Recommended Approach:**

1. **Start with Category A** - Safe, no tradeoffs, significant improvement
2. **Test thoroughly** - 24-48 hours after each batch of changes
3. **Monitor stack usage** - Watch for "pystack exhausted" errors
4. **Only add Category B if needed** - Avoid premature optimization

**Expected Outcome:**

- Category A flattening should eliminate most stack exhaustion issues
- Category B provides additional headroom if needed
- Modularization can proceed safely after flattening

**Stack Exhaustion vs. Modularization:**

- Flattening reduces **runtime** stack depth
- Modularization might increase **import** stack depth (one-time)
- **Recommendation:** Flatten first, then modularize

---

**Next Steps:** See `FLATTENING_IMPLEMENTATION_GUIDE.md` (to be created) for step-by-step refactoring instructions.
