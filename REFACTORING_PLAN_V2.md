# Controlled Refactoring Plan for Screeny 2.0

**Date**: November 16, 2025
**Starting Version**: 2.0.6 (stable, proven working)
**Goal**: Split monolithic code.py into modules WITHOUT introducing bugs

## Why Re-doing the Refactoring?

The previous refactoring attempt (v2.1.0+) introduced critical bugs:
- Stack exhaustion errors
- Socket pool issues
- Various runtime crashes

We've reverted to v2.0.6, the last fully stable version where all code was in a single `code.py` file. This version ran for hours without issues.

## Pre-Refactoring Fixes Applied

### 1. Nested Function Removed ✅
**Issue**: `format_hour()` was defined inside `show_forecast_display()`
**Fix**: Moved to module level (line 978) with other time utilities
**Why**: Reduces nesting depth, makes function reusable

### 2. Global State Documented ✅
**Issue**: 5 global objects accessed from many functions
**Strategy**:
- Keep globals in `code.py` to avoid circular imports
- Modules will import from `code.py` OR receive as parameters
- Global objects documented at line 856

**Global Objects**:
- `state` - WeatherDisplayState()
- `display_config` - DisplayConfig()
- `scheduled_display` - ScheduledDisplay()
- `_global_socket_pool` - Socket pool (reused)
- `_global_session` - HTTP session
- `bg_font`, `font` - Font objects

### 3. Code Already Flattened ✅
v2.0.6 already has stack exhaustion fixes from v2.0.1:
- Try/except blocks flattened
- No deeply nested structures
- 63 try blocks at safe nesting levels

## Refactoring Strategy - 8 Phases

### Phase 1: config.py (Lines ~1-455)
**Extract**:
- All configuration classes (Display, Layout, Timing, API, Recovery, Memory, Paths, Visual, System, TestData, Strings, DebugLevel)
- Constants (TIMEZONE_OFFSETS, MONTHS)
- ColorManager class
- DisplayConfig class
- validate_configuration() function
- get_remaining_schedule_time() function

**Why First**: Pure configuration with no dependencies

**Dependencies**: None

---

### Phase 2: utils.py (Lines ~866-1006)
**Extract**:
- Logging functions (log_entry, log_info, log_error, log_warning, log_debug, log_verbose)
- Time utilities (duration_message, parse_iso_datetime, format_datetime, format_hour)
- Basic helpers (initialize_display, interruptible_sleep)

**Why Second**: Only depends on config

**Dependencies**: config.py

---

### Phase 3: cache.py (Lines ~610-775)
**Extract**:
- ImageCache
- TextWidthCache
- MemoryMonitor
- WeatherDisplayState

**Why Third**: Depends on config and utils

**Dependencies**: config.py, utils.py

---

### Phase 4: network.py (Lines ~1007-1712)
**Extract**:
- RTC setup (setup_rtc, sync_time_with_timezone, update_rtc_datetime)
- WiFi management (setup_wifi_with_recovery, check_and_recover_wifi, is_wifi_connected)
- Timezone functions (get_timezone_offset, is_dst_active_for_timezone, get_timezone_from_location_api)
- Socket management (cleanup_sockets, get_requests_session, cleanup_global_session)
- API functions (fetch_weather_with_retries, fetch_current_and_forecast_weather, get_cached_weather_if_fresh, etc.)
- Error state management (get_current_error_state, should_fetch_forecast)

**Why Fourth**: Core infrastructure, depends on config/utils/cache

**Dependencies**: config.py, utils.py, cache.py, code.py (for global state)

---

### Phase 5: events.py (Lines ~1715-2413)
**Extract**:
- Event functions (get_today_events_info, get_today_all_events_info, load_events_from_csv, fetch_ephemeral_events, load_all_events, is_event_active, get_events, parse_events_csv_content)
- Schedule functions (parse_schedule_csv_content, fetch_github_data, load_schedules_from_csv)
- ScheduledDisplay class

**Why Fifth**: Depends on network for fetching data

**Dependencies**: config.py, utils.py, network.py, code.py (for global state)

---

### Phase 6: display.py (Lines ~2414-3759)
**Extract**:
- Display utilities (calculate_bottom_aligned_positions, clear_display, right_align_text, center_text, get_text_width, get_font_metrics)
- Display helpers (get_day_color, add_day_indicator, calculate_uv_bar_length, calculate_humidity_bar_length, add_indicator_bars)
- Image functions (detect_matrix_type, get_matrix_colors, convert_bmp_palette, load_bmp_image)
- All show_* display functions (show_weather_display, show_clock_display, show_event_display, show_color_test_display, show_icon_test_display, show_forecast_display, show_scheduled_display)
- Progress bar functions (create_progress_bar_tilegrid, update_progress_bar_bitmap, get_schedule_progress)
- Date/time calculations (calculate_weekday, calculate_yearday, calculate_display_durations)

**Why Sixth**: Depends on almost everything else

**Dependencies**: config.py, utils.py, cache.py, network.py, events.py, code.py (for global state)

---

### Phase 7: code.py Refactor
**Keep**:
- Imports from new modules
- Global state objects (state, display_config, scheduled_display, fonts, socket pool, session)
- System functions (check_daily_reset, initialize_system, setup_network_and_time, handle_extended_failure_mode)
- Main loop functions (fetch_cycle_data, run_display_cycle, main)

**Remove**:
- Everything extracted to modules

**Update**:
- Add imports from new modules
- Ensure proper initialization order

---

### Phase 8: Testing & Verification
**Tests**:
1. Syntax check (import all modules)
2. Run for 5 minutes - check for stack exhaustion
3. Run for 30 minutes - check for socket issues
4. Run overnight - verify stability
5. Test all features (weather, forecast, events, schedules, clock)

**Rollback Plan**: If any phase fails, revert to previous commit

---

## Key Principles

1. **One Phase at a Time**: Complete and test each phase before moving to next
2. **Dependencies Flow Down**: No circular imports (config → utils → cache → network → events → display → code.py)
3. **Commit After Each Phase**: So we can roll back easily
4. **Test After Each Phase**: Run basic tests to catch issues immediately
5. **Global State in code.py**: Prevents circular imports
6. **No Functional Changes**: Only moving code, not changing logic

---

## Testing Checklist (After Each Phase)

- [ ] Code imports without errors
- [ ] No circular import errors
- [ ] All functions accessible
- [ ] Run for 5 minutes without crashes
- [ ] Memory usage stable
- [ ] No stack exhaustion errors

---

## Context Window Management

**Current Usage**: ~35,500/200,000 tokens (18% used)
**Strategy**:
- Update this document regularly
- Commit after each phase with detailed messages
- Create summary docs if context gets above 70%
- Start new conversation if needed (documentation allows resumption)

---

## Version History

- **v2.0.6** - Stable baseline (restored from commit 0206fdc)
- **v2.0.6.1** - Pre-refactor fixes (nested function, documentation)
- **v2.1.0** - Target: Successfully refactored into modules

---

## Next Steps

1. ✅ Pre-refactor analysis complete
2. ✅ Nested function moved to module level
3. ✅ Global state documented
4. → **START PHASE 1**: Extract config.py
