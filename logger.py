"""
Pantallita 3.0 - Centralized Logging Module
Matches v2.5 log format with timestamps: [2025-12-07 03:04:08] INFO: message
"""

import gc
import state
import config

# ============================================================================
# TIMESTAMP FORMATTING
# ============================================================================

def get_timestamp():
    """
    Get current timestamp from RTC in v2.5 format: [2025-12-07 03:04:08]

    Returns:
        str: Formatted timestamp or placeholder if RTC unavailable
    """
    try:
        # Handle case where RTC is not yet initialized
        if state.rtc is None:
            return "[-------- --:--:--]"

        now = state.rtc.datetime
        return (f"[{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d} "
                f"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}]")
    except:
        return "[-------- --:--:--]"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

def log(message, level=config.LogLevel.INFO):
    """
    Log message with timestamp matching v2.5 format.

    Format: [2025-12-07 03:04:08] INFO: message

    Args:
        message: The message to log
        level: Log level (ERROR, WARNING, INFO, DEBUG, VERBOSE)
    """
    if level <= config.CURRENT_LOG_LEVEL:
        # Map level to name
        level_names = {
            config.LogLevel.ERROR: "ERROR",
            config.LogLevel.WARNING: "WARNING",
            config.LogLevel.INFO: "INFO",
            config.LogLevel.DEBUG: "DEBUG",
            config.LogLevel.VERBOSE: "VERBOSE"
        }
        level_name = level_names.get(level, "INFO")

        # Get timestamp and format message
        timestamp = get_timestamp()
        print(f"{timestamp} {level_name}: {message}")

# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def format_uptime(seconds):
    """
    Format uptime as HH:MM:SS.

    Args:
        seconds: Uptime in seconds (from time.monotonic())

    Returns:
        str: Formatted uptime like "08:15:42"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def format_duration(seconds):
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        str: Formatted like "2h 15m" or "45m 30s" or "30s"
    """
    if seconds >= 3600:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    elif seconds >= 60:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        return f"{int(seconds)}s"

def format_memory():
    """
    Format memory status with percentage.

    Returns:
        str: Formatted like "1,932,384 bytes (75%)"
    """
    gc.collect()
    free = gc.mem_free()

    # Calculate percentage (2MB total SRAM)
    total_ram = 2 * 1024 * 1024  # 2MB in bytes
    percent = int((free / total_ram) * 100)

    return f"{free:,} bytes ({percent}%)"

def format_memory_delta(baseline, current):
    """
    Format memory change with sign.

    Args:
        baseline: Starting memory value
        current: Current memory value

    Returns:
        str: Formatted like "+1,024" or "-2,048"
    """
    delta = current - baseline
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:,}"

# ============================================================================
# CYCLE AND STATISTICS LOGGING
# ============================================================================

def log_cycle_start(cycle_num):
    """Log cycle start matching v2.5 format"""
    log(f"## CYCLE {cycle_num} ##", config.LogLevel.INFO)

def log_weather(condition, temp, unit="C"):
    """
    Log weather data matching v2.5 format.

    Args:
        condition: Weather condition text
        temp: Temperature value
        unit: Temperature unit (C or F)
    """
    log(f"Weather: {condition}, {temp}°{unit}", config.LogLevel.INFO)

def log_forecast(hours, is_fresh, next_temp, unit="C"):
    """
    Log forecast data matching v2.5 format.

    Args:
        hours: Forecast hours (e.g., 12)
        is_fresh: Whether forecast is fresh or cached
        next_temp: Next forecast temperature
        unit: Temperature unit (C or F)
    """
    freshness = "fresh" if is_fresh else "cached"
    log(f"Forecast: {hours} hours ({freshness}) | Next: {next_temp}°{unit}", config.LogLevel.INFO)

def log_memory_status(baseline=None, low_watermark=None):
    """
    Log memory status with baseline and low watermark.

    Args:
        baseline: Baseline memory at startup
        low_watermark: Lowest memory seen so far
    """
    current = gc.mem_free()

    if baseline is not None and low_watermark is not None:
        delta = format_memory_delta(baseline, current)
        log(f"Memory: {current:,} bytes | Baseline: {baseline:,} ({delta}) | Low: {low_watermark:,}",
            config.LogLevel.INFO)
    elif baseline is not None:
        delta = format_memory_delta(baseline, current)
        log(f"Memory: {current:,} bytes | Baseline: {baseline:,} ({delta})", config.LogLevel.INFO)
    else:
        log(f"Memory: {format_memory()}", config.LogLevel.INFO)

def log_uptime(start_time, current_time):
    """
    Log uptime in HH:MM:SS format.

    Args:
        start_time: Start time from time.monotonic()
        current_time: Current time from time.monotonic()
    """
    uptime_seconds = current_time - start_time
    uptime_str = format_uptime(uptime_seconds)
    log(f"Uptime: {uptime_str}", config.LogLevel.INFO)

# ============================================================================
# NOTES
# ============================================================================
"""
v2.5 Log Format Examples:

[2025-12-07 03:04:08] INFO: ## CYCLE 1 ##
[2025-12-07 03:04:08] INFO: Weather: Snow, 0.1°C
[2025-12-07 03:04:09] INFO: Forecast: 12 hours (fresh) | Next: -4.9°C
[2025-12-07 03:04:10] INFO: Memory: 1,932,384 bytes (75%)
[2025-12-07 03:04:11] INFO: Uptime: 08:15:42

Usage:
    import logger

    logger.log("Starting weather display", logger.INFO)
    logger.log_cycle_start(1)
    logger.log_weather("Snow", 0.1, "C")
    logger.log_memory_status(baseline=2000000, low_watermark=1900000)
    logger.log_uptime(start_time, time.monotonic())

Stack Depth:
This module adds 1 level to the stack (leaf function):
- Level 0: main()
- Level 1: run_display_cycle()
- Level 2: display_weather.show()
- Level 3: logger.log() <- adds 1 level
Total: 3 of 32 levels (9% usage, 91% headroom)
"""
