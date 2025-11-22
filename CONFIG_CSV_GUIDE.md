# Display Configuration CSV Guide

## Overview

Display settings can now be controlled via CSV files, enabling remote configuration without USB access.

## Configuration Methods

### 1. Local File (Always Available)
**File:** `display_config.csv` (on device SD card)
**Priority:** Fallback if GitHub unavailable

### 2. GitHub Remote (Optional)
**Files:**
- `matrix1_config.csv` - For MATRIX1 device
- `matrix2_config.csv` - For MATRIX2 device

**Priority:** Checked first at startup

## Setup

### Step 1: Add URLs to settings.toml (Optional)

```toml
# Optional - for remote config
MATRIX1_CONFIG_URL = "https://raw.githubusercontent.com/user/repo/main/matrix1_config.csv"
MATRIX2_CONFIG_URL = "https://raw.githubusercontent.com/user/repo/main/matrix2_config.csv"
```

**If not set:** Uses local `display_config.csv` only

### Step 2: Create GitHub Config Files (Optional)

Create `matrix1_config.csv` and `matrix2_config.csv` in your GitHub repo with the same format as `display_config.csv`.

## CSV Format

```csv
# Display Configuration
# Format: setting,value
# Boolean values: 1 = True, 0 = False

# Core displays
show_weather,1
show_forecast,1
show_events,1

# Display elements
show_weekday_indicator,1
show_scheduled_displays,1
show_events_in_between_schedules,1
night_mode_minimal_display,1

# Safety features
delayed_start,0
```

## Available Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `show_weather` | Boolean | Display current weather | 1 (on) |
| `show_forecast` | Boolean | Display 12-hour forecast | 1 (on) |
| `show_events` | Boolean | Display calendar events | 1 (on) |
| `show_weekday_indicator` | Boolean | Show day-of-week colored square | 1 (on) |
| `show_scheduled_displays` | Boolean | Enable scheduled displays | 1 (on) |
| `show_events_in_between_schedules` | Boolean | Show events between schedule segments | 1 (on) |
| `night_mode_minimal_display` | Boolean | Hide weather icon & weekday indicator during night mode schedules | 1 (on) |
| `delayed_start` | Boolean | 10-second startup delay (boot loop protection) | 0 (off) |

**Note:** Dev/test settings (`use_live_weather`, `use_live_forecast`, `use_test_date`, `show_color_test`, `show_icon_test`) are hardcoded in `DisplayConfig` class and cannot be changed via CSV (they require USB access to modify code).

## How It Works

### Startup Sequence

1. **Device boots**
2. **Matrix ID detected** (MATRIX1 or MATRIX2)
3. **Try GitHub config:**
   - If URL configured: Fetch `matrix1_config.csv` or `matrix2_config.csv`
   - If found: Apply settings
   - If 404 or error: Continue to fallback
4. **Try local config:**
   - Load `display_config.csv` from device
   - Apply settings if found
5. **Use defaults:**
   - If no config found, use hardcoded defaults (all enabled)

### Logging

```
Loading display configuration...
GitHub config loaded for MATRIX1: 8 settings
Applied 8 config settings to display_config
```

Or:

```
Loading display configuration...
No GitHub config URL set for MATRIX1
Display config loaded from local file
Applied 8 config settings to display_config
```

## Use Cases

### Remote Testing
Disable displays remotely without USB:
```csv
show_weather,0
show_forecast,0
show_events,0
```
Push to GitHub → Device restarts at 3am → Config applied

### Per-Device Control
**matrix1_config.csv** (Living room):
```csv
show_events,1
show_scheduled_displays,1
```

**matrix2_config.csv** (Bedroom):
```csv
show_events,0
show_scheduled_displays,0
show_weekday_indicator,0
```

## Network Impact

**HTTP Requests:** 1 per startup (if GitHub URL configured)
**Socket Usage:** Same pattern as schedule/event loading
**Fallback:** Always uses local file if GitHub fails

## Refresh Frequency

**Current:** Startup only (once at boot, once at 3am daily restart)
**Why:** Minimizes HTTP requests and socket usage

**Future Option:** Could add mid-day refresh, but adds:
- 1 extra HTTP request/day
- Slight socket usage increase
- More complexity

**Recommendation:** Start with startup-only, add refresh if needed.

## Troubleshooting

### Config not loading

**Check logs:**
```
Failed to load display_config.csv: [Errno 2] No such file or directory
```
**Solution:** Create `display_config.csv` on device

### GitHub config not loading

**Check logs:**
```
No GitHub config URL set for MATRIX1
```
**Solution:** Add `MATRIX1_CONFIG_URL` to `settings.toml`

### Settings not applying

**Check logs:**
```
Applied 0 config settings to display_config
```
**Solution:** Verify CSV format (no extra spaces, correct setting names)

### Socket errors after adding config

**Unlikely** - follows proven pattern (1 HTTP request at startup)
**If occurs:** Remove GitHub URL, use local file only

## Migration from Hardcoded

**Before:** Settings in code (lines 385-406)
```python
self.show_weather = True
self.show_forecast = True
```

**After:** Settings loaded from CSV
```csv
show_weather,1
show_forecast,1
```

**Backwards Compatible:** If no CSV found, uses hardcoded defaults

## Stack Safety

✅ **Same depth as schedule loading** (proven safe)
✅ **No nested exception handlers**
✅ **Flat loops, no recursion**
✅ **Single try/except level**

No pystack exhaustion risk.

## Example Workflow

### Setup GitHub Remote Control

1. **Create config files in GitHub repo:**
   ```
   matrix1_config.csv
   matrix2_config.csv
   ```

2. **Add URLs to settings.toml on each device:**
   ```toml
   MATRIX1_CONFIG_URL = "https://raw.githubusercontent.com/strategeekal/pantallita-events/main/matrix1_config.csv"
   ```

3. **Restart device** (or wait for 3am restart)

4. **Verify in logs:**
   ```
   GitHub config loaded for MATRIX1: 12 settings
   ```

### Change Settings Remotely

1. **Edit config in GitHub** (e.g., disable weather)
   ```csv
   show_weather,0
   ```

2. **Commit and push**

3. **Wait for device restart** (3am or manual)

4. **Settings applied** at next boot

## Benefits

✅ **Remote control** - Change settings without USB
✅ **Per-device** - Independent config for each matrix
✅ **Fallback** - Local file if GitHub unavailable
✅ **Git tracked** - Version control for configs
✅ **Simple** - CSV format, easy to edit
✅ **Safe** - Minimal HTTP requests, proven pattern

## Next Steps

1. ✅ **Local file created** - `display_config.csv` ready to use
2. **Optional:** Add GitHub URLs to `settings.toml`
3. **Optional:** Create GitHub config files
4. **Test:** Restart device, check logs for config loading
5. **Verify:** Confirm settings applied correctly

---

**Note:** Settings only load at startup. To apply changes, device must restart (3am automatic or manual power cycle).
