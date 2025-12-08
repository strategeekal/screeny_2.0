# Pantallita 3.0 Refactoring Plan

## Overview
Complete rewrite with proper CircuitPython architecture, upgrading to CircuitPython 10.0.1

## Principles
1. **Flat call chains** - Main loop calls modules directly, no nesting
2. **Inline rendering** - Display functions have no helper functions
3. **Separate fetch from render** - Data fetching in API modules, rendering in display modules
4. **Zero-cost constants** - All config in separate module
5. **Minimal abstraction** - Only abstract what saves significant stack depth

## Phase 1: Foundation & Weather Display

### Step 1.1: Upgrade to CircuitPython 10
- [ ] Flash TinyUF2 0.33.0 bootloader to test MatrixPortal
- [ ] Install CircuitPython 10.0.1
- [ ] Test basic functionality (LED, display, WiFi)
- [ ] Validate 24-hour stability

### Step 1.2: Create Module Structure
- [ ] Create `config.py` - All constants
- [ ] Create `state.py` - Global state (WeatherDisplayState equivalent)
- [ ] Create `hardware.py` - Display, RTC, WiFi, button initialization
- [ ] Create `network.py` - HTTP session management
- [ ] Create `weather_api.py` - Weather data fetching
- [ ] Create `display_weather.py` - Weather rendering (inline everything)
- [ ] Create minimal `code.py` - Main loop only

### Step 1.3: Implement Current Weather Display
- [ ] `config.py`: Display constants, colors, API keys
- [ ] `state.py`: Main group, font, caches
- [ ] `hardware.py`: Initialize display, RTC, WiFi, buttons
- [ ] `network.py`: Session creation, fetch helper (NO retries in v1)
- [ ] `weather_api.py`: Fetch current weather, parse response
- [ ] `display_weather.py`: Render weather (inline image, text, bars)
- [ ] `code.py`: Connect WiFi → Fetch weather → Show weather → Loop

### Step 1.4: Test & Validate
- [ ] Run for 24 hours on test matrix
- [ ] Monitor memory usage
- [ ] Check stack depth (add logging)
- [ ] Verify WiFi recovery
- [ ] Test button stop functionality

**Success Criteria:** Weather display runs 24+ hours without crashes

## Phase 2: Forecast Display (Week 2)

### Step 2.1: Add Forecast Fetching
- [ ] `weather_api.py`: Add `fetch_forecast()` function
- [ ] Parse 12-hour forecast data
- [ ] Implement smart column selection logic (inline, no helpers)
- [ ] Cache forecast data with timestamps

### Step 2.2: Implement Forecast Rendering
- [ ] Create `display_forecast.py`
- [ ] Inline ALL positioning logic (no calculate_position helpers)
- [ ] Inline image loading (no load_bmp_image wrapper)
- [ ] Inline text rendering (no right_align_text helper)
- [ ] 3-column layout with precipitation detection

### Step 2.3: Integrate with Main Loop
- [ ] `code.py`: Add forecast to display rotation
- [ ] Implement display cycle timing
- [ ] Add forecast cache age checking

### Step 2.4: Test & Validate
- [ ] Test column selection logic (various weather conditions)
- [ ] Verify image loading fallback (missing icons)
- [ ] Run for 24 hours
- [ ] Compare stack depth to Phase 1

**Success Criteria:** Weather + Forecast rotation runs 24+ hours, no stack exhaustion

## Phase 3: Stock Market Display (Week 3)

### Step 3.1: Add Stock Fetching
- [ ] Create `stocks_api.py`
- [ ] Load stocks.csv (local and GitHub)
- [ ] Implement `fetch_batch_quotes()` for multi-stock
- [ ] Implement `fetch_intraday_chart()` for chart mode
- [ ] Market hours detection (inline, no timezone helpers)
- [ ] Cache management (per-stock, 15-min expiry)

### Step 3.2: Implement Stock Rendering
- [ ] Create `display_stocks.py`
- [ ] Multi-stock rotation mode (inline layout)
- [ ] Single stock chart mode (inline chart rendering)
- [ ] Triangle arrows (inline)
- [ ] Price formatting (inline, no helpers)
- [ ] Smart rotation logic

### Step 3.3: Test & Validate
- [ ] Test during market hours (fresh data)
- [ ] Test outside market hours (cached data)
- [ ] Test weekend behavior
- [ ] Test all asset types (stock, forex, crypto, commodity)
- [ ] Verify chart rendering with various price ranges
- [ ] Run for 48 hours (include weekend)

**Success Criteria:** Stocks display works in all market conditions, no stack exhaustion

## Phase 4: Remaining Displays (Week 4)

### Step 4.1: Events & Schedules
- [ ] Create `data_loader.py` for CSV parsing
- [ ] Load events.csv (local and GitHub)
- [ ] Load schedules.csv (local and GitHub)
- [ ] Create `display_other.py`
- [ ] Implement events display (inline)
- [ ] Implement schedules display (inline)
- [ ] Implement clock display (fallback)

### Step 4.2: CTA Transit
- [ ] Create `transit_api.py`
- [ ] Fetch train arrivals
- [ ] Fetch bus arrivals
- [ ] Combine and sort arrivals
- [ ] Add transit rendering to `display_other.py`

### Step 4.3: Main Loop Logic
- [ ] Schedule detection
- [ ] Display rotation logic
- [ ] Frequency controls
- [ ] Time-based filtering (commute hours, event hours)

### Step 4.4: Test & Validate
- [ ] Test full rotation cycle
- [ ] Test schedule priority
- [ ] Test transit display during commute hours
- [ ] Test event time filtering
- [ ] Run for 72 hours (full weekend test)

**Success Criteria:** All displays work, proper rotation, 72+ hour uptime

## Phase 5: Error Handling & Polish (Week 5)

### Step 5.1: Defensive Error Handling
- [ ] WiFi recovery with exponential backoff
- [ ] API retry logic (weather, stocks, transit)
- [ ] Cached data fallback
- [ ] Socket cleanup on errors
- [ ] Session recreation on failures

### Step 5.2: Monitoring & Logging
- [ ] Memory monitoring (report every 100 cycles)
- [ ] API call tracking (per service)
- [ ] Stack depth logging (at key checkpoints)
- [ ] Error state logging

### Step 5.3: Daily Restart & Maintenance
- [ ] 3am daily restart logic
- [ ] GitHub data refresh at restart
- [ ] Cache cleanup
- [ ] API counter reset

### Step 5.4: Production Deployment
- [ ] Deploy to production matrix
- [ ] Run side-by-side with v2.5.0 for comparison
- [ ] Monitor for 1 week
- [ ] Fix any issues
- [ ] Deploy to all matrices

**Success Criteria:** 7+ day uptime, no manual intervention required

## Stack Depth Budget

**CircuitPython 10 Stack Budget:** ~32 levels (increased from 25)

### Level Allocation:
- Framework overhead: 10 levels
- Main loop (code.py): 2 levels (main → run_cycle)
- Module calls: 1 level per module (fetch, render)
- Display rendering: 5 levels max (inline everything)
- **Reserve:** 14 levels (44% headroom)

### Critical Rules:
1. `code.py` calls modules directly - NO wrapper functions
2. Display modules have ZERO helper functions - inline everything
3. API modules can have 1 level of helpers (parse_response called from fetch)
4. NEVER nest try/except more than 1 level deep
5. Avoid f-strings in deep code (they add stack depth)

## Memory Budget

**ESP32-S3 SRAM:** 2MB total
**CircuitPython 10 Usage:** ~400KB (framework + libraries)
**Available:** ~1.6MB

### Module Import Costs (Estimated):
- config.py: ~50KB (constants only)
- state.py: ~100KB (data structures)
- hardware.py: ~80KB (initialization)
- network.py: ~100KB (session management)
- weather_api.py: ~80KB (fetch + parse)
- stocks_api.py: ~120KB (fetch + parse + cache)
- transit_api.py: ~60KB (fetch + parse)
- display_weather.py: ~100KB (rendering)
- display_forecast.py: ~120KB (rendering + logic)
- display_stocks.py: ~150KB (rendering + chart)
- display_other.py: ~150KB (events + schedules + transit + clock)

**Total Module Cost:** ~1.11MB
**Runtime Caches:** ~100KB (images, text widths, API data)
**Total Usage:** ~1.6MB / 2MB = 80%
**Reserve:** ~400KB (20% headroom)

## Testing Protocol

### Per-Phase Testing:
1. **Unit test:** Test module in isolation (if possible)
2. **Integration test:** Test with previous phases
3. **24-hour stability test:** Run on test matrix
4. **Stack depth check:** Log max depth during test
5. **Memory check:** Monitor for leaks
6. **Error injection:** Disconnect WiFi, kill API, etc.

### Final Validation:
1. **7-day production test:** One matrix, full feature set
2. **Multi-matrix test:** Deploy to 3 matrices, verify consistency
3. **Holiday/weekend test:** Verify market hours, transit hours, event filtering
4. **Friend deployment:** Gift matrices, monitor remotely for 2 weeks

## Rollback Plan

Keep v2.5.0 code in `code_v2.5.0.py` on device. If v3.0 fails:
1. Rename `code.py` to `code_v3.0.py`
2. Rename `code_v2.5.0.py` to `code.py`
3. Reset device
4. System boots with stable v2.5.0

## Success Metrics

### Primary Goals:
- [ ] 7+ day uptime without manual intervention
- [ ] Zero pystack exhaustion errors
- [ ] Zero socket exhaustion errors
- [ ] All displays functional

### Learning Goals:
- [ ] Understand CircuitPython stack limitations
- [ ] Learn proper module architecture for embedded systems
- [ ] Master inline optimization techniques
- [ ] Document lessons learned for future projects

### Stretch Goals:
- [ ] 30-day uptime
- [ ] Add new feature without stack exhaustion
- [ ] Deploy to 3+ friend matrices successfully
- [ ] Create reusable template for future CircuitPython projects

## Notes

- Document every stack exhaustion error (even during development)
- Measure stack depth at each checkpoint
- Keep refactoring journal for lessons learned
- Take before/after metrics (lines of code, memory usage, stack depth)
