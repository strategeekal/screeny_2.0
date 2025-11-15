# Phase 4 Testing Plan - Display Function Validation

**Date**: 2025-11-15
**Version**: Pantallita 2.1.0 (Phase 4 Complete)
**Branch**: `claude/bonjour-01QpCeLBqbWrwtjckmieTfMy`

---

## 📋 Overview

This testing plan validates that all extracted display functions in display.py work correctly on hardware without regressions. Phase 4 extracted 29 display functions (~1,125 lines) from code.py.

**Testing Goals**:
1. ✅ Verify all display functions execute without errors
2. ✅ Confirm no performance degradation
3. ✅ Validate all v2.0.6 socket fixes still work
4. ✅ Ensure memory stability
5. ✅ Check visual display correctness

---

## 🔍 Pre-Deployment Checks

### 1. Local Validation (Desktop)

Run these checks **before** deploying to hardware:

```bash
# 1. Syntax validation
python3 test_modules.py
# Expected: 19/19 tests PASSED ✅

# 2. Check display.py structure
python3 -c "import py_compile; py_compile.compile('display.py', doraise=True); print('✓ Syntax valid')"

# 3. Verify imports
grep "^from display import" code.py
# Should show all display functions imported

# 4. Check git status
git status
# Should be clean on claude/bonjour-01QpCeLBqbWrwtjckmieTfMy
```

**Expected Results**: All checks pass ✅

### 2. File Integrity Check

Verify all files are present and correct size:

```bash
ls -lh *.py | grep -E "(display|config|cache|utils|network|events|code)\.py"
```

**Expected sizes** (approximate):
- `display.py`: ~45-50 KB
- `config.py`: ~15-18 KB
- `utils.py`: ~12-15 KB
- `network.py`: ~25-28 KB
- `events.py`: ~22-25 KB
- `cache.py`: ~5-6 KB

---

## 🔧 Hardware Testing Plan

### Phase 1: Initial Boot Test (5-10 minutes)

**Objective**: Verify the device boots and displays without crashes

#### Steps:

1. **Deploy to device**:
   ```bash
   # Copy all .py files to CIRCUITPY drive
   cp *.py /Volumes/CIRCUITPY/
   ```

2. **Monitor serial output**:
   ```bash
   # Connect to serial console
   screen /dev/tty.usbmodem* 115200
   # OR
   tio /dev/ttyACM0
   ```

3. **Watch for startup sequence**:
   ```
   Expected log pattern:
   [timestamp] INFO: === STARTUP ===
   [timestamp] INFO: Display initialized: 64x32 @ 4-bit
   [timestamp] INFO: WiFi connected: <SSID>
   [timestamp] INFO: RTC synced
   [timestamp] INFO: Weather: <condition>, <temp>°C
   [timestamp] INFO: Forecast: <hours> hours (fresh)
   ```

#### Success Criteria:

- ✅ Device boots without Python errors
- ✅ Display initializes (log message appears)
- ✅ WiFi connects successfully
- ✅ Weather displays on screen
- ✅ No `ImportError` or `AttributeError` messages

#### Red Flags:

- ❌ `ImportError: cannot import name 'xxx' from 'display'`
- ❌ `AttributeError: module 'display' has no attribute 'xxx'`
- ❌ Display shows "Traceback" or error text
- ❌ Device reboots in a loop

---

### Phase 2: Display Function Testing (30-60 minutes)

**Objective**: Test each display function individually

#### Test Matrix

| Display Function | Test Scenario | Expected Result | Duration |
|------------------|---------------|-----------------|----------|
| **show_clock_display()** | Wait for weather failure or manual trigger | Date/time display with colored clock (error state) | 5 min |
| **show_weather_display()** | Normal operation | Weather icon, temp, UV/humidity bars, time | 5 min |
| **show_forecast_display()** | Normal cycle | 3-column forecast with temps and times | 5 min |
| **show_event_display()** | Create test event in events.csv | Event image, text, day indicator | Variable |
| **show_scheduled_display()** | Create test schedule | Schedule image, weather, progress bar | Variable |
| **show_color_test_display()** | Uncomment test mode in code.py | 12-color grid display | 30 sec |
| **show_icon_test_display()** | Uncomment test mode in code.py | 3 icons per screen, cycling | Variable |

#### Detailed Test Cases

##### Test 2.1: Clock Display

**Trigger**: Disconnect WiFi temporarily OR wait for weather API failure

**Steps**:
1. Note the clock color:
   - MINT = All OK (shouldn't happen if WiFi disconnected)
   - RED = WiFi failure ✅ (expected)
   - YELLOW = Weather API failure
   - PURPLE = Extended failure mode
   - WHITE = General error

2. Verify display shows:
   - Date in format: `MONTH DD` (e.g., "NOV 15")
   - Time in format: `H:MM:SS` (12-hour format)
   - Time updates every second
   - Day indicator (colored square top-right)

**Success**: Clock displays correctly with appropriate error color

##### Test 2.2: Weather Display

**Trigger**: Normal operation with weather data

**Steps**:
1. Verify weather icon displays (16x16 or 24x24 image)
2. Check temperature shows (large text, top-left)
3. Check time shows (bottom-right, updates every minute)
4. Verify UV bar (orange, top-left, varies by UV index)
5. Verify humidity bar (cyan, below UV bar)
6. Check day indicator (colored square, top-right)
7. If cached, temp should be LILAC color

**Success**: All elements display correctly, time updates smoothly

##### Test 2.3: Forecast Display

**Trigger**: Normal operation during forecast cycle

**Steps**:
1. Verify 3 columns display:
   - Column 1: Current weather icon + temp + current time
   - Column 2: Next hour icon + temp + time (e.g., "3P")
   - Column 3: Following hour icon + temp + time (e.g., "4P")

2. Check time label colors:
   - Column 2: DIMMEST_WHITE (immediate) or MINT (jumped ahead)
   - Column 3: DIMMEST_WHITE (immediate) or MINT (jumped ahead)

3. Verify column 1 time updates every minute
4. Check day indicator displays

**Success**: 3-column layout with correct times and colors

##### Test 2.4: Event Display

**Prerequisite**: Create test event in `events.csv`:
```csv
1115,Test Event,test.bmp,MINT,,,
```

**Steps**:
1. Place test event image in `/events/` directory
2. Wait for event cycle or restart device
3. Verify event image displays (top-right, 25x28)
4. Check text displays:
   - Line 1: "Test Event" (top, DIMMEST_WHITE)
   - Line 2: Event name (bottom, MINT or specified color)
5. Verify day indicator

**Success**: Event image and text display correctly

##### Test 2.5: Scheduled Display

**Prerequisite**: Create test schedule in `schedules.csv`:
```csv
Test Schedule,test_schedule.bmp,8,9,true
```

**Steps**:
1. Place schedule image in `/schedules/` directory
2. Trigger schedule (set time to 8:00-9:00) OR manually
3. Verify displays:
   - Schedule image (right side)
   - Weather icon (left, if available)
   - Temperature (left, LILAC if cached)
   - UV bar (if UV > 0)
   - Progress bar (bottom, fills left to right)
   - Time (bottom-left, updates)
   - Day indicator

4. Watch progress bar fill over time
5. Verify segment logging in serial output

**Success**: All elements display, progress bar animates

---

### Phase 3: Stress Testing (2-4 hours)

**Objective**: Validate stability over extended operation

#### Test 3.1: Normal Operation Soak Test

**Duration**: 2-4 hours
**Setup**: Let device run normally

**Monitor**:
1. **Serial logs** - Watch for:
   ```
   [timestamp] INFO: ## CYCLE N ##
   [timestamp] INFO: Displaying Weather: ...
   [timestamp] INFO: Displaying Forecast: ...
   [timestamp] Memory: XX% free
   ```

2. **Error counts** - Should remain zero or very low:
   ```
   consecutive_failures: 0
   socket errors: 0
   API failures: 0
   ```

3. **Memory trends**:
   ```bash
   # Extract memory stats from logs
   grep "Memory:" serial_output.log | tail -20
   ```
   - Should stay stable (10-15% free)
   - No gradual decline (memory leak)

4. **Cycle count** - Should increment steadily:
   ```
   Expected: 1 cycle every 5-10 minutes
   After 2 hours: ~12-24 cycles
   After 4 hours: ~24-48 cycles
   ```

**Success Criteria**:
- ✅ No crashes or reboots
- ✅ Memory stable (±2% variance)
- ✅ Error count remains low (<3 errors total)
- ✅ All displays cycle correctly

#### Test 3.2: WiFi Recovery Test

**Duration**: 30 minutes
**Setup**: Simulate WiFi interruption

**Steps**:
1. Note current cycle number
2. Turn off WiFi router
3. Watch device behavior:
   - Should show RED clock (WiFi error)
   - Should attempt reconnection (logs)
   - Should NOT crash

4. Turn WiFi router back on
5. Watch recovery:
   - Should reconnect within 2-5 minutes
   - Should resume weather display
   - Clock color should return to MINT (if weather succeeds)

**Success Criteria**:
- ✅ Device survives WiFi loss gracefully
- ✅ Reconnects automatically
- ✅ Resumes normal operation
- ✅ No socket exhaustion errors

#### Test 3.3: Weather API Failure Test

**Duration**: 15 minutes
**Setup**: Block weather API (if possible) OR wait for API failure

**Steps**:
1. Watch for weather API failure in logs:
   ```
   [timestamp] WARNING: Weather API request failed: ...
   ```

2. Verify fallback behavior:
   - Should show YELLOW clock (weather error)
   - Should retry with exponential backoff
   - Should use cached data if available

3. Wait for recovery:
   - Should eventually succeed
   - Should resume normal display

**Success Criteria**:
- ✅ Device handles API failures gracefully
- ✅ Fallback to clock display works
- ✅ Cached data used when fresh
- ✅ Automatic recovery when API available

---

### Phase 4: Visual Validation (15-30 minutes)

**Objective**: Verify all display elements are visually correct

#### Checklist

Use this checklist while watching the device:

**Weather Display**:
- [ ] Weather icon displays (correct size, centered)
- [ ] Temperature text (large, readable, correct value)
- [ ] Time text (updates every minute, correct format)
- [ ] UV bar (orange, correct length for UV index)
- [ ] Humidity bar (cyan, correct length)
- [ ] Day indicator (correct color for day of week)
- [ ] Cached indicator (LILAC temp when cached)

**Forecast Display**:
- [ ] 3 columns visible (evenly spaced)
- [ ] Icons load correctly (no missing/error icons)
- [ ] Temperatures match forecast data
- [ ] Times display in correct format (12-hour + AM/PM)
- [ ] Time colors indicate immediacy (MINT or WHITE)
- [ ] Column 1 time updates every minute
- [ ] Day indicator displays

**Clock Display**:
- [ ] Date displays (correct format, readable)
- [ ] Time displays (updates every second)
- [ ] Clock color matches error state
- [ ] Day indicator displays
- [ ] No visual glitches or artifacts

**Event Display** (if events exist):
- [ ] Event image displays (correct position, size)
- [ ] Event text readable (correct color, position)
- [ ] Text bottom-aligned (no overlap with image)
- [ ] Day indicator displays
- [ ] Multi-event cycling works (if multiple events)

**Schedule Display** (if schedules active):
- [ ] Schedule image displays (right side)
- [ ] Weather icon displays (left side, if weather available)
- [ ] Temperature displays (correct color if cached)
- [ ] UV bar (if UV > 0)
- [ ] Progress bar displays (bottom)
- [ ] Progress bar fills over time
- [ ] Time displays and updates
- [ ] Day indicator displays

---

## 📊 Success Metrics

### Quantitative Metrics

After testing period, collect these metrics:

```bash
# Extract from logs
grep "CYCLE" serial_output.log | wc -l
# Expected: Proportional to test duration (1 cycle per 5-10 min)

grep "ERROR" serial_output.log | wc -l
# Expected: 0-5 errors total

grep "Memory:" serial_output.log | tail -1
# Expected: 10-15% free (stable)

grep "API calls:" serial_output.log | tail -1
# Expected: <350 calls (within limits)
```

### Qualitative Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Stability** | ☐ Pass ☐ Fail | No crashes, reboots, or freezes |
| **Performance** | ☐ Pass ☐ Fail | Same speed as v2.0.6, no delays |
| **Memory** | ☐ Pass ☐ Fail | Stable 10-15% free, no leaks |
| **Visuals** | ☐ Pass ☐ Fail | All displays render correctly |
| **Error Handling** | ☐ Pass ☐ Fail | Graceful recovery from failures |
| **Network** | ☐ Pass ☐ Fail | WiFi stable, no socket exhaustion |

**Overall Assessment**: ☐ PASS ☐ FAIL

---

## 🚨 Known Issues to Watch For

### From Previous Versions (Should be FIXED)

These issues were fixed in v2.0.3-2.0.6 and should NOT reappear:

1. **Socket Exhaustion** (v2.0.5 fix)
   - Symptom: Device crashes after multiple weather API calls
   - Root cause: Socket pool not reused
   - Fix: Global socket pool + session reuse
   - **Test**: Run for 4+ hours, watch for crashes

2. **Response Object Leaks** (v2.0.3 fix)
   - Symptom: Gradual memory decline
   - Root cause: HTTP responses not closed
   - Fix: `response.close()` in try/finally blocks
   - **Test**: Monitor memory over 2+ hours

3. **API Key Exposure** (v2.1.0 fix)
   - Symptom: API key logged in plain text
   - Root cause: Debug logging
   - Fix: Removed API key logging
   - **Test**: Check logs for API key exposure

### New Issues to Watch For

Phase 4 refactoring could introduce:

1. **Import Errors**
   - Symptom: `ImportError` or `AttributeError` on boot
   - Cause: Missing function in display.py or incorrect import
   - **Test**: Check initial boot sequence

2. **Circular Import**
   - Symptom: Device hangs on boot, no display
   - Cause: display.py and code.py importing each other
   - **Test**: Boot test should catch immediately

3. **Missing Dependencies**
   - Symptom: `NameError` or `AttributeError` in display functions
   - Cause: Function uses variable/function not imported
   - **Test**: Exercise all display functions

---

## 🔄 Rollback Plan

If critical issues occur during testing:

### Option 1: Quick Rollback to v2.1.0 Pre-Phase 4

```bash
# Checkout previous commit (before Phase 4)
git checkout ec55e7f

# Copy to device
cp *.py /Volumes/CIRCUITPY/
```

### Option 2: Rollback to v2.0.6 (Last Stable)

```bash
# Checkout v2.0.6 tag (if exists)
git checkout v2.0.6

# OR revert to known-good commit
git log --oneline | grep "2.0.6"
git checkout <commit-hash>

# Copy to device
cp code.py /Volumes/CIRCUITPY/
```

### Option 3: Fix Forward

If issue is minor, fix in display.py and redeploy:

```bash
# Edit display.py
nano display.py

# Test locally
python3 test_modules.py

# Copy to device
cp display.py /Volumes/CIRCUITPY/
```

---

## 📝 Test Log Template

Use this template to document your testing session:

```markdown
# Phase 4 Testing Session

**Date**: YYYY-MM-DD
**Tester**: [Your Name]
**Device**: MatrixPortal S3 / [Your Device]
**Duration**: [Hours tested]

## Pre-Deployment Checks
- [ ] test_modules.py passed (19/19)
- [ ] Syntax validation passed
- [ ] Git status clean
- [ ] Files copied to device

## Phase 1: Initial Boot
- **Boot time**: [Timestamp]
- **Startup logs**: ☐ Clean ☐ Errors
- **Display initialized**: ☐ Yes ☐ No
- **WiFi connected**: ☐ Yes ☐ No
- **Weather displayed**: ☐ Yes ☐ No
- **Errors encountered**: [None / List errors]

## Phase 2: Display Functions
- **Clock display**: ☐ Pass ☐ Fail - [Notes]
- **Weather display**: ☐ Pass ☐ Fail - [Notes]
- **Forecast display**: ☐ Pass ☐ Fail - [Notes]
- **Event display**: ☐ Pass ☐ Fail ☐ N/A - [Notes]
- **Schedule display**: ☐ Pass ☐ Fail ☐ N/A - [Notes]

## Phase 3: Stress Testing
- **Duration**: [Hours]
- **Cycles completed**: [Count]
- **Errors encountered**: [Count] - [List]
- **Memory stability**: ☐ Stable ☐ Declining
- **WiFi recovery**: ☐ Pass ☐ Fail ☐ N/A
- **API failure recovery**: ☐ Pass ☐ Fail ☐ N/A

## Phase 4: Visual Validation
- **Weather elements**: ☐ All correct ☐ Issues
- **Forecast columns**: ☐ All correct ☐ Issues
- **Clock display**: ☐ Correct ☐ Issues
- **Event display**: ☐ Correct ☐ Issues ☐ N/A
- **Schedule display**: ☐ Correct ☐ Issues ☐ N/A

## Overall Assessment
- **Result**: ☐ PASS ☐ FAIL
- **Issues found**: [List]
- **Regression detected**: ☐ Yes ☐ No
- **Ready for production**: ☐ Yes ☐ No

## Notes
[Additional observations, screenshots, etc.]
```

---

## ✅ Test Completion Criteria

Phase 4 testing is complete when:

1. ✅ All display functions execute without errors
2. ✅ Device runs stable for 4+ hours
3. ✅ Memory remains stable (10-15% free)
4. ✅ No socket exhaustion errors
5. ✅ WiFi recovery works correctly
6. ✅ All visual elements render correctly
7. ✅ No regressions from v2.0.6
8. ✅ Test log completed and reviewed

**Sign-off**: Once all criteria met, Phase 4 is validated and ready for production deployment.

---

## 📞 Support

If issues occur during testing:

1. **Check logs** - Serial output has detailed error messages
2. **Review commits** - Compare with working version
3. **Test in isolation** - Comment out problem function, test others
4. **Document thoroughly** - Capture logs, screenshots, exact steps to reproduce

**Remember**: The goal is to validate, not to force it to work. If critical issues found, rollback and investigate offline.
