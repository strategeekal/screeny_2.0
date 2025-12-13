"""
Pantallita 3.0 - Global State Module
Global variables shared across modules
"""

# ============================================================================
# DISPLAY STATE
# ============================================================================

# Display objects (initialized by hardware.init_display)
display = None
main_group = None
font_large = None
font_small = None

# ============================================================================
# HARDWARE STATE
# ============================================================================

# RTC object (initialized by hardware.init_rtc)
rtc = None

# Button objects (initialized by hardware.init_buttons)
button_up = None
button_down = None

# ============================================================================
# NETWORK STATE
# ============================================================================

# HTTP session (initialized by hardware.connect_wifi)
session = None
socket_pool = None

# ============================================================================
# RUNTIME STATE
# ============================================================================

# Cycle counter
cycle_count = 0

# Uptime tracking (using time.monotonic())
start_time = 0  # Set in code_v3.py on startup

# Memory tracking
baseline_memory = 0      # Memory at startup (after initialization)
last_memory_free = 0     # Last memory check value
low_watermark_memory = 0 # Lowest memory seen so far

# ============================================================================
# WEATHER CACHE
# ============================================================================

# Weather data cache
last_weather_data = None
last_weather_time = 0

# Weather statistics
weather_fetch_count = 0
weather_fetch_errors = 0
