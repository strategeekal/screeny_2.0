"""
Pantallita 3.0 - Configuration Module
All constants and configuration - ZERO runtime cost
"""

import os

# ============================================================================
# DISPLAY HARDWARE
# ============================================================================

class Display:
    """RGB matrix display specifications"""
    WIDTH = 64
    HEIGHT = 32
    BIT_DEPTH = 4

# ============================================================================
# COLORS
# ============================================================================

class Colors:
    """Color palette for 4-bit display"""
    BLACK = 0x000000
    WHITE = 0xF5F5DC
    GREEN = 0x00FF00
    RED = 0xFF0000
    BLUE = 0x0000FF
    ORANGE = 0xFFA500
    GOLDEN = 0xFFD700
    DIMMEST_WHITE = 0x4A4A3C

# ============================================================================
# LAYOUT & POSITIONING
# ============================================================================

class Layout:
    """Display positioning constants"""
    WIDTH = 64
    HEIGHT = 32
    RIGHT_EDGE = 63

    # Weather display
    WEATHER_TEMP_X = 2
    WEATHER_TEMP_Y = 20
    WEATHER_TIME_X = 15
    WEATHER_TIME_Y = 24
    FEELSLIKE_Y = 16
    FEELSLIKE_SHADE_Y = 24

    # Indicator bars
    UV_BAR_Y = 27
    HUMIDITY_BAR_Y = 29
    BAR_MAX_LENGTH = 40

# ============================================================================
# API CONFIGURATION
# ============================================================================

class API:
    """API endpoints and configuration"""
    # AccuWeather
    ACCUWEATHER_BASE = "http://dataservice.accuweather.com"
    ACCUWEATHER_CURRENT = "/currentconditions/v1/{location}?details=true"

    # Timezone API
    TIMEZONE_API = "http://worldtimeapi.org/api/timezone/{timezone}"

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

class Env:
    """Environment variables from settings.toml"""

    @staticmethod
    def get(key, default=None):
        """Get environment variable with fallback"""
        try:
            return os.getenv(key, default)
        except:
            return default

    # WiFi
    WIFI_SSID = None
    WIFI_PASSWORD = None

    # Timezone
    TIMEZONE = None

    # Temperature unit
    TEMPERATURE_UNIT = None

    # AccuWeather
    ACCUWEATHER_KEY = None
    ACCUWEATHER_LOCATION = None

    @classmethod
    def load(cls):
        """Load all environment variables"""
        cls.WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
        cls.WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
        cls.TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")
        cls.TEMPERATURE_UNIT = os.getenv("TEMPERATURE_UNIT", "F")
        cls.ACCUWEATHER_KEY = os.getenv("ACCUWEATHER_API_KEY_TYPE1")
        cls.ACCUWEATHER_LOCATION = os.getenv("ACCUWEATHER_LOCATION_KEY")

# ============================================================================
# PATHS
# ============================================================================

class Paths:
    """File system paths"""
    FONT_LARGE = "/fonts/bigbit10-16.bdf"
    FONT_SMALL = "/fonts/tinybit6-16.bdf"
    WEATHER_IMAGES = "/img/weather"

# ============================================================================
# LOGGING
# ============================================================================

class LogLevel:
    """Logging levels"""
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    VERBOSE = 5

# Current log level
CURRENT_LOG_LEVEL = LogLevel.INFO

# ============================================================================
# TIMING
# ============================================================================

class Timing:
    """Timing constants in seconds"""
    # Display durations
    CLOCK_UPDATE_INTERVAL = 10
    WEATHER_DISPLAY_DURATION = 240

    # Update intervals
    WEATHER_UPDATE_INTERVAL = 300

    # Cache expiry
    WEATHER_CACHE_MAX_AGE = 900

    # System
    MEMORY_CHECK_INTERVAL = 10

# Load environment variables at import
Env.load()
