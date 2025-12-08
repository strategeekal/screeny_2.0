"""
Pantallita 3.0 - Main Entry Point
Flat architecture - NO nested function calls
"""

import time
import gc
import traceback
import supervisor

# Import modules (each import = one-time cost)
import v3_config as config
import v3_state as state
import v3_hardware as hardware
import v3_network as network
import v3_weather_api as weather_api
import v3_display_weather as display_weather

# Optional: Import only when needed
# import v3_display_forecast as display_forecast
# import v3_stocks_api as stocks_api
# import v3_display_stocks as display_stocks

gc.collect()

# ============================================================================
# LOGGING (Inline - no function calls in hot path)
# ============================================================================

def log(message, level=config.LogLevel.INFO):
    """Simple logging - only call from main loop, not nested"""
    if level <= config.CURRENT_LOG_LEVEL:
        print(f"[{level}] {message}")

# ============================================================================
# MAIN LOOP (FLAT - No wrapper functions)
# ============================================================================

def run_display_cycle(cycle_count):
    """
    Main display cycle - FLAT architecture
    Calls modules directly, NO wrapper functions
    """
    cycle_start = time.monotonic()

    # Check WiFi (module call - level 1)
    if not hardware.is_wifi_connected():
        log("WiFi disconnected, attempting reconnect", config.LogLevel.WARNING)
        hardware.reconnect_wifi()
        if not hardware.is_wifi_connected():
            log("WiFi reconnect failed, skipping cycle", config.LogLevel.ERROR)
            return

    # Fetch weather data (module call - level 1)
    try:
        weather_data = weather_api.fetch_current()
        if weather_data:
            log(f"Weather: {weather_data['temp']}°, UV:{weather_data['uv']}", config.LogLevel.INFO)
        else:
            log("Weather fetch returned None", config.LogLevel.WARNING)
            weather_data = state.get_cached_weather()  # Fallback to cache
    except Exception as e:
        log(f"Weather fetch error: {e}", config.LogLevel.ERROR)
        weather_data = state.get_cached_weather()

    # Display weather (module call - level 1)
    if weather_data:
        try:
            display_weather.show(weather_data, config.Timing.WEATHER_DURATION)
        except KeyboardInterrupt:
            raise  # Button pressed, exit gracefully
        except Exception as e:
            log(f"Display error: {e}", config.LogLevel.ERROR)
            traceback.print_exception(e)
    else:
        log("No weather data available", config.LogLevel.ERROR)

    # Memory management (inline - no function call)
    if cycle_count % config.Memory.GC_FREQUENCY == 0:
        gc.collect()
        if cycle_count % config.Memory.MEMORY_REPORT_FREQUENCY == 0:
            free = gc.mem_free()
            log(f"Memory: {free} bytes free", config.LogLevel.DEBUG)

    # Log cycle time (inline)
    cycle_time = time.monotonic() - cycle_start
    log(f"Cycle {cycle_count} complete in {cycle_time:.1f}s", config.LogLevel.DEBUG)

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main entry point"""
    log("=== Pantallita 3.0 Starting ===", config.LogLevel.INFO)

    # Initialize hardware (one-time setup)
    try:
        log("Initializing display...", config.LogLevel.INFO)
        hardware.init_display()

        log("Initializing RTC...", config.LogLevel.INFO)
        rtc = hardware.init_rtc()

        log("Initializing buttons...", config.LogLevel.INFO)
        hardware.init_buttons()

        log("Connecting to WiFi...", config.LogLevel.INFO)
        hardware.connect_wifi()

        log("Syncing time...", config.LogLevel.INFO)
        hardware.sync_time(rtc)

        log("System initialized successfully", config.LogLevel.INFO)
    except Exception as e:
        log(f"Initialization error: {e}", config.LogLevel.ERROR)
        traceback.print_exception(e)
        log("Halting - cannot continue without initialization", config.LogLevel.ERROR)
        return

    # Main loop
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            run_display_cycle(cycle_count)

            # Check for daily restart (inline - no function call)
            current_time = rtc.datetime
            if current_time.tm_hour == config.Timing.RESTART_HOUR and current_time.tm_min == 0:
                log("Daily restart triggered", config.LogLevel.INFO)
                supervisor.reload()

        except KeyboardInterrupt:
            log("=== Pantallita stopped by button press ===", config.LogLevel.INFO)
            free = gc.mem_free()
            log(f"Final memory: {free} bytes free", config.LogLevel.INFO)
            break
        except Exception as e:
            log(f"Main loop error: {e}", config.LogLevel.ERROR)
            traceback.print_exception(e)
            # Continue running despite errors
            time.sleep(5)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
