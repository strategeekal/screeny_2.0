# Quick Fix Guide - Socket Exhaustion During Schedule Displays

## TL;DR - The Problem

Your code runs great for 300+ normal cycles (25+ hours), but socket exhaustion happens during **2-hour schedule displays** around segment 8-10 because:

1. **Response objects aren't being closed** explicitly
2. During 24-segment schedule, responses accumulate in the same session
3. Cleanup only happens at END of schedule, not between segments
4. Garbage collection can't keep up with socket accumulation

## The Solution (3 Parts)

### Part 1: Close All Responses ⚠️ **CRITICAL** (30 min)
Add `try/finally` blocks with `response.close()` to 5 locations

### Part 2: Mid-Schedule Cleanup 🔧 **HIGH PRIORITY** (15 min)
Add cleanup every 4th segment (every 20 minutes)

### Part 3: Smarter Caching 💡 **OPTIMIZATION** (10 min)
Cache weather for 15 minutes during schedules instead of fetching every 5 minutes

---

## Part 1: Fix Response Closing (DO THIS FIRST!)

### Location 1: `fetch_weather_with_retries()` - Line ~1293

**FIND THIS CODE:**
```python
response = session.get(url)

# Success case
if response.status_code == API.HTTP_OK:
    log_verbose(f"{context}: Success")
    return response.json()  # ❌ PROBLEM: Response never closed!
```

**REPLACE WITH:**
```python
response = session.get(url)

try:
    # Success case
    if response.status_code == API.HTTP_OK:
        log_verbose(f"{context}: Success")
        data = response.json()  # Extract data first
        return data

    # [Keep all your existing error handling code]
    # elif response.status_code == API.HTTP_SERVICE_UNAVAILABLE:
    # ...

finally:
    # CRITICAL: Always close response
    if response is not None:
        try:
            response.close()
        except:
            pass  # Ignore close errors
```

**IMPORTANT:** The `finally` block goes INSIDE the `for attempt in range(...)` loop, so the response is closed after each attempt, not after all retries!

**Full Pattern:**
```python
for attempt in range(max_retries + 1):
    response = None  # Initialize before try block
    try:
        # ... your WiFi/session checks ...

        response = session.get(url)

        try:
            if response.status_code == API.HTTP_OK:
                data = response.json()
                return data

            # ... all your other error handling ...

        finally:
            # Close after each attempt
            if response:
                try:
                    response.close()
                except:
                    pass

    except RuntimeError as e:
        # Your existing RuntimeError handling
        pass
    except OSError as e:
        # Your existing OSError handling
        pass
```

---

### Location 2: `get_timezone_from_location_api()` - Line ~1148

**FIND:**
```python
response = session.get(url)

if response.status_code == 200:
    data = response.json()
    # ... process data ...
```

**REPLACE WITH:**
```python
response = session.get(url)

try:
    if response.status_code == 200:
        data = response.json()
        # ... process data ...
        return {...}
    else:
        log_warning(f"Location API failed: {response.status_code}")
        return None
finally:
    response.close()
```

---

### Location 3, 4, 5: `fetch_github_data()` - Line ~2136

This function has **3 response objects** to close!

**FIND:**
```python
# ===== FETCH EVENTS =====
response = session.get(events_url, timeout=10)

if response.status_code == 200:
    events = parse_events_csv_content(response.text, rtc)
```

**REPLACE WITH:**
```python
# ===== FETCH EVENTS =====
response = session.get(events_url, timeout=10)

try:
    if response.status_code == 200:
        events = parse_events_csv_content(response.text, rtc)
        log_verbose(f"Events fetched: {len(events)} event dates")
    else:
        log_warning(f"Failed to fetch events: HTTP {response.status_code}")
finally:
    response.close()  # ✅ Close events response
```

**THEN FIND:**
```python
# Try date-specific schedule first
response = session.get(schedule_url, timeout=10)

if response.status_code == 200:
    schedules = parse_schedule_csv_content(response.text, rtc)
elif response.status_code == 404:
    # Try default
    response = session.get(default_url, timeout=10)  # ❌ First response not closed!
```

**REPLACE WITH:**
```python
# Try date-specific schedule first
response = session.get(schedule_url, timeout=10)

try:
    if response.status_code == 200:
        schedules = parse_schedule_csv_content(response.text, rtc)
        schedule_source = "date-specific"

    elif response.status_code == 404:
        response.close()  # ✅ Close first response

        # Try default
        response = session.get(default_url, timeout=10)
        try:
            if response.status_code == 200:
                schedules = parse_schedule_csv_content(response.text, rtc)
                schedule_source = "default"
        finally:
            response.close()  # ✅ Close default response
    else:
        log_warning(f"Failed to fetch schedule: HTTP {response.status_code}")
finally:
    # Make sure date-specific response is closed
    try:
        response.close()
    except:
        pass  # May already be closed in 404 case
```

**Test After Part 1:** Run a 2-hour schedule, monitor logs for socket errors

---

## Part 2: Add Mid-Schedule Cleanup

### Location: `show_scheduled_display()` - After Line ~3436

**FIND:**
```python
# Light cleanup before segment (keep session alive for connection reuse)
gc.collect()
clear_display()
```

**REPLACE WITH:**
```python
# Light cleanup before segment (keep session alive for connection reuse)
gc.collect()

# PERIODIC CLEANUP: Every 4th segment during long schedules
# Prevents socket accumulation over multi-hour sessions
segment_num = int(elapsed / Timing.SCHEDULE_SEGMENT_DURATION) + 1
if segment_num > 1 and segment_num % 4 == 0:
    log_info(f"Mid-schedule cleanup at segment {segment_num}")
    cleanup_global_session()
    gc.collect()
    time.sleep(0.5)  # Let sockets fully close

clear_display()
```

**What This Does:**
- Every 4 segments (20 minutes), destroys and recreates the global session
- Ensures any leaked sockets are cleaned up
- Adds safety net even if response.close() fails

**Test After Part 2:** Run 2-hour schedule, check logs for "Mid-schedule cleanup" messages every 20 min

---

## Part 3: Smarter Weather Caching

### Location: `run_display_cycle()` - Around Line ~3930

**FIND:**
```python
if schedule_name:
    # Fetch weather for this segment
    current_data = fetch_current_weather_only()
```

**REPLACE WITH:**
```python
if schedule_name:
    # Try cached weather first (15 min = 3 segments)
    current_data = get_cached_weather_if_fresh(max_age_seconds=900)

    if current_data:
        cache_age_min = int((time.monotonic() - state.cached_current_weather_time) / 60)
        log_debug(f"Using cached weather for schedule ({cache_age_min} min old)")
    else:
        # Cache stale or missing - fetch fresh
        log_debug("Fetching fresh weather for schedule")
        current_data = fetch_current_weather_only()
```

**What This Does:**
- Uses cached weather if less than 15 minutes old
- 2-hour schedule: 24 fetches → 8 fetches
- Saves ~16 API calls per long schedule
- Weather rarely changes in 15 minutes, especially at night

**Test After Part 3:** Check logs for "Using cached weather" messages

---

## Testing Checklist

### Quick Test (30 minutes)
- [ ] Code compiles without errors
- [ ] Device starts up
- [ ] Normal weather cycle works
- [ ] No new errors in logs

### Normal Cycle Test (2 hours)
- [ ] Weather displays correctly
- [ ] Forecast displays correctly
- [ ] Events display correctly
- [ ] No socket errors
- [ ] Memory stable at 10-20%

### Schedule Display Test (2+ hours) **CRITICAL**
- [ ] Schedule starts correctly
- [ ] Weather updates each segment
- [ ] Mid-schedule cleanup logs appear (every 20 min)
- [ ] **NO socket exhaustion errors!**
- [ ] Schedule completes all 24 segments
- [ ] Display transitions correctly at end

### Success Criteria
✅ Complete 2-hour schedule without any socket errors
✅ All segments display weather (not falling back to cached)
✅ Logs show "Mid-schedule cleanup" every 4th segment
✅ Memory remains 10-20% throughout

---

## What To Watch For

### Good Signs ✅
```
[LOG] Segment 1/24 (Displaying Schedule: Sleep - 10°, 5.0 min)
[LOG] Segment 4/24 (...)
[LOG] Mid-schedule cleanup at segment 4
[LOG] Segment 8/24 (...)
[LOG] Mid-schedule cleanup at segment 8
...
[LOG] Segment 24/24 (...)
[LOG] Schedule complete
```

### Bad Signs ❌
```
[ERROR] Socket already connected
[ERROR] Runtime error: pystack exhausted
[WARNING] No weather data for scheduled display segment
[WARNING] Display schedule + clock only
```

If you see bad signs:
1. Check if all 5 `response.close()` fixes were applied correctly
2. Verify mid-schedule cleanup code is running (check logs)
3. Look for any OTHER places that call `session.get()` that we missed

---

## Expected Improvements

### Before Fixes:
```
2-Hour Schedule:
├─ Segment 1-7: Working fine
├─ Segment 8: 🔥 Socket exhaustion
├─ Segment 9+: Fallback to cached/clock only
└─ API calls: 7-8 before failure
```

### After Part 1 (Response Closing):
```
2-Hour Schedule:
├─ All 24 segments: ✅ Working
├─ Weather every segment: ✅ Fresh data
└─ API calls: 24 (all successful)
```

### After Part 1 + Part 2 (+ Mid-Schedule Cleanup):
```
2-Hour Schedule:
├─ All 24 segments: ✅ Working
├─ Cleanup at segments 4, 8, 12, 16, 20: ✅ Safety net
├─ Weather every segment: ✅ Fresh data
└─ API calls: 24 (all successful, no accumulation)
```

### After All Parts (+ Caching):
```
2-Hour Schedule:
├─ All 24 segments: ✅ Working
├─ Weather fetches: 8 (cached for 3 segments each)
├─ Cleanup at segments 4, 8: ✅ Sufficient
└─ API calls: 8 (saved 16 calls!)

Daily Savings:
├─ Before: ~40 calls for schedules
├─ After: ~15 calls for schedules
└─ Freed up: 25 calls/day for new features!
```

---

## Troubleshooting

### "I still see socket errors after Part 1"
- Did you add `try/finally` to ALL 5 locations?
- Is the `finally` block at the right indentation level?
- Check you're not calling `response.json()` after `response.close()`

### "Mid-schedule cleanup isn't running"
- Check indentation of the new code
- Verify `elapsed` is being calculated correctly
- Add more logging to debug segment number calculation

### "Weather shows as cached even though it shouldn't"
- Check `state.cached_current_weather_time` is being updated
- Verify cache duration (900 seconds = 15 minutes)
- Look for "Using cached weather" vs "Fetching fresh weather" in logs

### "Device crashes after changes"
- Syntax error - check indentation carefully
- Missing variable - verify you didn't accidentally delete code
- Upload just Part 1 first, test, then add Part 2, etc.

---

## Quick Reference: All 5 Response Locations

1. **Line ~1293** - `fetch_weather_with_retries()` - Main weather/forecast fetching
2. **Line ~1148** - `get_timezone_from_location_api()` - Timezone detection at startup
3. **Line ~2158** - `fetch_github_data()` - Events CSV from GitHub
4. **Line ~2180** - `fetch_github_data()` - Date-specific schedule CSV
5. **Line ~2192** - `fetch_github_data()` - Default schedule CSV

**Pattern for all:**
```python
response = session.get(url)
try:
    if response.status_code == 200:
        data = response.json()  # or response.text
        # ... process ...
        return result
    else:
        # ... error handling ...
finally:
    response.close()
```

---

## Need Help?

If socket errors persist after implementing all fixes:
1. Check console logs for specific error messages
2. Note which segment number the error occurs at
3. Verify all 5 response.close() locations are correct
4. Consider reducing mid-schedule cleanup interval (every 3 segments instead of 4)

**Good luck! Your code is excellent - this is just the final polish!** 🎉
