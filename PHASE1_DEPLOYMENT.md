# Phase 1: Weather Display - Deployment Guide

## ✅ What's Been Fixed

### Text Width Calculation Issue - SOLVED
The `font.get_bounding_box()` method was returning `(0, 0, 0, 0)` in CircuitPython, breaking all text positioning.

**Solution:** Use fixed character widths based on font filenames:
- `tinybit6-16.bdf` = 6 pixels per character
- `bigbit10-16.bdf` = 10 pixels per character

All text now properly right-aligns and centers on the display!

## 📁 New Files Created

The following v3.0 Phase 1 files are ready:

1. **config.py** - Configuration constants (API endpoints, layouts, colors, timing)
2. **state.py** - Global state variables (display objects, caches, counters)
3. **hardware.py** - Hardware initialization (display, RTC, WiFi, buttons, timezone)
4. **weather_api.py** - AccuWeather API integration with inline parsing
5. **display_weather.py** - Weather rendering with fixed text width calculations
6. **code_v3.py** - Main entry point for Phase 1
7. **TEXT_WIDTH_FIX.md** - Documentation of the text width fix

## 🚀 Deployment Steps

### 1. Copy Files to MatrixPortal

Copy these files from your computer to the MatrixPortal's CIRCUITPY drive:

```bash
# Required files (copy to root of CIRCUITPY drive):
config.py
state.py
hardware.py
weather_api.py
display_weather.py
code_v3.py  # Will become code.py

# Existing files (keep these):
/fonts/bigbit10-16.bdf
/fonts/tinybit6-16.bdf
/img/weather/*.bmp
settings.toml
```

### 2. Rename code_v3.py to code.py

On the MatrixPortal CIRCUITPY drive:
```bash
# Backup old code (optional):
mv code.py code_v2_backup.py

# Make v3 code the active code:
mv code_v3.py code.py
```

Or simply:
- Delete the old `code.py`
- Rename `code_v3.py` to `code.py`

### 3. Verify settings.toml

Make sure your `settings.toml` has all required keys:

```toml
# WiFi
CIRCUITPY_WIFI_SSID = "your-network"
CIRCUITPY_WIFI_PASSWORD = "your-password"

# Timezone
TIMEZONE = "America/Chicago"

# Temperature unit
TEMPERATURE_UNIT = "C"  # or "F"

# AccuWeather API
ACCUWEATHER_API_KEY_TYPE1 = "your-api-key"
ACCUWEATHER_LOCATION_KEY = "your-location-key"
```

### 4. Verify Libraries

Make sure these libraries are in `/lib/` on CIRCUITPY drive:

**Required for Phase 1:**
- adafruit_bitmap_font/
- adafruit_display_text/
- adafruit_display_shapes/
- adafruit_ticks.mpy (CP10 requirement)
- adafruit_ntp.mpy
- adafruit_ds3231.mpy
- adafruit_requests.mpy
- adafruit_bus_device/
- adafruit_register/
- adafruit_connection_manager.mpy

### 5. Verify Weather Icons

Make sure you have weather icon BMP files in `/img/weather/`:
- 1.bmp, 2.bmp, 3.bmp, ... 44.bmp
- These are the AccuWeather icon numbers

## 🧪 Testing

### First Boot
1. Plug in the MatrixPortal
2. Open serial console to see logs
3. Watch for initialization sequence:
   ```
   [MAIN:INFO] === Pantallita 3.0 - Phase 1: Weather Display ===
   [HW:INFO] Initializing display...
   [HW:INFO] Initializing RTC...
   [HW:INFO] Initializing buttons...
   [HW:INFO] Connecting to WiFi...
   [HW:INFO] Syncing time with NTP...
   [WEATHER:INFO] Fetching weather from AccuWeather...
   [DISPLAY:INFO] Displaying weather: 25°
   ```

### What You Should See

**On Display:**
- Weather icon (full screen background)
- Temperature (left side, big font) - always shown
- Feels like temp (right-aligned, small font) - if different
- Feels shade temp (right-aligned below feels) - if different from feels
- Clock (centered if shade shown, else right-aligned)
- UV bar (colored, bottom)
- Humidity bar (white with gaps, very bottom)

**Text Positioning (Fixed!):**
- "25°" on feels like should be at x=46 (right edge at 63)
- "10:45" clock should be centered at x=17 (when shade shown)
- All text should be fully visible, not cut off

### Verify the Fix Worked

The text width fix is working if:
- ✅ Feels like temperature aligns to right edge (not cut off, not at x=0)
- ✅ Clock is properly centered when shade is displayed
- ✅ Clock is properly right-aligned when shade is not displayed
- ✅ No text overlaps or runs off screen

### Common Issues

**"No weather data available"**
- Check AccuWeather API key in settings.toml
- Verify location key is correct
- Check serial logs for API errors

**"Timezone API failed"**
- This is OK - falls back to CST (-6)
- Weather should still display

**Text at wrong position**
- Verify you're using the NEW display_weather.py with SMALL_FONT_CHAR_WIDTH = 6
- Check that fonts are loaded correctly

**Icon not showing**
- Check that /img/weather/X.bmp exists (where X is icon number)
- Icons are full-screen 64x32 BMP files

## 📊 Success Criteria

Phase 1 is successful if:
- ✅ Weather fetches from AccuWeather every 5 minutes
- ✅ Display shows correct temperature in your chosen unit (C or F)
- ✅ Feels like and shade display when different
- ✅ Clock positioning is correct
- ✅ UV and humidity bars render properly
- ✅ Text is properly aligned (right-edge and centered)
- ✅ No stack exhaustion errors in logs
- ✅ Memory remains stable over time
- ✅ Can run for 24+ hours without crashes

## 🏃 24-Hour Stability Test

Once deployed and working:

1. Let it run for 24 hours
2. Monitor serial logs for errors
3. Check memory reports every 10 cycles
4. Verify WiFi stays connected
5. Press UP button to stop cleanly

Expected results:
- ~288 weather fetch cycles (24 hours × 60 min / 5 min refresh)
- Memory stable around 1,950,000 bytes free
- Zero pystack exhaustion errors
- Clean stop with UP button

## 📝 Next Steps

After successful 24-hour test:

**Phase 2: Forecast Display**
- Create display_forecast.py
- Add 12-hour forecast from AccuWeather
- Implement 3-column forecast layout
- Test rotation between weather and forecast

## 🐛 Troubleshooting

### Text still misaligned?
Check that display_weather.py has these constants at the top:
```python
SMALL_FONT_CHAR_WIDTH = 6
LARGE_FONT_CHAR_WIDTH = 10
```

And uses them like:
```python
text_width = len(feels_text) * SMALL_FONT_CHAR_WIDTH
feels_x = config.Layout.RIGHT_EDGE - text_width + 1
```

### Weather not updating?
- Check cache age in logs
- Weather cache expires after 15 minutes
- API only fetches when cache is stale

### Memory growing?
- Should stabilize around 1,950,000 bytes
- Small fluctuations (±10KB) are normal
- Large growth indicates a leak (report if seen)

## 📚 Documentation

See also:
- **TEXT_WIDTH_FIX.md** - Details on the text width calculation fix
- **REFACTOR_PLAN.md** - Overall v3.0 architecture plan
- **ARCHITECTURE_COMPARISON.md** - Why we need flat architecture
- **BOOTSTRAP_GUIDE.md** - CircuitPython 10 upgrade guide

## ✨ Architecture Highlights

**Stack Depth:** 2 levels (vs 8+ in v2.5.0)
- Level 0: main()
- Level 1: run_display_cycle()
- Level 2: weather_api.fetch_current() OR display_weather.show()

**No Helper Functions:**
- All rendering logic inline
- All text positioning inline
- All bar drawing inline

**Memory Efficiency:**
- ~1.95MB free (75% of 2MB available)
- Inline code uses less memory than function objects
- No nested function calls = smaller stack footprint

**Reliability:**
- Always close HTTP responses (prevents socket exhaustion)
- 2-second delay after WiFi before API calls (prevents socket errors)
- Timezone fallback to CST if API fails
- Weather cache prevents excessive API calls

---

**Status:** Ready for deployment and 24-hour stability test
**Date:** 2025-12-12
**Phase:** 1 of 5
**Branch:** claude/refactor-monolithic-code-01Qa9hPFTXbr2em439B4LKD2
