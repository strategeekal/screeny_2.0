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

# ============================================================================
# LOGGING
# ============================================================================

def log(message, level=config.LogLevel.INFO):
    """Simple logging"""
    if isinstance(level, str):
        level = config.LogLevel.INFO
    if level <= config.CURRENT_LOG_LEVEL:
        level_name = ["", "ERROR", "WARN", "INFO", "DEBUG", "VERBOSE"][level]
        print(f"[DISPLAY:{level_name}] {message}")

# ============================================================================
# FONT CHARACTER WIDTHS (Fixed - get_bounding_box returns 0)
# ============================================================================

# Font widths based on font file names:
# tinybit6-16.bdf = 6 pixels per character
# bigbit10-16.bdf = 10 pixels per character
SMALL_FONT_CHAR_WIDTH = 6
LARGE_FONT_CHAR_WIDTH = 10

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

    log(f"Displaying weather: {weather_data['temp']}°", config.LogLevel.INFO)

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
        log(f"Weather icon {icon_num} not found: {e}", config.LogLevel.WARN)

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

        # Calculate text width using fixed char width (6px for small font)
        text_width = len(feels_text) * SMALL_FONT_CHAR_WIDTH
        feels_x = config.Layout.RIGHT_EDGE - text_width + 1

        feels_label = bitmap_label.Label(
            state.font_small,
            text=feels_text,
            color=config.Colors.WHITE,
            x=feels_x,
            y=config.Layout.FEELSLIKE_Y
        )
        state.main_group.append(feels_label)

    # ========================================================================
    # FEELS SHADE (Right-aligned below feels, temp only)
    # ========================================================================
    if show_shade:
        shade_text = f"{shade}°"

        # Calculate text width using fixed char width
        text_width = len(shade_text) * SMALL_FONT_CHAR_WIDTH
        shade_x = config.Layout.RIGHT_EDGE - text_width + 1

        shade_label = bitmap_label.Label(
            state.font_small,
            text=shade_text,
            color=config.Colors.WHITE,
            x=shade_x,
            y=config.Layout.FEELSLIKE_SHADE_Y
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

    # Calculate text width using fixed char width
    time_text_width = len(time_text) * SMALL_FONT_CHAR_WIDTH

    if show_shade:
        # Centered
        time_x = (config.Display.WIDTH - time_text_width) // 2
    else:
        # Right-aligned at shade position
        time_x = config.Layout.RIGHT_EDGE - time_text_width + 1

    time_label = bitmap_label.Label(
        state.font_small,
        text=time_text,
        color=config.Colors.WHITE,
        x=time_x,
        y=config.Layout.WEATHER_TIME_Y
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
    # INTERRUPTIBLE SLEEP (Inline - no sleep helper)
    # ========================================================================
    end_time = time.monotonic() + duration

    while time.monotonic() < end_time:
        # Check button inline (import hardware only when needed to avoid circular imports)
        import hardware
        if hardware.button_up_pressed():
            log("UP button pressed during weather display", config.LogLevel.INFO)
            raise KeyboardInterrupt

        time.sleep(0.1)

# ============================================================================
# NOTES
# ============================================================================
"""
Character width calculation:

OLD (broken):
bbox = font.get_bounding_box()  # Returns (0, 0, 0, 0) in CircuitPython!
char_width = bbox[2]  # Always 0
text_width = len(text) * char_width  # Always 0 - BROKEN

NEW (fixed):
SMALL_FONT_CHAR_WIDTH = 6  # From tinybit6-16.bdf filename
text_width = len(text) * SMALL_FONT_CHAR_WIDTH  # Works!

Right-alignment calculation:
feels_x = RIGHT_EDGE - text_width + 1
Example: "25°" = 3 chars * 6px = 18px wide
feels_x = 63 - 18 + 1 = 46 (perfectly right-aligned)

V2 Layout Logic:
1. Temp always shows (left, big font)
2. Feels shows if different (right-aligned, small font, temp only)
3. Shade shows if different from feels (right-aligned below, temp only)
4. Clock: centered if shade shown, else at shade position (right-aligned)
5. UV bar (colored)
6. Humidity bar (white, 1px per 10%, gaps every 2px)
7. NO condition text

Stack depth: 2 levels (main -> show)
"""
