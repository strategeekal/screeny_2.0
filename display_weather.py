"""
Pantallita 3.0 - Weather Display Module
CRITICAL: ALL logic is INLINE - NO helper functions
"""

import time
import displayio
from adafruit_display_text import bitmap_label
from adafruit_display_shapes.rect import Rect

import config
import state
import logger

# ============================================================================
# TEXT ALIGNMENT NOTE
# ============================================================================

# Using CircuitPython's anchor_point system for proper text alignment:
# - anchor_point=(0.0, 0.0) = top-left anchor (default)
# - anchor_point=(1.0, 0.0) = top-right anchor (for right-alignment)
# - anchor_point=(0.5, 0.0) = top-center anchor (for centering)
# - anchored_position=(x, y) = where to place the anchor point
#
# This works with variable-width fonts automatically!

# ============================================================================
# WEATHER DISPLAY (EVERYTHING INLINE)
# ============================================================================

def show(weather_data, duration):
    """
    Show current weather display matching v2 layout exactly.

    V2 Layout:
    - Icon: Full screen background (0, 0)
    - Temperature: Left, big font (actual temp always shown)
    - Feels like: Right-aligned if different from temp (temp only)
    - Feels shade: Right-aligned below feels if different from feels (temp only)
    - Clock: Centered if shade shown, else right-aligned at shade position
    - UV bar: Bottom (colored)
    - Humidity bar: Bottom-most (white with gaps every 2 pixels)
    - NO condition text

    Args:
        weather_data: {temp, feels_like, feels_shade, uv, humidity, icon}
        duration: Display time in seconds
    """

    logger.log(f"Displaying weather: {weather_data['temp']}°", config.LogLevel.INFO)

    # ========================================================================
    # CLEAR DISPLAY (Inline - fixed for CircuitPython)
    # ========================================================================
    try:
        while True:
            state.main_group.pop()
    except IndexError:
        pass  # Group is empty

    # ========================================================================
    # LOAD WEATHER ICON (Inline - OnDiskBitmap for full screen)
    # ========================================================================
    icon_num = weather_data['icon']
    icon_path = f"{config.Paths.WEATHER_IMAGES}/{icon_num}.bmp"

    try:
        bitmap = displayio.OnDiskBitmap(icon_path)
        tile_grid = displayio.TileGrid(
            bitmap,
            pixel_shader=bitmap.pixel_shader,
            x=0,
            y=0
        )
        state.main_group.append(tile_grid)
    except OSError as e:
        logger.log(f"Weather icon {icon_num} not found: {e}", config.LogLevel.WARNING)

    # ========================================================================
    # TEMPERATURE DATA
    # ========================================================================
    temp = weather_data['temp']
    feels = weather_data['feels_like']
    shade = weather_data['feels_shade']

    # Determine what to show
    show_feels = (feels != temp)
    show_shade = (shade != feels)

    # ========================================================================
    # ACTUAL TEMPERATURE (Always shown - left, big font)
    # ========================================================================
    temp_text = f"{temp}°"
    temp_label = bitmap_label.Label(
        state.font_large,
        text=temp_text,
        color=config.Colors.WHITE,
        x=config.Layout.WEATHER_TEMP_X,
        y=config.Layout.WEATHER_TEMP_Y
    )
    state.main_group.append(temp_label)

    # ========================================================================
    # FEELS LIKE (Right-aligned, temp only, same Y as main temp)
    # ========================================================================
    if show_feels:
        feels_text = f"{feels}°"

        # Use anchor point for proper right-alignment with variable-width fonts
        feels_label = bitmap_label.Label(
            state.font_small,
            text=feels_text,
            color=config.Colors.WHITE,
            anchor_point=(1.0, 0.0),  # Right-top anchor
            anchored_position=(config.Layout.RIGHT_EDGE, config.Layout.FEELSLIKE_Y)
        )
        state.main_group.append(feels_label)

    # ========================================================================
    # FEELS SHADE (Right-aligned below feels, temp only)
    # ========================================================================
    if show_shade:
        shade_text = f"{shade}°"

        # Use anchor point for proper right-alignment
        shade_label = bitmap_label.Label(
            state.font_small,
            text=shade_text,
            color=config.Colors.WHITE,
            anchor_point=(1.0, 0.0),  # Right-top anchor
            anchored_position=(config.Layout.RIGHT_EDGE, config.Layout.FEELSLIKE_SHADE_Y)
        )
        state.main_group.append(shade_label)

    # ========================================================================
    # CLOCK (Centered if shade shown, else right-aligned at shade position)
    # ========================================================================
    # Get time from RTC
    now = state.rtc.datetime
    hour = now.tm_hour
    minute = now.tm_min

    # Convert to 12-hour format inline
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12

    time_text = f"{hour_12}:{minute:02d}"

    # Use anchor point for proper alignment with variable-width fonts
    if show_shade:
        # Centered
        time_label = bitmap_label.Label(
            state.font_small,
            text=time_text,
            color=config.Colors.WHITE,
            anchor_point=(0.5, 0.0),  # Center-top anchor
            anchored_position=(config.Display.WIDTH // 2, config.Layout.WEATHER_TIME_Y)
        )
    else:
        # Right-aligned at shade position
        time_label = bitmap_label.Label(
            state.font_small,
            text=time_text,
            color=config.Colors.WHITE,
            anchor_point=(1.0, 0.0),  # Right-top anchor
            anchored_position=(config.Layout.RIGHT_EDGE, config.Layout.WEATHER_TIME_Y)
        )

    state.main_group.append(time_label)

    # ========================================================================
    # UV INDEX BAR (Inline - colored bar)
    # ========================================================================
    uv = weather_data.get('uv', 0)

    # Calculate bar length inline (UV index 0-11+)
    uv_length = int((uv / 11) * config.Layout.BAR_MAX_LENGTH)
    uv_length = min(uv_length, config.Layout.BAR_MAX_LENGTH)

    # Choose color inline
    if uv < 3:
        uv_color = config.Colors.GREEN
    elif uv < 6:
        uv_color = config.Colors.GOLDEN
    elif uv < 8:
        uv_color = config.Colors.ORANGE
    else:
        uv_color = config.Colors.RED

    # Draw bar inline
    for i in range(uv_length):
        rect = Rect(i, config.Layout.UV_BAR_Y, 1, 1, fill=uv_color)
        state.main_group.append(rect)

    # ========================================================================
    # HUMIDITY BAR (Inline - white with gaps every 2 pixels)
    # ========================================================================
    humidity = weather_data.get('humidity', 0)

    # Calculate: 1 pixel per 10% humidity (0-100% = 0-10 pixels)
    humidity_pixels = int(humidity / 10)
    humidity_pixels = min(humidity_pixels, 10)

    # Draw bar with gaps every 2 pixels
    for i in range(humidity_pixels):
        # Skip every other pixel to create gaps (skip pixels 2, 4, 6, 8, 10)
        if i > 0 and i % 2 == 0:
            continue  # Gap

        rect = Rect(i, config.Layout.HUMIDITY_BAR_Y, 1, 1, fill=config.Colors.WHITE)
        state.main_group.append(rect)

    # ========================================================================
    # INTERRUPTIBLE SLEEP WITH LIVE CLOCK (Inline)
    # ========================================================================
    end_time = time.monotonic() + duration
    last_minute = -1  # Track last minute to avoid unnecessary updates

    while time.monotonic() < end_time:
        # Check button inline (import hardware only when needed to avoid circular imports)
        import hardware
        if hardware.button_up_pressed():
            logger.log("UP button pressed during weather display", config.LogLevel.INFO)
            raise KeyboardInterrupt

        # Update clock only when minute changes (prevents blinking)
        now = state.rtc.datetime
        current_minute = now.tm_min

        if current_minute != last_minute:
            # Minute changed - update display
            hour = now.tm_hour
            hour_12 = hour % 12
            if hour_12 == 0:
                hour_12 = 12

            new_time_text = f"{hour_12}:{current_minute:02d}"
            time_label.text = new_time_text
            last_minute = current_minute

        time.sleep(0.1)

# ============================================================================
# NOTES
# ============================================================================
"""
Text Alignment with Anchor Points:

CircuitPython's bitmap_label.Label supports anchor_point and anchored_position
which automatically handle text alignment for variable-width fonts!

RIGHT-ALIGNMENT:
    anchor_point=(1.0, 0.0)      # Right-top corner of text
    anchored_position=(63, y)    # Place that anchor at right edge

CENTER-ALIGNMENT:
    anchor_point=(0.5, 0.0)      # Center-top of text
    anchored_position=(32, y)    # Place that anchor at center

LEFT-ALIGNMENT (default):
    anchor_point=(0.0, 0.0)      # Left-top corner (or just use x, y)
    anchored_position=(x, y)     # Or just x, y parameters

This works with both fixed-width and proportional fonts!

Example:
    # Right-align "25°" at right edge (x=63)
    label = bitmap_label.Label(
        font,
        text="25°",
        anchor_point=(1.0, 0.0),
        anchored_position=(63, 16)
    )
    # The rightmost pixel of the text will be at x=63
    # Works perfectly regardless of actual text width!

V2 Layout Implementation:
1. Temp always shows (left, big font, x/y positioning)
2. Feels shows if different (right-aligned with anchor_point=1.0)
3. Shade shows if different from feels (right-aligned with anchor_point=1.0)
4. Clock: centered (anchor_point=0.5) if shade shown, else right-aligned (anchor_point=1.0)
5. UV bar (colored, pixel-by-pixel)
6. Humidity bar (white, 1px per 10%, gaps every 2px)
7. NO condition text

Stack depth: 2 levels (main -> show)
"""
