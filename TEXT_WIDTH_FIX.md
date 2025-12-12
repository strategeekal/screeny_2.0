# Text Width Calculation Fix

## Problem

In CircuitPython, the `font.get_bounding_box()` method returns `(0, 0, 0, 0)` instead of the actual character dimensions. This broke all text width calculations for right-alignment:

```python
# BROKEN CODE
bbox = font.get_bounding_box()
char_width = bbox[2]  # Returns 0!
text_width = len(text) * char_width  # Always 0
feels_x = RIGHT_EDGE - text_width + 1  # Wrong position!
```

## Solution

Use **fixed character widths** based on the font file names:

```python
# Font widths from filenames:
# tinybit6-16.bdf = 6 pixels per character
# bigbit10-16.bdf = 10 pixels per character

SMALL_FONT_CHAR_WIDTH = 6
LARGE_FONT_CHAR_WIDTH = 10

# FIXED CODE
text_width = len(text) * SMALL_FONT_CHAR_WIDTH  # Works!
feels_x = RIGHT_EDGE - text_width + 1  # Correct!
```

## Examples

### Feels Like Temperature (Right-Aligned)
```python
feels_text = "25°"  # 3 characters
text_width = 3 * 6 = 18 pixels
feels_x = 63 - 18 + 1 = 46
# Text starts at x=46 and extends to x=63 (right edge)
```

### Clock (Centered)
```python
time_text = "10:45"  # 5 characters
text_width = 5 * 6 = 30 pixels
time_x = (64 - 30) // 2 = 17
# Text is centered on 64-pixel wide display
```

## Implementation

The fix is implemented in `display_weather.py`:

1. **Constants defined at module level:**
   ```python
   SMALL_FONT_CHAR_WIDTH = 6
   LARGE_FONT_CHAR_WIDTH = 10
   ```

2. **Used for all text positioning:**
   - Feels like temperature (right-aligned)
   - Feels shade temperature (right-aligned)
   - Clock (centered or right-aligned)

3. **All calculations inline:**
   ```python
   text_width = len(feels_text) * SMALL_FONT_CHAR_WIDTH
   feels_x = config.Layout.RIGHT_EDGE - text_width + 1
   ```

## Why This Works

The font filenames indicate their character width:
- `tinybit6-16.bdf` = 6 pixels wide, 16 pixels tall
- `bigbit10-16.bdf` = 10 pixels wide, 16 pixels tall

These are **fixed-width (monospace) fonts**, so every character is exactly the same width. This makes text width calculation simple and reliable.

## V2 Layout Requirements

With fixed text width calculation, we achieve the exact v2 layout:

1. **Temperature:** Always left-aligned, big font
2. **Feels like:** Right-aligned if different from temp
3. **Feels shade:** Right-aligned below feels if different
4. **Clock:**
   - Centered if shade is shown
   - Right-aligned at shade position if shade not shown
5. **UV bar:** Colored bar at bottom
6. **Humidity bar:** White bar with gaps every 2 pixels

All text aligns perfectly with the 64-pixel display width!

## Stack Depth Impact

This fix maintains the **flat architecture** principle:
- No helper functions for text measurement
- All calculations inline
- Stack depth remains at 2 levels

## Testing

To verify the fix works:
1. Deploy to MatrixPortal
2. Check that feels like temperature aligns to right edge
3. Check that clock is properly centered when shade shows
4. Check that clock aligns right when shade doesn't show
5. Verify all text is readable and not cut off

## Related Files

- `display_weather.py` - Implementation
- `config.py` - Layout constants (RIGHT_EDGE = 63)
- `state.py` - Font objects (font_small, font_large)

## Date

Fixed: 2025-12-12
Phase: Phase 1 - Weather Display
