"""
Pantallita 3.0 - Configuration Module
All constants and configuration classes.
ZERO runtime cost - pure data only.
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
    # Basic colors
    BLACK = 0x000000
    WHITE = 0xF5F5DC
    RED = 0xFF0000
    GREEN = 0x00FF00
    BLUE = 0x0000FF

    # Named colors
    MINT = 0x95E1D3
    LILAC = 0xC5B4E3
    BUGAMBILIA = 0xF38BA0
    GOLDEN = 0xFFD700
    ORANGE = 0xFFA500

    # Dimmed variants
    DIMMEST_WHITE = 0x4A4A3C
    MEDIUM_WHITE = 0x9A9A7A

    # Day indicators
    MONDAY_COLOR = RED
    TUESDAY_COLOR = ORANGE
    WEDNESDAY_COLOR = GOLDEN
    THURSDAY_COLOR = GREEN
    FRIDAY_COLOR = BLUE
    SATURDAY_COLOR = BUGAMBILIA
    SUNDAY_COLOR = LILAC

# ============================================================================
# LAYOUT & POSITIONING
# ============================================================================

class Layout:
    """Display positioning constants"""
    # Display boundaries
    RIGHT_EDGE = 63
    BOTTOM_EDGE = 31

    # Weather display
    WEATHER_TEMP_X = 2
    WEATHER_TEMP_Y = 20
    WEATHER_TIME_X = 15
    WEATHER_TIME_Y = 24
    FEELSLIKE_Y = 16

    # Indicator bars
    UV_BAR_Y = 27
    HUMIDITY_BAR_Y = 29
    BAR_MAX_LENGTH = 40

    # Forecast display
    FORECAST_TIME_Y = 1
    FORECAST_TEMP_Y = 25
    FORECAST_ICON_Y = 9
    FORECAST_COL1_X = 3
    FORECAST_COL2_X = 25
    FORECAST_COL3_X = 48
    FORECAST_COLUMN_WIDTH = 13

    # Stock display
    STOCK_ROW1_Y = 2
    STOCK_ROW2_Y = 14
    STOCK_ROW3_Y = 26
    STOCK_CHART_Y = 14
    STOCK_CHART_HEIGHT = 16

    # Event display
    EVENT_IMAGE_X = 37
    EVENT_IMAGE_Y = 2
    EVENT_TEXT_X = 2

    # Text margins
    TEXT_MARGIN = 2
    BOTTOM_MARGIN = 2
    LINE_SPACING = 1

# ============================================================================
# TIMING
# ============================================================================

class Timing:
    """Timing constants in seconds"""
    # Display durations
    WEATHER_DURATION = 240  # 4 minutes
    FORECAST_DURATION = 60  # 1 minute
    STOCKS_DURATION = 60    # 1 minute
    EVENTS_DURATION = 60    # 1 minute
    TRANSIT_DURATION = 60   # 1 minute
    CLOCK_DURATION = 300    # 5 minutes (error mode)

    # Update intervals
    WEATHER_UPDATE_INTERVAL = 300  # 5 minutes
    FORECAST_UPDATE_INTERVAL = 900  # 15 minutes
    STOCKS_UPDATE_INTERVAL = 300   # 5 minutes

    # Cache expiry
    WEATHER_CACHE_MAX_AGE = 900  # 15 minutes
    FORECAST_CACHE_MAX_AGE = 1800  # 30 minutes
    STOCKS_CACHE_MAX_AGE = 900  # 15 minutes (during market hours)

    # Network recovery
    WIFI_RECONNECT_DELAY = 300  # 5 minutes between WiFi attempts
    API_RETRY_BASE_DELAY = 2  # Exponential backoff base
    API_MAX_RETRIES = 3

    # Daily restart
    RESTART_HOUR = 3  # 3am daily restart

# ============================================================================
# API CONFIGURATION
# ============================================================================

class API:
    """API endpoints and configuration"""
    # AccuWeather
    ACCUWEATHER_BASE = "http://dataservice.accuweather.com"
    ACCUWEATHER_CURRENT = "/currentconditions/v1/{location}?details=true"
    ACCUWEATHER_FORECAST = "/forecasts/v1/hourly/12hour/{location}"

    # Twelve Data (Stocks)
    TWELVE_DATA_BASE = "https://api.twelvedata.com"
    TWELVE_DATA_QUOTE = "/quote"
    TWELVE_DATA_TIME_SERIES = "/time_series"

    # CTA Transit
    CTA_TRAIN_TRACKER = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"
    CTA_BUS_TRACKER = "http://www.ctabustracker.com/bustime/api/v2/getpredictions"

    # GitHub (remote config)
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

    # Timezone API
    TIMEZONE_API = "http://worldtimeapi.org/api/timezone/{timezone}"

# ============================================================================
# PATHS
# ============================================================================

class Paths:
    """File system paths"""
    # Fonts
    FONT_LARGE = "/fonts/bigbit10-16.bdf"
    FONT_SMALL = "/fonts/tinybit6-16.bdf"

    # Images
    WEATHER_IMAGES = "/img/weather"
    FORECAST_IMAGES = "/img/weather/columns"
    EVENT_IMAGES = "/img/events"
    SCHEDULE_IMAGES = "/img/schedules"

    # Data files
    EVENTS_CSV = "/events.csv"
    SCHEDULES_CSV = "/schedules.csv"
    STOCKS_CSV = "/stocks.csv"
    DISPLAY_CONFIG_CSV = "/display_config.csv"

# ============================================================================
# HARDWARE
# ============================================================================

class Hardware:
    """Hardware pin definitions"""
    # MatrixPortal S3 buttons
    BUTTON_UP_PIN = "board.BUTTON_UP"    # Stop button
    BUTTON_DOWN_PIN = "board.BUTTON_DOWN"  # Reserved for future

    # I2C for RTC
    I2C_SDA = "board.SDA"
    I2C_SCL = "board.SCL"

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
    WIFI_SSID = get.__func__("CIRCUITPY_WIFI_SSID")
    WIFI_PASSWORD = get.__func__("CIRCUITPY_WIFI_PASSWORD")

    # AccuWeather
    ACCUWEATHER_KEY_TYPE1 = get.__func__("ACCUWEATHER_API_KEY_TYPE1")
    ACCUWEATHER_KEY_TYPE2 = get.__func__("ACCUWEATHER_API_KEY_TYPE2")
    ACCUWEATHER_LOCATION = get.__func__("ACCUWEATHER_LOCATION_KEY")

    # Twelve Data
    TWELVE_DATA_KEY = get.__func__("TWELVE_DATA_API_KEY")

    # CTA Transit
    CTA_API_KEY = get.__func__("CTA_API_KEY")

    # Device identification
    MATRIX_ID = get.__func__("MATRIX1", "unknown")

    # Timezone
    TIMEZONE = get.__func__("TIMEZONE", "America/Chicago")

    # GitHub URLs (optional)
    GITHUB_EVENTS_URL = get.__func__("GITHUB_REPO_URL")
    GITHUB_STOCKS_URL = get.__func__("STOCKS_CSV_URL")

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

class DisplayConfig:
    """Feature toggles - can be overridden by CSV"""

    # Core displays
    show_weather = True
    show_forecast = True
    show_stocks = True
    show_events = True
    show_schedules = True
    show_transit = False  # CTA transit

    # Display elements
    show_weekday_indicator = True

    # API controls
    use_live_weather = True
    use_live_forecast = True

    # Market hours
    stocks_respect_market_hours = True

    # Transit hours
    transit_respect_commute_hours = True

    # Display frequencies (show every N cycles)
    stocks_display_frequency = 1
    transit_display_frequency = 3

    # Test modes
    use_test_date = False
    test_date = "01-01"  # MM-DD format

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
# MARKET HOURS
# ============================================================================

class MarketHours:
    """US stock market trading hours (Eastern Time)"""
    # Market open/close times in ET
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_HOUR = 16
    MARKET_CLOSE_MINUTE = 0

    # Grace period after close (show cached data)
    GRACE_PERIOD_HOURS = 1.5

    # Trading days (0=Monday, 4=Friday)
    TRADING_DAYS = [0, 1, 2, 3, 4]

# ============================================================================
# COMMUTE HOURS
# ============================================================================

class CommuteHours:
    """Chicago morning commute hours"""
    START_HOUR = 9
    END_HOUR = 11

# ============================================================================
# MEMORY LIMITS
# ============================================================================

class Memory:
    """Memory management constants"""
    IMAGE_CACHE_MAX = 12  # Max images in cache
    TEXT_CACHE_MAX = 50   # Max text width calculations
    GC_FREQUENCY = 10     # Run gc.collect() every N cycles
    MEMORY_REPORT_FREQUENCY = 100  # Log memory every N cycles

# ============================================================================
# HELPER FUNCTIONS (TRULY ZERO-COST)
# ============================================================================

def get_day_color(weekday):
    """Get color for day indicator (0=Monday, 6=Sunday)"""
    day_colors = [
        Colors.MONDAY_COLOR,
        Colors.TUESDAY_COLOR,
        Colors.WEDNESDAY_COLOR,
        Colors.THURSDAY_COLOR,
        Colors.FRIDAY_COLOR,
        Colors.SATURDAY_COLOR,
        Colors.SUNDAY_COLOR
    ]
    return day_colors[weekday] if 0 <= weekday < 7 else Colors.WHITE
