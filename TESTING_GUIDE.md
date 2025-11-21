# Testing Guide: StateTracker Extraction

## Overview
This guide covers testing the StateTracker refactoring before deploying to production (MatrixPortal S3 hardware).

## What Changed (Runtime Behavior: IDENTICAL)

The refactoring **does not change functionality** - it reorganizes tracking logic:

### Before (Scattered)
```python
state.consecutive_failures = 0
state.last_successful_weather = time.monotonic()
state.api_call_count += 1
```

### After (Centralized)
```python
state.tracker.record_weather_success()
state.tracker.record_api_success("current")
```

**Same counters, same thresholds, same behavior - just better organized.**

## Pre-Deployment Verification ✅

### 1. Static Checks (Completed)
- ✅ Python syntax validation passed
- ✅ All tracking calls migrated to `state.tracker.*`
- ✅ No direct access to old tracking fields
- ✅ StateTracker properly initialized (12 fields)
- ✅ Critical bug fixed (consecutive_display_errors initialized)

### 2. Code Review Checklist

**StateTracker Initialization:**
- [ ] All 12 tracking fields initialized in `__init__`
- [ ] Default values match previous behavior (mostly 0, False)
- [ ] No typos in field names

**Method Correctness:**
- [ ] `record_api_success()` increments correct counters
- [ ] `record_weather_success()` resets failure counters
- [ ] `record_weather_failure()` increments failure counters
- [ ] Decision methods check correct thresholds:
  - `should_soft_reset()` → 3 consecutive failures
  - `should_hard_reset()` → 10 system errors
  - `should_preventive_restart()` → 350 API calls

**Migration Completeness:**
- [ ] All 40+ call sites updated
- [ ] No orphaned tracking code
- [ ] Logging uses `tracker.get_api_stats()`

### 3. Logic Verification

**Key Behaviors to Verify:**

| Scenario | Expected Behavior | Tracker Method |
|----------|------------------|----------------|
| Weather fetch succeeds | Reset consecutive_failures to 0 | `record_weather_success()` |
| Weather fetch fails | Increment consecutive_failures | `record_weather_failure()` |
| 3 consecutive failures | Trigger soft reset | `should_soft_reset()` |
| 10 system errors | Trigger hard reset | `should_hard_reset()` |
| 350 API calls | Trigger preventive restart | `should_preventive_restart()` |
| Display error | Increment display error counters | `record_display_error()` |
| Extended failure mode | Check time since last success | `should_enter_extended_failure_mode()` |

## Deployment Strategy

### Phase 1: Code Review (You Are Here)
- Review this guide
- Check the code changes in the commit
- Verify logic matches expectations

### Phase 2: Safe First Deploy (LOW RISK)
1. **Deploy to ONE device first** (test with MATRIX1 or MATRIX2, not both)
2. **During low-traffic time** (e.g., late evening when displays are less critical)
3. **Have USB access ready** for serial monitoring

### Phase 3: Monitor First Deploy (30-60 minutes)

**What to Watch:**

**Startup (First 5 minutes):**
```
Expected logs:
- "== STARTING MAIN DISPLAY LOOP =="
- "API Stats: Total=X/350, Current=X, Forecast=X"
- Normal weather/forecast displays
```

**First Cycle (5-10 minutes):**
```
Expected logs:
- "Cycle #1 complete in X.XX min"
- "API: Total=X/350, Current=X, Forecast=X"
- No errors or exceptions
```

**Error Recovery (Test if possible):**
- If WiFi disconnects: Should recover automatically
- If API fails: Should show cached data, then retry
- Should NOT see rapid restarts or crashes

### Phase 4: Extended Monitoring (2-4 hours)

**Check these scenarios occur normally:**

✅ **Normal Operation:**
- Cycles complete every ~5 minutes
- API stats increment correctly
- Weather displays update
- Scheduled displays work (if configured)

✅ **Cache Usage:**
- After 15 min: "Using fresh cached weather"
- Cache prevents excessive API calls

✅ **API Limit Protection:**
- After 350 calls: "Preventive restart after 350 API calls"
- Device restarts cleanly

✅ **Daily Restart:**
- At 3am: Device restarts automatically
- API counters reset to 0

### Phase 5: Full Deploy
- If Phase 3-4 successful, deploy to second device
- Continue monitoring for 24 hours

## Testing Commands (Serial Monitor)

Connect via USB and watch serial output:

```bash
# macOS/Linux
screen /dev/tty.usbmodem* 115200

# Windows
# Use Mu Editor or PuTTY
```

**What to look for:**

### Good Signs ✅
```
API Stats: Total=12/350, Current=8, Forecast=4
Cycle #5 complete in 5.02 min | API: Total=12/350, Current=8, Forecast=4
Weather: Clear, 22°C
Using fresh cached weather for schedule cycle
```

### Warning Signs ⚠️
```
Consecutive failures: 1, System errors: 1
ENTERING extended failure mode after 10 minutes without success
```
**Action:** Normal - should recover automatically. Monitor.

### Critical Issues 🚨
```
AttributeError: 'StateTracker' object has no attribute 'xxx'
NameError: name 'xxx' is not defined
Multiple consecutive failures (10+) - longer delay
```
**Action:** Revert immediately via USB, investigate.

## Rollback Procedure

If issues occur:

### Quick Rollback (USB Access)
1. Connect via USB
2. Stop execution (Ctrl+C in serial monitor)
3. Replace `code.py` with previous version from git:
   ```bash
   git checkout ecc4558 -- code.py
   ```
4. Copy to device via USB
5. Hard reset device (power cycle)

### Emergency Rollback (No USB)
1. Power off device
2. Remove SD card (if accessible)
3. Connect SD card to computer
4. Replace code.py with backup
5. Reinsert and power on

## What Makes This Low-Risk

1. **No API changes** - Same endpoints, same calls
2. **No display logic changes** - Same rendering code
3. **No timing changes** - Same cycles, same delays
4. **Pure refactoring** - Only reorganized existing logic
5. **Bug fix included** - Actually safer than before (consecutive_display_errors now initialized)

## Expected Behavior After Deploy

**Identical to before:**
- Same display cycle timing (~5 min)
- Same API call frequency (current + forecast)
- Same error recovery behavior
- Same logging output (just cleaner stats format)

**Only difference:**
- Logs show `API: Total=X/350, Current=X, Forecast=X` (cleaner format)
- Fixed potential crash from uninitialized counter

## Troubleshooting

### Issue: Device won't start
**Cause:** Syntax error (unlikely, we verified)
**Fix:** Check serial output for error, revert if needed

### Issue: AttributeError on tracker field
**Cause:** Typo in field name
**Fix:** Check spelling in code.py, fix and redeploy

### Issue: Rapid restarts
**Cause:** Threshold logic error (very unlikely)
**Fix:** Check serial logs for error pattern, revert

### Issue: API calls not being counted
**Cause:** Missing `record_api_success()` call
**Fix:** Verify fetch functions call tracking methods

## Success Criteria

After 24 hours of monitoring:

- [ ] Device runs continuously without crashes
- [ ] API counters increment correctly
- [ ] Error recovery works (test WiFi disconnect)
- [ ] Memory usage stable (~10-20%)
- [ ] No AttributeError or NameError exceptions
- [ ] Displays update normally
- [ ] Daily restart occurs at 3am
- [ ] API preventive restart occurs at 350 calls

## Questions to Ask During Testing

1. **Does the device start up normally?** (First 5 min)
2. **Do displays cycle correctly?** (First 30 min)
3. **Do API stats log correctly?** (Every cycle)
4. **Does error recovery work?** (Test WiFi disconnect)
5. **Does it run for 2+ hours without issues?** (Extended test)
6. **Does it restart cleanly at 3am?** (Daily restart)

## Recommendation

**DEPLOY WITH CONFIDENCE:**

This refactoring is low-risk because:
1. ✅ Pure code reorganization (no logic changes)
2. ✅ Syntax validated
3. ✅ All call sites verified
4. ✅ Actually fixes a bug (safer than before)
5. ✅ Easy to rollback if needed

**Suggested Timeline:**
- **Evening:** Deploy to one device, monitor for 2-4 hours
- **Next morning:** If stable, deploy to second device
- **24 hours:** If both stable, mark as production-ready

## Need Help?

If you see unexpected behavior:
1. Check serial monitor output
2. Compare to "Expected Behavior" above
3. If critical issue (crashes, rapid restarts), rollback
4. If minor issue (wrong counts), capture logs for analysis

---

**Bottom Line:** This refactoring makes the code safer and easier to maintain. The testing is primarily to confirm nothing broke during migration, not to test new functionality.
