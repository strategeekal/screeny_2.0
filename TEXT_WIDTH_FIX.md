# Text Alignment Fix

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

Use CircuitPython's **anchor_point and anchored_position** system which automatically handles text alignment for both fixed-width and proportional fonts:

```python
# PROPER SOLUTION - Works with variable-width fonts!
label = bitmap_label.Label(
    font,
    text="25°",
    anchor_point=(1.0, 0.0),      # Right-top anchor
    anchored_position=(63, 16)    # Place anchor at right edge
)
# Text is automatically right-aligned at x=63!
```

## Anchor Point System

### How It Works

**Anchor Point:** A position within the text bounding box (0.0 to 1.0 range)
- `(0.0, 0.0)` = top-left corner
- `(1.0, 0.0)` = top-right corner
- `(0.5, 0.0)` = top-center
- `(0.0, 1.0)` = bottom-left corner
- etc.

**Anchored Position:** Where to place that anchor point on the display

### Examples

#### Right-Align Text
```python
# Place the RIGHT edge of text at x=63 (right edge of display)
label = bitmap_label.Label(
    font,
    text="25°",
    anchor_point=(1.0, 0.0),      # Anchor at right-top of text
    anchored_position=(63, 16)    # Place that point at x=63, y=16
)
# Works for "25°" (narrow) or "-100°" (wide) automatically!
```

#### Center Text
```python
# Place the CENTER of text at x=32 (center of 64-pixel display)
label = bitmap_label.Label(
    font,
    text="10:45",
    anchor_point=(0.5, 0.0),      # Anchor at center-top of text
    anchored_position=(32, 24)    # Place that point at x=32, y=24
)
# Perfectly centered regardless of text width!
```

#### Left-Align Text (Default)
```python
# Traditional x, y positioning (no anchor needed)
label = bitmap_label.Label(
    font,
    text="77°",
    x=2,
    y=20
)
# Or use anchor_point=(0.0, 0.0) explicitly
```

## Implementation

The fix is implemented in `display_weather.py` using anchor points throughout:

### Feels Like Temperature (Right-Aligned)
```python
feels_label = bitmap_label.Label(
    state.font_small,
    text=f"{feels}°",
    color=config.Colors.WHITE,
    anchor_point=(1.0, 0.0),
    anchored_position=(config.Layout.RIGHT_EDGE, config.Layout.FEELSLIKE_Y)
)
```

### Feels Shade Temperature (Right-Aligned)
```python
shade_label = bitmap_label.Label(
    state.font_small,
    text=f"{shade}°",
    color=config.Colors.WHITE,
    anchor_point=(1.0, 0.0),
    anchored_position=(config.Layout.RIGHT_EDGE, config.Layout.FEELSLIKE_SHADE_Y)
)
```

### Clock (Centered or Right-Aligned)
```python
if show_shade:
    # Centered
    time_label = bitmap_label.Label(
        state.font_small,
        text=time_text,
        anchor_point=(0.5, 0.0),
        anchored_position=(config.Display.WIDTH // 2, config.Layout.WEATHER_TIME_Y)
    )
else:
    # Right-aligned
    time_label = bitmap_label.Label(
        state.font_small,
        text=time_text,
        anchor_point=(1.0, 0.0),
        anchored_position=(config.Layout.RIGHT_EDGE, config.Layout.WEATHER_TIME_Y)
    )
```

## Why This Works

The `anchor_point` and `anchored_position` system is built into CircuitPython's `bitmap_label.Label` class. It:

1. **Calculates actual text width** automatically (handles variable-width fonts)
2. **Positions the anchor** at the specified point within the text bounding box
3. **Places that anchor** at the specified display coordinates

This works for:
- ✅ Fixed-width (monospace) fonts like `tinybit6-16.bdf`
- ✅ Variable-width (proportional) fonts
- ✅ Different text lengths ("5°" vs "-100°")
- ✅ Different characters ("WWW" vs "iii")

## V2 Layout Requirements

With anchor point alignment, we achieve the exact v2 layout:

1. **Temperature:** Always left-aligned, big font (standard x, y positioning)
2. **Feels like:** Right-aligned if different from temp (anchor_point=1.0)
3. **Feels shade:** Right-aligned below feels if different (anchor_point=1.0)
4. **Clock:**
   - Centered if shade is shown (anchor_point=0.5)
   - Right-aligned at shade position if shade not shown (anchor_point=1.0)
5. **UV bar:** Colored bar at bottom (pixel-by-pixel rendering)
6. **Humidity bar:** White bar with gaps every 2 pixels (pixel-by-pixel rendering)

All text aligns perfectly regardless of font type or text width!

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
