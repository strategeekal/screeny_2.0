# Image Loading Analysis - Extraction Opportunities

## Current State

### Components
1. **ImageCache class** (lines 619-659) - ✅ Well-designed, centralized
2. **load_bmp_image()** (line 1926) - ✅ Simple helper, works well
3. **Image loading with fallback** - ❌ **DUPLICATED 5 TIMES**
4. **TileGrid creation** - ❌ **DUPLICATED 8+ TIMES**

## Duplication Patterns Found

### Pattern 1: Load with Blank Fallback (5 occurrences)

**Location 1 - Weather Icon (line 2734):**
```python
bitmap, palette = state.image_cache.get_image(f"{Paths.WEATHER_ICONS}/{icon}.bmp")
if bitmap is None:
    log_warning(f"Icon {icon} failed, trying blank")
    bitmap, palette = state.image_cache.get_image(Paths.BLANK_WEATHER)
    if bitmap is None:
        log_error(f"Blank fallback failed, skipping icon")
        return
```

**Location 2 - Event Image (line 2939):**
```python
bitmap, palette = state.image_cache.get_image(image_file)
if bitmap is None:
    log_warning(f"Event image failed, trying blank")
    bitmap, palette = state.image_cache.get_image(Paths.BLANK_EVENT)
    if bitmap is None:
        log_error(f"Event blank fallback failed, skipping event")
        return False
```

**Location 3 - Forecast Column (line 3312):**
```python
bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{col['image']}")
if bitmap is None:
    log_warning(f"Forecast column {i+1} image failed, trying blank")
    bitmap, palette = state.image_cache.get_image(Paths.BLANK_COLUMN)
    if bitmap is None:
        log_error(f"Blank fallback failed for column {i+1}, skipping")
        continue
```

**Location 4 - Schedule Weather Icon (line 3641):**
```python
bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{weather_icon}")
if bitmap is None:
    log_warning(f"Schedule weather icon {weather_icon} failed, trying blank")
    bitmap, palette = state.image_cache.get_image(Paths.BLANK_COLUMN)
    if bitmap is None:
        log_error(f"Schedule weather blank fallback failed, skipping icon")
        return None
```

**Location 5 - Forecast Column Loop (line 3159):**
```python
bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{icon_num}.bmp")
# No fallback here - potential bug!
```

**Lines of duplication: ~40 lines (8 lines × 5 occurrences)**

### Pattern 2: TileGrid Creation (8+ occurrences)

Repeated everywhere:
```python
image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
image_grid.x = some_x
image_grid.y = some_y
state.main_group.append(image_grid)
```

**Lines of duplication: ~32 lines (4 lines × 8 occurrences)**

### Pattern 3: Schedule Image (Special Case - line 3673)

**INCONSISTENCY:**
```python
# Schedule image doesn't use cache (bypasses ImageCache!)
bitmap, palette = load_bmp_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
```

All others use `state.image_cache.get_image()` - this one doesn't.

## Problems Identified

### 1. Code Duplication ❌
- Load-with-fallback pattern: **~40 lines duplicated**
- TileGrid creation: **~32 lines duplicated**
- **Total waste: ~70 lines** that could be 2 helper functions

### 2. Inconsistent Error Handling ❌
- Some use `return`, some use `continue`, some use `return False`
- Different log message formats
- Inconsistent blank fallback paths

### 3. Cache Bypass Bug ❌
- Schedule images bypass cache (line 3673)
- Loads same schedule image repeatedly during segmented displays
- Wastes memory and CPU

### 4. Missing Fallback ❌
- Forecast column loop (line 3159) has no blank fallback
- Will fail silently if icon missing

## Extraction Opportunities

### High Value Extractions

#### 1. `load_image_with_fallback()` - **HIGH IMPACT**

**Before (8 lines each, 5 locations = 40 lines):**
```python
bitmap, palette = state.image_cache.get_image(f"{Paths.WEATHER_ICONS}/{icon}.bmp")
if bitmap is None:
    log_warning(f"Icon {icon} failed, trying blank")
    bitmap, palette = state.image_cache.get_image(Paths.BLANK_WEATHER)
    if bitmap is None:
        log_error(f"Blank fallback failed")
        return None
return bitmap, palette
```

**After (1 line each, 5 locations = 5 lines):**
```python
bitmap, palette = load_image_with_fallback(
    f"{Paths.WEATHER_ICONS}/{icon}.bmp",
    Paths.BLANK_WEATHER,
    "weather icon"
)
```

**Savings: ~35 lines** (40 → 5 + 15 line helper)

#### 2. `create_tilegrid()` - **MEDIUM IMPACT**

**Before (4 lines each, 8 locations = 32 lines):**
```python
image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
image_grid.x = some_x
image_grid.y = some_y
state.main_group.append(image_grid)
```

**After (1 line each, 8 locations = 8 lines):**
```python
create_tilegrid(bitmap, palette, x=some_x, y=some_y)
```

**Savings: ~18 lines** (32 → 8 + 6 line helper)

#### 3. Fix Schedule Image Caching - **BUG FIX**

**Before:**
```python
bitmap, palette = load_bmp_image(...)  # Bypasses cache
```

**After:**
```python
bitmap, palette = load_image_with_fallback(...)  # Uses cache
```

**Benefit:** Consistent caching, better memory usage

### Medium Value Extractions

#### 4. `load_weather_icon()` - Specialized helper
```python
def load_weather_icon(icon_num, for_forecast=False):
    """Load weather icon with appropriate blank fallback"""
    if for_forecast:
        path = f"{Paths.COLUMN_IMAGES}/{icon_num}.bmp"
        blank = Paths.BLANK_COLUMN
    else:
        path = f"{Paths.WEATHER_ICONS}/{icon_num}.bmp"
        blank = Paths.BLANK_WEATHER
    return load_image_with_fallback(path, blank, "weather icon")
```

## Proposed Helper Functions

### 1. Core Image Helper

```python
def load_image_with_fallback(primary_path, fallback_path, image_type="image"):
    """Load image with automatic fallback to blank

    Args:
        primary_path: Primary image path
        fallback_path: Blank fallback path
        image_type: Description for logging

    Returns:
        (bitmap, palette) or (None, None) if both fail
    """
    # Try primary
    bitmap, palette = state.image_cache.get_image(primary_path)

    if bitmap is not None:
        return bitmap, palette

    # Try fallback
    log_warning(f"{image_type} '{primary_path}' failed, using blank")
    bitmap, palette = state.image_cache.get_image(fallback_path)

    if bitmap is None:
        log_error(f"Blank fallback '{fallback_path}' failed for {image_type}")

    return bitmap, palette
```

**Benefits:**
- Consistent error handling
- Consistent logging
- Single source of truth
- ~15 lines replaces ~40 lines

### 2. TileGrid Helper

```python
def create_tilegrid(bitmap, palette, x=0, y=0, append=True):
    """Create and optionally append TileGrid to main group

    Args:
        bitmap: Bitmap to display
        palette: Color palette
        x: X position (default 0)
        y: Y position (default 0)
        append: Auto-append to main_group (default True)

    Returns:
        TileGrid instance or None if bitmap is None
    """
    if bitmap is None:
        return None

    grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    grid.x = x
    grid.y = y

    if append:
        state.main_group.append(grid)

    return grid
```

**Benefits:**
- Single line to create positioned TileGrid
- Optional auto-append
- Handles None bitmap gracefully
- ~6 lines replaces ~32 lines

### 3. Specialized Weather Icon Helper

```python
def load_weather_icon(icon_num, for_forecast=False):
    """Load weather icon with correct blank fallback

    Args:
        icon_num: Weather icon number (1-44)
        for_forecast: True for small forecast icons, False for large

    Returns:
        (bitmap, palette) or (None, None)
    """
    if for_forecast:
        primary = f"{Paths.COLUMN_IMAGES}/{icon_num}.bmp"
        blank = Paths.BLANK_COLUMN
        desc = f"forecast icon {icon_num}"
    else:
        primary = f"{Paths.WEATHER_ICONS}/{icon_num}.bmp"
        blank = Paths.BLANK_WEATHER
        desc = f"weather icon {icon_num}"

    return load_image_with_fallback(primary, blank, desc)
```

**Benefits:**
- Single function for all weather icons
- Automatic path selection
- Consistent fallback logic

## Impact Summary

### Code Reduction
- **Current:** ~72 lines of duplicated image handling
- **After:** ~26 lines (3 helpers + minimal call sites)
- **Net savings:** ~46 lines (~1% of codebase)

### Bugs Fixed
1. ✅ Schedule image caching (memory leak)
2. ✅ Forecast column missing fallback
3. ✅ Inconsistent error handling

### Maintainability
- ✅ Single place to modify image loading logic
- ✅ Consistent error messages
- ✅ Easier to add new image types
- ✅ Clearer display function code

### Risks
- ⚠️ **LOW RISK** - Pure refactoring, same logic
- ⚠️ Need to test all image types load correctly
- ⚠️ Schedule image caching change needs verification

## Recommendation

**PROCEED with extraction in this order:**

1. **Phase 1:** Create `load_image_with_fallback()` helper
   - Replace 5 duplicated patterns
   - Test with existing code

2. **Phase 2:** Create `create_tilegrid()` helper
   - Replace 8+ duplicated patterns
   - Verify displays render correctly

3. **Phase 3:** Create `load_weather_icon()` specialized helper
   - Simplify weather icon loading
   - Fix forecast column missing fallback

4. **Phase 4:** Fix schedule image caching
   - Change to use cache
   - Test segmented displays

**Total time:** 1-2 hours
**Risk level:** Low (pure refactoring)
**Testing:** Visual verification on hardware

## Call Sites to Update

### load_image_with_fallback()
- Line 2734: Weather icon
- Line 2939: Event image
- Line 3312: Forecast column
- Line 3641: Schedule weather icon
- Line 3673: Schedule image (+ add caching)

### create_tilegrid()
- Line 2745: Weather icon grid
- Line 2956: Birthday image grid
- Line 2961: Event image grid
- Line 3160: Forecast icon grid (loop)
- Line 3323: Forecast column grid (loop)
- Line 3652: Schedule weather grid
- Line 3674: Schedule image grid
- Line 2615: UV bar grid (different - bitmap created inline)
- Line 2633: Humidity bar grid (different - bitmap created inline)

**Note:** UV/humidity grids create bitmaps inline, may not benefit from helper.
