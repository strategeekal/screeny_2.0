"""
Pantallita 3.0 - Phase 1: Weather Display
Tests weather fetching and display with proper v3 architecture
"""

import time
import gc
import traceback
import supervisor
from adafruit_display_text import bitmap_label

import config
import state
import hardware
import weather_api
import display_weather
import logger

# ============================================================================
# DISPLAY FUNCTIONS (Inline - no helper functions)
# ============================================================================

def show_message(text, color=config.Colors.GREEN, y_pos=16):
    """Show a simple text message on display"""
    # Clear display inline
    try:
        while True:
            state.main_group.pop()
    except IndexError:
        pass

    # Create label inline
    label = bitmap_label.Label(
        state.font_large,
        text=text,
        color=color,
        x=2,
        y=y_pos
    )
    state.main_group.append(label)

def show_clock():
    """Show current time from RTC (fallback display)"""
    # Clear display inline
    try:
        while True:
            state.main_group.pop()
    except IndexError:
        pass

    # Get time from RTC
    now = state.rtc.datetime
    hour = now.tm_hour
    minute = now.tm_min
    second = now.tm_sec

    # Convert to 12-hour format inline
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12
    ampm = "AM" if hour < 12 else "PM"

    # Create time label inline
    time_text = f"{hour_12}:{minute:02d}"
    time_label = bitmap_label.Label(
        state.font_large,
        text=time_text,
        color=config.Colors.WHITE,
        x=5,
        y=12
    )
    state.main_group.append(time_label)

    # Create AM/PM label inline
    ampm_label = bitmap_label.Label(
        state.font_large,
        text=ampm,
        color=config.Colors.GREEN,
        x=5,
        y=24
    )
    state.main_group.append(ampm_label)

# ============================================================================
# MAIN LOOP
# ============================================================================

def run_display_cycle():
    """Run one display cycle - Phase 1: Weather"""
    state.cycle_count += 1

    # Log cycle start (v2.5 format)
    logger.log_cycle_start(state.cycle_count)

    # Check WiFi status
    if not hardware.is_wifi_connected():
        logger.log("WiFi disconnected!", config.LogLevel.WARNING)
        show_message("NO WIFI", config.Colors.RED)
        time.sleep(5)

        # Try to reconnect
        if hardware.reconnect_wifi():
            show_message("WIFI OK", config.Colors.GREEN)
            time.sleep(2)
        else:
            logger.log("WiFi reconnect failed - showing clock fallback", config.LogLevel.ERROR)
            show_clock()
            time.sleep(config.Timing.CLOCK_UPDATE_INTERVAL)
        return

    # Fetch weather data
    weather_data = weather_api.fetch_current()

    # Display weather or fallback to clock
    if weather_data:
        try:
            display_weather.show(weather_data, config.Timing.WEATHER_DISPLAY_DURATION)
        except Exception as e:
            logger.log(f"Weather display error: {e}", config.LogLevel.ERROR)
            traceback.print_exception(e)
            show_clock()
            time.sleep(config.Timing.CLOCK_UPDATE_INTERVAL)
    else:
        logger.log("No weather data available - showing clock fallback", config.LogLevel.WARNING)
        show_clock()
        time.sleep(config.Timing.CLOCK_UPDATE_INTERVAL)

    # Memory check (inline)
    if state.cycle_count % config.Timing.MEMORY_CHECK_INTERVAL == 0:
        gc.collect()
        current = gc.mem_free()
        state.last_memory_free = current

        # Update low watermark
        if state.low_watermark_memory == 0 or current < state.low_watermark_memory:
            state.low_watermark_memory = current

        # Log memory status with baseline and low watermark
        logger.log_memory_status(
            baseline=state.baseline_memory,
            low_watermark=state.low_watermark_memory
        )

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize():
    """Initialize all hardware and services"""
    logger.log("=== Pantallita 3.0 - Phase 1: Weather Display ===")
    logger.log(f"CircuitPython version: {supervisor.runtime.serial_connected}")

    # Show startup message
    show_message("INIT...", config.Colors.GREEN, 16)

    try:
        # Initialize display (already done to show message, but formalize it)
        hardware.init_display()

        # Initialize RTC
        show_message("RTC...", config.Colors.GREEN, 16)
        hardware.init_rtc()

        # Initialize buttons
        show_message("BUTTONS", config.Colors.GREEN, 16)
        hardware.init_buttons()

        # Connect to WiFi
        show_message("WIFI...", config.Colors.GREEN, 16)
        hardware.connect_wifi()

        # Sync time (includes 2-second delay and timezone fetch)
        show_message("SYNC...", config.Colors.GREEN, 16)
        hardware.sync_time(state.rtc)

        # Ready!
        show_message("READY!", config.Colors.GREEN, 16)
        time.sleep(2)

        logger.log("=== Initialization complete ===")
        logger.log("Press UP button to stop")
        logger.log("Running Phase 1: Weather Display")

        return True

    except Exception as e:
        logger.log(f"Initialization failed: {e}", config.LogLevel.ERROR)
        traceback.print_exception(e)
        show_message("INIT ERR", config.Colors.RED, 16)
        return False

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main entry point"""

    # Initialize hardware
    if not initialize():
        log("Cannot continue - initialization failed", config.LogLevel.ERROR)
        time.sleep(10)
        return

    # Main display loop
    try:
        # Get baseline memory
        gc.collect()
        state.last_memory_free = gc.mem_free()
        log(f"Baseline memory: {state.last_memory_free} bytes free")

        # Run display cycles
        while True:
            try:
                run_display_cycle()
            except KeyboardInterrupt:
                raise  # Pass up to outer handler
            except Exception as e:
                log(f"Display cycle error: {e}", config.LogLevel.ERROR)
                traceback.print_exception(e)
                # Show error briefly then continue
                show_message("ERROR!", config.Colors.RED, 16)
                time.sleep(5)

    except KeyboardInterrupt:
        log("=== Weather display stopped by button press ===")
        show_message("STOPPED", config.Colors.ORANGE, 16)
        time.sleep(2)

        # Final statistics
        gc.collect()
        final_memory = gc.mem_free()
        log(f"Final memory: {final_memory} bytes free")
        log(f"Total cycles: {state.cycle_count}")
        log(f"Weather fetches: {state.weather_fetch_count}")
        log(f"Weather errors: {state.weather_fetch_errors}")

        # Calculate uptime
        uptime_minutes = state.cycle_count * config.Timing.WEATHER_DISPLAY_DURATION / 60
        log(f"Estimated uptime: {uptime_minutes:.1f} minutes")

    except Exception as e:
        log(f"Fatal error: {e}", config.LogLevel.ERROR)
        traceback.print_exception(e)
        show_message("FATAL!", config.Colors.RED, 16)
        time.sleep(10)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()

# ============================================================================
# NOTES ON PHASE 1
# ============================================================================
"""
Phase 1 Goals:
1. ✅ Fetch weather from AccuWeather API
2. ✅ Display weather with v2 layout
3. ✅ Fixed text width calculation (6px char width for small font)
4. ⏳ 24-hour stability test

Success Criteria:
- Weather displays correctly
- Temperature in correct unit (C or F from settings.toml)
- Feels like and shade logic working
- Clock positioned correctly (centered or right-aligned)
- UV and humidity bars rendering
- No stack exhaustion errors
- Memory stable

Stack Depth Analysis:
Level 0: main()
Level 1: run_display_cycle()
Level 2: weather_api.fetch_current() OR display_weather.show()
Level 3: None - everything inline!

Total: 2 levels
Budget: 32 levels (CircuitPython 10)
Headroom: 30 levels (94%)

Next Phase:
Phase 2: Forecast display (12-hour forecast)
"""
