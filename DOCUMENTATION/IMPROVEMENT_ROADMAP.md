# Pantallita 2.0.0 - Code Improvement Roadmap

**Document Version:** 1.0
**Created:** 2025-11-13
**Audience:** AI agents assisting with code improvements, future development
**Purpose:** Prioritized roadmap to maximize existing codebase before continuing development

---

## Executive Summary

Pantallita 2.0.0 is a **functional, production-ready** dual RGB matrix weather display system that has demonstrated stability (300+ cycles, 25+ hours uptime). However, it was developed without formal code review, resulting in technical debt that should be addressed before major feature additions.

**Primary Risk:** Stack exhaustion ("pystack exhausted" errors)
**Secondary Issue:** Socket accumulation during long schedule displays (graceful degradation, but causes 20-40s recovery blackouts)
**Current State:** Working reliably for main functionality, occasional issues during edge cases

**This roadmap prioritizes improvements by:**
- **Risk Reduction:** Eliminate crash potential (stack exhaustion)
- **Effort vs. Return:** Quick wins before major refactors
- **Maintainability:** Enable future development without increasing complexity
- **Pragmatism:** This is a hobby project - don't over-engineer

---

## Project Context

### What Is This Project?

**Hardware:**
- Adafruit MatrixPortal S3 (ESP32-S3, 8MB flash, 2MB SRAM)
- 2× 64×32 RGB LED matrices (4-bit color)
- DS3231 RTC module
- CircuitPython 9.2.8

**Functionality:**
- Weather display with current conditions (AccuWeather API)
- 12-hour weather forecast with icons
- Event reminders (birthdays, holidays) with custom images
- Time-based scheduled displays (e.g., "Get Dressed" at 7:00 AM with progress bar)
- Automatic daily restart at 3 AM

**Scale:**
- Single 4117-line monolithic code.py file
- 12 weather icons cached in memory
- ~384 API calls/day (77% of 15K/month budget)
- 10-20% memory usage (healthy)
- No logging in production (CircuitPython read-only filesystem limitation)

**Current Issues:**
1. **Stack exhaustion risk** - Deep nesting (5-7 levels) causes "pystack exhausted" errors
2. **Socket accumulation** - Long schedules (2 hours) cause socket exhaustion, resulting in 20-40s blackouts during recovery
3. **No documentation** - Zero README until recent code review
4. **Resource leaks** - HTTP responses never explicitly closed
5. **Large functions** - 150-220 line functions are hard to maintain

---

## Current State Assessment

### ✅ What Works Well

| Aspect | Details |
|--------|---------|
| **Stability** | 300+ cycles, 25+ hours continuous operation |
| **Error Handling** | Graceful degradation - shows cached data when API fails |
| **Memory Management** | 10-20% usage, image cache (12 max), text cache (50 max) |
| **WiFi Recovery** | Automatic reconnection with exponential backoff |
| **Logging** | Clear, actionable log messages (development mode) |
| **Configuration** | CSV-based events/schedules (non-technical editing) |
| **Time Management** | RTC integration, timezone-aware, NTP sync |
| **User Experience** | Smooth transitions, clear display, readable fonts |

### ⚠️ Known Issues (Prioritized by Risk)

| Priority | Issue | Impact | Frequency |
|----------|-------|--------|-----------|
| **P0** | Stack exhaustion | System crash | Rare but catastrophic |
| **P1** | Socket accumulation in long schedules | 20-40s blackout during recovery | 2-hour schedules only |
| **P1** | Response objects not closed | Socket leaks, eventual exhaustion | Every API call (subtle) |
| **P2** | No structured testing | Bugs found in production | Continuous |
| **P2** | 4117-line monolithic file | Hard to navigate/maintain | Development only |
| **P3** | 150-220 line functions | Hard to understand/test | Development only |
| **P3** | Excessive API calls during schedules | Budget usage, unnecessary load | 2-hour schedules |

### 📊 Risk Assessment

**Stack Exhaustion:**
- 570 lines with 4+ indentation levels
- 200 lines with 5+ indentation levels
- Max nesting: 7 levels (in `show_scheduled_display`)
- Estimated stack frames: 8-9 deep
- **User quote:** "even a simple if would trip it"

**Socket Exhaustion:**
- 5 locations where response.close() missing
- 24 API calls during 2-hour schedule (1 per 5-min segment)
- No mid-schedule cleanup
- Weather fetched fresh every segment (should cache 15 min)

---

## Prioritized Improvement Roadmap

### Priority 0: Critical (Do First) - Stack Exhaustion Mitigation

**Goal:** Reduce stack depth by 30-40% to eliminate crash risk

**Effort:** 2-3 weeks (phased)
**Impact:** 🔴 Eliminates primary crash risk
**Dependencies:** None
**Status:** Analysis complete (CODE_FLATTENING_ANALYSIS.md)

#### Steps:

1. **Week 1: Implement Category A1-A4 Flattening** (High-Value Functions)
   - `fetch_weather_with_retries()` - Extract error handlers → helpers
   - `run_display_cycle()` - Extract schedule/normal cycle → separate functions
   - `show_scheduled_display()` - Extract weather/icon/progress rendering → helpers
   - `fetch_current_and_forecast_weather()` - Extract processing logic → helpers

   **Expected Gain:** 20-25% stack reduction

   **Implementation Pattern:**
   ```python
   # BEFORE (5 levels deep)
   def main_function():
       for attempt in retries:
           try:
               if check_wifi():
                   if get_session():
                       response = fetch()
                       if response.status_code == 200:
                           # Finally do work

   # AFTER (2 levels deep)
   def main_function():
       for attempt in retries:
           result = _attempt_fetch()  # Helper handles all logic
           if result:
               return result

   def _attempt_fetch():  # Isolated, testable
       if not check_wifi():
           return None
       session = get_session()
       if not session:
           return None
       # ... flat, early returns
   ```

2. **Week 2: Implement Category A5-A8 Flattening** (Display Functions)
   - `show_weather_display()` - Extract rendering → helpers
   - `show_forecast_display()` - Extract icon/text rendering → helpers
   - `show_event_display()` - Extract rendering → helpers
   - `draw_progress_bar()` - Simplify nested color logic

   **Expected Gain:** Additional 10-15% stack reduction

3. **Week 3: Testing & Validation**
   - 24-hour continuous test (no stack errors)
   - 2-hour schedule test (complete 24 segments)
   - Memory leak monitoring (memory usage should be stable)
   - Verify no functional regressions

#### Success Criteria:
- ✅ No "pystack exhausted" errors in 72-hour test
- ✅ Max nesting reduced from 7 to 3-4 levels
- ✅ Stack frames reduced from 8-9 to 5-6
- ✅ All existing functionality works identically

#### Reference Documents:
- `CODE_FLATTENING_ANALYSIS.md` - Detailed refactoring examples
- Functions to refactor are in code.py lines: 1272-1411, 3406-3625, 3879-4034

---

### Priority 1: High Impact - Socket Exhaustion Fixes

**Goal:** Eliminate socket leaks and 20-40s blackout recovery periods

**Effort:** 2 days
**Impact:** 🟠 Fixes user-visible issue (blackouts)
**Dependencies:** None (independent of stack fixes)
**Status:** ✅ COMPLETED (commit 5593803)

#### Steps:

1. ✅ **Add response.close() in 5 locations**
   - fetch_weather_with_retries() (~line 1293)
   - get_timezone_from_location_api() (~line 1148)
   - fetch_github_data() - 3 locations (~lines 2158, 2180, 2192)

2. ✅ **Implement mid-schedule cleanup**
   - Every 4 segments (20 minutes) during long schedules
   - Calls cleanup_global_session() + gc.collect()
   - Location: show_scheduled_display() (~line 3462)

3. ✅ **Add 15-minute weather caching for schedules**
   - Reduces API calls from 24 → ~8 per 2-hour schedule
   - Reuses cached weather for 3 segments (15 min)
   - Location: run_display_cycle() (~line 3968)

#### Success Criteria:
- ✅ 2-hour schedule completes all 24 segments
- ✅ No socket exhaustion errors
- ✅ No 20-40s blackout periods
- ✅ Weather updates appropriately (not stale)
- ✅ API calls reduced by ~25/day

---

### Priority 2: Quality of Life - Testing Framework

**Goal:** Catch issues before production deployment

**Effort:** 3-4 days
**Impact:** 🟡 Prevents production bugs, enables confident changes
**Dependencies:** Socket fixes complete (cleaner baseline)

#### Steps:

1. **Create TEST_PLAN.md** (1 day)

   Document systematic test scenarios:

   ```markdown
   ## Pre-Deployment Test Checklist

   ### Basic Functionality (30 min)
   - [ ] Weather cycle displays correctly
   - [ ] Forecast displays with icons
   - [ ] Events display on configured dates
   - [ ] RTC time is accurate
   - [ ] Display transitions smoothly

   ### Edge Cases (2 hours)
   - [ ] WiFi disconnection during API call → graceful fallback
   - [ ] API failure → uses cached data
   - [ ] Invalid API key → shows error state
   - [ ] Schedule overlap → correct priority
   - [ ] Midnight rollover → date changes correctly

   ### Stress Tests (24-72 hours)
   - [ ] 24-hour continuous operation → no crashes
   - [ ] 2-hour schedule → all 24 segments complete
   - [ ] Memory leak test → usage stays 10-20%
   - [ ] API budget test → <400 calls/day

   ### Regression Tests (before each deployment)
   - [ ] All basic functionality tests pass
   - [ ] No new errors in logs
   - [ ] Memory usage unchanged
   ```

2. **Create development_logs/ directory** (1 day)

   Enable logging during development testing:

   ```python
   # Add to startup (development only)
   if os.path.exists("/sd"):  # SD card present
       LOG_FILE = "/sd/pantallita.log"
       ENABLE_LOGGING = True
   ```

   Create log analysis scripts:
   - `parse_errors.py` - Extract error messages
   - `api_call_counter.py` - Count API calls per hour
   - `memory_trend.py` - Track memory usage over time

3. **Setup staging environment** (2 days)

   Test on device before production:
   - Use spare MatrixPortal or same device with test mode
   - Mock API for rapid testing (avoid hitting API limits)
   - Create `settings_test.toml` with test API key

   ```python
   # Add environment detection
   TEST_MODE = os.getenv("TEST_MODE", "0") == "1"

   if TEST_MODE:
       # Shorter timeouts, more verbose logging
       API.MAX_RETRIES = 2
       Timing.CYCLE_DURATION = 30  # 30s instead of 5 min
   ```

#### Success Criteria:
- ✅ TEST_PLAN.md exists with comprehensive test cases
- ✅ Can collect logs during development testing
- ✅ Pre-deployment checklist followed before each release
- ✅ Catch at least 1 bug before production (validates process)

#### Reference:
- CircuitPython doesn't have unittest - manual testing is standard
- Focus on systematic, repeatable test procedures
- Log collection requires SD card or USB serial capture

---

### Priority 3: Maintainability - Function Decomposition

**Goal:** Break 150-220 line functions into manageable 30-60 line units

**Effort:** 1 week
**Impact:** 🟡 Easier to understand, test, and modify
**Dependencies:** Stack flattening complete (avoids duplicate work)

#### Why After Stack Flattening?

Stack flattening (P0) already extracts many functions into helpers. Doing this work first means you'll decompose functions once, not twice.

#### Steps:

1. **Identify extraction opportunities** (1 day)

   Run analysis on remaining large functions:
   ```bash
   # Find functions >80 lines
   awk '/^def / {name=$0; line=NR; next}
        /^def / || /^class / {if (NR-line > 80) print line, name}
        END {if (NR-line > 80) print line, name}' code.py
   ```

   Target functions:
   - `draw_temperature_icon()` - Icon selection logic
   - `parse_events_csv_content()` - Parsing + validation
   - `parse_schedule_csv_content()` - Parsing + validation
   - `check_and_recover_wifi()` - Connection + recovery logic

2. **Extract pure logic functions** (2 days)

   Focus on stateless, easily testable functions:

   ```python
   # BEFORE: 120-line function with mixed concerns
   def parse_events_csv_content(text, rtc):
       # 20 lines of parsing
       # 30 lines of date validation
       # 40 lines of color parsing
       # 30 lines of time range handling

   # AFTER: 4 focused functions
   def parse_events_csv_content(text, rtc):
       """Orchestrate CSV parsing (30 lines)"""
       lines = _split_csv_lines(text)
       return [_parse_event_line(line, rtc) for line in lines]

   def _split_csv_lines(text):
       """Extract non-comment lines (10 lines)"""
       # Simple, testable

   def _parse_event_line(line, rtc):
       """Parse single event (30 lines)"""
       parts = line.split(',')
       return {
           'date': _parse_date(parts[0]),
           'color': _parse_color(parts[4]),
           'time_range': _parse_time_range(parts[5:])
       }

   def _parse_color(color_str):
       """Map color name to RGB (15 lines)"""
       # Isolated, easily testable
   ```

3. **Document function responsibilities** (1 day)

   Add docstrings to all extracted functions:
   ```python
   def _parse_color(color_str):
       """
       Convert color name to RGB tuple.

       Args:
           color_str: Color name (e.g., "RED", "BLUE", "BUGAMBILIA")

       Returns:
           tuple: (R, G, B) values 0-15 for 4-bit color

       Raises:
           ValueError: If color name not recognized
       """
   ```

4. **Update README with new structure** (1 day)

   Document the helper function pattern in README.md

#### Success Criteria:
- ✅ No functions >100 lines (except display orchestrators)
- ✅ Most functions 30-60 lines
- ✅ All extracted functions have docstrings
- ✅ Logic is easier to trace (subjective but noticeable)

#### Guidelines:
- Extract helpers with leading underscore: `_helper_name()`
- Keep helpers near parent function in file
- Don't extract if it creates more complexity than it solves
- Prioritize functions that will change frequently

---

### Priority 4: Architecture - Controlled Modularization

**Goal:** Split code.py into 3-5 focused modules **without breaking functionality**

**Effort:** 1-2 weeks
**Impact:** 🟢 Easier navigation, better organization
**Dependencies:** ALL previous priorities complete (stable baseline)
**Risk:** ⚠️ Highest risk of introducing bugs - save for last

#### Why Last?

Modularization is the lowest priority because:
1. **The monolith works** - It's stable, you know it
2. **Imports cost memory** - Need to measure actual overhead
3. **Highest refactor risk** - Easiest place to introduce bugs
4. **Benefits are development-time** - Doesn't improve runtime behavior

Do this ONLY after everything else is stable and tested.

#### Steps:

1. **Measure import overhead** (1 day)

   Test memory cost of imports before committing:

   ```python
   # test_import_overhead.py
   import gc

   gc.collect()
   baseline = gc.mem_free()
   print(f"Baseline free memory: {baseline}")

   # Import proposed modules
   import network_utils
   import display_rendering
   import api_client

   gc.collect()
   after_imports = gc.mem_free()
   overhead = baseline - after_imports

   print(f"Import overhead: {overhead} bytes ({overhead/1024:.1f} KB)")

   # Decision criteria:
   # < 50 KB  → Proceed with modularization
   # 50-100 KB → Acceptable, proceed cautiously
   # > 100 KB → Reconsider, monolith might be better
   ```

2. **Phase 1: Extract config.py** (2 days)

   Lowest-risk extraction - pure constants:

   ```python
   # config.py (150 lines)
   class Display:
       WIDTH = 64
       HEIGHT = 32
       BIT_DEPTH = 4

   class API:
       HTTP_OK = 200
       MAX_RETRIES = 5

   class Timing:
       CYCLE_DURATION = 300

   class Colors:
       # All color definitions

   class Strings:
       # All string constants
   ```

   In code.py:
   ```python
   from config import Display, API, Timing, Colors, Strings
   ```

   **Test:** 24-hour continuous operation, verify identical behavior

3. **Phase 2: Extract network_utils.py** (3 days)

   Network functions - high cohesion:

   ```python
   # network_utils.py (400 lines)
   def connect_to_wifi():
       """Connect to WiFi with retries"""

   def check_and_recover_wifi():
       """Check WiFi and reconnect if needed"""

   def get_requests_session():
       """Get or create requests session"""

   def cleanup_global_session():
       """Clean up session and sockets"""

   def fetch_weather_with_retries():
       """Fetch weather data with retry logic"""

   def fetch_github_data():
       """Fetch events and schedules from GitHub"""
   ```

   **Test:** API calls work, WiFi recovery works, 2-hour schedule completes

4. **Phase 3: Extract display_rendering.py** (3 days)

   Display functions - visual rendering:

   ```python
   # display_rendering.py (800 lines)
   def show_weather_display():
       """Render current weather"""

   def show_forecast_display():
       """Render 12-hour forecast"""

   def show_event_display():
       """Render event reminder"""

   def show_scheduled_display():
       """Render scheduled display with progress"""

   def draw_progress_bar():
       """Render progress bar"""

   def draw_temperature_icon():
       """Render temperature indicator"""
   ```

   **Test:** All display modes render correctly, no visual regressions

5. **Phase 4: Extract api_client.py** (Optional, 2 days)

   Only if memory overhead is <50 KB:

   ```python
   # api_client.py (200 lines)
   def fetch_current_weather_only():
       """Fetch current weather"""

   def fetch_current_and_forecast_weather():
       """Fetch weather + forecast"""

   def get_timezone_from_location_api():
       """Fetch timezone from location API"""

   def sync_time_with_timezone():
       """Sync RTC with NTP"""
   ```

6. **Final structure:**
   ```
   code.py              (2000 lines) - Main orchestration, state management
   config.py            (150 lines)  - Constants only
   network_utils.py     (400 lines)  - WiFi, sessions, HTTP
   display_rendering.py (800 lines)  - All visual rendering
   api_client.py        (200 lines)  - API-specific logic (optional)
   ```

#### Success Criteria:
- ✅ Import overhead measured and acceptable (<100 KB)
- ✅ 72-hour stability test passes
- ✅ All functionality identical to monolith
- ✅ No new bugs introduced
- ✅ Code is easier to navigate (find function in <10 seconds)

#### Rollback Plan:
If issues occur, revert to monolith:
```bash
git revert <modularization-commit>
git push -f origin <branch>
```

#### When to Skip This:
- If import overhead >100 KB
- If you're comfortable with monolith
- If not planning major new features

---

## Implementation Guidelines

### General Principles

1. **One Priority at a Time**
   - Complete P0 before starting P1
   - Test thoroughly between priorities
   - Don't mix refactoring with feature development

2. **Test Before and After Each Change**
   ```
   Before: 24-hour test → baseline behavior
   After:  24-hour test → verify identical behavior
   ```

3. **Keep a Working Branch**
   ```bash
   # Always have a known-good commit to revert to
   git tag stable-before-p0
   git tag stable-before-p1
   # ... etc
   ```

4. **Small, Incremental Changes**
   - Commit after each function refactored
   - Don't refactor 5 functions then test
   - Test after each commit

5. **Maintain Backwards Compatibility**
   - CSV formats should not change
   - Display behavior should be identical
   - Configuration should not require changes

### Development Workflow

```
1. Create feature branch:
   git checkout -b refactor/stack-flattening-a1

2. Make small change (1 function):
   - Refactor fetch_weather_with_retries()
   - Add helper functions

3. Test immediately:
   - Deploy to device
   - Run 30-min basic test
   - Check for errors

4. Commit if successful:
   git commit -m "Refactor: Flatten fetch_weather_with_retries from 5→2 levels"

5. Repeat for next function

6. After 4-5 functions, run 24-hour test:
   - If successful: merge to main
   - If issues: revert problematic commit

7. Start next batch
```

### Testing Protocol

**After Each Commit (30 min):**
- Deploy to device
- Verify display shows weather
- Check memory usage: `state.memory_monitor.check_memory()`
- Watch for any errors

**After Each Priority (24-72 hours):**
- Continuous operation test
- 2-hour schedule test (if applicable)
- Memory leak monitoring
- API call counting

**Before Declaring "Done" (1 week):**
- 7-day continuous operation
- Multiple 2-hour schedule completions
- No errors in logs
- Memory usage stable

---

## Success Metrics

### Overall Project Health

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| **Max Stack Depth** | 8-9 frames | 5-6 frames | Manual code review |
| **Max Nesting Level** | 7 levels | 3-4 levels | Count indentation |
| **Lines with 4+ indents** | 570 lines | <200 lines | grep -c "^\t\t\t\t" |
| **Lines with 5+ indents** | 200 lines | <50 lines | grep -c "^\t\t\t\t\t" |
| **Socket leaks** | 5 locations | 0 locations | Code review |
| **Longest function** | 220 lines | <100 lines | Manual review |
| **Functions >80 lines** | ~15 functions | <5 functions | Script analysis |
| **API calls during 2hr schedule** | 24 calls | ~8 calls | Log analysis |
| **Schedule blackout periods** | 20-40s | 0s | User observation |
| **Stack exhaustion crashes** | Occasional | Never | 7-day test |

### Per-Priority Success Criteria

**P0 (Stack Flattening):**
- No "pystack exhausted" in 72-hour test ✅
- Stack depth reduced 30-40% ✅
- All functionality unchanged ✅

**P1 (Socket Fixes):**
- 2-hour schedule completes without errors ✅
- No blackout periods ✅
- API calls reduced ~25/day ✅

**P2 (Testing):**
- TEST_PLAN.md exists ✅
- Pre-deployment checklist followed ✅
- Catch ≥1 bug before production ✅

**P3 (Function Decomposition):**
- No functions >100 lines ✅
- Code easier to navigate ✅
- All functions documented ✅

**P4 (Modularization):**
- Import overhead measured <100 KB ✅
- 72-hour stability test passes ✅
- No new bugs ✅

---

## Anti-Patterns to Avoid

### ❌ Don't Do This:

1. **Big Bang Refactoring**
   ```
   ❌ Refactor 10 functions → test once
   ✅ Refactor 1 function → test → commit → repeat
   ```

2. **Refactoring Without Testing**
   ```
   ❌ Change code → commit → deploy
   ✅ Change code → test 30 min → commit → deploy → test 24 hr
   ```

3. **Mixing Priorities**
   ```
   ❌ Flatten functions while modularizing
   ✅ Complete P0 entirely → then P1
   ```

4. **Changing Behavior "Opportunistically"**
   ```
   ❌ "While I'm here, let me change this logic..."
   ✅ Refactor structure only, preserve exact behavior
   ```

5. **Over-Engineering**
   ```
   ❌ "Let me add a plugin system for future extensibility"
   ✅ Solve the problems you have, not ones you might have
   ```

### ✅ Do This:

1. **Preserve Exact Behavior**
   - Refactoring changes structure, not behavior
   - Before/after should be functionally identical
   - Tests should catch any differences

2. **Commit Frequently**
   - One function refactored = one commit
   - Makes rollback easy
   - Creates clear history

3. **Test Incrementally**
   - Don't accumulate untested changes
   - 30-min test after each commit
   - 24-hr test after each batch

4. **Document as You Go**
   - Add docstrings when extracting functions
   - Update comments when changing structure
   - Keep README in sync

5. **Measure Before/After**
   - Memory usage
   - API call counts
   - Stack depth (manual review)

---

## Timeline Summary

| Priority | Description | Duration | Dependencies |
|----------|-------------|----------|--------------|
| **P0** | Stack flattening (8 functions) | 2-3 weeks | None - start immediately |
| **P1** | Socket exhaustion fixes | ✅ Done | None (already completed) |
| **P2** | Testing framework | 3-4 days | P1 complete |
| **P3** | Function decomposition | 1 week | P0 complete |
| **P4** | Modularization | 1-2 weeks | P0, P1, P2, P3 complete |

**Total Estimated Time:** 6-8 weeks (if doing all priorities)

**Minimum Viable Improvement:** P0 + P1 = ~3 weeks for critical fixes

---

## Next Steps

### Immediate Actions (This Week):

1. **Review CODE_FLATTENING_ANALYSIS.md**
   - Understand Category A refactoring patterns
   - Identify first function to refactor

2. **Test Socket Fixes (P1 - Already Deployed)**
   - Run 2-hour schedule test
   - Monitor for blackout periods
   - Verify weather caching works

3. **Create Test Plan (P2 - Start Now)**
   - Document current test procedure
   - Create TEST_PLAN.md from template above
   - Establish baseline metrics

### Month 1: Critical Fixes (P0 + P1)

- Week 1: Stack flattening A1-A4
- Week 2: Stack flattening A5-A8
- Week 3: Testing and validation
- Week 4: Create test plan and document

### Month 2: Quality Improvements (P2 + P3)

- Week 1: Implement testing framework
- Week 2-3: Function decomposition
- Week 4: Testing and documentation

### Month 3: Architecture (P4 - Optional)

- Week 1: Measure import overhead
- Week 2-3: Phased modularization
- Week 4: Final stability testing

---

## Context for AI Agents

### When Assisting with This Project:

**If asked to implement P0 (Stack Flattening):**
- Refer to CODE_FLATTENING_ANALYSIS.md for detailed examples
- Focus on Category A functions (no tradeoffs)
- Extract helpers with single responsibility
- Use early returns instead of nested if/else
- Test each function individually before moving to next

**If asked to implement P1 (Socket Fixes):**
- ✅ Already complete (commit 5593803)
- Review: code.py lines 1293, 1148, 2158, 2180, 2192, 3462, 3968

**If asked to implement P2 (Testing):**
- Create TEST_PLAN.md using template in this document
- Focus on manual testing (no unittest available)
- Emphasize systematic, repeatable procedures

**If asked to implement P3 (Function Decomposition):**
- Wait until P0 complete (avoid duplicate work)
- Target functions >80 lines
- Extract pure logic functions first (easiest to test)
- Add docstrings to all extracted functions

**If asked to implement P4 (Modularization):**
- Verify P0, P1, P2, P3 are complete first
- Measure import overhead before proceeding
- Start with config.py (lowest risk)
- Test 24 hours after each module extracted

### Key Files to Reference:

- **code.py** - Main application (4117 lines)
- **CODE_REVIEW_REVISED.md** - Socket exhaustion analysis
- **QUICK_FIX_GUIDE.md** - Socket fix implementation (completed)
- **CODE_FLATTENING_ANALYSIS.md** - Stack flattening strategy (P0)
- **README.md** - Full project documentation
- **This file (IMPROVEMENT_ROADMAP.md)** - Prioritized improvement plan

### Project Constraints:

- **Memory:** 2MB SRAM, currently 10-20% used, ~1800 KB available
- **API Budget:** 15K calls/month, currently ~384/day (77% used)
- **No logging in production:** CircuitPython read-only filesystem
- **No unit tests:** Manual testing only
- **Single user:** Don't over-engineer for scale

### Development Philosophy:

- **Working system:** Don't break what works
- **Incremental:** Small changes, test frequently
- **Pragmatic:** Hobby project, not enterprise software
- **Risk-focused:** Eliminate crashes, then improve maintainability

---

## Conclusion

This roadmap provides a systematic path from the current codebase to a more maintainable, stable system. The priorities balance risk reduction (P0: stack exhaustion) with quality improvements (P2-P4) while respecting the reality that this is a working hobby project, not a commercial product.

**Remember:** The system works today. These improvements reduce risk and enable future development, but they're not urgent. Take your time, test thoroughly, and don't break what works.

**Most Important:** Complete P0 (stack flattening) and P1 (socket fixes). Everything else is optional.

---

**Document Changelog:**
- 2025-11-13: Initial version (v1.0)
