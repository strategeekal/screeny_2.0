##### PANTALLITA 2.3.0 #####
# Stack exhaustion fix: Flattened nested try/except blocks to prevent crashes (v2.0.1)
# Socket exhaustion fix: response.close() + smart caching (v2.0.2)
# Comprehensive socket fix: Added response.close() to ALL HTTP requests - startup & runtime (v2.0.3)
# CRITICAL socket pool fix: Reuse single global socket pool instead of creating new pools (v2.0.5)
# Simplified approach: Removed mid-schedule cleanup - matches proven regular cycle behavior (v2.0.6)
# Simplified and flattened: image fallbacks, hour formatting, csv parsing, GitHub imports and element display (v2.0.7)
# Split forecast and current weather functions into fully independent functions and helpers (v2.0.8)
# Added remote display control via .csv like events and schedules (v2.0.9)
# Stock market integration: Real-time stock prices with Twelve Data API, 3-stock rotation display (v2.1.0)
# Single stock chart display with intraday data, smart rotation, API tracking (v2.2.0)
# Built-in button control: MatrixPortal UP button for stop/exit (v2.3.0)

# === LIBRARIES ===
# Standard library
import board
import digitalio
import os
import supervisor
import gc
import time
import ssl
import microcontroller
import random
import traceback

# Display
import displayio
import framebufferio
import rgbmatrix
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.triangle import Triangle
import adafruit_imageload

# Network
import wifi
import socketpool
import adafruit_requests as requests

# Hardware
import adafruit_ds3231
import adafruit_ntp

gc.collect()

# === CONSTANTS ===

## Display Hardware

class Display:
	WIDTH = 64
	HEIGHT = 32
	BIT_DEPTH = 4

## Layout & Positioning

class Layout:
	RIGHT_EDGE = 63
	UV_BAR_Y = 27
	HUMIDITY_BAR_Y = 29
	
	# Current Layout
	WEATHER_TEMP_X = 2
	WEATHER_TEMP_Y = 20
	WEATHER_TIME_X = 15
	WEATHER_TIME_Y = 24
	CLOCK_DATE_X = 5
	CLOCK_DATE_Y = 7
	CLOCK_TIME_X = 5
	CLOCK_TIME_Y = 20
	FEELSLIKE_Y = 16
	FEELSLIKE_SHADE_Y = 24
	BG_PADDING_TOP = -5
	
	# Forecast layout
	FORECAST_COLUMN_Y = 9
	FORECAST_COLUMN_WIDTH = 13
	FORECAST_TIME_Y = 1
	FORECAST_TEMP_Y = 25
	FORECAST_COL1_X = 3
	FORECAST_COL2_X = 25
	FORECAST_COL3_X = 48
	
	# Event image positioning
	EVENT_IMAGE_X = 37        # Right-aligned for 25px wide image
	EVENT_IMAGE_Y = 2
	EVENT_TEXT_X = 2
	COLOR_TEST_TEXT_X = 2
	COLOR_TEST_TEXT_Y = 2
	
	# Text margins
	TEXT_MARGIN = 2
	LINE_SPACING = 1
	BOTTOM_MARGIN = 2
	DESCENDER_EXTRA_MARGIN = 2
	
	# Schedule image positioning
	SCHEDULE_IMAGE_X = 23        # Image size 40 x 28 px
	SCHEDULE_IMAGE_Y = 0
	SCHEDULE_LEFT_MARGIN_X = 2
	SCHEDULE_W_IMAGE_Y = 9
	SCHEDULE_TEMP_Y = 24
	SCHEDULE_UV_Y = 30
	SCHEDULE_X_OFFSET = -1
	
	# Progress bar positioning (below day indicator)
	PROGRESS_BAR_HORIZONTAL_X = 23 # 23 (aligned with image)
	PROGRESS_BAR_HORIZONTAL_Y = 29  # Below 28px tall image + 1px gap = y=31
	PROGRESS_BAR_HORIZONTAL_WIDTH = 40
	PROGRESS_BAR_HORIZONTAL_HEIGHT = 2
	
	# Icon test layout (2 rows x 3 columns)
	ICON_TEST_COL_WIDTH = 21  # 64 / 3 ≈ 21
	ICON_TEST_ROW_HEIGHT = 16  # 32 / 2 = 16
	ICON_TEST_COL1_X = 4
	ICON_TEST_COL2_X = 25
	ICON_TEST_COL3_X = 46
	ICON_TEST_ROW1_Y = 5
	ICON_TEST_ROW2_Y = 17
	ICON_TEST_NUMBER_Y_OFFSET = 17  # Below 23px tall icon
	
class DayIndicator:
	SIZE = 4
	X = 60              # 64 - 4
	Y = 0
	MARGIN_LEFT_X = 59  # X - 1
	MARGIN_BOTTOM_Y = 4 # Y + SIZE
	
## Timing (all in seconds)

class Timing:
	DEFAULT_CYCLE = 300
	DEFAULT_FORECAST = 60
	DEFAULT_EVENT = 30
	MIN_EVENT_DURATION = 10
	CLOCK_DISPLAY_DURATION = 300
	COLOR_TEST = 300
	ICON_TEST = 5
	MAX_CACHE_AGE = 900
	
	# Schedule segment constants
	SCHEDULE_SEGMENT_DURATION = 300
	MIN_SLEEP_INTERVAL = 1 # Minimum sleep between display updates
	MAX_SLEEP_INTERVAL = 5 # Maximum sleep between display updates

	# Stock update constants
	STOCK_UPDATE_INTERVAL = 900  # 15 minutes between stock price updates
	STOCK_CACHE_MAX_AGE = 1800  # 30 minutes max age for cached prices

	# US Stock Market Hours (Eastern Time)
	MARKET_OPEN_HOUR = 9
	MARKET_OPEN_MINUTE = 30
	MARKET_CLOSE_HOUR = 16  # 4:00 PM ET
	MARKET_CLOSE_MINUTE = 0
	MARKET_CACHE_GRACE_MINUTES = 90  # Show cached data for 1.5 hours after close (until 5:30pm ET)

	FORECAST_UPDATE_INTERVAL = 900  # - 3 cycles
	DAILY_RESET_HOUR = 3
	DAILY_RESET_MINUTE_DEVICE1 = 0
	DAILY_RESET_MINUTE_DEVICE2 = 2
	EXTENDED_FAILURE_THRESHOLD = 900  # 15 minutes   When to enter clock-only mode for recovery
	INTERRUPTIBLE_SLEEP_INTERVAL = 0.1
	
	# Retry delays
	RTC_RETRY_DELAY = 2
	WIFI_RETRY_DELAY = 2
	
	SLEEP_BETWEEN_ERRORS = 5
	ERROR_SAFETY_DELAY = 30  # Delay on errors to prevent runaway loops
	FAST_CYCLE_THRESHOLD = 10  # Cycles faster than this are suspicious
	RESTART_DELAY = 10
	
	WEATHER_UPDATE_INTERVAL = 60
	MEMORY_CHECK_INTERVAL = 60
	GC_INTERVAL = 120
	
	CYCLES_TO_MONITOR_MEMORY = 10
	CYCLES_FOR_FORCE_CLEANUP = 25
	CYCLES_FOR_MEMORY_REPORT = 100
	CYCLES_FOR_CACHE_STATS = 50
	
	EVENT_CHUNK_SIZE = 60
	EVENT_MEMORY_MONITORING = 600 # For long events (e.g. all day)
	
	# Event time filtering
	EVENT_ALL_DAY_START = 0   # All-day events start at midnight
	EVENT_ALL_DAY_END = 24    # All-day events end at midnight next day
	
	API_RECOVERY_RETRY_INTERVAL = 1800

## CTA Transit Configuration
class CTA:
	# API URLs
	TRAIN_TRACKER_URL = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"
	BUS_TRACKER_URL = "http://www.ctabustracker.com/bustime/api/v2/getpredictions"

	# Station IDs (mapid for trains)
	STATION_DIVERSEY = "40530"      # Brown & Purple lines
	STATION_FULLERTON = "41220"     # Red line

	# Bus stop IDs (stpid for buses)
	STOP_HALSTED_WRIGHTWOOD = "1446"  # 8 bus southbound (approximate - may need adjustment)

	# Route IDs
	ROUTE_8_HALSTED = "8"

	# Line colors (for display circles)
	COLOR_RED = 0xC60C30      # CTA Red
	COLOR_BROWN = 0x62361B    # CTA Brown
	COLOR_PURPLE = 0x522398   # CTA Purple
	COLOR_BUS = 0xFFFFFF      # White for buses

	# Cache settings
	CACHE_MAX_AGE = 60        # 1 minute cache for transit data
	UPDATE_INTERVAL = 60      # Update every minute

	# Commute hours (9-11 AM)
	COMMUTE_START_HOUR = 9
	COMMUTE_END_HOUR = 11

# Timezone offset table
TIMEZONE_OFFSETS = {
		"America/New_York": {"std": -5, "dst": -4, "dst_start": (3, 8), "dst_end": (11, 7)},
		"America/Chicago": {"std": -6, "dst": -5, "dst_start": (3, 8), "dst_end": (11, 7)},
		"America/Denver": {"std": -7, "dst": -6, "dst_start": (3, 8), "dst_end": (11, 7)},
		"America/Los_Angeles": {"std": -8, "dst": -7, "dst_start": (3, 8), "dst_end": (11, 7)},
	}
	
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

## API Configuration
class API:
	TIMEOUT = 30
	MAX_RETRIES = 2
	RETRY_BASE_DELAY = 2
	RETRY_DELAY = 2
	MAX_CALLS_BEFORE_RESTART = 350
	
	MAX_FORECAST_HOURS = 12
	DEFAULT_FORECAST_HOURS = 12
	
	# URLs (base parts)
	BASE_URL = "https://dataservice.accuweather.com"
	CURRENT_ENDPOINT = "currentconditions/v1"
	FORECAST_ENDPOINT = "forecasts/v1/hourly/12hour"
	
	# HTTP Status codes
	HTTP_OK = 200
	HTTP_SERVICE_UNAVAILABLE = 503
	HTTP_BAD_REQUEST = 400
	HTTP_UNAUTHORIZED = 401
	HTTP_FORBIDDEN = 403
	HTTP_NOT_FOUND = 404
	HTTP_TOO_MANY_REQUESTS = 429
	HTTP_INTERNAL_SERVER_ERROR = 500

## Error Handling & Recovery
class Recovery:
	# Retry strategies
	MAX_WIFI_RETRY_ATTEMPTS = 5
	WIFI_RETRY_BASE_DELAY = 2        # Exponential backoff starting point
	WIFI_RETRY_MAX_DELAY = 60        # Cap exponential backoff
	
	API_RETRY_BASE_DELAY = 2
	API_RETRY_MAX_DELAY = 30
	
	# Degradation thresholds
	MAX_CONSECUTIVE_API_FAILURES = 3
	MAX_WIFI_RECONNECT_ATTEMPTS = 3
	
	# Recovery actions
	SOFT_RESET_THRESHOLD = 5         # Consecutive failures before soft reset
	HARD_RESET_THRESHOLD = 15
	WIFI_RECONNECT_COOLDOWN = 300  # 5 minutes between WiFi reconnection attempts
	
## Memory Management
class Memory:
	ESTIMATED_TOTAL = 2000000           # ESTIMATED_TOTAL_MEMORY
	SOCKET_CLEANUP_CYCLES = 3

## File Paths
class Paths:
	EVENTS_CSV = "events.csv"
	STOCKS_CSV = "stocks.csv"
	FONT_BIG = "fonts/bigbit10-16.bdf"
	FONT_SMALL = "fonts/tinybit6-16.bdf"

	WEATHER_ICONS = "img/weather"
	EVENT_IMAGES = "img/events"
	COLUMN_IMAGES = "img/weather/columns"
	SCHEDULE_IMAGES = "img/schedules"

	# Blank image fallbacks (user must create these)
	BLANK_WEATHER = "img/weather/0.bmp"
	BLANK_EVENT = "img/events/blank.bmp"
	BLANK_COLUMN = "img/weather/columns/0.bmp"
	BLANK_SCHEDULE = "img/schedules/blank.bmp"

	# Legacy paths
	FALLBACK_EVENT_IMAGE = "img/events/blank_sq.bmp"
	BIRTHDAY_IMAGE = "img/events/cake.bmp"
	
	# GitHub schedule paths
	GITHUB_SCHEDULE_FOLDER = "schedules"  # Folder in your repo
	LOCAL_SCHEDULE_FILE = "/schedules/schedules.csv"
	SCHEDULE_CACHE_MARKER = "/schedules/.last_update"  # Track last update
	
## Colors & Visual
class Visual:
	# UV bar calculation breakpoints
	UV_BREAKPOINT_1 = 3
	UV_BREAKPOINT_2 = 6
	UV_BREAKPOINT_3 = 9
	
	# UV spacing positions
	UV_SPACING_POSITIONS = [3, 7, 11]
	
	# Humidity calculation
	HUMIDITY_PERCENT_PER_PIXEL = 10    # 10% per pixel
	HUMIDITY_SPACING_POSITIONS = [2, 5, 8, 11]  # Every 20%
	
	# Color test grid
	COLOR_TEST_GRID_COLS = 3
	COLOR_TEST_COL_SPACING = 16
	COLOR_TEST_ROW_SPACING = 11
	
	# Temperature display threshold
	FEELS_LIKE_TEMP_THRESHOLD = 15  # Use feels-like above, feels-shade below
	
## System_constants
class System:
	MAX_RTC_ATTEMPTS = 5
	MAX_WIFI_ATTEMPTS = 3
	MAX_LOG_FAILURES_BEFORE_RESTART = 3
	HOURS_BEFORE_DAILY_RESTART = 24
	RESTART_GRACE_MINUTES = 5          # rtc.datetime.tm_min < 5
	
	# Matrix device mappings
	DEVICE_TYPE1_ID = os.getenv("MATRIX1")
	DEVICE_TYPE2_ID = os.getenv("MATRIX2")
	
	# Hour format constants
	HOURS_IN_DAY = 24
	HOURS_IN_HALF_DAY = 12
	SECONDS_PER_MINUTE = 60
	SECONDS_PER_HOUR = 3600
	SECONDS_HALF_HOUR = 1800
	
	# Startup and Restart timing control
	STARTUP_DELAY_TIME = 60
	RESTART_GRACE_MINUTES = 10
	MINIMUM_RUNTIME_BEFORE_RESTART = 0.2
	
## Test Data Constants

class TestData:
	# Move TEST_DATE_DATA values here
	TEST_YEAR = None
	TEST_MONTH = None
	TEST_DAY =  None
	TEST_HOUR = None
	TEST_MINUTE = None
	
	# Dummy weather values
	DUMMY_WEATHER_DATA = {
		"weather_icon": 1,
		"temperature": -12,
		"feels_like": -13.6,
		"feels_shade": -14.6,
		"humidity": 90,
		"uv_index": 7,
		"weather_text": "DUMMY",
		"is_day_time": True,
		"has_precipitation": False,
	}
	
	TEST_ICONS = [1, 2, 3] # If None, screen will batch through all icons

## String Constants
class Strings:
	DEFAULT_EVENT_COLOR = "MINT"
	TIMEZONE_DEFAULT = os.getenv("TIMEZONE")    # TIMEZONE_CONFIG["timezone"]
	
	# API key names
	API_KEY_TYPE1 = "ACCUWEATHER_API_KEY_TYPE1"
	API_KEY_TYPE2 = "ACCUWEATHER_API_KEY_TYPE2"
	API_KEY_FALLBACK = "ACCUWEATHER_API_KEY"
	API_LOCATION_KEY = "ACCUWEATHER_LOCATION_KEY"
	TWELVE_DATA_API_KEY = "TWELVE_DATA_API_KEY"
	
	# Environment variables
	WIFI_SSID_VAR = "CIRCUITPY_WIFI_SSID"
	WIFI_PASSWORD_VAR = "CIRCUITPY_WIFI_PASSWORD"
	
	# Event sources
	GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")
	STOCKS_CSV_URL = os.getenv("STOCKS_CSV_URL")
	GITHUB_STOCKS_FILE = "stocks.csv"  # Stocks file in GitHub repo

	# Font test characters
	FONT_METRICS_TEST_CHARS = "Aygjpq"
	DESCENDER_CHARS = {'g', 'j', 'p', 'q', 'y'}
	
	# Time format strings:
	AM_SUFFIX = "A"
	PM_SUFFIX = "P"
	NOON_12AM = "12A"
	NOON_12PM = "12P"
	
# Debug configuration
class DebugLevel:
	NONE = 0      # Silence (not recommended)
	ERROR = 1     # Errors only - something broke
	WARNING = 2   # Errors + warnings - potential issues
	INFO = 3      # Errors + warnings + key events (DEFAULT - recommended)
	DEBUG = 4     # Add troubleshooting details
	VERBOSE = 5   # Everything including routine operations

# Recommended for production
CURRENT_DEBUG_LEVEL = DebugLevel.INFO

class DisplayConfig:
	"""
	Centralized display and feature control
	
	Controls what content is displayed and how data is fetched.
	Changes take effect on next cycle.
	"""
	
	### ================== ### ================== ### ================== ### ================== ### ==================
	###################### === ################## === ################## === ################## === ##################
	### ================== ### ================== ### ================== ### ================== ### ==================
	
	def __init__(self):
		# DEVELOPMENT vs PRODUCTION toggle
		self.delayed_start = False  # False for dev (faster), True for production (safer)
		
		# Core displays (always try to show if data available)
		self.show_weather = True
		self.show_forecast = True
		self.show_events = True
		self.show_stocks = False  # Stock market display (disabled by default)
		self.stocks_display_frequency = 3  # Show stocks every N cycles (e.g., 3 = every 15 min)
		self.stocks_respect_market_hours = True  # True = only show during market hours + grace period, False = always show (for testing)
		self.show_transit = False  # CTA transit display (disabled by default)
		self.transit_display_frequency = 3  # Show transit every N cycles
		self.transit_respect_commute_hours = True  # True = only show 9-11 AM, False = always show (for testing)

		# Display Elements
		self.show_weekday_indicator = True
		self.show_scheduled_displays = True
		self.show_events_in_between_schedules = True
		self.night_mode_minimal_display = True  # Hide weather icon & weekday indicator during night mode schedules

		# API controls (fetch real data vs use dummy data)
		self.use_live_weather = True      # False = use dummy data
		self.use_live_forecast = True     # False = use dummy data
		
		# Test/debug modes
		self.use_test_date = False
		self.show_color_test = False
		self.show_icon_test = False
		
	### ================== ### ================== ### ================== ### ================== ### ==================
	###################### === ################## === ################## === ################## === ##################
	### ================== ### ================== ### ================== ### ================== ### ==================
	

	def validate(self):
		"""Validate configuration and return list of issues"""
		issues = []
		warnings = []

		# NOTE: Forecast can be shown without weather display
		# The forecast display uses current weather data for the first column,
		# but doesn't require the weather display to be enabled

		# Warn about dummy modes
		if not self.use_live_weather:
			log_warning("Using DUMMY weather data (not fetching from API)")

		if not self.use_live_forecast:
			log_warning("Using DUMMY forecast data (not fetching from API)")

		if self.use_test_date:
			log_warning("Test date mode enabled - NTP sync will be skipped")

	
	def should_fetch_weather(self):
		"""Should we fetch current weather from API?

		Note: Current weather data is needed by both weather display AND forecast display
		(forecast uses it for the first column showing current conditions)
		"""
		return (self.show_weather or self.show_forecast) and self.use_live_weather
	
	def should_fetch_forecast(self):
		"""Should we fetch forecast from API?"""
		return self.show_forecast and self.use_live_forecast
	
	def get_active_features(self):
		"""Return list of enabled features"""
		features = []
		if self.show_weather: features.append("weather")
		if self.show_forecast: features.append("forecast")
		if self.show_events: features.append("events")
		if self.show_stocks: features.append("stocks")
		if self.show_transit: features.append("transit")
		if self.show_weekday_indicator: features.append("weekday_indicator")

		# Add data source info
		if not self.use_live_weather: features.append("dummy_weather")
		if not self.use_live_forecast: features.append("dummy_forecast")
		# if self.use_test_date: features.append("test_date")
		if self.show_color_test: features.append("color_test")
		if self.show_icon_test: features.append("icon_test")
		
		return features
	
	def log_status(self):
		"""Log current configuration status"""
		log_info(f"Features: {', '.join(self.get_active_features())}")
		
display_config = DisplayConfig()

def get_remaining_schedule_time(rtc, schedule_config):
	"""Calculate how much time remains in the current schedule window"""
	current = rtc.datetime
	current_mins = current.tm_hour * 60 + current.tm_min
	end_mins = schedule_config["end_hour"] * 60 + schedule_config["end_min"]
	
	# Calculate remaining minutes
	remaining_mins = end_mins - current_mins
	
	# Convert to seconds, with minimum of 1 minute
	remaining_seconds = max(remaining_mins * 60, 60)
	
	return remaining_seconds

class ColorManager:
	"""Centralized color management with dynamic bit depth support"""
	
	# Define base colors as 8-bit RGB (0-255 range)
	BASE_COLORS_8BIT = {
		"BLACK": (0, 0, 0),
		"DIMMEST_WHITE": (96, 96, 96),      # - - reduced flicker
		"MINT": (40, 140, 60),              
		"BUGAMBILIA": (64, 0, 64),           # 0x400040
		"LILAC": (64, 32, 64),               # 0x402040
		"RED": (204, 0, 0),                  # 0xCC0000
		"GREEN": (0, 68, 0),                # 0x00CC00
		"LIME": (0, 204, 0),                # 0x00CC00
		"BLUE": (0, 51, 102),  # 0x003366 - 4-bit: 0, 3, 6
		"ORANGE": (204, 80, 0),             # 0xCC6600
		"YELLOW": (204, 140, 0),             # 0xCCCC00
		"CYAN": (0, 204, 204),               # 0x00CCCC
		"PURPLE": (102, 0, 204),             # 0x6600CC
		"PINK": (204, 64, 120),             # 0xCC66AA
		"LIGHT_PINK": (204, 102, 170),             # 0xCC66AA
		"AQUA": (0, 102, 102),               # 0x006666
		"WHITE": (204, 204, 204),            # 0xCCCCCC - bright, less flicker
		"GRAY": (102, 102, 102),             # 0x666666
		"DARK_GRAY": (32, 32, 32),        #Flickers
		"BEIGE": (136, 85, 34),  # 0x885522 - 4-bit: 8, 5, 2
		"BROWN": (51, 17, 0),  # 0x331100 - 4-bit: 3, 1, 0
	}
	
	@staticmethod
	def swap_green_blue(r, g, b):
		"""Swap green and blue channels for type1 matrix"""
		return (r, b, g)  # Green and blue swapped
	
	@staticmethod
	def quantize_channel(value_8bit, bit_depth):
		"""Quantize an 8-bit color channel to specified bit depth"""
		if bit_depth == 8:
			return value_8bit
		
		# Calculate how many levels we have
		max_value = (1 << bit_depth) - 1  # 2^bit_depth - 1
		
		# Scale from 8-bit to bit_depth
		quantized = (value_8bit * max_value) // 255
		
		# Scale back to 8-bit range for display
		return (quantized * 255) // max_value
	
	@staticmethod
	def rgb_to_hex(r, g, b):
		"""Convert RGB tuple to hex color"""
		return (r << 16) | (g << 8) | b
	
	@classmethod
	def generate_colors(cls, matrix_type, bit_depth):
		"""
		Generate color dictionary for specified matrix type and bit depth
		
		Args:
			matrix_type: "type1" or "type2"
			bit_depth: 3, 4, 5, or 6
		
		Returns:
			Dictionary of color names to hex values
		"""
		colors = {}
		
		for name, (r, g, b) in cls.BASE_COLORS_8BIT.items():
			# Swap channels if type1 matrix
			if matrix_type == "type1":
				r, g, b = cls.swap_green_blue(r, g, b)
			
			# Quantize to bit depth
			r_quantized = cls.quantize_channel(r, bit_depth)
			g_quantized = cls.quantize_channel(g, bit_depth)
			b_quantized = cls.quantize_channel(b, bit_depth)
			
			# Convert to hex
			colors[name] = cls.rgb_to_hex(r_quantized, g_quantized, b_quantized)
		
		return colors

# System Configuration
DAILY_RESET_ENABLED = True

### CONFIGURATION VALIDATION ###

def validate_configuration():
	"""Validate configuration values and log warnings for potential issues"""
	issues = []
	warnings = []
	
	# Timing validations
	if Timing.DEFAULT_CYCLE < (Timing.DEFAULT_FORECAST + Timing.DEFAULT_EVENT):
		issues.append(f"DEFAULT_CYCLE ({Timing.DEFAULT_CYCLE}s) is too short for forecast+event ({Timing.DEFAULT_FORECAST + Timing.DEFAULT_EVENT}s)")
	
	if Timing.CLOCK_DISPLAY_DURATION > Timing.DEFAULT_CYCLE:
		warnings.append(f"CLOCK_DISPLAY_DURATION ({Timing.CLOCK_DISPLAY_DURATION}s) exceeds DEFAULT_CYCLE ({Timing.DEFAULT_CYCLE}s)")
	
	if Timing.EXTENDED_FAILURE_THRESHOLD < Timing.CLOCK_DISPLAY_DURATION:
		issues.append(f"EXTENDED_FAILURE_THRESHOLD ({Timing.EXTENDED_FAILURE_THRESHOLD}s) should be >= CLOCK_DISPLAY_DURATION ({Timing.CLOCK_DISPLAY_DURATION}s)")
		
	if System.RESTART_GRACE_MINUTES < (Timing.DEFAULT_CYCLE / 60) + 3:
		warnings.append(f"RESTART_GRACE_MINUTES ({System.RESTART_GRACE_MINUTES}) should be at least {int(Timing.DEFAULT_CYCLE/60) + 3} minutes to accommodate cycle length")
	
	# API validations
	if API.MAX_RETRIES > 5:
		warnings.append(f"API.MAX_RETRIES ({API.MAX_RETRIES}) is high - may cause long delays")
	
	if API.DEFAULT_FORECAST_HOURS > API.MAX_FORECAST_HOURS:
		issues.append(f"DEFAULT_FORECAST_HOURS ({API.DEFAULT_FORECAST_HOURS}) exceeds MAX_FORECAST_HOURS ({API.MAX_FORECAST_HOURS})")
	
	# Recovery validations
	if Recovery.SOFT_RESET_THRESHOLD >= Recovery.HARD_RESET_THRESHOLD:
		issues.append(f"SOFT_RESET_THRESHOLD ({Recovery.SOFT_RESET_THRESHOLD}) should be < HARD_RESET_THRESHOLD ({Recovery.HARD_RESET_THRESHOLD})")
	
	if Recovery.WIFI_RECONNECT_COOLDOWN < 60:
		warnings.append(f"WIFI_RECONNECT_COOLDOWN ({Recovery.WIFI_RECONNECT_COOLDOWN}s) is very short - may cause excessive reconnection attempts")
	
	# Display validations
	if Display.WIDTH != 64 or Display.HEIGHT != 32:
		warnings.append(f"Non-standard display dimensions: {Display.WIDTH}x{Display.HEIGHT}")
	
	# Report issues
	if issues:
		log_error("=== CONFIGURATION ERRORS ===")
		for issue in issues:
			log_error(f"  - {issue}")
		log_error("Fix these issues before running!")
		return False
	
	if warnings:
		log_warning("=== CONFIGURATION WARNINGS ===")
		for warning in warnings:
			log_warning(f"  - {warning}")
	
	log_debug("Configuration validation passed")
	return True

### CACHE ###

class ImageCache:
	def __init__(self, max_size=10):
		self.cache = {}  # filepath -> (bitmap, palette)
		self.max_size = max_size
		self.hit_count = 0
		self.miss_count = 0
	
	def get_image(self, filepath):
		if filepath in self.cache:
			self.hit_count += 1
			return self.cache[filepath]
		
		# Cache miss - load the image
		try:
			bitmap, palette = load_bmp_image(filepath)
			self.miss_count += 1
			
			# Check if cache is full
			if len(self.cache) >= self.max_size:
				# Remove oldest entry (simple FIFO)
				oldest_key = next(iter(self.cache))
				del self.cache[oldest_key]
				log_verbose(f"Image cache full, removed: {oldest_key}")
			
			self.cache[filepath] = (bitmap, palette)
			log_verbose(f"Cached image: {filepath}")
			return bitmap, palette
			
		except Exception as e:
			log_error(f"Failed to load image {filepath}: {e}")
			return None, None
	
	def clear_cache(self):
		self.cache.clear()
		log_verbose("Image cache cleared")
	
	def get_stats(self):
		total = self.hit_count + self.miss_count
		hit_rate = (self.hit_count / total * 100) if total > 0 else 0
		return f"Cache: {len(self.cache)} items, {hit_rate:.1f}% hit rate"
		
class TextWidthCache:
		def __init__(self, max_size=50):
			self.cache = {}  # (text, font_id) -> width
			self.max_size = max_size
			self.hit_count = 0
			self.miss_count = 0
		
		def get_text_width(self, text, font):
			if not text:
				return 0
				
			cache_key = (text, id(font))
			
			if cache_key in self.cache:
				self.hit_count += 1
				return self.cache[cache_key]
			
			# Cache miss - calculate width
			temp_label = bitmap_label.Label(font, text=text)
			bbox = temp_label.bounding_box
			width = bbox[2] if bbox else 0
			
			self.miss_count += 1
			
			# Evict oldest if cache full
			if len(self.cache) >= self.max_size:
				oldest_key = next(iter(self.cache))
				del self.cache[oldest_key]
			
			self.cache[cache_key] = width
			return width
		
		def get_stats(self):
			total = self.hit_count + self.miss_count
			hit_rate = (self.hit_count / total * 100) if total > 0 else 0
			return f"Text cache: {len(self.cache)} items, {hit_rate:.1f}% hit rate"
		
class MemoryMonitor:
	def __init__(self):
		self.baseline_memory = gc.mem_free()
		self.startup_time = time.monotonic()
		self.peak_usage = 0
		self.measurements = []
		self.max_measurements = 5  # Reduced from 10
		
	def get_memory_stats(self):
		"""Get current memory statistics with percentages"""
		current_free = gc.mem_free()
		current_used = Memory.ESTIMATED_TOTAL - current_free
		usage_percent = (current_used / Memory.ESTIMATED_TOTAL) * 100
		free_percent = (current_free / Memory.ESTIMATED_TOTAL) * 100
		
		return {
			"free_bytes": current_free,
			"used_bytes": current_used,
			"usage_percent": usage_percent,
			"free_percent": free_percent,
		}
	
	def get_runtime(self):
		"""Get runtime since startup"""
		elapsed = time.monotonic() - self.startup_time
		hours = int(elapsed // System.SECONDS_PER_HOUR)
		minutes = int((elapsed % System.SECONDS_PER_HOUR) // System.SECONDS_PER_MINUTE)
		seconds = int(elapsed % System.SECONDS_PER_MINUTE)
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
	
	def check_memory(self, checkpoint_name=""):
		"""Check memory and log only if there's an issue"""
		stats = self.get_memory_stats()
		runtime = self.get_runtime()

		if stats["used_bytes"] > self.peak_usage:
			self.peak_usage = stats["used_bytes"]

		self.measurements.append({
			"name": checkpoint_name,
			"used_percent": stats["usage_percent"],
			"runtime": runtime
		})
		if len(self.measurements) > self.max_measurements:
			self.measurements.pop(0)

		# Only log if memory usage is concerning (>50%) or at VERBOSE level
		if stats["usage_percent"] > 50:
			log_warning(f"High memory: {stats['usage_percent']:.1f}% at {checkpoint_name}")
		else:
			log_verbose(f"Memory: {stats['usage_percent']:.1f}% at {checkpoint_name}")

		return "ok"
	
	def get_memory_report(self):
		"""Generate a simplified memory report"""
		stats = self.get_memory_stats()
		runtime = self.get_runtime()
		peak_percent = (self.peak_usage / Memory.ESTIMATED_TOTAL) * 100

		report = [
			"=== MEMORY REPORT ===",
			f"Runtime: {runtime}",
			f"Current: {stats['usage_percent']:.1f}% used",
			f"Peak usage: {peak_percent:.1f}%",
		]
		
		if self.measurements:
			report.append("Recent measurements:")
			for measurement in self.measurements:
				name = measurement["name"] or "unnamed"
				used_pct = measurement["used_percent"]
				runtime = measurement["runtime"]
				report.append(f"  {name}: {used_pct:.1f}% used [{runtime}]")
		
		return "\n".join(report)
	
	def log_report(self):
		"""Log the memory report"""
		report = self.get_memory_report()
		for line in report.split("\n"):
			log_debug(line)
		

## State Tracker
class StateTracker:
	"""Centralized success/failure tracking for API calls, errors, and recovery logic"""

	def __init__(self):
		# API call tracking
		self.api_call_count = 0
		self.current_api_calls = 0
		self.forecast_api_calls = 0
		self.stock_api_calls = 0
		self.consecutive_failures = 0
		self.last_successful_display = 0  # Last time ANY display was successful
		self.last_successful_weather = 0  # Last time weather API was successful (for hard reset)

		# WiFi failure management
		self.wifi_reconnect_attempts = 0
		self.last_wifi_attempt = 0
		self.system_error_count = 0

		# Extended failure tracking
		self.in_extended_failure_mode = False
		self.scheduled_display_error_count = 0
		self.consecutive_display_errors = 0  # Fix uninitialized counter bug
		self.has_permanent_error = False

		# Stock rotation tracking
		self.current_stock_offset = 0  # Current page offset (increments by 3 each display)

	# API Tracking Methods
	def record_api_success(self, call_type, count=1):
		"""Track successful API call (call_type: 'current', 'forecast', or 'stock')
		count: Number of API credits used (e.g., 4 for batch stock request)"""
		if call_type == "current":
			self.current_api_calls += count
		elif call_type == "forecast":
			self.forecast_api_calls += count
		elif call_type == "stock":
			self.stock_api_calls += count
		self.api_call_count += count

	def get_api_stats(self):
		"""Get formatted API stats string for logging"""
		return f"Total={self.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={self.current_api_calls}, Forecast={self.forecast_api_calls}, Stocks={self.stock_api_calls}/800"

	def reset_api_counters(self):
		"""Reset API call tracking - returns old total for logging"""
		old_total = self.api_call_count
		self.api_call_count = 0
		self.current_api_calls = 0
		self.forecast_api_calls = 0
		self.stock_api_calls = 0
		return old_total

	# Display Success/Failure Tracking
	def record_display_success(self):
		"""Handle successful display - reset failure counters and log recovery"""
		# Log recovery if coming out of extended failure mode
		if self.in_extended_failure_mode:
			recovery_time = int((time.monotonic() - self.last_successful_display) / System.SECONDS_PER_MINUTE)
			log_info(f"Display recovered after {recovery_time} minutes of failures")

		self.consecutive_failures = 0
		self.last_successful_display = time.monotonic()
		self.wifi_reconnect_attempts = 0
		self.system_error_count = 0

	def record_weather_success(self):
		"""Handle successful weather fetch - updates both display and weather timestamps"""
		self.record_display_success()  # Update display success (for extended failure mode)
		self.last_successful_weather = time.monotonic()  # Update weather success (for hard reset)

	def record_weather_failure(self):
		"""Handle failed weather fetch - increment failure counters"""
		self.consecutive_failures += 1
		self.system_error_count += 1
		log_warning(f"Consecutive failures: {self.consecutive_failures}, System errors: {self.system_error_count}")

	def record_display_error(self):
		"""Track display errors"""
		self.consecutive_display_errors += 1
		self.scheduled_display_error_count += 1

	def reset_display_errors(self):
		"""Reset display error counters"""
		self.consecutive_display_errors = 0
		self.scheduled_display_error_count = 0

	# Decision Methods
	def should_soft_reset(self):
		"""Check if soft reset is needed due to consecutive failures"""
		return self.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD

	def should_hard_reset(self):
		"""Check if hard reset is needed due to system errors"""
		return self.system_error_count >= Recovery.HARD_RESET_THRESHOLD

	def should_preventive_restart(self):
		"""Check if preventive restart is needed due to API call limit"""
		return self.api_call_count >= API.MAX_CALLS_BEFORE_RESTART

	def should_enter_extended_failure_mode(self):
		"""Check if extended failure mode should be entered"""
		if self.has_permanent_error:
			return True
		if self.last_successful_display == 0:
			return False
		time_since_success = time.monotonic() - self.last_successful_display
		return time_since_success > Recovery.EXTENDED_FAILURE_TIME

	def reset_after_soft_reset(self):
		"""Reset state after soft reset"""
		self.consecutive_failures = 0

## State Class
class WeatherDisplayState:
	def __init__(self):
		# Hardware instances
		self.rtc_instance = None
		self.display = None
		self.main_group = None
		self.matrix_type_cache = None
		self.button_up = None  # MatrixPortal UP button
		self.button_down = None  # MatrixPortal DOWN button

		# Centralized success/failure tracking
		self.tracker = StateTracker()

		# Timing and cache
		self.startup_time = 0
		self.last_forecast_fetch = -Timing.FORECAST_UPDATE_INTERVAL
		self.cached_current_weather = None
		self.cached_current_weather_time = 0
		self.cached_forecast_data = None
		self.cached_events = None
		self.cached_stocks = []
		self.cached_stock_prices = {}  # {symbol: {price, change_percent, direction, timestamp}}
		self.last_stock_fetch_time = 0
		self.market_holiday_date = None  # Cache holiday status (YYYY-MM-DD format)
		self.cached_intraday_data = {}  # {symbol: {data: [...], timestamp: monotonic, open_price: float}}
		self.last_intraday_fetch_time = {}  # {symbol: monotonic_timestamp}
		self.cached_transit_arrivals = []  # [{route, destination, minutes, type, color}, ...]
		self.last_transit_fetch_time = 0  # monotonic timestamp

		# Colors (set after matrix detection)
		self.colors = {}

		# Network session
		self.global_requests_session = None

		# Caches
		self.image_cache = ImageCache(max_size=12)
		self.text_cache = TextWidthCache()

		# Add memory monitor
		self.memory_monitor = MemoryMonitor()

		# Schedule session tracking (for segmented displays)
		self.active_schedule_name = None
		self.active_schedule_start_time = None  # monotonic time when schedule started
		self.active_schedule_end_time = None    # monotonic time when schedule should end
		self.active_schedule_segment_count = 0  # Count segments within current schedule (for display)
		self.schedule_just_ended = False

	def reset_api_counters(self):
		"""Reset API call tracking"""
		old_total = self.tracker.reset_api_counters()
		log_debug(f"API counters reset (was {old_total} total calls)")
	
	def cleanup_session(self):
		"""Clean up network session"""
		if self.global_requests_session:
			try:
				self.global_requests_session.close()
				del self.global_requests_session
				self.global_requests_session = None
				log_verbose("Global session cleaned up")
			except:
				pass

### GLOBAL STATE ###
state = WeatherDisplayState()

# Load fonts once at startup
bg_font = bitmap_font.load_font(Paths.FONT_BIG)
font = bitmap_font.load_font(Paths.FONT_SMALL)

### ====================================== FUNCTIONS AND UTILITIES  ====================================== ###

### LOGGING UTILITIES ###

def log_entry(message, level="INFO"):
	"""
	Unified logging with timestamp and level filtering
	"""
	# Map string levels to numeric levels
	level_map = {
		"DEBUG": DebugLevel.DEBUG,
		"INFO": DebugLevel.INFO,
		"WARNING": DebugLevel.WARNING,
		"ERROR": DebugLevel.ERROR
	}
	
	# Check if this message should be logged based on current debug level
	message_level = level_map.get(level, DebugLevel.INFO)
	if message_level > CURRENT_DEBUG_LEVEL:
		return  # Skip this message
	
	try:
		# Try RTC first, fallback to system time
		if state.rtc_instance:
			try:
				dt = state.rtc_instance.datetime
				timestamp = f"{dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d} {dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
				time_source = ""
			except Exception:
				import time
				monotonic_time = time.monotonic()
				timestamp = f"SYS+{int(monotonic_time)}"
				time_source = " [SYS]"
		else:
			import time
			monotonic_time = time.monotonic()
			hours = int(monotonic_time // System.SECONDS_PER_HOUR)
			minutes = int((monotonic_time % System.SECONDS_PER_HOUR) // System.SECONDS_PER_MINUTE)
			seconds = int(monotonic_time % System.SECONDS_PER_MINUTE)
			timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
			time_source = " [UPTIME]"
		
		# Build log entry
		log_line = f"[{timestamp}{time_source}] {level}: {message}"
		print(log_line)
			
	except Exception as e:
		print(f"[LOG-ERROR] Failed to log: {message} (Error: {e})")

def log_info(message):
	"""Log info message"""
	log_entry(message, "INFO")

def log_error(message):
	"""Log error message"""
	log_entry(message, "ERROR")

def log_warning(message):
	"""Log warning message"""
	log_entry(message, "WARNING")

def log_debug(message):
	"""Log debug message"""
	log_entry(message, "DEBUG")

def log_verbose(message):
	"""Log verbose message (extra detail)"""
	if CURRENT_DEBUG_LEVEL >= DebugLevel.VERBOSE:
		log_entry(message, "DEBUG")  # Use DEBUG level for formatting
		
def duration_message(seconds):
	"""Convert seconds to a readable duration string"""
	h, remainder = divmod(seconds, System.SECONDS_PER_HOUR)
	m, s = divmod(remainder, System.SECONDS_PER_MINUTE)
	
	parts = []
	if h > 0:
		parts.append(f"{h} hour{'s' if h != 1 else ''}")
	if m > 0:
		parts.append(f"{m} minute{'s' if m != 1 else ''}")
	if s > 0:
		parts.append(f"{s} second{'s' if s != 1 else ''}")
	
	return " ".join(parts) if parts else "0 seconds"
		

### PARSING FUNCTIONS ###

def parse_iso_datetime(iso_string):
	# Parse "2025-09-25T01:00:00-05:00"
	date_part, time_part = iso_string.split('T')
	
	# Parse date
	year, month, day = map(int, date_part.split('-'))
	
	# Parse time (ignoring timezone for now)
	time_with_tz = time_part.split('-')[0] if '-' in time_part else time_part.split('+')[0]
	hour, minute, second = map(int, time_with_tz.split(':'))
	
	return year, month, day, hour, minute, second
	
def format_datetime(iso_string):
	year, month, day, hour, minute, second = parse_iso_datetime(iso_string)
			
	# Format time
	if hour == 0:
		time_str = "12am"
	elif hour < 12:
		time_str = f"{hour}am"
	elif hour == 12:
		time_str = "12pm"
	else:
		time_str = f"{hour - 12}pm"
	
	return f"{MONTHS[month]} {day}, {time_str}"

### HARDWARE INITIALIZATION ###

def initialize_display():
	"""Initialize RGB matrix display"""
	
	displayio.release_displays()
	
	matrix = rgbmatrix.RGBMatrix(
		width=Display.WIDTH, height=Display.HEIGHT, bit_depth=Display.BIT_DEPTH,
		rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
				board.MTX_R2, board.MTX_G2, board.MTX_B2],
		addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB,
				board.MTX_ADDRC, board.MTX_ADDRD],
		clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT,
		output_enable_pin=board.MTX_OE,
		serpentine=True, doublebuffer=True,
	)
	
	state.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
	state.main_group = displayio.Group()
	state.display.root_group = state.main_group


def interruptible_sleep(duration):
	"""Sleep that can be interrupted more easily (checks stop button)"""
	end_time = time.monotonic() + duration
	while time.monotonic() < end_time:
		# Check stop button - direct GPIO read, no function calls to avoid stack depth
		if state.button_up and not state.button_up.value:
			raise KeyboardInterrupt("Stop button pressed")

		time.sleep(Timing.INTERRUPTIBLE_SLEEP_INTERVAL)

def setup_rtc():
	"""Initialize RTC with retry logic"""
	
	for attempt in range(System.MAX_RTC_ATTEMPTS):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			state.rtc_instance = rtc
			log_debug(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			log_debug(f"RTC attempt {attempt + 1} failed: {e}")
			if attempt < 4:
				interruptible_sleep(Timing.RTC_RETRY_DELAY)
	
	log_error("RTC initialization failed, restarting...")
	supervisor.reload()

### BUTTON FUNCTIONS ###

def setup_buttons():
	"""Initialize built-in MatrixPortal S3 buttons (optional - graceful if not available)"""
	try:
		# Set up UP button (typically used for stop/exit)
		button_up = digitalio.DigitalInOut(board.BUTTON_UP)
		button_up.direction = digitalio.Direction.INPUT
		button_up.pull = digitalio.Pull.UP
		state.button_up = button_up

		# Set up DOWN button (typically used for manual advance)
		button_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
		button_down.direction = digitalio.Direction.INPUT
		button_down.pull = digitalio.Pull.UP
		state.button_down = button_down

		log_info("MatrixPortal buttons initialized - UP=stop, DOWN=advance")
		return True

	except Exception as e:
		log_debug(f"Buttons not available (optional): {e}")
		state.button_up = None
		state.button_down = None
		return False

### NETWORK FUNCTIONS ###

def setup_wifi_with_recovery():
	"""Enhanced WiFi connection with exponential backoff and reconnection"""
	ssid = os.getenv(Strings.WIFI_SSID_VAR)
	password = os.getenv(Strings.WIFI_PASSWORD_VAR)
	
	if not ssid or not password:
		log_error("WiFi credentials missing in settings.toml")
		return False
	
	try:
		if wifi.radio.connected:
			log_debug("WiFi already connected")  # DEBUG - not important
			return True
	except:
		pass
	
	for attempt in range(Recovery.MAX_WIFI_RETRY_ATTEMPTS):
		try:
			delay = min(
				Recovery.WIFI_RETRY_BASE_DELAY * (2 ** attempt),
				Recovery.WIFI_RETRY_MAX_DELAY
			)
			
			# Only log first and subsequent attempts differently:
			if attempt == 0:
				log_debug(f"Connecting to WiFi...")  # DEBUG
			else:
				log_debug(f"WiFi retry {attempt}/{Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1} in {delay}s")
			
			wifi.radio.connect(ssid, password, timeout=10)
			
			if wifi.radio.connected:
				# SUCCESS at INFO level:
				log_info(f"WiFi: {ssid[:8]}... ({wifi.radio.ipv4_address})")
				return True
				
		except ConnectionError as e:
			# Individual failures at DEBUG:
			log_debug(f"WiFi attempt {attempt + 1} failed")
			if attempt < Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1:
				interruptible_sleep(delay)
				
		except Exception as e:
			log_debug(f"WiFi error: {type(e).__name__}")
			if attempt < Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1:
				interruptible_sleep(delay)
	
	# Complete failure at ERROR:
	log_error(f"WiFi failed after {Recovery.MAX_WIFI_RETRY_ATTEMPTS} attempts")
	return False

def check_and_recover_wifi():
	"""Check WiFi connection with cooldown protection"""
	try:
		if wifi.radio.connected:
			return True

		# Only attempt reconnection if enough time has passed
		current_time = time.monotonic()
		time_since_attempt = current_time - state.tracker.last_wifi_attempt

		if time_since_attempt < Recovery.WIFI_RECONNECT_COOLDOWN:
			return False

		log_warning("WiFi DISCONNECTED, attempting recovery...")
		state.tracker.last_wifi_attempt = current_time
		return setup_wifi_with_recovery()
		
	except Exception as e:
		log_error(f"WiFi check failed: {e}")
		return False
		
def is_wifi_connected():
		"""Simple WiFi status check without recovery attempt"""
		try:
			return wifi.radio.connected
		except:
			return False

def get_timezone_offset(timezone_name, utc_datetime):
	"""Calculate timezone offset including DST for a given timezone"""
	
	if timezone_name not in TIMEZONE_OFFSETS:
		log_warning(f"Unknown timezone: {timezone_name}, using Chicago")
		timezone_name = Strings.TIMEZONE_DEFAULT
	
	tz_info = TIMEZONE_OFFSETS[timezone_name]
	
	# If timezone doesn't observe DST
	if tz_info["dst_start"] is None:
		return tz_info["std"]
	
	# Check if DST is active
	dst_active = is_dst_active_for_timezone(timezone_name, utc_datetime)
	return tz_info["dst"] if dst_active else tz_info["std"]
	
def is_dst_active_for_timezone(timezone_name, utc_datetime):
	"""Check if DST is active for a specific timezone and date"""
	
	if timezone_name not in TIMEZONE_OFFSETS:
		return False
	
	tz_info = TIMEZONE_OFFSETS[timezone_name]
	
	# No DST for this timezone
	if tz_info["dst_start"] is None:
		return False
	
	month = utc_datetime.tm_mon
	day = utc_datetime.tm_mday
	
	dst_start_month, dst_start_day = tz_info["dst_start"]
	dst_end_month, dst_end_day = tz_info["dst_end"]
	
	# DST logic for Northern Hemisphere (US/Europe)
	if month < dst_start_month or month > dst_end_month:
		return False
	elif month > dst_start_month and month < dst_end_month:
		return True
	elif month == dst_start_month:
		return day >= dst_start_day
	elif month == dst_end_month:
		return day < dst_end_day
	
	return False
	
def get_timezone_from_location_api():
	"""Get timezone and location info from AccuWeather Location API"""
	response = None
	try:
		api_key = get_api_key()
		location_key = os.getenv(Strings.API_LOCATION_KEY)
		url = f"http://dataservice.accuweather.com/locations/v1/{location_key}?apikey={api_key}"

		session = get_requests_session()
		response = session.get(url)

		try:
			if response.status_code == 200:
				data = response.json()
				timezone_info = data.get("TimeZone", {})

				# Extract location details
				city = data.get("LocalizedName", "Unknown")
				state = data.get("AdministrativeArea", {}).get("ID", "")

				return {
					"name": timezone_info.get("Name", Strings.TIMEZONE_DEFAULT),
					"offset": int(timezone_info.get("GmtOffset", -6)),
					"is_dst": timezone_info.get("IsDaylightSaving", False),
					"city": city,  # NEW
					"state": state,  # NEW
					"location": f"{city}, {state}" if state else city  # NEW
				}
			else:
				log_warning(f"Location API failed: {response.status_code}")
				return None
		finally:
			# CRITICAL: Always close response to release socket
			if response:
				try:
					response.close()
				except:
					pass  # Ignore errors during cleanup

	except Exception as e:
		log_warning(f"Location API error: {e}")
		return None

def sync_time_with_timezone(rtc):
	"""Enhanced NTP sync with Location API timezone detection"""
	
	# Try to get timezone from Location API
	tz_info = get_timezone_from_location_api()
	
	if tz_info:
		timezone_name = tz_info["name"]
		offset = tz_info["offset"]
		log_debug(f"Timezone from API: {timezone_name} (UTC{offset:+d})")
	else:
		# Fallback to hardcoded timezone
		timezone_name = Strings.TIMEZONE_DEFAULT
		log_warning(f"Using fallback timezone: {timezone_name}")
		
		# Use existing hardcoded logic
		try:
			cleanup_sockets()
			pool = socketpool.SocketPool(wifi.radio)
			ntp_utc = adafruit_ntp.NTP(pool, tz_offset=0)
			utc_time = ntp_utc.datetime
			offset = get_timezone_offset(timezone_name, utc_time)
		except Exception as e:
			log_error(f"NTP sync failed: {e}")
			return None  # IMPORTANT: Return None on failure
	
	try:
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		ntp = adafruit_ntp.NTP(pool, tz_offset=offset)
		rtc.datetime = ntp.datetime
		
		log_info(f"Time synced to {timezone_name} (UTC{offset:+d})")
		
		return tz_info  # Return location info (or None if using fallback)
		
	except Exception as e:
		log_error(f"NTP sync failed: {e}")
		return None  # IMPORTANT: Return None on failure

def is_market_hours_or_cache_valid(local_datetime, has_cached_data=False):
	"""
	Check if US stock markets are open or if cached data is still valid.

	Args:
		local_datetime: RTC datetime in user's local timezone
		has_cached_data: Whether we have cached stock prices

	Returns:
		tuple: (should_fetch: bool, should_display: bool, reason: str)
		- should_fetch: True if we should fetch new prices from API
		- should_display: True if we should show stocks (fresh or cached)
		- reason: Human-readable reason (for logging)
	"""
	import time

	# Check cached holiday status FIRST (avoid timezone calculations if holiday)
	today = f"{local_datetime.tm_year:04d}-{local_datetime.tm_mon:02d}-{local_datetime.tm_mday:02d}"
	if state.market_holiday_date == today:
		# It's a cached holiday - skip display entirely
		return (False, False, "Market holiday (cached)")

	# Get user's timezone from settings
	user_timezone = os.getenv("TIMEZONE", Strings.TIMEZONE_DEFAULT)

	# Convert local time to ET
	# First, figure out user's offset from UTC
	user_offset = get_timezone_offset(user_timezone, local_datetime)

	# Get ET offset from UTC
	et_offset = get_timezone_offset("America/New_York", local_datetime)

	# Calculate difference: how many hours to add to local time to get ET
	offset_diff = et_offset - user_offset

	# Convert local time to ET
	et_hour = local_datetime.tm_hour + offset_diff
	et_min = local_datetime.tm_min

	# Handle day rollover
	if et_hour < 0:
		et_hour += 24
	elif et_hour >= 24:
		et_hour -= 24

	# Check if it's a weekday (0=Monday, 4=Friday)
	weekday = local_datetime.tm_wday
	is_weekday = 0 <= weekday <= 4

	if not is_weekday:
		return (False, False, "Weekend - markets closed")

	# Convert times to minutes for easier comparison
	current_et_minutes = et_hour * 60 + et_min
	market_open_minutes = Timing.MARKET_OPEN_HOUR * 60 + Timing.MARKET_OPEN_MINUTE  # 9:30 AM = 570
	market_close_minutes = Timing.MARKET_CLOSE_HOUR * 60 + Timing.MARKET_CLOSE_MINUTE  # 4:00 PM = 960
	grace_end_minutes = market_close_minutes + Timing.MARKET_CACHE_GRACE_MINUTES  # 5:30 PM = 1050

	# Check time windows
	if current_et_minutes < market_open_minutes:
		# Before market open
		return (False, False, f"Before market open (ET {et_hour:02d}:{et_min:02d})")

	elif market_open_minutes <= current_et_minutes < market_close_minutes:
		# During market hours - fetch and display
		return (True, True, f"Market open (ET {et_hour:02d}:{et_min:02d})")

	elif market_close_minutes <= current_et_minutes < grace_end_minutes:
		# After close but within grace period - use cache if available
		if has_cached_data:
			return (False, True, f"Market CLOSED, using cache (ET {et_hour:02d}:{et_min:02d})")
		else:
			return (False, False, f"After hours, no cache (ET {et_hour:02d}:{et_min:02d})")

	else:
		# After grace period
		return (False, False, f"Markets closed (ET {et_hour:02d}:{et_min:02d})")

def cleanup_sockets():
	"""Aggressive socket cleanup to prevent memory issues"""
	for _ in range(Memory.SOCKET_CLEANUP_CYCLES):
		gc.collect()
		
# Global session management
_global_socket_pool = None  # Socket pool created ONCE and reused
_global_session = None

def get_requests_session():
	"""Get or create the global requests session"""
	global _global_session, _global_socket_pool

	if _global_session is None:
		try:
			# Create socket pool ONCE globally, reuse for all sessions
			if _global_socket_pool is None:
				_global_socket_pool = socketpool.SocketPool(wifi.radio)
				log_debug("Created global socket pool")

			_global_session = requests.Session(_global_socket_pool, ssl.create_default_context())
			log_debug("Created new global session (reusing socket pool)")
		except Exception as e:
			log_error(f"Failed to create session: {e}")
			return None

	return _global_session


def cleanup_global_session():
	"""Clean up the global requests session and force socket release

	IMPORTANT: We destroy the session but KEEP the socket pool.
	The socket pool is tied to wifi.radio and should be reused.
	Creating new pools every cleanup was causing socket exhaustion!
	"""
	global _global_session  # NOTE: We do NOT touch _global_socket_pool!

	if _global_session is not None:
		try:
			log_debug("Destroying global session (keeping socket pool)")
			# Try to close gracefully first
			try:
				_global_session.close()
			except:
				pass

			# Set to None (will be recreated with same pool)
			_global_session = None

			# Aggressive garbage collection
			cleanup_sockets()
			gc.collect()

			# Brief pause to let sockets fully close
			time.sleep(0.5)

			log_debug("Global session destroyed (socket pool preserved for reuse)")
		except Exception as e:
			log_debug(f"Session cleanup error (non-critical): {e}")
			_global_session = None
		

### API FUNCTIONS ###

def _handle_network_error(error, context, attempt, max_retries):
	"""Helper: Handle network errors - reduces nesting in fetch functions"""
	error_msg = str(error)

	if "pystack exhausted" in error_msg.lower():
		log_error(f"{context}: Stack exhausted - forcing cleanup")
	elif "already connected" in error_msg.lower():
		log_error(f"{context}: Socket stuck - forcing cleanup")
	elif "ETIMEDOUT" in error_msg or "104" in error_msg or "32" in error_msg:
		log_warning(f"{context}: Network timeout on attempt {attempt + 1}")
	else:
		log_warning(f"{context}: Network error on attempt {attempt + 1}: {error_msg}")

	# Nuclear cleanup for socket/stack issues
	if "pystack exhausted" in error_msg.lower() or "already connected" in error_msg.lower():
		cleanup_global_session()
		cleanup_sockets()
		gc.collect()
		time.sleep(2)

	# Retry delay
	if attempt < max_retries:
		delay = API.RETRY_BASE_DELAY * (2 ** attempt)
		log_verbose(f"Retrying in {delay}s...")
		time.sleep(delay)

	return f"Network error: {error_msg}"

def _process_response_status(response, context):
	"""Helper: Process HTTP response status - returns data or None"""
	status = response.status_code

	# Success
	if status == API.HTTP_OK:
		log_verbose(f"{context}: Success")
		return response.json()

	# Permanent errors (return None to signal exit)
	permanent_errors = {
		API.HTTP_UNAUTHORIZED: "Unauthorized (401) - check API key",
		API.HTTP_NOT_FOUND: "Not found (404) - check location key",
		API.HTTP_BAD_REQUEST: "Bad request (400) - check URL/parameters",
		API.HTTP_FORBIDDEN: "Forbidden (403) - API key lacks permissions"
	}

	if status in permanent_errors:
		log_error(f"{context}: {permanent_errors[status]}")
		state.tracker.has_permanent_error = True
		return None

	# Retryable errors (return False to signal retry)
	if status == API.HTTP_SERVICE_UNAVAILABLE:
		log_warning(f"{context}: Service unavailable (503)")
		return False
	elif status == API.HTTP_INTERNAL_SERVER_ERROR:
		log_warning(f"{context}: Server error (500)")
		return False
	elif status == API.HTTP_TOO_MANY_REQUESTS:
		log_warning(f"{context}: Rate limited (429)")
		return False  # Caller will handle rate limit delay
	else:
		log_error(f"{context}: HTTP {status}")
		return False

def fetch_weather_with_retries(url, max_retries=None, context="API"):
	"""Fetch weather with retries - defensive error handling"""
	if max_retries is None:
		max_retries = API.MAX_RETRIES

	last_error = None

	for attempt in range(max_retries + 1):
		# Early exits - no nesting
		if not check_and_recover_wifi():
			log_error(f"{context}: WiFi unavailable")
			return None

		session = get_requests_session()
		if not session:
			log_error(f"{context}: No requests session available")
			return None

		log_verbose(f"{context} attempt {attempt + 1}/{max_retries + 1}")

		# Try to fetch - exception handling delegated to helper
		response = None
		try:
			response = session.get(url)
		except (RuntimeError, OSError) as e:
			last_error = _handle_network_error(e, context, attempt, max_retries)
			continue  # Retry
		except Exception as e:
			log_error(f"{context} unexpected error: {type(e).__name__}: {e}")
			last_error = str(e)
			if attempt < max_retries:
				interruptible_sleep(API.RETRY_DELAY)
			continue  # Retry

		# Process and cleanup response
		try:
			# Process response - status handling delegated to helper
			result = _process_response_status(response, context)

			# Success or permanent error
			if result is not None and result is not False:
				return result

			# Permanent error (None from helper)
			if result is None:
				return None

			# Retryable error (False from helper)
			# Special case: rate limiting needs longer delay
			if response.status_code == API.HTTP_TOO_MANY_REQUESTS:
				if attempt < max_retries:
					delay = API.RETRY_DELAY * 3
					log_debug(f"Rate limit cooldown: {delay}s")
					interruptible_sleep(delay)
			else:
				# Standard exponential backoff
				if attempt < max_retries:
					delay = min(
						API.RETRY_DELAY * (2 ** attempt),
						Recovery.API_RETRY_MAX_DELAY
					)
					log_debug(f"Retrying in {delay}s...")
					interruptible_sleep(delay)

			last_error = f"HTTP {response.status_code}"
		finally:
			# Always close response to free socket (ignore errors)
			if response and hasattr(response, 'close'):
				response.close()

	log_error(f"{context}: All {max_retries + 1} attempts failed. Last error: {last_error}")
	return None

# ============================================================================
# Weather Fetch Helpers
# ============================================================================

def parse_current_weather(current_json):
	"""Parse current weather JSON response into data dict"""
	current = current_json[0]
	temp_data = current.get("Temperature", {}).get("Metric", {})
	realfeel_data = current.get("RealFeelTemperature", {}).get("Metric", {})
	realfeel_shade_data = current.get("RealFeelTemperatureShade", {}).get("Metric", {})

	current_data = {
		"weather_icon": current.get("WeatherIcon", 0),
		"temperature": temp_data.get("Value", 0),
		"feels_like": realfeel_data.get("Value", 0),
		"feels_shade": realfeel_shade_data.get("Value", 0),
		"humidity": current.get("RelativeHumidity", 0),
		"uv_index": current.get("UVIndex", 0),
		"weather_text": current.get("WeatherText", "Unknown"),
		"is_day_time": current.get("IsDayTime", True),
		"has_precipitation": current.get("HasPrecipitation", False),
	}

	log_verbose(f"CURRENT DATA: {current_data}")
	log_info(f"Weather: {current_data['weather_text']}, {current_data['feels_like']}°C")

	return current_data

def parse_forecast_weather(forecast_json):
	"""Parse forecast weather JSON response into data list"""
	forecast_fetch_length = min(API.DEFAULT_FORECAST_HOURS, API.MAX_FORECAST_HOURS)

	if not forecast_json or len(forecast_json) < forecast_fetch_length:
		log_warning("12-hour forecast fetch failed or insufficient data")
		return None

	forecast_data = []
	for i in range(forecast_fetch_length):
		hour_data = forecast_json[i]
		forecast_data.append({
			"temperature": hour_data.get("Temperature", {}).get("Value", 0),
			"feels_like": hour_data.get("RealFeelTemperature", {}).get("Value", 0),
			"feels_shade": hour_data.get("RealFeelTemperatureShade", {}).get("Value", 0),
			"weather_icon": hour_data.get("WeatherIcon", 1),
			"weather_text": hour_data.get("IconPhrase", "Unknown"),
			"datetime": hour_data.get("DateTime", ""),
			"has_precipitation": hour_data.get("HasPrecipitation", False)
		})

	log_info(f"Forecast: {len(forecast_data)} hours (fresh) | Next: {forecast_data[0]['feels_like']}°C")
	if len(forecast_data) >= forecast_fetch_length and CURRENT_DEBUG_LEVEL >= DebugLevel.VERBOSE:
		for h, item in enumerate(forecast_data):
			log_verbose(f"  Hour {h+1}: {item['temperature']}°C, {item['weather_text']}")

	return forecast_data

def track_api_call_success(call_type):
	"""Track successful API call (call_type: 'current' or 'forecast')"""
	state.tracker.record_api_success(call_type)
	log_debug(f"API Stats: {state.tracker.get_api_stats()}")

def handle_weather_success():
	"""Handle successful weather fetch - reset failure counters and log recovery"""
	state.tracker.record_weather_success()

def handle_weather_failure():
	"""Handle failed weather fetch - increment failure counters and trigger recovery if needed"""
	state.tracker.record_weather_failure()

	# Soft reset on repeated failures
	if state.tracker.should_soft_reset():
		log_warning("Soft reset: clearing network session")
		cleanup_global_session()
		state.tracker.reset_after_soft_reset()

		# Enter temporary extended failure mode for cooldown
		was_in_extended_mode = state.tracker.in_extended_failure_mode
		state.tracker.in_extended_failure_mode = True

		# Show purple clock during 30s cooldown
		log_info("Cooling down for 30 seconds before retry...")
		show_clock_display(state.rtc_instance, 30)

		# Restore previous extended mode state
		state.tracker.in_extended_failure_mode = was_in_extended_mode

	# Hard reset if soft resets aren't helping
	if state.tracker.should_hard_reset():
		log_error(f"Hard reset after {state.tracker.system_error_count} system errors")
		interruptible_sleep(Timing.RESTART_DELAY)
		supervisor.reload()

def check_preventive_restart():
	"""Check if preventive restart is needed due to API call limit"""
	if state.tracker.should_preventive_restart():
		log_warning(f"Preventive restart after {state.tracker.api_call_count} API calls")
		cleanup_global_session()
		interruptible_sleep(API.RETRY_DELAY)
		supervisor.reload()

# ============================================================================
# Weather Fetch Functions
# ============================================================================

def fetch_current_and_forecast_weather():
	"""Convenience wrapper to fetch both current and forecast weather

	Each independent function handles its own error tracking, recovery, and API counting.
	This wrapper simply calls both and returns the results as a tuple.
	"""
	current_data = fetch_current_weather()
	forecast_data = fetch_forecast_weather()
	return current_data, forecast_data

def fetch_current_weather():
	"""Fetch only current weather - independent function with full error handling"""
	state.memory_monitor.check_memory("current_fetch_start")

	# Check if enabled
	if not display_config.should_fetch_weather():
		log_debug("Current weather fetching disabled")
		return None

	try:
		# Get API key
		api_key = get_api_key()
		if not api_key:
			handle_weather_failure()
			return None

		# Build URL
		location = os.getenv(Strings.API_LOCATION_KEY)
		current_url = f"{API.BASE_URL}/{API.CURRENT_ENDPOINT}/{location}?apikey={api_key}&details=true"

		# Fetch with retries (default: 3 retries)
		current_json = fetch_weather_with_retries(current_url, context="Current Weather")

		if current_json:
			# Track successful API call
			track_api_call_success("current")

			# Parse the data
			current_data = parse_current_weather(current_json)

			# Cache for fallback
			state.cached_current_weather = current_data
			state.cached_current_weather_time = time.monotonic()

			# Handle success
			handle_weather_success()

			# Check for preventive restart
			check_preventive_restart()

			state.memory_monitor.check_memory("current_fetch_complete")
			return current_data
		else:
			log_warning("Current weather fetch failed")
			handle_weather_failure()
			return None

	except Exception as e:
		log_error(f"Current weather critical error: {type(e).__name__}: {e}")
		state.memory_monitor.check_memory("current_fetch_error")
		handle_weather_failure()
		return None

def fetch_forecast_weather():
	"""Fetch only forecast weather - independent function with full error handling"""
	state.memory_monitor.check_memory("forecast_fetch_start")

	# Check if enabled
	if not display_config.should_fetch_forecast():
		log_debug("Forecast weather fetching disabled")
		return None

	try:
		# Get API key
		api_key = get_api_key()
		if not api_key:
			handle_weather_failure()
			return None

		# Build URL
		location = os.getenv(Strings.API_LOCATION_KEY)
		forecast_url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{location}?apikey={api_key}&metric=true&details=true"

		# Fetch with retries (max_retries=1 for forecast - less aggressive)
		forecast_json = fetch_weather_with_retries(forecast_url, max_retries=1, context="Forecast")

		if forecast_json:
			# Track successful API call
			track_api_call_success("forecast")

			# Parse the data
			forecast_data = parse_forecast_weather(forecast_json)

			if forecast_data:
				state.memory_monitor.check_memory("forecast_data_complete")
				handle_weather_success()
				check_preventive_restart()
				return forecast_data
			else:
				# Parsing failed (insufficient data)
				handle_weather_failure()
				check_preventive_restart()
				return None
		else:
			log_warning("Forecast fetch failed")
			handle_weather_failure()
			return None

	except Exception as e:
		log_error(f"Forecast critical error: {type(e).__name__}: {e}")
		state.memory_monitor.check_memory("forecast_fetch_error")
		handle_weather_failure()
		return None

def get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE):
	"""
	Get cached current weather if it's not too old
	
	Args:
		max_age_seconds: Maximum age in seconds (default 30 minutes)
	
	Returns:
		Cached weather data if fresh enough, None otherwise
	"""
	if not state.cached_current_weather:
		return None
	
	age = time.monotonic() - state.cached_current_weather_time
	
	if age <= max_age_seconds:
		log_debug(f"Cache is {int(age/60)} minutes old (acceptable)")
		return state.cached_current_weather
	else:
		log_debug(f"Cache is {int(age/60)} minutes old (too stale, discarding)")
		return None
		
def fetch_current_weather_only():
	"""Fetch only current weather (not forecast) - uses independent fetch function"""
	if display_config.use_live_weather:
		return fetch_current_weather()
	else:
		return TestData.DUMMY_WEATHER_DATA

def get_api_key():
	"""Extract API key logic into separate function"""
	matrix_type = detect_matrix_type()
	
	if matrix_type == "type1":
		api_key_name = Strings.API_KEY_TYPE1
	elif matrix_type == "type2":
		api_key_name = Strings.API_KEY_TYPE2
	else:
		api_key_name = Strings.API_KEY_FALLBACK
	
	# Read the appropriate API key
	try:
		api_key = os.getenv(api_key_name)
		log_verbose(f"Using key with ending: {api_key[-5:]} for {matrix_type}")
		return api_key
	except Exception as e:
		log_warning(f"Failed to read API key: {e}")
		
	# Fallback to original key
	try:
		api_key = os.getenv(api_key_name)
		log_warning(f"Using fallback ACCUWEATHER_API_KEY. Ending: {api_key[-5:]}")
		return api_key
	except Exception as e:
		log_error(f"Failed to read fallback API key: {e}")
	
	return None
	
def get_current_error_state():
	"""Determine current error state based on system status"""

	# During startup (before first weather attempt), show OK
	if state.startup_time == 0:
		return None

	# Extended failure mode takes priority over permanent errors
	# (shows system is degraded, even if error is permanent)
	if state.tracker.in_extended_failure_mode:
		return "extended"  # PURPLE

	# Check for permanent configuration errors
	if state.tracker.has_permanent_error:
		return "general"  # WHITE

	# Check for WiFi issues
	if not is_wifi_connected():
		return "wifi"  # RED

	# Check for schedule display errors (file system issues)
	if state.tracker.scheduled_display_error_count >= 3:
		return "general"  # WHITE

	# Check for display failures (only after startup)
	time_since_success = time.monotonic() - state.tracker.last_successful_display
	if state.tracker.last_successful_display > 0 and time_since_success > 600:
		return "display"  # YELLOW

	# Check for consecutive failures
	if state.tracker.consecutive_failures >= 3:
		return "weather"  # YELLOW

	# All OK
	return None  # MINT
	
def should_fetch_forecast():
	"""Check if forecast data needs to be refreshed"""
	current_time = time.monotonic()
	log_verbose(f"LAST FORECAST FETCH: {state.last_forecast_fetch} seconds ago. Needs Refresh? = {(current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL}")
	return (current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL
	
def get_today_events_info(rtc):
	"""Get information about today's ACTIVE events (filtered by time and year)"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	events = get_events()

	if month_day not in events:
		return 0, []

	current_hour = rtc.datetime.tm_hour
	current_year = rtc.datetime.tm_year

	# Filter events by current time AND year (0 = any year, otherwise must match current year)
	active_events = [event for event in events[month_day]
	                 if is_event_active(event, current_hour)
	                 and (len(event) < 7 or event[6] == 0 or event[6] == current_year)]

	return len(active_events), active_events
	
def get_today_all_events_info(rtc):
	"""Get ALL events for today (not filtered by time, but filtered by year)"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	events = get_events()

	if month_day not in events:
		return 0, []

	current_year = rtc.datetime.tm_year

	# Filter by year (0 = any year, otherwise must match current year)
	today_events = [event for event in events[month_day]
	                if (len(event) < 7 or event[6] == 0 or event[6] == current_year)]

	return len(today_events), today_events

### DISPLAY UTILITIES ###

def detect_matrix_type():
	"""Auto-detect matrix wiring type (cached for performance)"""
	if state.matrix_type_cache is not None:
		return state.matrix_type_cache
	
	uid = microcontroller.cpu.uid
	device_id = "".join([f"{b:02x}" for b in uid[-3:]])
	
	device_mappings = {
		System.DEVICE_TYPE1_ID: "type1",
		System.DEVICE_TYPE2_ID: "type2",
	}
	
	state.matrix_type_cache = device_mappings.get(device_id, "type1")
	log_debug(f"Device ID: {device_id}, Matrix type: {state.matrix_type_cache}")
	return state.matrix_type_cache
	
# Function to get corrected colors for current matrix
def get_matrix_colors():
	"""Get color constants with corrections applied"""
	matrix_type = detect_matrix_type()
	bit_depth = Display.BIT_DEPTH
	
	return ColorManager.generate_colors(matrix_type, bit_depth)

def convert_bmp_palette(palette):
	"""Convert BMP palette for RGB matrix display"""
	if not palette or 'ColorConverter' in str(type(palette)):
		return palette
	
	try:
		palette_len = len(palette)
	except TypeError:
		return palette
	
	converted_palette = displayio.Palette(palette_len)
	matrix_type = detect_matrix_type()
	bit_depth = Display.BIT_DEPTH
	
	for i in range(palette_len):
		original_color = palette[i]
		
		# Extract 8-bit RGB
		r = (original_color >> 16) & 0xFF
		g = (original_color >> 8) & 0xFF
		b = original_color & 0xFF
		
		# Swap for type1
		if matrix_type == "type1":
			r, g, b = ColorManager.swap_green_blue(r, g, b)
		
		# Quantize to bit depth
		r_quantized = ColorManager.quantize_channel(r, bit_depth)
		g_quantized = ColorManager.quantize_channel(g, bit_depth)
		b_quantized = ColorManager.quantize_channel(b, bit_depth)
		
		# Pack as RGB888
		converted_palette[i] = (r_quantized << 16) | (g_quantized << 8) | b_quantized
	
	return converted_palette

def load_bmp_image(filepath):
	"""Load and convert BMP image for display"""
	bitmap, palette = adafruit_imageload.load(filepath)
	if palette and 'Palette' in str(type(palette)):
		palette = convert_bmp_palette(palette)
	return bitmap, palette

def get_text_width(text, font):
	return state.text_cache.get_text_width(text, font)
	
def get_font_metrics(font, text="Aygjpq"):
	"""
	Calculate font metrics including ascenders and descenders
	Uses test text with both tall and descending characters
	"""
	try:
		temp_label = bitmap_label.Label(font, text=text)
		bbox = temp_label.bounding_box
		
		if bbox and len(bbox) >= 4:
			# bbox format: (x, y, width, height)
			font_height = bbox[3]  # Total height including ascenders/descenders
			baseline_offset = abs(bbox[1]) if bbox[1] < 0 else 0  # How much above baseline
			return font_height, baseline_offset
		else:
			# Fallback if bbox is invalid
			return 8, 2
	except Exception as e:
		log_error(f"Font metrics error: {e}")
		# Safe fallback values for small font
		return 8, 2

def fetch_ephemeral_events():
	"""
	Fetch ephemeral events from online source
	NOTE: Events are fetched during initialization, this is just a wrapper
	"""
	try:
		# Check if events already cached from initialization
		if state.cached_events:
			log_debug("Using cached events from initialization")
			return state.cached_events
		
		# If not cached (shouldn't happen), fetch now
		log_info("Events not cached, fetching now...")
		events, _, _, _ = fetch_github_data(state.rtc_instance)  # ← Updated
		
		if events:
			state.cached_events = events
			return events
		
		return {}
		
	except Exception as e:
		log_warning(f"Failed to fetch ephemeral events: {e}")
		return {}
		
def normalize_date_key(date_str):
	"""Normalize date string to MMDD format (e.g., '01-15' or '115' -> '0115')"""
	date_key = date_str.replace("-", "")
	# Manual padding for CircuitPython (no zfill support)
	while len(date_key) < 4:
		date_key = '0' + date_key
	return date_key

def parse_event_data(parts):
	"""Extract event data fields from CSV parts. Returns [top_line, bottom_line, image, color, start_hour, end_hour, year]"""
	return [
		parts[1],  # top_line
		parts[2],  # bottom_line
		parts[3],  # image
		parts[4] if len(parts) > 4 and parts[4].strip() else Strings.DEFAULT_EVENT_COLOR,
		int(parts[5]) if len(parts) > 5 and parts[5].strip() else Timing.EVENT_ALL_DAY_START,
		int(parts[6]) if len(parts) > 6 and parts[6].strip() else Timing.EVENT_ALL_DAY_END,
		0  # year - will be set when parsing (0 = any year for permanent events)
	]

def load_events_from_file(filepath):
	"""Load events from CSV file. Returns dict of {date_key: [event_data, ...]}"""
	events = {}
	count = 0

	try:
		with open(filepath, 'r') as f:
			for line_num, line in enumerate(f, 1):
				line = line.strip()
				if not line or line.startswith("#"):
					continue

				try:
					parts = [p.strip() for p in line.split(",")]

					# Format: MM-DD,TopLine,BottomLine,ImageFile,Color[,StartHour,EndHour]
					if len(parts) < 4:
						log_warning(f"Line {line_num}: Not enough fields (need at least 4)")
						continue

					date_key = normalize_date_key(parts[0])
					event_data = parse_event_data(parts)
					events.setdefault(date_key, []).append(event_data)
					count += 1
					log_verbose(f"Loaded: {date_key} - {event_data[0]} {event_data[1]}")

				except Exception as e:
					log_warning(f"Line {line_num} parse error: {e} | Line: {line}")

		log_debug(f"Loaded {count} events from {filepath}")
		return events, count

	except Exception as e:
		log_warning(f"Failed to load {filepath}: {e}")
		return {}, 0

def load_all_events():
	"""Load and merge all event sources"""
	# Load permanent events from local CSV
	permanent_events, permanent_count = load_events_from_file(Paths.EVENTS_CSV)
	state.permanent_event_count = permanent_count

	# Get ephemeral events - check temp storage first, then try fetching
	if hasattr(state, '_github_events_temp') and state._github_events_temp:
		ephemeral_events = state._github_events_temp
		log_debug("Using GitHub events from initialization")
	else:
		ephemeral_events = fetch_ephemeral_events()

	ephemeral_count = sum(len(events) for events in ephemeral_events.values())
	state.ephemeral_event_count = ephemeral_count
	log_debug(f"Loaded {ephemeral_count} ephemeral events")

	# Merge events using dictionary approach
	merged = dict(permanent_events)  # Start with copy of permanent events
	for date_key, event_list in ephemeral_events.items():
		merged.setdefault(date_key, []).extend(event_list)

	state.total_event_count = sum(len(events) for events in merged.values())
	log_debug(f"Events merged: {permanent_count} permanent + {ephemeral_count} ephemeral = {state.total_event_count} total")

	return merged
	
def is_event_active(event_data, current_hour):
	"""
	Check if event should be displayed at current hour
	
	Args:
		event_data: [top_line, bottom_line, image, color, start_hour, end_hour]
		current_hour: Current hour (0-23)
	
	Returns:
		True if event is active, False otherwise
	"""
	# Check if event has time data (6 elements)
	if len(event_data) < 6:
		# Old format or missing times - treat as all-day
		return True
	
	start_hour = event_data[4]
	end_hour = event_data[5]
	
	# All-day event
	if start_hour == Timing.EVENT_ALL_DAY_START and end_hour == Timing.EVENT_ALL_DAY_END:
		return True
	
	# Check if current hour is within window
	return start_hour <= current_hour < end_hour

def get_events():
	"""Get cached events - loads from both sources only once"""
	if state.cached_events is None:
		state.cached_events = load_all_events()
		if not state.cached_events:
			log_warning("Warning: No events loaded, using minimal fallback")
			state.cached_events = {}
	
	return state.cached_events

def parse_events_csv_content(csv_content, rtc):
	"""Parse events CSV content directly from string"""
	events = {}
	skipped_count = 0

	try:
		# Get today's date for comparison
		if rtc:
			today_year = rtc.datetime.tm_year
			today_month = rtc.datetime.tm_mon
			today_day = rtc.datetime.tm_mday
		else:
			# Fallback if RTC not available - import all
			today_year = 1900
			today_month = 1
			today_day = 1

		for line in csv_content.split('\n'):
			line = line.strip()
			if line and not line.startswith("#"):
				parts = [part.strip() for part in line.split(",")]
				if len(parts) >= 4:
					date = parts[0]  # YYYY-MM-DD format

					# Parse date to check if it's in the past
					try:
						date_parts = date.split("-")
						if len(date_parts) == 3:
							event_year = int(date_parts[0])
							event_month = int(date_parts[1])
							event_day = int(date_parts[2])

							# Skip if event is in the past
							if (event_year < today_year or
								(event_year == today_year and event_month < today_month) or
								(event_year == today_year and event_month == today_month and event_day < today_day)):
								skipped_count += 1
								log_verbose(f"Skipping past event: {date} - {parts[1]} {parts[2]}")
								continue

							# Convert YYYY-MM-DD to MMDD and extract event data
							date_key = normalize_date_key(f"{date_parts[1]}-{date_parts[2]}")
							event_data = parse_event_data(parts)
							event_data[6] = event_year  # Store the year for ephemeral events
							events.setdefault(date_key, []).append(event_data)

					except (ValueError, IndexError):
						log_warning(f"Invalid date format in events: {date}")
						continue

		if skipped_count > 0:
			log_debug(f"Parsed {len(events)} event dates ({skipped_count} past events skipped)")
		else:
			log_debug(f"Parsed {len(events)} event dates")

		return events

	except Exception as e:
		log_error(f"Error parsing events CSV: {e}")
		return {}
	
def parse_schedule_data(parts):
	"""Extract schedule fields from CSV parts. Returns (name, schedule_dict)."""
	name = parts[0]
	schedule = {
		"enabled": parts[1] == "1",
		"days": [int(d) for d in parts[2] if d.isdigit()],
		"start_hour": int(parts[3]),
		"start_min": int(parts[4]),
		"end_hour": int(parts[5]),
		"end_min": int(parts[6]),
		"image": parts[7],
		"progressbar": parts[8] == "1" if len(parts) > 8 else True
	}
	return name, schedule

def parse_schedule_csv_content(csv_content, rtc):
	"""Parse schedule CSV content directly from string (no file I/O)"""
	schedules = {}

	try:
		lines = csv_content.strip().split('\n')

		if not lines:
			return schedules

		# Skip header row
		for line in lines[1:]:
			line = line.strip()
			if not line or line.startswith('#'):
				continue

			parts = [p.strip() for p in line.split(',')]

			if len(parts) >= 8:
				name, schedule = parse_schedule_data(parts)
				schedules[name] = schedule
				log_verbose(f"Parsed schedule: {name} ({'enabled' if schedule['enabled'] else 'disabled'}, {len(schedule['days'])} days)")

		return schedules

	except Exception as e:
		log_error(f"Error parsing schedule CSV: {e}")
		return {}

def parse_stocks_csv_content(csv_content):
	"""Parse stock/forex/crypto/commodity CSV content directly from string.

	Format: symbol,name,type,display_name,highlight
	- symbol: Ticker, forex pair, crypto, or commodity symbol (required)
	- name: Full name for reference (required)
	- type: "stock", "forex", "crypto", or "commodity" (optional, default: "stock")
	- display_name: Short name for display (optional, default: symbol)
	- highlight: 0 or 1 to show in chart mode (optional, default: 0)

	Display behavior:
	- highlight=1: Show as single stock chart with intraday price graph
	- highlight=0: Show in multi-stock rotation (3 stocks at a time)
	- stock: Triangle arrow + ticker + percentage change
	- forex: $ indicator + ticker + price (colored, with K/M suffix)
	- crypto: $ indicator + ticker + price (colored, with K/M suffix)
	- commodity: $ indicator + ticker + price (colored, with K/M suffix)
	"""
	stocks = []

	try:
		lines = csv_content.strip().split('\n')

		if not lines:
			return stocks

		# Parse each line
		for line in lines:
			line = line.strip()
			if not line or line.startswith('#'):
				continue

			parts = [p.strip() for p in line.split(',')]

			if len(parts) >= 2:
				symbol = parts[0].upper()  # Ticker symbols always uppercase
				name = parts[1]

				# Parse optional type field (default: "stock")
				item_type = parts[2].lower() if len(parts) >= 3 and parts[2] else "stock"

				# Parse optional display_name field (default: symbol)
				display_name = parts[3].upper() if len(parts) >= 4 and parts[3] else symbol

				# Parse optional highlight field (default: False/0)
				highlight = False
				if len(parts) >= 5 and parts[4]:
					highlight = (parts[4] == '1' or parts[4].lower() == 'true')

				stocks.append({
					"symbol": symbol,
					"name": name,
					"type": item_type,
					"display_name": display_name,
					"highlight": highlight
				})
				highlight_str = " [CHART]" if highlight else ""
				log_verbose(f"Parsed {item_type}: {symbol} ({name}) -> display as '{display_name}'{highlight_str}")

		log_debug(f"Parsed {len(stocks)} stocks/forex from CSV")
		return stocks

	except Exception as e:
		log_error(f"Error parsing stocks CSV: {e}")
		return []

def fetch_github_events(session, cache_buster, rtc):
	"""Fetch events from GitHub. Returns events dict."""
	events_url = f"{Strings.GITHUB_REPO_URL}?t={cache_buster}"
	events = {}
	response = None

	try:
		log_verbose(f"Fetching: {events_url}")
		response = session.get(events_url, timeout=10)

		try:
			if response.status_code == 200:
				events = parse_events_csv_content(response.text, rtc)
				log_verbose(f"Events fetched: {len(events)} event dates")
			else:
				log_warning(f"Failed to fetch events: HTTP {response.status_code}")
		finally:
			# CRITICAL: Close events response to release socket
			if response:
				try:
					response.close()
				except:
					pass  # Ignore close errors
	except Exception as e:
		log_warning(f"Failed to fetch events: {e}")

	return events

def fetch_github_schedules(session, github_base, cache_buster, rtc, date_str):
	"""Fetch schedules from GitHub (date-specific or default). Returns (schedules, schedule_source)."""
	schedules = {}
	schedule_source = None
	response = None

	try:
		# Try date-specific schedule first
		schedule_url = f"{github_base}/{Paths.GITHUB_SCHEDULE_FOLDER}/{date_str}.csv?t={cache_buster}"
		log_verbose(f"Fetching: {schedule_url}")

		response = session.get(schedule_url, timeout=10)

		try:
			if response.status_code == 200:
				schedules = parse_schedule_csv_content(response.text, rtc)
				schedule_source = "date-specific"
				log_verbose(f"Schedule fetched: {date_str}.csv ({len(schedules)} schedule(s))")

			elif response.status_code == 404:
				# No date-specific file, try default
				log_verbose(f"No schedule for {date_str}, trying default.csv")

				# CRITICAL: Close date-specific response before making second request
				try:
					response.close()
				except:
					pass

				default_url = f"{github_base}/{Paths.GITHUB_SCHEDULE_FOLDER}/default.csv?t={cache_buster}"
				response = session.get(default_url, timeout=10)

				try:
					if response.status_code == 200:
						schedules = parse_schedule_csv_content(response.text, rtc)
						schedule_source = "default"
						log_verbose(f"Schedule fetched: default.csv ({len(schedules)} schedule(s))")
					else:
						log_warning(f"No default schedule found: HTTP {response.status_code}")
				finally:
					# CRITICAL: Close default response
					if response:
						try:
							response.close()
						except:
							pass
			else:
				log_warning(f"Failed to fetch schedule: HTTP {response.status_code}")
		finally:
			# CRITICAL: Ensure date-specific response is closed
			# (May already be closed in 404 case, but safe to call again)
			if response:
				try:
					response.close()
				except:
					pass  # Already closed or error

	except Exception as e:
		log_warning(f"Failed to fetch schedule: {e}")

	return schedules, schedule_source

def fetch_stocks_from_github(session, cache_buster):
	"""Fetch stock symbols from GitHub. Returns stocks list."""
	if not Strings.STOCKS_CSV_URL:
		log_verbose("No STOCKS_CSV_URL configured")
		return []

	stocks = []
	response = None
	stocks_url = f"{Strings.STOCKS_CSV_URL}?t={cache_buster}"

	try:
		log_verbose(f"Fetching: {stocks_url}")
		response = session.get(stocks_url, timeout=10)

		# Check if response is valid before accessing attributes
		if not response:
			log_warning("Failed to fetch stocks: No response from server")
			return stocks

		try:
			if response.status_code == 200:
				# Parse CSV content using helper function
				stocks = parse_stocks_csv_content(response.text)
				log_verbose(f"Stocks fetched: {len(stocks)} symbols")
			else:
				log_warning(f"Failed to fetch stocks: HTTP {response.status_code}")
		finally:
			# CRITICAL: Close stocks response to release socket
			if response:
				try:
					response.close()
				except:
					pass  # Ignore close errors
	except Exception as e:
		log_warning(f"Failed to fetch stocks from GitHub: {e}")

	return stocks

def fetch_stock_prices(symbols_to_fetch):
	"""
	Fetch current stock prices from Twelve Data API.
	Fetches up to 3 symbols in a single batch request.

	Args:
		symbols_to_fetch: List of stock symbol dicts [{"symbol": "AAPL", "name": "Apple"}, ...]

	Returns:
		dict: {symbol: {"price": float, "change_percent": float, "direction": str}}
	"""
	import time

	if not symbols_to_fetch:
		log_verbose("No stock symbols to fetch")
		return {}

	# Get API key
	api_key = os.getenv(Strings.TWELVE_DATA_API_KEY)
	if not api_key:
		log_warning("TWELVE_DATA_API_KEY not configured in settings.toml")
		return {}

	session = get_requests_session()
	if not session:
		log_warning("No session available for stock fetch")
		return {}

	stock_data = {}
	response = None

	try:
		# Build comma-separated symbol list (typically 3 symbols)
		symbols_list = [s["symbol"] for s in symbols_to_fetch]
		symbols_str = ",".join(symbols_list)

		# Twelve Data Quote API endpoint (batch)
		url = f"https://api.twelvedata.com/quote?symbol={symbols_str}&apikey={api_key}"

		log_verbose(f"Fetching: {symbols_str}")
		response = session.get(url, timeout=10)

		# Check if response is valid
		if not response:
			log_warning("No response from server")
			return stock_data

		if response.status_code == 200:
			import json
			data = json.loads(response.text)

			# Handle Twelve Data response formats:
			# Single symbol: {"symbol": "AAPL", "name": ..., "close": ..., "percent_change": ...}
			# Multiple symbols: {"AAPL": {"symbol": "AAPL", "close": ...}, "MSFT": {...}}

			# Check if it's a single quote (has "symbol" key at top level)
			if "symbol" in data:
				quotes = [data]
			# Otherwise it's a batch response (dict with ticker keys)
			elif isinstance(data, dict):
				quotes = list(data.values())
			else:
				log_warning(f"Unexpected API response format: {type(data)}")
				quotes = []

			log_verbose(f"Processing {len(quotes)} quote(s)")

			for quote in quotes:
				# Check if quote has error
				if "status" in quote and quote["status"] == "error":
					log_warning(f"Error fetching {quote.get('symbol', 'unknown')}: {quote.get('message', 'unknown error')}")
					continue

				symbol = quote.get("symbol")
				if not symbol:
					log_warning(f"Quote missing symbol field: {str(quote)[:100]}")
					continue

				# Check market status (for holiday detection)
				is_market_open = quote.get("is_market_open", True)
				if not is_market_open and state.market_holiday_date is None:
					# Market closed on a weekday during business hours = holiday!
					# Cache this for the rest of the day to avoid repeated API calls
					import time
					# Get current date from RTC (we don't have direct access here, will handle in caller)
					log_info(f"Market closed detected via API (holiday or early close)")

				# Extract price and change data
				try:
					price = float(quote.get("close", 0))
					open_price = float(quote.get("open", 0))
					change_percent = float(quote.get("percent_change", 0))
					direction = "up" if change_percent >= 0 else "down"

					stock_data[symbol] = {
						"price": price,
						"open_price": open_price,
						"change_percent": change_percent,
						"direction": direction,
						"is_market_open": is_market_open  # Include market status
					}

					log_verbose(f"{symbol}: ${price:.2f} ({change_percent:+.2f}%)")
				except (ValueError, TypeError) as e:
					log_warning(f"Error parsing data for {symbol}: {e}")
					continue

			# Track API usage: Each symbol counts as 1 API credit
			if len(stock_data) > 0:
				state.tracker.record_api_success("stock", len(stock_data))
				log_verbose(f"Stock API: +{len(stock_data)} credits (Total: {state.tracker.stock_api_calls}/800)")

			# Log summary
			if len(stock_data) < len(symbols_list):
				failed = [sym for sym in symbols_list if sym not in stock_data]
				log_warning(f"Failed to fetch: {', '.join(failed)}")
		else:
			log_warning(f"HTTP {response.status_code}")
			if response.text:
				log_verbose(f"Response: {response.text[:200]}")

	except Exception as e:
		log_warning(f"Failed to fetch stock prices: {e}")
		log_verbose(f"Exception type: {type(e).__name__}")

	finally:
		# CRITICAL: Close response to release socket
		if response:
			try:
				response.close()
			except:
				pass

	return stock_data

def fetch_intraday_time_series(symbol, interval="15min", outputsize=26):
	"""
	Fetch intraday time series data from Twelve Data API.

	Args:
		symbol: Stock ticker symbol (e.g., "CRM")
		interval: Data interval ("5min", "15min", "30min", "1h")
		outputsize: Number of data points to fetch (default 26 for ~6.5 hours with 15min interval)

	Returns:
		List of dicts: [{datetime, open_price, close_price}, ...] ordered chronologically (oldest first)
		Returns empty list on error
	"""
	import time

	# Get API key
	api_key = os.getenv(Strings.TWELVE_DATA_API_KEY)
	if not api_key:
		log_warning("TWELVE_DATA_API_KEY not configured in settings.toml")
		return []

	session = get_requests_session()
	if not session:
		log_warning("No session available for intraday fetch")
		return []

	response = None

	try:
		# Build URL with string concatenation (CircuitPython f-string limitation)
		url = "https://api.twelvedata.com/time_series?symbol=" + symbol
		url += "&interval=" + interval
		url += "&outputsize=" + str(outputsize)
		url += "&timezone=America/New_York&apikey=" + api_key

		log_verbose("Fetching intraday data for " + symbol)
		response = session.get(url, timeout=10)

		if not response:
			log_warning("No response from server")
			return []

		if response.status_code == 200:
			import json
			data = json.loads(response.text)

			# Check for errors
			if "status" in data and data["status"] == "error":
				log_warning("API error for " + symbol + ": " + data.get("message", "unknown"))
				return []

			# Extract values array
			if "values" not in data:
				log_warning("No values in time series response")
				return []

			values = data["values"]
			if not values or len(values) == 0:
				log_warning("Empty values array in time series")
				return []

			# Parse data points (API returns newest first, we want oldest first)
			time_series = []
			for point in reversed(values):
				try:
					time_series.append({
						"datetime": point.get("datetime", ""),
						"open_price": float(point.get("open", 0)),
						"close_price": float(point.get("close", 0))
					})
				except (ValueError, TypeError) as e:
					log_verbose("Skipping invalid data point: " + str(e))
					continue

			num_points = len(time_series)
			# Track API usage: 1 credit for time_series call
			state.tracker.record_api_success("stock", 1)
			log_verbose("Received " + str(num_points) + " data points for " + symbol + " (Stock API: +" + str(1) + ", Total: " + str(state.tracker.stock_api_calls) + "/800)")
			return time_series
		else:
			log_warning("HTTP " + str(response.status_code) + " for intraday fetch")
			return []

	except Exception as e:
		log_warning("Failed to fetch intraday data: " + str(e))
		return []

	finally:
		# CRITICAL: Close response to release socket
		if response:
			try:
				response.close()
			except:
				pass

	return []

def fetch_github_data(rtc):
	"""
	Fetch events, schedules, and stocks from GitHub in one operation
	Returns: (events_dict, schedules_dict, schedule_source, stocks_list)
		schedule_source: "date-specific", "default", or None
	"""

	session = get_requests_session()
	if not session:
		log_warning("No session available for GitHub fetch")
		return None, None, None, None

	# Check if GitHub URL is configured
	if not Strings.GITHUB_REPO_URL:
		log_warning("GITHUB_REPO_URL not configured")
		return None, None, None, None

	import time
	cache_buster = int(time.monotonic())
	github_base = Strings.GITHUB_REPO_URL.rsplit('/', 1)[0] if Strings.GITHUB_REPO_URL else None

	# Fetch events, schedules, and stocks
	events = fetch_github_events(session, cache_buster, rtc)

	now = rtc.datetime
	date_str = f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}"
	schedules, schedule_source = fetch_github_schedules(session, github_base, cache_buster, rtc, date_str)

	stocks = fetch_stocks_from_github(session, cache_buster)

	return events, schedules, schedule_source, stocks
	
def load_schedules_from_csv():
	"""Load schedules from CSV file"""
	schedules = {}
	try:
		log_verbose("Loading schedules from schedules.csv...")
		with open("schedules.csv", "r") as f:
			for line in f:
				line = line.strip()
				if line and not line.startswith("#"):
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 8:
						name, schedule = parse_schedule_data(parts)
						schedules[name] = schedule

		# Log successful load
		if schedules:
			log_debug(f"{len(schedules)} schedules loaded")
		else:
			log_warning("No schedules found in schedules.csv")

		return schedules

	except Exception as e:
		log_warning(f"Failed to load schedules.csv: {e}")
		return {}

def load_stocks_from_csv():
	"""Load stock symbols from CSV file"""
	stocks = []
	try:
		log_verbose("Loading stocks from stocks.csv...")
		with open("stocks.csv", "r") as f:
			for line in f:
				line = line.strip()
				if line and not line.startswith("#"):
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 2:
						symbol = parts[0].upper()  # Ticker symbols always uppercase
						name = parts[1]
						stocks.append({"symbol": symbol, "name": name})

		# Log successful load
		if stocks:
			log_debug(f"{len(stocks)} stock symbols loaded")
		else:
			log_warning("No stocks found in stocks.csv")

		return stocks

	except Exception as e:
		log_warning(f"Failed to load stocks.csv: {e}")
		return []

# ============================================================================
# Display Configuration Loading
# ============================================================================

def parse_display_config_csv(csv_content):
	"""Parse display config CSV content. Returns dict of settings."""
	config = {}

	try:
		lines = csv_content.strip().split('\n')

		if not lines:
			return config

		# Parse key-value pairs
		for line in lines:
			line = line.strip()
			if not line or line.startswith('#'):
				continue

			parts = [p.strip() for p in line.split(',')]

			if len(parts) >= 2:
				key = parts[0]
				value = parts[1]

				# Convert to appropriate type
				if value in ('0', '1'):
					# Boolean values
					config[key] = (value == '1')
				elif value.isdigit():
					# Numeric values (e.g., stocks_display_frequency=3)
					config[key] = int(value)
				else:
					# String values
					config[key] = value

				log_verbose(f"Config: {key} = {config[key]}")

		log_debug(f"Parsed {len(config)} config settings")
		return config

	except Exception as e:
		log_error(f"Error parsing config CSV: {e}")
		return {}

def load_display_config_from_csv(filepath):
	"""Load display config from local CSV file"""
	try:
		with open(filepath, 'r') as f:
			csv_content = f.read()
		return parse_display_config_csv(csv_content)

	except Exception as e:
		log_warning(f"Failed to load {filepath}: {e}")
		return {}

def fetch_display_config_from_github():
	"""Fetch display config from GitHub based on matrix ID"""
	session = get_requests_session()
	if not session:
		log_warning("No session available for config fetch")
		return {}

	# Determine which config to fetch based on matrix type
	matrix_type = detect_matrix_type()

	# Get URL from settings (fallback to None if not set)
	if matrix_type == "type1":
		config_url = os.getenv("MATRIX1_CONFIG_URL")
	elif matrix_type == "type2":
		config_url = os.getenv("MATRIX2_CONFIG_URL")
	else:
		log_warning(f"Unknown matrix type: {matrix_type}")
		return {}

	if not config_url:
		log_debug(f"No GitHub config URL set for matrix type {matrix_type}")
		return {}

	# Add cache buster
	cache_buster = int(time.monotonic())
	url = f"{config_url}?t={cache_buster}"

	response = None
	config = {}

	try:
		log_verbose(f"Fetching config: {url}")
		response = session.get(url, timeout=10)

		try:
			if response.status_code == 200:
				config = parse_display_config_csv(response.text)
				log_info(f"GitHub config loaded for matrix {matrix_type}: {len(config)} settings")
			elif response.status_code == 404:
				log_debug(f"No GitHub config found for matrix {matrix_type} (404)")
			else:
				log_warning(f"Failed to fetch config: HTTP {response.status_code}")
		finally:
			# CRITICAL: Close response to release socket
			if response:
				try:
					response.close()
				except:
					pass

	except Exception as e:
		log_warning(f"Failed to fetch GitHub config: {e}")

	return config

def apply_display_config(config_dict):
	"""Apply loaded config settings to display_config"""
	if not config_dict:
		return

	applied = 0

	# Core displays
	if "show_weather" in config_dict:
		display_config.show_weather = config_dict["show_weather"]
		applied += 1
	if "show_forecast" in config_dict:
		display_config.show_forecast = config_dict["show_forecast"]
		applied += 1
	if "show_events" in config_dict:
		display_config.show_events = config_dict["show_events"]
		applied += 1
	if "show_stocks" in config_dict:
		display_config.show_stocks = config_dict["show_stocks"]
		applied += 1
	if "stocks_display_frequency" in config_dict:
		display_config.stocks_display_frequency = config_dict["stocks_display_frequency"]
		applied += 1
	if "stocks_respect_market_hours" in config_dict:
		display_config.stocks_respect_market_hours = config_dict["stocks_respect_market_hours"]
		applied += 1

	# Display elements
	if "show_weekday_indicator" in config_dict:
		display_config.show_weekday_indicator = config_dict["show_weekday_indicator"]
		applied += 1
	if "show_scheduled_displays" in config_dict:
		display_config.show_scheduled_displays = config_dict["show_scheduled_displays"]
		applied += 1
	if "show_events_in_between_schedules" in config_dict:
		display_config.show_events_in_between_schedules = config_dict["show_events_in_between_schedules"]
		applied += 1
	if "night_mode_minimal_display" in config_dict:
		display_config.night_mode_minimal_display = config_dict["night_mode_minimal_display"]
		applied += 1

	# Safety features
	if "delayed_start" in config_dict:
		display_config.delayed_start = config_dict["delayed_start"]
		applied += 1

	log_debug(f"Applied {applied} config settings to display_config")


class ScheduledDisplay:
	"""Configuration for time-based scheduled displays"""
	
	def __init__(self):
		self.schedules = {}
		self.schedules_loaded = False
		self.last_fetch_date = None
	
	def ensure_loaded(self, rtc):
		"""Ensure schedules are loaded, refresh if new day"""
		
		current_date = f"{rtc.datetime.tm_year:04d}-{rtc.datetime.tm_mon:02d}-{rtc.datetime.tm_mday:02d}"
		
		# Check if we need daily refresh
		if self.last_fetch_date and self.last_fetch_date != current_date:
			log_info("New day - refreshing GitHub data")
			events, schedules, schedule_source, stocks = fetch_github_data(rtc)  # ← Updated

			if schedules:
				self.schedules = schedules
				self.schedules_loaded = True
				self.last_fetch_date = current_date

				# Update cached events too
				if events:
					state.cached_events = events

				# Update cached stocks too
				if stocks:
					state.cached_stocks = stocks
				
				# Summary with counts
				event_count = len(events) if events else 0
				source_msg = f" ({schedule_source})" if schedule_source else ""
				log_debug(f"Refreshed: {event_count} event dates, {len(schedules)} schedules{source_msg}")
		
		# Fallback if still not loaded (safety net)
		if not self.schedules_loaded:
			log_debug("Schedules not loaded, trying local fallback")
			local_schedules = load_schedules_from_csv()
			if local_schedules:
				self.schedules = local_schedules
				self.schedules_loaded = True
				self.last_fetch_date = current_date
				log_debug(f"Local fallback: {len(local_schedules)} schedules")
		
		# Fallback if still not loaded (safety net)
		if not self.schedules_loaded:
			log_debug("Schedules not loaded, trying local fallback")
			local_schedules = load_schedules_from_csv()
			if local_schedules:
				self.schedules = local_schedules
				self.schedules_loaded = True
				self.last_fetch_date = current_date
				log_debug(f"Local fallback: {len(local_schedules)} schedules")
			else:
				log_warning("No schedules available")
				self.schedules_loaded = False
	
	def is_active(self, rtc, schedule_name):
		"""Check if a schedule is currently active"""
		
		# Ensure schedules are loaded
		self.ensure_loaded(rtc)
		
		if schedule_name not in self.schedules:
			return False
		
		schedule = self.schedules[schedule_name]
		
		if not schedule["enabled"]:
			return False
		
		current = rtc.datetime
		
		# Check if current day is in schedule
		if current.tm_wday not in schedule["days"]:
			return False
		
		# Convert times to minutes for easier comparison
		current_mins = current.tm_hour * 60 + current.tm_min
		start_mins = schedule["start_hour"] * 60 + schedule["start_min"]
		end_mins = schedule["end_hour"] * 60 + schedule["end_min"]
		
		return start_mins <= current_mins < end_mins
	
	def get_active_schedule(self, rtc):
		"""Check if any schedule is currently active"""
		
		# Ensure schedules are loaded
		self.ensure_loaded(rtc)
		
		for schedule_name, schedule_config in self.schedules.items():
			if self.is_active(rtc, schedule_name):
				return schedule_name, schedule_config
		
		return None, None


# Create instance
scheduled_display = ScheduledDisplay()

def calculate_bottom_aligned_positions(font, line1_text, line2_text, display_height=32, bottom_margin=2, line_spacing=1):
	"""
	Calculate optimal y positions for two lines of text aligned to bottom
	Enhanced to account for descender characters (g, j, p, q, y)
	
	Returns:
		tuple: (line1_y, line2_y) positions
	"""
	
	# Get font metrics
	font_height, baseline_offset = get_font_metrics(font, line1_text + line2_text)
	
	# Check if ONLY the second line (bottom line) has lowercase descender characters
	has_descenders = any(char in Strings.DESCENDER_CHARS for char in line2_text)
	
	# Add extra bottom margin if descenders are present
	adjusted_bottom_margin = bottom_margin + (2 if has_descenders else 0)
	
	# Calculate positions working backwards from bottom
	bottom_edge = display_height - adjusted_bottom_margin
	
	# Second line position (bottom line)
	line2_y = bottom_edge - baseline_offset
	
	# First line position (needs space for font height + line spacing)
	line1_y = line2_y - font_height - line_spacing
	
	# Ensure we don't go above display area
	if line1_y < baseline_offset:
		line1_y = baseline_offset
		line2_y = line1_y + font_height + line_spacing
	
	return int(line1_y), int(line2_y)


def clear_display():
	"""Clear all display elements"""
	if state.main_group is not None:
		while len(state.main_group):
			state.main_group.pop()

### CTA TRANSIT FUNCTIONS ###

def fetch_cta_train_arrivals(station_mapid):
	"""
	Fetch train arrivals from CTA Train Tracker API.
	Returns list of dicts: [{route, destination, minutes, color}, ...]
	"""
	api_key = os.getenv("CTA_API_KEY")
	if not api_key:
		log_warning("CTA_API_KEY not configured in settings.toml")
		return []

	session = get_requests_session()
	if not session:
		log_warning("No session available for CTA train fetch")
		return []

	response = None
	try:
		# Build URL - CTA Train Tracker API
		url = CTA.TRAIN_TRACKER_URL + "?key=" + api_key
		url += "&mapid=" + station_mapid
		url += "&max=5&outputType=JSON"

		log_verbose("Fetching CTA train arrivals for station " + station_mapid)
		response = session.get(url, timeout=10)

		if not response:
			log_warning("No response from CTA Train Tracker")
			return []

		if response.status_code == 200:
			import json
			data = json.loads(response.text)

			# Check for errors
			if "ctatt" not in data:
				log_warning("Invalid CTA response format")
				return []

			ctatt = data["ctatt"]
			if "eta" not in ctatt:
				log_verbose("No arrivals for station " + station_mapid)
				return []

			arrivals = []
			for eta in ctatt["eta"]:
				# Calculate minutes until arrival
				arrival_time = eta.get("arrT", "")
				prediction_time = eta.get("prdt", "")

				# Parse times and calculate difference
				# Format: YYYYMMDD HH:MM:SS
				try:
					import time
					# Simple minute calculation from prediction
					arr_parts = arrival_time.split()
					pred_parts = prediction_time.split()

					if len(arr_parts) == 2 and len(pred_parts) == 2:
						arr_time_parts = arr_parts[1].split(":")
						pred_time_parts = pred_parts[1].split(":")

						arr_minutes = int(arr_time_parts[0]) * 60 + int(arr_time_parts[1])
						pred_minutes = int(pred_time_parts[0]) * 60 + int(pred_time_parts[1])

						minutes_until = arr_minutes - pred_minutes
						if minutes_until < 0:
							minutes_until += 1440  # Handle midnight rollover

						route = eta.get("rt", "")
						destination = eta.get("destNm", "")

						# Determine color based on route
						color = CTA.COLOR_RED
						if route == "Brn":
							color = CTA.COLOR_BROWN
						elif route == "P" or route == "Pexp":
							color = CTA.COLOR_PURPLE

						arrivals.append({
							"route": route,
							"destination": destination,
							"minutes": minutes_until,
							"type": "train",
							"color": color
						})

				except Exception as e:
					log_debug(f"Error parsing arrival time: {e}")
					continue

			log_verbose(f"Found {len(arrivals)} train arrivals")
			return arrivals

		else:
			log_warning(f"CTA Train API error: {response.status_code}")
			return []

	except Exception as e:
		log_warning(f"Error fetching CTA trains: {e}")
		return []

	finally:
		if response:
			try:
				response.close()
			except:
				pass

def fetch_cta_bus_arrivals(stop_id, route):
	"""
	Fetch bus arrivals from CTA Bus Tracker API.
	Returns list of dicts: [{route, destination, minutes, color}, ...]
	"""
	api_key = os.getenv("CTA_API_KEY")
	if not api_key:
		log_warning("CTA_API_KEY not configured in settings.toml")
		return []

	session = get_requests_session()
	if not session:
		log_warning("No session available for CTA bus fetch")
		return []

	response = None
	try:
		# Build URL - CTA Bus Tracker API
		url = CTA.BUS_TRACKER_URL + "?key=" + api_key
		url += "&stpid=" + stop_id
		url += "&rt=" + route
		url += "&format=json"

		log_verbose("Fetching CTA bus arrivals for stop " + stop_id)
		response = session.get(url, timeout=10)

		if not response:
			log_warning("No response from CTA Bus Tracker")
			return []

		if response.status_code == 200:
			import json
			data = json.loads(response.text)

			# Check for errors
			if "bustime-response" not in data:
				log_warning("Invalid CTA bus response format")
				return []

			bus_response = data["bustime-response"]
			if "prd" not in bus_response:
				log_verbose("No bus predictions for stop " + stop_id)
				return []

			arrivals = []
			for prd in bus_response["prd"]:
				# Get predicted minutes
				minutes_until = int(prd.get("prdctdn", "0"))
				route_name = prd.get("rt", "")
				destination = prd.get("des", "")

				arrivals.append({
					"route": route_name,
					"destination": destination,
					"minutes": minutes_until,
					"type": "bus",
					"color": CTA.COLOR_BUS
				})

			log_verbose(f"Found {len(arrivals)} bus arrivals")
			return arrivals

		else:
			log_warning(f"CTA Bus API error: {response.status_code}")
			return []

	except Exception as e:
		log_warning(f"Error fetching CTA buses: {e}")
		return []

	finally:
		if response:
			try:
				response.close()
			except:
				pass

def fetch_all_transit_arrivals():
	"""
	Fetch all configured CTA transit arrivals (trains + buses).
	Returns combined list sorted by arrival time.
	"""
	all_arrivals = []

	# Fetch Diversey station (Brown & Purple)
	diversey_arrivals = fetch_cta_train_arrivals(CTA.STATION_DIVERSEY)
	all_arrivals.extend(diversey_arrivals)

	# Fetch Fullerton station (Red)
	fullerton_arrivals = fetch_cta_train_arrivals(CTA.STATION_FULLERTON)
	all_arrivals.extend(fullerton_arrivals)

	# Fetch 8 bus at Halsted & Wrightwood
	bus_arrivals = fetch_cta_bus_arrivals(CTA.STOP_HALSTED_WRIGHTWOOD, CTA.ROUTE_8_HALSTED)
	all_arrivals.extend(bus_arrivals)

	# Sort by minutes (earliest first)
	all_arrivals.sort(key=lambda x: x["minutes"])

	# Update cache
	state.cached_transit_arrivals = all_arrivals
	state.last_transit_fetch_time = time.monotonic()

	log_info(f"Fetched {len(all_arrivals)} total transit arrivals")
	return all_arrivals

### DISPLAY FUNCTIONS ###

def right_align_text(text, font, right_edge):
	return right_edge - get_text_width(text, font)

def center_text(text, font, area_x, area_width):
	return area_x + (area_width - get_text_width(text, font)) // 2

def get_12h_hour(hour):
	"""Convert 24-hour to 12-hour format (returns 1-12)
	Examples: 0→12, 1→1, 13→1, 23→11
	"""
	return hour % 12 or 12

def format_hour_12h(hour):
	"""Convert 24-hour time to 12-hour format with AM/PM suffix (e.g., '3P', '12A')"""
	h = get_12h_hour(hour)
	suffix = Strings.AM_SUFFIX if hour < 12 else Strings.PM_SUFFIX
	return f"{h}{suffix}"

def get_day_color(rtc):
	"""Get color for day of week indicator"""
	day_colors = {
		0: state.colors["RED"],      # Monday
		1: state.colors["ORANGE"],   # Tuesday
		2: state.colors["YELLOW"],   # Wednesday
		3: state.colors["GREEN"],    # Thursday
		4: state.colors["AQUA"],     # Friday
		5: state.colors["PURPLE"],   # Saturday
		6: state.colors["PINK"]      # Sunday
	}
	
	weekday = rtc.datetime.tm_wday  # 0=Monday, 6=Sunday
	return day_colors.get(weekday, state.colors["WHITE"])  # Default to white if error

def add_day_indicator_bitmap(main_group, rtc):
	"""Add 4x4 day-of-week color indicator using Bitmap (OPTIMIZED: 1 object vs 25)"""
	day_color = get_day_color(rtc)

	# Create 5x5 bitmap (4x4 square + 1px margin on left/bottom)
	width = DayIndicator.SIZE + 1  # 5 pixels
	height = DayIndicator.SIZE + 1  # 5 pixels

	bitmap = displayio.Bitmap(width, height, 2)  # 2 colors: black, day color
	palette = displayio.Palette(2)
	palette[0] = state.colors["BLACK"]  # Margin color
	palette[1] = day_color              # Day color

	# Fill entire bitmap with black (margin)
	for y in range(height):
		for x in range(width):
			bitmap[x, y] = 0

	# Fill 4x4 colored square (offset by 1 to leave left/top margin)
	for y in range(0, DayIndicator.SIZE):
		for x in range(1, DayIndicator.SIZE + 1):
			bitmap[x, y] = 1

	# Create TileGrid at correct position (offset -1 for margin)
	day_grid = displayio.TileGrid(
		bitmap,
		pixel_shader=palette,
		x=DayIndicator.MARGIN_LEFT_X,  # Position includes margin
		y=DayIndicator.Y
	)
	main_group.append(day_grid)

def add_day_indicator(main_group, rtc):
	"""Add day-of-week indicator using Bitmap (1 object vs 25 Line objects)"""
	add_day_indicator_bitmap(main_group, rtc)

def add_weekday_indicator_if_enabled(main_group, rtc, display_name=""):
	"""Add weekday indicator if enabled, with optional logging"""
	if display_config.show_weekday_indicator:
		add_day_indicator(main_group, rtc)
		if display_name:
			log_verbose(f"Showing Weekday Color Indicator on {display_name} Display")
		else:
			log_verbose("Showing Weekday Color Indicator")
	else:
		if display_name:
			log_verbose(f"Weekday Color Indicator Disabled on {display_name} Display")
		else:
			log_verbose("Weekday Color Indicator Disabled")

def calculate_uv_bar_length(uv_index):
	"""Calculate UV bar length with spacing for readability"""
	if uv_index <= Visual.UV_BREAKPOINT_1:
		return uv_index
	elif uv_index <= Visual.UV_BREAKPOINT_2:
		return uv_index + 1
	elif uv_index <= Visual.UV_BREAKPOINT_3:
		return uv_index + 2
	else:
		return uv_index + 3

def calculate_humidity_bar_length(humidity):
	"""Calculate humidity bar length (10% per pixel) with spacing every 20%"""
	pixels = round(humidity / Visual.HUMIDITY_PERCENT_PER_PIXEL)  # 10% per pixel, so max 10 pixels at 100%
	
	# Add spacing pixels (black dots every 2 pixels = every 20%)
	if pixels <= 2:
		return pixels
	elif pixels <= 4:
		return pixels + 1  # Add 1 spacing pixel
	elif pixels <= 6:
		return pixels + 2
	elif pixels <= 8:
		return pixels + 3
	else:
		return pixels + 4
		
def add_indicator_bars_bitmap(main_group, x_start, uv_index, humidity):
	"""Add UV and humidity bars using Bitmap (OPTIMIZED: 2 objects vs 4-10)"""

	# UV bar (only if UV > 0)
	if uv_index > 0:
		uv_length = calculate_uv_bar_length(uv_index)

		# Create UV bar bitmap
		uv_bitmap = displayio.Bitmap(uv_length, 1, 2)  # width x height, 2 colors
		uv_palette = displayio.Palette(2)
		uv_palette[0] = state.colors["BLACK"]  # Spacing dots
		uv_palette[1] = state.colors["DIMMEST_WHITE"]  # Bar color

		# Fill bar with color, add black spacing dots
		for x in range(uv_length):
			uv_bitmap[x, 0] = 0 if x in Visual.UV_SPACING_POSITIONS else 1

		# Create TileGrid
		uv_grid = displayio.TileGrid(uv_bitmap, pixel_shader=uv_palette, x=x_start, y=Layout.UV_BAR_Y)
		main_group.append(uv_grid)

	# Humidity bar
	if humidity > 0:
		humidity_length = calculate_humidity_bar_length(humidity)

		# Create humidity bar bitmap
		humidity_bitmap = displayio.Bitmap(humidity_length, 1, 2)
		humidity_palette = displayio.Palette(2)
		humidity_palette[0] = state.colors["BLACK"]  # Spacing dots
		humidity_palette[1] = state.colors["DIMMEST_WHITE"]  # Bar color

		# Fill bar with color, add black spacing dots
		for x in range(humidity_length):
			humidity_bitmap[x, 0] = 0 if x in Visual.HUMIDITY_SPACING_POSITIONS else 1

		# Create TileGrid
		humidity_grid = displayio.TileGrid(humidity_bitmap, pixel_shader=humidity_palette, x=x_start, y=Layout.HUMIDITY_BAR_Y)
		main_group.append(humidity_grid)

def add_indicator_bars(main_group, x_start, uv_index, humidity):
	"""Add UV and humidity indicator bars using Bitmap (2 objects vs 4-10 Line objects)"""
	add_indicator_bars_bitmap(main_group, x_start, uv_index, humidity)


def show_weather_display(rtc, duration, weather_data=None):
	"""Optimized weather display - only update time text in loop"""
	state.memory_monitor.check_memory("weather_display_start")
	
	# Require weather_data to be provided
	if not weather_data:
		# Try cached weather as fallback (max 30 min old)
		weather_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)
		
		if weather_data:
			log_debug("Using cached current weather for weather display")
			is_cached = True
		else:
			log_warning("Weather unavailable, showing clock")
			show_clock_display(rtc, duration)
			return
	else:
		is_cached = False
	
	log_debug(f"Displaying weather for {duration_message(duration)}")
	
	# Clear display and setup static elements ONCE
	clear_display()
	
	# LOG what we're displaying
	temp = round(weather_data["feels_like"])
	condition = weather_data.get("weather_text", "Unknown")
	cache_indicator = " [CACHED]" if is_cached else ""
	log_info(f"Displaying Weather: {condition}, {temp}°C ({duration/60:.0f} min){cache_indicator}")
	
	# Set temperature color based on cache status
	temp_color = state.colors["LILAC"] if is_cached else state.colors["DIMMEST_WHITE"]
	
	# Create all static display elements ONCE
	temp_text = bitmap_label.Label(
		bg_font,
		color=temp_color,  # ← FIXED: Use dynamic color
		text=f"{round(weather_data['temperature'])}°",
		x=Layout.WEATHER_TEMP_X,
		y=Layout.WEATHER_TEMP_Y,
		background_color=state.colors["BLACK"],
		padding_top=Layout.BG_PADDING_TOP,
		padding_bottom=1,
		padding_left=1
	)
	
	# Create time text - this is the ONLY element we'll update
	time_text = bitmap_label.Label(
		font,
		color=state.colors["DIMMEST_WHITE"],
		x=Layout.WEATHER_TIME_X,
		y=Layout.WEATHER_TIME_Y,
		background_color=state.colors["BLACK"],
		padding_top=Layout.BG_PADDING_TOP,
		padding_bottom=-2,
		padding_left=1
	)
	
	# Create feels-like temperatures if different (static)
	temp_rounded = round(weather_data['temperature'])
	feels_like_rounded = round(weather_data['feels_like'])
	feels_shade_rounded = round(weather_data['feels_shade'])
	
	feels_like_text = None
	feels_shade_text = None
	
	if feels_like_rounded != temp_rounded:
		feels_like_text = bitmap_label.Label(
			font,
			color=temp_color,  # ← Already correct
			text=f"{feels_like_rounded}°",
			y=Layout.FEELSLIKE_Y,
			background_color=state.colors["BLACK"],
			padding_top=Layout.BG_PADDING_TOP,
			padding_bottom=-2,
			padding_left=1
		)
		feels_like_text.x = right_align_text(feels_like_text.text, font, Layout.RIGHT_EDGE)
	
	if feels_shade_rounded != feels_like_rounded:
		feels_shade_text = bitmap_label.Label(
			font,
			color=temp_color,  # ← Already correct
			text=f"{feels_shade_rounded}°",
			y=Layout.FEELSLIKE_SHADE_Y,
			background_color=state.colors["BLACK"],
			padding_top=Layout.BG_PADDING_TOP,
			padding_bottom=-2,
			padding_left=1
		)
		feels_shade_text.x = right_align_text(feels_shade_text.text, font, Layout.RIGHT_EDGE)
	
	# Load weather icon ONCE - fallback to blank
	bitmap, palette = state.image_cache.get_image(f"{Paths.WEATHER_ICONS}/{weather_data['weather_icon']}.bmp")

	# Try blank if primary failed (check return value, not exception)
	if bitmap is None:
		log_warning(f"Weather icon {weather_data['weather_icon']}.bmp failed, trying blank")
		bitmap, palette = state.image_cache.get_image(Paths.BLANK_WEATHER)
		if bitmap is None:
			log_error(f"Weather blank fallback failed, skipping icon")

	# Add icon if successfully loaded
	if bitmap:
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		state.main_group.append(image_grid)
	
	# Add all static elements to display ONCE
	state.main_group.append(temp_text)
	state.main_group.append(time_text)
	
	if feels_like_text:
		state.main_group.append(feels_like_text)
	if feels_shade_text:
		state.main_group.append(feels_shade_text)
	
	# Add UV and humidity indicator bars ONCE (they're static)
	add_indicator_bars(state.main_group, temp_text.x, weather_data['uv_index'], weather_data['humidity'])

	# Add day indicator ONCE
	add_weekday_indicator_if_enabled(state.main_group, rtc, "Weather")
	
	# Optimized display update loop - ONLY update time text
	start_time = time.monotonic()
	loop_count = 0
	last_minute = -1
	
	while time.monotonic() - start_time < duration:
		loop_count += 1
		
		# Memory monitoring and cleanup
		if loop_count % Timing.GC_INTERVAL == 0:
			gc.collect()
			state.memory_monitor.check_memory(f"weather_display_gc_{loop_count//System.SECONDS_PER_MINUTE}")
		elif loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:
			state.memory_monitor.check_memory(f"weather_display_loop_{loop_count}")
		
		# Get current time
		hour = rtc.datetime.tm_hour
		minute = rtc.datetime.tm_min
		
		# Only update display when minute changes (not every second)
		if minute != last_minute:
			display_hour = get_12h_hour(hour)
			current_time = f"{display_hour}:{minute:02d}"
			
			# Update ONLY the time text content
			time_text.text = current_time
			
			# Position time text based on other elements
			if feels_shade_text:
				time_text.x = center_text(current_time, font, 0, Display.WIDTH)
			else:
				time_text.x = right_align_text(current_time, font, Layout.RIGHT_EDGE)
			
			last_minute = minute
		
		interruptible_sleep(1)
	
	state.memory_monitor.check_memory("weather_display_complete")
				
def show_startup_message(duration=3):
	"""Display 'Hola!!' startup message during initialization"""
	log_debug("Displaying startup message...")
	clear_display()

	# Create centered "Hola!!" text
	startup_text = bitmap_label.Label(
		bg_font,
		text="Hola!!",
		color=state.colors.get("MINT", 0x00FF88),  # Use MINT color, fallback to green
		x=12,  # Centered for "Hola!!" with big font
		y=16   # Vertically centered
	)

	state.main_group.append(startup_text)
	state.display.root_group = state.main_group

	# Display for specified duration
	interruptible_sleep(duration)
	clear_display()

def show_clock_display(rtc, duration=Timing.CLOCK_DISPLAY_DURATION):
	"""Display clock as fallback when weather unavailable"""
	log_warning(f"Displaying clock for {duration_message(duration)}...")
	clear_display()
	
	# Determine clock color based on error state
	error_state = get_current_error_state()
	
	clock_colors = {
		None: state.colors[Strings.DEFAULT_EVENT_COLOR],  # MINT = All OK
		"wifi": state.colors["RED"],                      # WiFi failure
		"weather": state.colors["YELLOW"],                # Weather API failure
		"extended": state.colors["PURPLE"],               # Extended failure
		"general": state.colors["WHITE"]                  # Unknown error
	}
	
	clock_color = clock_colors.get(error_state, state.colors["MINT"])
	
	date_text = bitmap_label.Label(
		font, 
		color=state.colors["DIMMEST_WHITE"], 
		x=Layout.CLOCK_DATE_X, 
		y=Layout.CLOCK_DATE_Y
	)
	time_text = bitmap_label.Label(
		bg_font, 
		color=clock_color,  # Use error-based color
		x=Layout.CLOCK_TIME_X, 
		y=Layout.CLOCK_TIME_Y
	)
	
	state.main_group.append(date_text)
	state.main_group.append(time_text)

	# Add day indicator after other elements
	add_weekday_indicator_if_enabled(state.main_group, rtc, "Clock")
	
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		dt = rtc.datetime
		date_str = f"{MONTHS[dt.tm_mon].upper()} {dt.tm_mday:02d}"

		hour = dt.tm_hour
		display_hour = get_12h_hour(hour)
		time_str = f"{display_hour}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
		
		date_text.text = date_str
		time_text.text = time_str
		interruptible_sleep(1)
	
	# Check for restart conditions ONLY if not in startup phase
	if state.startup_time > 0:  # Only check if we've completed initialization
		time_since_weather = time.monotonic() - state.tracker.last_successful_weather

		# Hard reset after 1 hour without weather (even if other displays work)
		if time_since_weather > System.SECONDS_PER_HOUR:
			log_error(f"Hard reset after {int(time_since_weather/System.SECONDS_PER_MINUTE)} minutes without successful weather fetch")
			interruptible_sleep(Timing.RESTART_DELAY)
			supervisor.reload()

		# Warn after 30 minutes
		elif time_since_success > System.SECONDS_HALF_HOUR and state.tracker.consecutive_failures >= System.MAX_LOG_FAILURES_BEFORE_RESTART:
			log_warning(f"Extended failure: {int(time_since_success/System.SECONDS_PER_MINUTE)}min without success, {state.tracker.consecutive_failures} consecutive failures")
		
def show_event_display(rtc, duration):
	"""Display special calendar events - cycles through multiple events if present"""
	state.memory_monitor.check_memory("event_display_start")
	
	# Get currently active events
	num_events, event_list = get_today_events_info(rtc)
	
	# Check if there are ANY events today (even if not active now)
	total_events_today, all_today_events = get_today_all_events_info(rtc)
	
	if total_events_today > 0 and num_events == 0:
		# Events exist but none are currently active
		current_hour = rtc.datetime.tm_hour
		
		# Find when next event becomes active
		next_event_time = None
		for event in all_today_events:
			if len(event) >= 6:  # Has time window
				start_hour = int(event[4])
				if start_hour > current_hour:
					if next_event_time is None or start_hour < next_event_time:
						next_event_time = start_hour
		
		if next_event_time:
			log_verbose(f"Event inactive: {total_events_today} event(s) today, next active at {next_event_time}:00")
		else:
			log_verbose(f"Event inactive: {total_events_today} event(s) today, time window passed")
		
		return False
	
	if num_events == 0:
		return False
	
	# Log activation for time-windowed events
	for event in event_list:
		if len(event) >= 6:  # Has time window
			start_hour = event[4]
			end_hour = event[5]
			log_debug(f"Event active: {event[1]} {event[0]} (time window: {start_hour}:00-{end_hour}:00)")
	
	if num_events == 1:
		# Single event - use full duration
		event_data = event_list[0]
		log_info(f"Showing event: {event_data[0]} {event_data[1]}")
		log_debug(f"Showing event display for {duration_message(duration)}")
		_display_single_event_optimized(event_data, rtc, duration)
	else:
		# Multiple events - split time between them
		event_duration = max(duration // num_events, Timing.MIN_EVENT_DURATION)
		log_verbose(f"Showing {num_events} events, {duration_message(event_duration)} each")
		
		for i, event_data in enumerate(event_list):
			state.memory_monitor.check_memory(f"event_{i+1}_start")
			log_info(f"Event {i+1}/{num_events}: {event_data[0]} {event_data[1]}")
			_display_single_event_optimized(event_data, rtc, event_duration)
	
	state.memory_monitor.check_memory("event_display_complete")
	return True

def _display_single_event_optimized(event_data, rtc, duration):
	"""Optimized helper function to display a single event"""
	clear_display()
	
	# Force garbage collection before loading images
	gc.collect()
	state.memory_monitor.check_memory("single_event_start")
	
	# Load image - fallback to blank if primary fails
	bitmap = None
	palette = None

	if event_data[0] == "Birthday":
		# Try birthday cake image
		bitmap, palette = state.image_cache.get_image(Paths.BIRTHDAY_IMAGE)
	else:
		# Try event-specific image
		image_file = f"{Paths.EVENT_IMAGES}/{event_data[2]}"
		bitmap, palette = state.image_cache.get_image(image_file)

	# Try blank if primary failed (check return value, not exception)
	if bitmap is None:
		log_warning(f"Event image failed, trying blank")
		bitmap, palette = state.image_cache.get_image(Paths.BLANK_EVENT)
		if bitmap is None:
			log_error(f"Event blank fallback failed, skipping event")
			return False

	# Now display the loaded image
	try:
		if event_data[0] == "Birthday":
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			state.main_group.append(image_grid)
		else:
			
			# Position 25px wide image at top right
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			image_grid.x = Layout.EVENT_IMAGE_X
			image_grid.y = Layout.EVENT_IMAGE_Y
			
			# Calculate optimal text positions dynamically
			# NEW: Swapped indices - [0] is top, [1] is bottom
			top_text = event_data[0]     # e.g., "Puchis" - shows on TOP
			bottom_text = event_data[1]  # e.g., "Cumple" - shows on BOTTOM
			text_color = event_data[3] if len(event_data) > 3 else Strings.DEFAULT_EVENT_COLOR
			
			# Color map through dictionary access:
			line2_color = state.colors.get(text_color.upper(), state.colors[Strings.DEFAULT_EVENT_COLOR])
			
			# Get dynamic positions
			line1_y, line2_y = calculate_bottom_aligned_positions(
				font,
				top_text,
				bottom_text,
				display_height=Display.HEIGHT,
				bottom_margin=Layout.BOTTOM_MARGIN,
				line_spacing=Layout.LINE_SPACING
			)
			
			# Create text labels (line1 = top, line2 = bottom)
			text1 = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=top_text,
				x=Layout.TEXT_MARGIN, y=line1_y
			)
			
			text2 = bitmap_label.Label(
				font,
				color=line2_color,
				text=bottom_text,
				x=Layout.TEXT_MARGIN,
				y=line2_y
			)
			
			# Add elements to display
			state.main_group.append(image_grid)
			state.main_group.append(text1)
			state.main_group.append(text2)

			# Add day indicator
			add_weekday_indicator_if_enabled(state.main_group, rtc, "Event")		
		
		# Simple strategy optimized for usage patterns
		if duration <= Timing.EVENT_CHUNK_SIZE:
			# Most common case: 10-60 second events, just sleep
			interruptible_sleep(duration)
		else:
			# Rare case: all-day events, use 60-second chunks with minimal monitoring
			elapsed = 0
			chunk_size = Timing.EVENT_CHUNK_SIZE  # 1-minute chunks for long events
			
			while elapsed < duration:
				remaining = duration - elapsed
				sleep_time = min(chunk_size, remaining)
				
				interruptible_sleep(sleep_time)
				elapsed += sleep_time
				
				# Very minimal monitoring for all-day events (every 10 minutes)
				if elapsed % Timing.EVENT_MEMORY_MONITORING == 0:  # Every 10 minutes
					state.memory_monitor.check_memory(f"event_display_allday_{int(elapsed//System.SECONDS_PER_MINUTE)}min")
		
	except Exception as e:
		log_error(f"Event display error: {e}")
		state.memory_monitor.check_memory("single_event_error")
	
	# Clean up after event display
	gc.collect()
	state.memory_monitor.check_memory("single_event_complete")
			
def show_color_test_display(duration=Timing.COLOR_TEST):
	log_debug(f"Displaying Color Test for {duration_message(Timing.COLOR_TEST)}")
	clear_display()
	gc.collect()
	
	try:
		# Get test colors dynamically from COLORS dictionary
		test_color_names = ["MINT", "BUGAMBILIA", "LILAC", "RED", "GREEN", "BLUE",
						   "ORANGE", "YELLOW", "CYAN", "PURPLE", "PINK", "BROWN"]
		texts = ["Aa", "Bb", "Cc", "Dd", "Ee", "Ff", "Gg", "Hh", "Ii", "Jj", "Kk", "Ll"]
		
		key_text = "Color Key: "
		
		for i, (color_name, text) in enumerate(zip(test_color_names, texts)):
			color = state.colors[color_name]
			col = i // Visual.COLOR_TEST_GRID_COLS
			row = i % Visual.COLOR_TEST_GRID_COLS
			
			label = bitmap_label.Label(
				font, color=color, text=text,
				x=Layout.COLOR_TEST_TEXT_X + col * Visual.COLOR_TEST_COL_SPACING , y=Layout.COLOR_TEST_TEXT_Y + row * Visual.COLOR_TEST_ROW_SPACING
			)
			state.main_group.append(label)
			key_text += f"{text}={color_name}(0x{color:06X}) | "
	
	except Exception as e:
		log_error(f"Color Test display error: {e}")
	
	log_info(key_text)
	interruptible_sleep(duration)
	gc.collect()
	return True
	
def show_icon_test_display(icon_numbers=None, duration=Timing.ICON_TEST):
	"""
	Test display for weather icon columns
	
	Args:
		icon_numbers: List of up to 3 icon numbers to display, e.g. [1, 5, 33]
					 If None, cycles through all icons
		duration: How long to display (only used when cycling all icons)
	"""
	
	if icon_numbers is None:
		# Original behavior - cycle through all icons
		log_info("Starting Icon Test Display - All Icons (Ctrl+C to exit)")
		
		# AccuWeather icon numbers (skipping 9, 10, 27, 28)
		all_icons = []
		for i in range(1, 45):
			if i not in [9, 10, 27, 28]:
				all_icons.append(i)
		
		total_icons = len(all_icons)
		icons_per_batch = 3
		num_batches = (total_icons + icons_per_batch - 1) // icons_per_batch
		
		log_info(f"Testing {total_icons} icons in {num_batches} batches")
		
		try:
			for batch_num in range(num_batches):
				start_idx = batch_num * icons_per_batch
				end_idx = min(start_idx + icons_per_batch, total_icons)
				batch_icons = all_icons[start_idx:end_idx]
				
				_display_icon_batch(batch_icons, batch_num + 1, num_batches)
				
				# Shorter sleep intervals for better interrupt response
				for _ in range(int(duration * 10)):
					time.sleep(0.1)
					
		except KeyboardInterrupt:
			log_info("Icon test interrupted by user")
			clear_display()
			raise
	else:
		# Manual mode - display specific icons indefinitely
		if len(icon_numbers) > 3:
			log_warning(f"Too many icons specified ({len(icon_numbers)}), showing first 3")
			icon_numbers = icon_numbers[:3]
		
		log_info(f"Displaying icons: {icon_numbers} (Ctrl+C to exit)")
		_display_icon_batch(icon_numbers, manual_mode=True)
		
		# Loop indefinitely until interrupted
		try:
			while True:
				time.sleep(0.1)  # Keep display active, check for interrupt
		except KeyboardInterrupt:
			log_info("Icon test interrupted")
			clear_display()
			raise
	
	log_info("Icon Test Display complete")
	gc.collect()
	return True


def _display_icon_batch(icon_numbers, batch_num=None, total_batches=None, manual_mode=False):
	"""Helper function to display a batch of icons"""
	
	if not manual_mode:
		log_info(f"Batch {batch_num}/{total_batches}: Icons {icon_numbers}")
	
	clear_display()
	gc.collect()
	
	try:
		# Position icons horizontally (up to 3)
		positions = [
			(Layout.ICON_TEST_COL1_X, Layout.ICON_TEST_ROW1_Y),  # Left
			(Layout.ICON_TEST_COL2_X, Layout.ICON_TEST_ROW1_Y),  # Center
			(Layout.ICON_TEST_COL3_X, Layout.ICON_TEST_ROW1_Y),  # Right
		]
		
		for i, icon_num in enumerate(icon_numbers):
			if i >= len(positions):
				break
			
			x, y = positions[i]
			
			# Load icon image
			try:
				bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{icon_num}.bmp")
				icon_img = displayio.TileGrid(bitmap, pixel_shader=palette)
				icon_img.x = x
				icon_img.y = y
				state.main_group.append(icon_img)
			except Exception as e:
				log_warning(f"Failed to load icon {icon_num}: {e}")
				# Show error text instead
				error_label = bitmap_label.Label(
					font,
					color=state.colors["RED"],
					text="ERR",
					x=x + 1,
					y=y + 4
				)
				state.main_group.append(error_label)
			
			# Add icon number below image
			number_label = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=str(icon_num),
				x=x + (5 if icon_num < 10 else 3),  # Center single vs double digits
				y=y + Layout.ICON_TEST_NUMBER_Y_OFFSET
			)
			state.main_group.append(number_label)
			
	except Exception as e:
		log_error(f"Icon display error: {e}")

def format_price_with_suffix(price):
	"""Format prices for forex/crypto/commodity display

	Rules:
	- >= 1000: Remove cents and add comma separator (e.g., "86,932")
	- < 1000: Keep 2 decimals (e.g., "18.49")

	Examples:
		86932.49 → "86,932"
		1234.56 → "1,234"
		18.49 → "18.49"
		1500000 → "1,500,000"
	"""
	if price >= 1000:
		# Remove cents and add comma separators for thousands
		return f"{int(price):,}"
	else:
		# Under 1000, show with 2 decimals
		return f"{price:.2f}"

def format_price_with_dollar(price):
	"""Format price with dollar sign, using comma separators for large values.

	Rules:
	- >= $1000: No cents, comma separators (e.g., "$86,932")
	- < $1000: Show 2 decimals (e.g., "$226.82")

	Args:
		price: Price value as float

	Returns:
		str: Formatted price string with $ prefix

	Examples:
		86932.49 → "$86,932"
		1234.56 → "$1,234"
		226.82 → "$226.82"
	"""
	if price >= 1000:
		return "${:,}".format(int(price))
	else:
		return "${:.2f}".format(price)

def get_stock_display_name(symbol):
	"""Get display name for a stock symbol from cached stocks list.

	Args:
		symbol: Stock ticker symbol (e.g., "USDMXN")

	Returns:
		str: Display name if found, otherwise symbol

	Examples:
		"USDMXN" → "MXN" (if display_name is set)
		"CRM" → "CRM" (if no display_name)
	"""
	for stock in state.cached_stocks:
		if stock["symbol"] == symbol:
			return stock.get("display_name", symbol)
	return symbol

def show_stocks_display(duration, offset, rtc):
	"""Display stock/forex/crypto/commodity market data - 3 items at a time

	Display format by type:
	- Stock: Triangle arrows (▲▼) + ticker + percentage change (colored)
	- Forex: $ indicator + ticker + price (colored, with K/M suffix)
	- Crypto: $ indicator + ticker + price (colored, with K/M suffix)
	- Commodity: $ indicator + ticker + price (colored, with K/M suffix)

	Args:
		duration: How long to display in seconds
		offset: Starting index in stocks list (for rotation)
		rtc: Real-time clock object for market hours detection

	Returns:
		tuple: (success: bool, next_offset: int)
	"""
	state.memory_monitor.check_memory("stocks_display_start")

	# Check if stocks are configured
	if not state.cached_stocks:
		log_verbose("No stock symbols configured")
		return (False, offset)

	stocks_list = state.cached_stocks

	# Wrap offset if needed
	if offset >= len(stocks_list):
		offset = 0

	# Get 4 stocks to fetch (3 to display + 1 buffer for failures)
	stocks_to_fetch = []
	for i in range(4):
		idx = (offset + i) % len(stocks_list)
		stocks_to_fetch.append(stocks_list[idx])

	# Check market hours FIRST before attempting to fetch or display
	import time
	has_any_cached = len(state.cached_stock_prices) > 0

	# Respect market hours toggle (can be disabled for testing)
	if display_config.stocks_respect_market_hours:
		should_fetch, should_display, reason = is_market_hours_or_cache_valid(rtc.datetime, has_any_cached)

		if not should_display:
			# Markets closed and no valid cache - skip display entirely
			log_verbose(f"Stocks skipped: {reason}")
			return (False, offset)
	else:
		# Market hours check disabled - always fetch and display (testing mode)
		should_fetch = True
		should_display = True
		reason = "Market hours check disabled (testing mode)"
		log_verbose(reason)

	# Initialize stock_prices - will be either fresh or from cache
	stock_prices = {}

	if should_fetch:
		# Markets are open - fetch fresh prices with rate limiting
		current_time = time.monotonic()
		time_since_last_fetch = current_time - state.last_stock_fetch_time
		MIN_FETCH_INTERVAL = 65  # Seconds between API calls (rate limit is 8 credits/minute)

		if time_since_last_fetch < MIN_FETCH_INTERVAL and state.last_stock_fetch_time > 0:
			wait_time = MIN_FETCH_INTERVAL - time_since_last_fetch
			log_info(f"Rate limit: waiting {int(wait_time)}s before next fetch")
			time.sleep(wait_time)

		# Fetch prices for 4 stocks (3 to display + 1 buffer)
		log_verbose(f"Fetching prices for: {', '.join([s['symbol'] for s in stocks_to_fetch])}")
		stock_prices = fetch_stock_prices(stocks_to_fetch)
		state.last_stock_fetch_time = time.monotonic()

		# Cache the fetched prices and check for holiday
		if stock_prices:
			market_closed_detected = False
			for symbol, data in stock_prices.items():
				state.cached_stock_prices[symbol] = {
					"price": data["price"],
					"change_percent": data["change_percent"],
					"direction": data["direction"],
					"timestamp": time.monotonic()
				}
				# Check if market is closed (holiday detection)
				if not data.get("is_market_open", True):
					market_closed_detected = True

			# If market closed during business hours = holiday, cache for the day
			if market_closed_detected:
				today = f"{rtc.datetime.tm_year:04d}-{rtc.datetime.tm_mon:02d}-{rtc.datetime.tm_mday:02d}"
				state.market_holiday_date = today
				log_info(f"Market holiday detected and cached: {today}")
				# Only skip display if respecting market hours
				if display_config.stocks_respect_market_hours:
					return (False, offset)
				else:
					log_verbose("Holiday detected but market hours check disabled - continuing display")

			log_verbose(f"Cached {len(stock_prices)} stock prices ({reason})")
		else:
			log_info("Failed to fetch stock prices, skipping display")
			return (False, offset)
	else:
		# After hours - use cached prices
		log_verbose(f"Using cached stock prices ({reason})")
		stock_prices = state.cached_stock_prices

	# Build display data from fetched prices (with buffer tolerance)
	stocks_to_show = []
	failed_tickers = []
	for stock_symbol in stocks_to_fetch:
		symbol = stock_symbol["symbol"]
		if symbol in stock_prices:
			stocks_to_show.append({
				"symbol": symbol,
				"name": stock_symbol["name"],
				"type": stock_symbol.get("type", "stock"),  # Default to stock for backward compatibility
				"display_name": stock_symbol.get("display_name", symbol),  # Use symbol if no display_name
				"price": stock_prices[symbol]["price"],
				"change_percent": stock_prices[symbol]["change_percent"],
				"direction": stock_prices[symbol]["direction"]
			})
		else:
			failed_tickers.append(stock_symbol.get("display_name", symbol))
			log_warning(f"Failed to fetch ticker '{stock_symbol.get('display_name', symbol)}' ({symbol}) - check symbol is valid")

	# Progressive degradation: show 3 if available, 2 if only 2, skip if <2
	if len(stocks_to_show) < 2:
		if failed_tickers:
			log_info(f"Too many failed tickers ({len(failed_tickers)}/{len(stocks_to_fetch)}): {', '.join(failed_tickers)} - skipping display")
		else:
			log_info(f"Insufficient stock data ({len(stocks_to_show)}/{len(stocks_to_fetch)}), skipping display")
		return (False, offset)

	# Log if we had partial failures but are still displaying
	if failed_tickers:
		log_info(f"Buffer absorbed failures: {', '.join(failed_tickers)} not displayed this cycle")

	# Take only first 3 stocks (in case we got all 4)
	stocks_to_show = stocks_to_show[:3]

	# Calculate next offset (advance by 3, not 4, to avoid skipping tickers)
	# The 4th fetched ticker becomes the 1st of next cycle (buffer overlap)
	next_offset = (offset + 3) % len(stocks_list)

	# Build condensed log message with market status and stock/forex/crypto/commodity details
	detail_parts = []
	for s in stocks_to_show:
		display_name = s.get('display_name', s['symbol'])
		item_type = s.get('type', 'stock')
		if item_type == 'stock':
			# Stock: Show percentage change
			detail_parts.append(f"{display_name} {s['change_percent']:+.2f}%")
		else:
			# Forex/Crypto/Commodity: Show price with K/M suffix formatting
			formatted_price = format_price_with_suffix(s['price'])
			detail_parts.append(f"{display_name} {formatted_price}")
	stock_details = ", ".join(detail_parts)

	# Add market status to log if displaying cached data
	# Note: Show count out of fetched (4) to indicate buffer usage
	cache_status = "(fresh)" if should_fetch else "(cached)"
	if "CLOSED" in reason:
		log_info(f"Stocks ({len(stocks_to_show)}/{len(stocks_to_fetch)}), markets closed, displaying cached data: {stock_details} {cache_status}")
	else:
		log_info(f"Stocks ({len(stocks_to_show)}/{len(stocks_to_fetch)}): {stock_details} {cache_status}")

	clear_display()
	gc.collect()

	try:
		# Display stocks/forex in vertical rows (2-3 items depending on buffer success)
		# Row positions (dividing 32px height into 3 sections)
		row_positions = [2, 13, 24]  # Y positions for each row

		for i, stock in enumerate(stocks_to_show):
			if i >= 3:  # Max 3 items (stocks/forex) per display
				break

			y_pos = row_positions[i]
			item_type = stock.get("type", "stock")

			# Determine color based on direction
			if stock["direction"] == "up":
				color = state.colors["GREEN"]
			else:
				color = state.colors["RED"]

			# Format value based on type
			if item_type == "stock":
				# Stock: Show percentage change (e.g., "+2.3%")
				pct = stock["change_percent"]
				value_text = f"{pct:+.1f}%"
			else:
				# Forex/Crypto/Commodity: Show price with K/M suffix, no $ prefix
				# Examples: "86.9K", "18.49", "1234"
				value_text = format_price_with_suffix(stock['price'])

			# Calculate right-aligned position for value (1px margin from right edge)
			value_width = get_text_width(value_text, font)
			value_x = Display.WIDTH - value_width - 1  # Right-align with 1px margin

			# Create indicator (left side, centered with text)
			if item_type in ["forex", "crypto", "commodity"]:
				# Forex/Crypto/Commodity: Dollar sign indicator
				indicator_label = bitmap_label.Label(
					font,
					color=color,  # Use direction color
					text="$",
					x=1,
					y=y_pos
				)
				state.main_group.append(indicator_label)
			else:
				# Stock: Triangle arrow indicator
				if stock["direction"] == "up":
					# Up triangle: ▲ pointing upward
					arrow_triangle = Triangle(
						1, y_pos + 4,   # Bottom left
						3, y_pos + 1,   # Top peak
						5, y_pos + 4,   # Bottom right
						fill=color
					)
				else:
					# Down triangle: ▼ pointing downward
					arrow_triangle = Triangle(
						1, y_pos + 1,   # Top left
						3, y_pos + 4,   # Bottom peak
						5, y_pos + 1,   # Top right
						fill=color
					)
				state.main_group.append(arrow_triangle)

			# Ticker symbol (use display_name if available)
			display_text = stock.get("display_name", stock["symbol"])
			ticker_label = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=display_text,
				x=8,
				y=y_pos
			)
			state.main_group.append(ticker_label)

			# Value (percentage or price, right-aligned)
			# All types use direction-based coloring (green for up, red for down)
			value_label = bitmap_label.Label(
				font,
				color=color,
				text=value_text,
				x=value_x,
				y=y_pos
			)
			state.main_group.append(value_label)

		# Display for specified duration
		start_time = time.monotonic()
		while time.monotonic() - start_time < duration:
			interruptible_sleep(1)

	except Exception as e:
		log_error(f"Stocks display error: {e}")
		state.memory_monitor.check_memory("stocks_display_error")
		return (False, offset)

	gc.collect()
	state.memory_monitor.check_memory("stocks_display_complete")
	return (True, next_offset)

def get_stock_display_mode(stocks_list, offset):
	"""Determine if we should show chart or multi-stock based on highlight flags.

	Args:
		stocks_list: List of stock dicts with 'highlight' field
		offset: Current rotation offset

	Returns:
		tuple: (mode, ticker_or_stocks)
			mode: "chart" or "multi"
			ticker_or_stocks: symbol string (for chart) or None (for multi)
	"""
	if not stocks_list:
		return ("multi", None)

	# Wrap offset
	offset = offset % len(stocks_list)
	current_stock = stocks_list[offset]

	# Check if current stock is highlighted
	if current_stock.get("highlight", False):
		# Show chart for this highlighted stock
		return ("chart", current_stock["symbol"])

	# Current stock is NOT highlighted - check edge case
	# Edge case: All stocks are highlighted (shouldn't happen in normal rotation)
	# In this case, just show first stock as chart
	if all(s.get("highlight", False) for s in stocks_list):
		return ("chart", stocks_list[0]["symbol"])

	# Normal case: show multi-stock mode
	# The show_stocks_display function will handle fetching and display
	return ("multi", None)

def show_single_stock_chart(ticker, duration, rtc):
	"""
	Display single stock with intraday price chart using time series data.

	Layout:
	- Row 1 (y=1): Ticker symbol + percentage change
	- Row 2 (y=9): Current price
	- Chart area (y=16-31): Intraday price movement (16 pixels tall, 64 pixels wide)

	Args:
		ticker: Stock symbol to display (e.g., "CRM")
		duration: Display duration in seconds
		rtc: RTC object for timing

	Returns:
		bool: True if displayed, False if skipped
	"""
	import time
	from adafruit_display_shapes.line import Line

	INTRADAY_CACHE_MAX_AGE = 900  # 15 minutes (900 seconds)

	# Check if we need to fetch new data
	current_time = time.monotonic()
	should_fetch = True
	data_is_fresh = False

	if ticker in state.last_intraday_fetch_time:
		time_since_fetch = current_time - state.last_intraday_fetch_time[ticker]
		if time_since_fetch < INTRADAY_CACHE_MAX_AGE:
			should_fetch = False
			log_verbose("Using cached intraday data for " + ticker)

	# Fetch time series if needed
	if should_fetch:
		data_is_fresh = True
		log_info("Fetching intraday data for " + ticker)
		time_series = fetch_intraday_time_series(ticker, interval="15min", outputsize=26)

		if not time_series or len(time_series) == 0:
			log_warning("No intraday data available for " + ticker)
			return False

		# Note: We'll get the actual opening price from the quote API later
		# For now, just cache the time series data
		state.cached_intraday_data[ticker] = {
			"data": time_series,
			"timestamp": current_time
		}
		state.last_intraday_fetch_time[ticker] = current_time

	# Get cached data
	if ticker not in state.cached_intraday_data:
		log_warning("No cached data for " + ticker)
		return False

	cached = state.cached_intraday_data[ticker]
	time_series = cached["data"]

	# Fetch current quote for latest price and percentage
	quote_data = fetch_stock_prices([{"symbol": ticker, "name": ticker}])

	if ticker not in quote_data:
		log_warning("Could not fetch current quote for " + ticker)
		return False

	current_price = quote_data[ticker]["price"]
	change_percent = quote_data[ticker]["change_percent"]
	direction = quote_data[ticker]["direction"]
	actual_open_price = quote_data[ticker]["open_price"]

	# Get display name (uses display_name from stocks.csv if available)
	display_name = get_stock_display_name(ticker)

	# Use the actual day's percentage change from the quote API
	# This represents the change from market open (9:30 AM) to current price
	day_change_percent = change_percent

	# Determine color based on direction
	if day_change_percent >= 0:
		chart_color = state.colors["GREEN"]
		pct_color = state.colors["GREEN"]
	else:
		chart_color = state.colors["RED"]
		pct_color = state.colors["RED"]

	# Clear display
	clear_display()
	gc.collect()

	try:
		# Row 1 (y=1): Ticker + percentage
		ticker_label = bitmap_label.Label(
			font,
			text=display_name,
			color=state.colors["WHITE"],
			y=1
		)
		state.main_group.append(ticker_label)

		# Format percentage with + sign for positive values
		if day_change_percent >= 0:
			pct_text = "+" + "{:.2f}".format(day_change_percent) + "%"
		else:
			pct_text = "{:.2f}".format(day_change_percent) + "%"

		pct_label = bitmap_label.Label(
			font,
			text=pct_text,
			color=pct_color,
			x=64 - get_text_width(pct_text, font),  # Right-aligned
			y=1
		)
		state.main_group.append(pct_label)

		# Row 2 (y=9): Current price (format with commas if >= $1000, no cents)
		price_text = format_price_with_dollar(current_price)
		price_label = bitmap_label.Label(
			font,
			text=price_text,
			color=state.colors["WHITE"],
			# x=1,
			x=64 - get_text_width(price_text, font),  # Right-aligned
			y=9
		)
		state.main_group.append(price_label)

		# Chart area: y=16 to y=31 (16 pixels tall)
		CHART_HEIGHT = 15
		CHART_Y_START = 17
		CHART_WIDTH = 64

		# Find min and max prices for scaling
		prices = [point["close_price"] for point in time_series]
		min_price = min(prices)
		max_price = max(prices)
		price_range = max_price - min_price

		# Handle flat line (all prices the same)
		if price_range == 0:
			price_range = 1

		# Scale prices to chart height and spread across chart width
		data_points = []
		num_points = len(time_series)

		for i, point in enumerate(time_series):
			# X position: spread evenly across 64 pixels
			x = int((i / (num_points - 1)) * (CHART_WIDTH - 1)) if num_points > 1 else 0

			# Y position: scale price to chart height (inverted because y increases downward)
			price_scaled = (point["close_price"] - min_price) / price_range
			y = CHART_Y_START + CHART_HEIGHT - 1 - int(price_scaled * (CHART_HEIGHT - 1))

			data_points.append((x, y))

		# Draw lines connecting data points
		for i in range(len(data_points) - 1):
			x1, y1 = data_points[i]
			x2, y2 = data_points[i + 1]
			line = Line(x1, y1, x2, y2, color=chart_color)
			state.main_group.append(line)

		cache_status = "(fresh)" if data_is_fresh else "(cached)"
		log_info("Chart: " + display_name + " " + pct_text + " (" + price_text + ") with " + str(num_points) + " data points " + cache_status)

		# Hold display for duration
		time.sleep(duration)

		return True

	except Exception as e:
		log_error("Chart display error: " + str(e))
		traceback.print_exception(e)
		return False

	finally:
		gc.collect()

def show_forecast_display(current_data, forecast_data, display_duration, is_fresh=False):
	"""Optimized forecast display with smart precipitation detection"""
	
	# CRITICAL: Aggressive cleanup
	clear_display()
	gc.collect()
	state.memory_monitor.check_memory("forecast_display_start")
	
	# Check if we have real data
	if not current_data or not forecast_data or len(forecast_data) < 2:
		log_warning(f"Skipping forecast display - insufficient data")
		return False
	
	# Precipitation analysis - simple sequential logic
	current_has_precip = current_data.get('has_precipitation', False)
	forecast_indices = [0, 1]  # Default
	
	# Pre-extract precipitation flags (avoid nested access)
	precip_flags = [h.get('has_precipitation', False) for h in forecast_data[:6]]
	
	if current_has_precip:
		# Currently raining - find when it stops
		for i in range(len(precip_flags)):
			if not precip_flags[i]:
				forecast_indices = [i, min(i + 1, len(forecast_data) - 1)]
				log_debug(f"Rain stops at hour {i+1}")
				break
	else:
		# Not raining - find when it starts
		rain_start = -1
		rain_stop = -1
		
		for i in range(len(precip_flags)):
			if precip_flags[i] and rain_start == -1:
				rain_start = i
			elif not precip_flags[i] and rain_start != -1 and rain_stop == -1:
				rain_stop = i
				break
		
		if rain_start != -1:
			if rain_stop != -1:
				forecast_indices = [rain_start, rain_stop]
				log_debug(f"Rain: hour {rain_start+1} to {rain_stop+1}")
			else:
				forecast_indices = [rain_start, min(rain_start + 1, len(forecast_data) - 1)]
				log_debug(f"Rain starts at hour {rain_start+1}")
	
	# Simple duplicate hour check
	current_hour = state.rtc_instance.datetime.tm_hour
	first_forecast_hour = int(forecast_data[forecast_indices[0]]['datetime'][11:13]) % 24
	
	if first_forecast_hour == current_hour and forecast_indices[0] == 0 and len(forecast_data) >= 3:
		forecast_indices = [1, 2]
		log_debug(f"Adjusted to skip duplicate hour {current_hour}, Will show hours: {forecast_indices[0]+1} and {forecast_indices[1]+1}")
	
	clear_display()
	gc.collect()
	
	# LOG what we're about to display
	current_temp = round(current_data["feels_like"])
	next_temps = [round(h["feels_like"]) for h in forecast_data[:2]]
	status = "Fresh" if is_fresh else "Cached"
	log_info(f"Displaying Forecast: Current {current_temp}°C → Next: {next_temps[0]}°C, {next_temps[1]}°C ({display_duration/60:.0f} min) [{status}]")

	# Extract weather data (no exception handling needed for dict access with defaults)
	try:
		
		# Column 1 - feels-like temperature and icon
		col1_temp = f"{current_temp}°"
		col1_icon = f"{current_data['weather_icon']}.bmp"
		
		# Column 2 - feels-like temperature and icon
		col2_temp = f"{round(forecast_data[forecast_indices[0]]['feels_like'])}°"
		col2_icon = f"{forecast_data[forecast_indices[0]]['weather_icon']}.bmp"
		
		# Column 3 - feels-like temperature and icon
		col3_temp = f"{round(forecast_data[forecast_indices[1]]['feels_like'])}°"
		col3_icon = f"{forecast_data[forecast_indices[1]]['weather_icon']}.bmp"
		
		hour_plus_1 = int(forecast_data[forecast_indices[0]]['datetime'][11:13]) % System.HOURS_IN_DAY
		hour_plus_2 = int(forecast_data[forecast_indices[1]]['datetime'][11:13]) % System.HOURS_IN_DAY
		
		# Calculate actual hours from datetime strings
		current_hour = state.rtc_instance.datetime.tm_hour
		col2_hour = int(forecast_data[forecast_indices[0]]['datetime'][11:13]) % System.HOURS_IN_DAY
		col3_hour = int(forecast_data[forecast_indices[1]]['datetime'][11:13]) % System.HOURS_IN_DAY
		
		# Calculate hours ahead from current time (handle midnight wraparound)
		col2_hours_ahead = (col2_hour - current_hour) % System.HOURS_IN_DAY
		col3_hours_ahead = (col3_hour - current_hour) % System.HOURS_IN_DAY
		
		# Determine colors based on hour gaps
		# Default: both jumped ahead
		col2_color = state.colors["MINT"]
		col3_color = state.colors["MINT"]

		# Override if col2 is immediate
		if col2_hours_ahead <= 1:
			col2_color = state.colors["DIMMEST_WHITE"]
			col3_color = state.colors["DIMMEST_WHITE"]

		# Generate static time labels for columns 2 and 3
		col2_time = format_hour_12h(hour_plus_1)
		col3_time = format_hour_12h(hour_plus_2)
	except Exception as e:
		log_error(f"Forecast data extraction error: {e}")
		return False

	# Column positioning constants
	column_y = Layout.FORECAST_COLUMN_Y
	column_width = Layout.FORECAST_COLUMN_WIDTH
	time_y = Layout.FORECAST_TIME_Y
	temp_y = Layout.FORECAST_TEMP_Y

	# Load weather icon columns - NO parent try block (reduces nesting to 1 level)
	columns_data = [
		{"image": col1_icon, "x": Layout.FORECAST_COL1_X, "temp": col1_temp},
		{"image": col2_icon, "x": Layout.FORECAST_COL2_X, "temp": col2_temp},
		{"image": col3_icon, "x": Layout.FORECAST_COL3_X, "temp": col3_temp}
	]

	for i, col in enumerate(columns_data):
		# Try primary weather icon
		bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{col['image']}")

		# Try blank if primary failed (check return value, not exception)
		if bitmap is None:
			log_warning(f"Forecast column {i+1} image {col['image']} failed, trying blank")
			bitmap, palette = state.image_cache.get_image(Paths.BLANK_COLUMN)
			if bitmap is None:
				log_error(f"Blank fallback failed for column {i+1}, skipping column")
				continue

		# Create and add column
		col_img = displayio.TileGrid(bitmap, pixel_shader=palette)
		col_img.x = col["x"]
		col_img.y = column_y
		state.main_group.append(col_img)

	# Create and display labels - wrap in try block for display errors
	try:
		# Create time labels - only column 1 will be updated
		col1_time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			x=max(center_text("00:00", font, Layout.FORECAST_COL1_X, column_width), 1),  # Initial placeholder
			y=time_y
		)
		
		# Use these colors in the labels
		col2_time_label = bitmap_label.Label(
			font,
			color=col2_color,
			text=col2_time,
			x=max(center_text(col2_time, font, Layout.FORECAST_COL2_X, column_width), 1),
			y=time_y
		)
		
		col3_time_label = bitmap_label.Label(
			font,
			color=col3_color,
			text=col3_time,
			x=max(center_text(col3_time, font, Layout.FORECAST_COL3_X, column_width), 1),
			y=time_y
		)
		
		# Add time labels to display
		state.main_group.append(col1_time_label)
		state.main_group.append(col2_time_label)
		state.main_group.append(col3_time_label)
		
		# Create temperature labels (all static)
		for col in columns_data:
			centered_x = center_text(col["temp"], font, col["x"], column_width) + 1
			
			temp_label = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=col["temp"],
				x=centered_x,
				y=temp_y
			)
			state.main_group.append(temp_label)

		# Add day indicator if enabled
		add_weekday_indicator_if_enabled(state.main_group, state.rtc_instance, "Forecast")
		
		
		# Display update loop - update column 1 time only when minute changes
		start_time = time.monotonic()
		loop_count = 0
		last_minute = -1

		while time.monotonic() - start_time < display_duration:
			loop_count += 1

			# Update first column time only when minute changes
			if not state.rtc_instance:
				# Memory check and continue
				if loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:
					state.memory_monitor.check_memory(f"forecast_display_loop_{loop_count}")
				interruptible_sleep(1)
				continue

			# RTC available - check minute change
			current_hour = state.rtc_instance.datetime.tm_hour
			current_minute = state.rtc_instance.datetime.tm_min

			if current_minute != last_minute:
				display_hour = get_12h_hour(current_hour)
				new_time = f"{display_hour}:{current_minute:02d}"

				# Update ONLY the first column time text
				col1_time_label.text = new_time
				# Recenter the text
				col1_time_label.x = max(center_text(new_time, font, Layout.FORECAST_COL1_X, column_width), 1)

				last_minute = current_minute

			# Memory monitoring and cleanup
			if loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:
				needs_gc = display_duration > Timing.GC_INTERVAL and loop_count % Timing.GC_INTERVAL == 0
				if needs_gc:
					gc.collect()
					state.memory_monitor.check_memory(f"forecast_display_gc_{loop_count//System.SECONDS_PER_HOUR}")
				else:
					state.memory_monitor.check_memory(f"forecast_display_loop_{loop_count}")

			interruptible_sleep(1)
	
	except Exception as e:
		log_error(f"Forecast display error: {e}")
		state.memory_monitor.check_memory("forecast_display_error")
		return False
	
	gc.collect()
	state.memory_monitor.check_memory("forecast_display_complete")
	return True
	
def calculate_display_durations(rtc):
	"""Calculate current weather duration based on cycle and forecast times"""
	
	# Check if there are events today
	event_count, _ = get_today_events_info(rtc)
	event_time = Timing.DEFAULT_EVENT if event_count > 0 else 0
	
	# Current weather gets the remaining time
	current_weather_time = Timing.DEFAULT_CYCLE - Timing.DEFAULT_FORECAST - event_time
	
	# Ensure minimum time for current weather
	if current_weather_time < Timing.MIN_EVENT_DURATION:
		current_weather_time = Timing.MIN_EVENT_DURATION
		log_warning(f"Current weather time adjusted to minimum: {current_weather_time}s")
	
	return current_weather_time, Timing.DEFAULT_FORECAST, event_time

def create_progress_bar_tilegrid():
	"""Create a TileGrid-based progress bar with tick marks"""
	# Progress bar dimensions
	bar_width = Layout.PROGRESS_BAR_HORIZONTAL_WIDTH
	bar_height = Layout.PROGRESS_BAR_HORIZONTAL_HEIGHT
	tick_height_above = 2
	tick_height_below = 1
	total_height = tick_height_above + bar_height + tick_height_below  # 5px total
	
	# Bar position within bitmap
	bar_y_start = tick_height_above  # Bar starts at row 2
	bar_y_end = bar_y_start + bar_height  # Bar ends at row 4
	
	# Create bitmap
	progress_bitmap = displayio.Bitmap(bar_width, total_height, 4)
	
	# Create palette
	progress_palette = displayio.Palette(4)
	progress_palette[0] = state.colors["BLACK"]
	progress_palette[1] = state.colors["LILAC"]  # Elapsed
	progress_palette[2] = state.colors["MINT"]   # Remaining
	progress_palette[3] = state.colors["WHITE"]  # Tick marks
	
	# Initialize with black background
	for y in range(total_height):
		for x in range(bar_width):
			progress_bitmap[x, y] = 0
	
	# Fill bar area with "remaining" color
	for y in range(bar_y_start, bar_y_end):
		for x in range(bar_width):
			progress_bitmap[x, y] = 2
	
	# Add tick marks at 0%, 25%, 50%, 75%, 100%
	tick_positions = [0, bar_width // 4, bar_width // 2, 3 * bar_width // 4, bar_width - 1]
	
	for pos in tick_positions:
		# Major ticks (start, middle, end) get 2px above
		if pos == 0 or pos == bar_width // 2 or pos == bar_width - 1:
			progress_bitmap[pos, 0] = 3
			progress_bitmap[pos, 1] = 3
		else:  # Minor ticks (25%, 75%) get 1px above
			progress_bitmap[pos, 1] = 3
		
		# All ticks get 1px below
		progress_bitmap[pos, bar_y_end] = 3
	
	# Create TileGrid
	progress_grid = displayio.TileGrid(
		progress_bitmap,
		pixel_shader=progress_palette,
		x=Layout.PROGRESS_BAR_HORIZONTAL_X,
		y=Layout.PROGRESS_BAR_HORIZONTAL_Y - tick_height_above
	)
	
	return progress_grid, progress_bitmap

def update_progress_bar_bitmap(progress_bitmap, elapsed_seconds, total_seconds):
	"""Update progress bar bitmap (fills left to right as time elapses)"""
	if total_seconds <= 0:
		return
	
	# Calculate elapsed pixels
	elapsed_ratio = min(1.0, elapsed_seconds / total_seconds)
	elapsed_width = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * elapsed_ratio)
	
	# Bar position (rows 2-3 in the 5-row bitmap)
	bar_y_start = 2
	bar_y_end = 4
	
	# Update only the bar area
	for y in range(bar_y_start, bar_y_end):
		for x in range(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH):
			if x < elapsed_width:
				progress_bitmap[x, y] = 1  # Elapsed (LILAC)
			else:
				progress_bitmap[x, y] = 2  # Remaining (MINT)
		
def get_schedule_progress():
	"""
	Calculate progress for active schedule session
	Returns: (elapsed_seconds, total_duration, progress_ratio) or (None, None, None)
	"""
	if not state.active_schedule_name or not state.active_schedule_start_time:
		return None, None, None
	
	current_time = time.monotonic()
	
	# Check if schedule has expired
	if state.active_schedule_end_time and current_time >= state.active_schedule_end_time:
		# Schedule is over - clear session
		log_debug(f"Schedule session ended: {state.active_schedule_name}")
		state.active_schedule_name = None
		state.active_schedule_start_time = None
		state.active_schedule_end_time = None
		state.active_schedule_segment_count = 0
		return None, None, None
	
	elapsed = current_time - state.active_schedule_start_time
	total_duration = state.active_schedule_end_time - state.active_schedule_start_time
	progress_ratio = elapsed / total_duration if total_duration > 0 else 0
	
	return elapsed, total_duration, progress_ratio

def show_scheduled_display(rtc, schedule_name, schedule_config, total_duration, current_data=None):
	"""
	Display scheduled message for one segment (max 5 minutes)
	Supports multi-segment schedules by tracking overall progress
	"""
	
	# Calculate how long this segment should display
	elapsed, full_duration, progress = get_schedule_progress()
	
	if elapsed is None:
		# First segment of schedule - initialize session
		state.active_schedule_name = schedule_name
		state.active_schedule_start_time = time.monotonic()
		state.active_schedule_end_time = state.active_schedule_start_time + total_duration
		state.active_schedule_segment_count = 0  # Reset segment counter
		elapsed = 0
		full_duration = total_duration
		progress = 0

		log_info(f"Starting schedule session: {schedule_name} ({total_duration}s total)")

	else:
		log_debug(f"Continuing schedule: {schedule_name} (elapsed: {elapsed:.0f}s / {full_duration:.0f}s)")

	# Increment segment count
	state.active_schedule_segment_count += 1
	log_debug(f"Schedule segment #{state.active_schedule_segment_count}")

	# This segment duration: min(5 minutes, remaining time)
	remaining = full_duration - elapsed
	segment_duration = min(Timing.SCHEDULE_SEGMENT_DURATION, remaining)

	log_debug(f"Segment duration: {segment_duration}s (remaining: {remaining:.0f}s)")

	# Light cleanup before segment (keep session alive for connection reuse)
	gc.collect()
	clear_display()

	# Fetch weather data (separate try block for data fetching)
	try:
		# Fetch weather if not provided
		if not current_data:
			# Smart caching: check cache first before fetching
			current_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)

			if current_data:
				log_debug("Using fresh cached weather (< 15 minutes old)")
				is_cached = True
			else:
				# Cache stale or missing - fetch new data
				log_debug("Cache stale or missing - fetching fresh weather")
				current_data = fetch_current_weather_only()
				is_cached = False

		else:
			# current_data was provided as parameter
			is_cached = False

		if not current_data:
			# No weather data available, skip weather section
			log_warning("No weather data - Display schedule + clock only")
			is_cached = False

	except Exception as e:
		log_error(f"Schedule weather fetch error: {e}")
		current_data = None
		is_cached = False

	# Check if we should hide elements during night mode (used by weather and weekday sections)
	is_night_mode = schedule_name in ["Night Mode AM", "Night Mode"]

	# === WEATHER SECTION (CONDITIONAL) - No parent try block ===
	if current_data:
		# Extract weather data
		temperature = f"{round(current_data['feels_like'])}°"
		weather_icon = f"{current_data['weather_icon']}.bmp"
		uv_index = current_data['uv_index']

		# Add UV bar if present
		if uv_index > 0:
			uv_length = calculate_uv_bar_length(uv_index)
			for i in range(uv_length):
				if i not in Visual.UV_SPACING_POSITIONS:
					uv_pixel = Line(
						Layout.SCHEDULE_LEFT_MARGIN_X + i,
						Layout.SCHEDULE_UV_Y,
						Layout.SCHEDULE_LEFT_MARGIN_X + i,
						Layout.SCHEDULE_UV_Y,
						state.colors["DIMMEST_WHITE"]
					)
					state.main_group.append(uv_pixel)

		y_offset = Layout.SCHEDULE_X_OFFSET if uv_index > 0 else 0

		# Determine if weather icon should be shown based on night mode setting
		show_weather_icon = not (display_config.night_mode_minimal_display and is_night_mode)

		if current_data and show_weather_icon:
			# Load weather icon - fallback to blank
			bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{weather_icon}")
	
			# Try blank if primary failed (check return value, not exception)
			if bitmap is None:
				log_warning(f"Schedule weather icon {weather_icon} failed, trying blank")
				bitmap, palette = state.image_cache.get_image(Paths.BLANK_COLUMN)
				if bitmap is None:
					log_error(f"Schedule weather blank fallback failed, skipping icon")
	
			# Add icon if successfully loaded
			if bitmap:
				weather_img = displayio.TileGrid(bitmap, pixel_shader=palette)
				weather_img.x = Layout.SCHEDULE_LEFT_MARGIN_X
				weather_img.y = Layout.SCHEDULE_W_IMAGE_Y + y_offset
				state.main_group.append(weather_img)

		# Set temperature color based on cache status
		temp_color = state.colors["LILAC"] if is_cached else state.colors["DIMMEST_WHITE"]

		# Temp Labels

		temp_label = bitmap_label.Label(
			font,
			color=temp_color,
			text=temperature,
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.SCHEDULE_TEMP_Y + y_offset
		)
		state.main_group.append(temp_label)

	# === SCHEDULE IMAGE (ALWAYS) - Skip schedule if image fails ===
	try:
		bitmap, palette = state.image_cache.get_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
		schedule_img = displayio.TileGrid(bitmap, pixel_shader=palette)
		schedule_img.x = Layout.SCHEDULE_IMAGE_X
		schedule_img.y = Layout.SCHEDULE_IMAGE_Y
		state.main_group.append(schedule_img)
		state.tracker.reset_display_errors()
	except Exception as e:
		log_warning(f"Failed to load schedule image {schedule_config['image']}, skipping schedule display")
		state.tracker.record_display_error()
		if state.tracker.scheduled_display_error_count >= 3:
			log_error(f"Too many schedule errors ({state.tracker.scheduled_display_error_count}), disabling schedules")
			display_config.show_scheduled_displays = False
		return  # Skip schedule, return to normal cycle

	# === CLOCK LABEL AND DISPLAY LOOP - wrap in try for display errors ===
	try:
		# === CLOCK LABEL (ALWAYS) ===
		time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.FORECAST_TIME_Y
		)
		state.main_group.append(time_label)

		# === WEEKDAY INDICATOR (IF ENABLED) ===
		# Check if we should hide weekday indicator during night mode
		show_weekday = not (display_config.night_mode_minimal_display and is_night_mode)
		if show_weekday:
			add_weekday_indicator_if_enabled(state.main_group, rtc, "Schedule")
			
		# LOG what's being displayed this segment
		segment_num = int(elapsed / Timing.SCHEDULE_SEGMENT_DURATION) + 1
		total_segments = int(full_duration / Timing.SCHEDULE_SEGMENT_DURATION) + (1 if full_duration % Timing.SCHEDULE_SEGMENT_DURATION else 0)

		state.schedule_just_ended = (segment_num >= total_segments)
		
		if current_data:
			cache_indicator = " [CACHED]" if is_cached else ""
			log_info(f"Displaying Schedule: {schedule_name} - Segment {segment_num}/{total_segments} ({temperature}, {segment_duration/60:.1f} min, progress: {progress*100:.0f}%){cache_indicator}")
		else:
			log_info(f"Displaying Schedule: {schedule_name} - Segment {segment_num}/{total_segments} (Weather Skipped, progress: {progress*100:.0f}%)")
		
		# Mark display as successful
		state.tracker.record_display_success()
		
		# === PROGRESS BAR ===
		## Progress bar - based on FULL schedule progress, not segment
		if schedule_config.get("progressbar", True):
			progress_grid, progress_bitmap = create_progress_bar_tilegrid()
			
			# Pre-fill progress bar based on elapsed time using existing function
			if progress > 0:
				update_progress_bar_bitmap(progress_bitmap, elapsed, full_duration)
				log_debug(f"Pre-filled progress bar to {progress*100:.0f}%")
			
			state.main_group.append(progress_grid)
			show_progress_bar = True
		else:
			progress_grid = None
			progress_bitmap = None
			show_progress_bar = False
		
		# === DISPLAY LOOP ===
		segment_start = time.monotonic()
		last_minute = -1
		last_displayed_column = -1
		
		# Adaptive sleep for smooth updates
		sleep_interval = max(Timing.MIN_SLEEP_INTERVAL, min(segment_duration / 60, Timing.MAX_SLEEP_INTERVAL))  # 1-5 seconds
		
		while time.monotonic() - segment_start < segment_duration:
			current_minute = rtc.datetime.tm_min
			current_time = time.monotonic()
			
			# Calculate OVERALL progress (from schedule start, not segment start)
			overall_elapsed = elapsed + (current_time - segment_start)
			overall_progress = overall_elapsed / full_duration
			current_column = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * overall_progress)
			
			# Update progress bar
			if show_progress_bar and current_column != last_displayed_column and current_column < Layout.PROGRESS_BAR_HORIZONTAL_WIDTH:
				update_progress_bar_bitmap(progress_bitmap, overall_elapsed, full_duration)
				last_displayed_column = current_column
			
			# Update clock
			if current_minute != last_minute:
				hour = rtc.datetime.tm_hour
				display_hour = get_12h_hour(hour)
				time_label.text = f"{display_hour}:{current_minute:02d}"
				last_minute = current_minute
			
			time.sleep(sleep_interval)
		
		log_debug(f"Segment complete")
		
	except Exception as e:
		log_error(f"Scheduled display segment error: {e}")
		
		# CRITICAL: Add delay to prevent runaway loops on errors

		# Safety: If too many errors in a row, take a break
		if state.tracker.consecutive_display_errors >= 5:
			log_error("Too many consecutive errors - safe mode")
			safe_duration = Timing.CLOCK_DISPLAY_DURATION  # 5 minutes
		else:
			# If segment_duration is very small or 0, use minimum 30 seconds
			safe_duration = max(Timing.ERROR_SAFETY_DELAY, segment_duration)
		
		show_clock_display(rtc, safe_duration)
	
	finally:
		# Cleanup after segment
		gc.collect()
		
		# Return segment info
		# return is_last_segment # Boolean - is this last segment of schedule display

### SYSTEM MANAGEMENT ###

def check_daily_reset(rtc):
	"""Handle daily reset and cleanup operations"""
	if not DAILY_RESET_ENABLED:
		return
	
	current_time = time.monotonic()
	hours_running = (current_time - state.startup_time) / System.SECONDS_PER_HOUR
	
	# Scheduled restart conditions
	should_restart = (
		hours_running > System.HOURS_BEFORE_DAILY_RESTART or
		(hours_running > System.MINIMUM_RUNTIME_BEFORE_RESTART and 
		rtc.datetime.tm_hour == Timing.DAILY_RESET_HOUR and 
		rtc.datetime.tm_min < System.RESTART_GRACE_MINUTES)
	)
	
	if should_restart:
		log_info(f"Daily restart triggered ({hours_running:.1f}h runtime)")
		interruptible_sleep(API.RETRY_DELAY)
		supervisor.reload()
		
def calculate_weekday(year, month, day):
	"""
	Calculate day of the week using Zeller's congruence algorithm
	Returns: 0=Monday, 1=Tuesday, ..., 6=Sunday (to match tm_wday format)
	"""
	# Zeller's congruence requires January and February to be counted as months 13 and 14 of the previous year
	if month < 3:
		month += 12
		year -= 1
	
	# Zeller's formula
	q = day
	m = month
	k = year % 100
	j = year // 100
	
	h = (q + ((13 * (m + 1)) // 5) + k + (k // 4) + (j // 4) - 2 * j) % 7
	
	# Convert Zeller's result (0=Saturday) to tm_wday format (0=Monday)
	# Zeller: 0=Sat, 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri
	# tm_wday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
	weekday_conversion = {0: 5, 1: 6, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4}
	return weekday_conversion[h]
		
def calculate_yearday(year, month, day):
	"""Calculate day of year (1-366)"""
	days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
	
	# Check for leap year
	if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
		days_in_month[1] = 29
	
	return sum(days_in_month[:month-1]) + day
		
def update_rtc_datetime(rtc, new_year=None, new_month=None, new_day=None, new_hour=None, new_minute=None):
	"""Update RTC date and optionally time"""
	try:
		current_dt = rtc.datetime
		
		# Use current time if not specified
		new_year = new_year if new_year is not None else current_dt.tm_year
		new_month = new_month if new_month is not None else current_dt.tm_mon
		new_day = new_day if new_day is not None else current_dt.tm_mday
		new_hour = new_hour if new_hour is not None else current_dt.tm_hour
		new_minute = new_minute if new_minute is not None else current_dt.tm_min
		
		# Validate inputs
		if not (1 <= new_month <= 12):
			log_error(f"Invalid month: {new_month}. Must be 1-12.")
			return False
			
		if not (1 <= new_day <= 31):
			log_error(f"Invalid day: {new_day}. Must be 1-31.")
			return False
			
		# Calculate correct weekday and yearday
		new_weekday = calculate_weekday(new_year, new_month, new_day)
		new_yearday = calculate_yearday(new_year, new_month, new_day)
		
		# Create new datetime with updated month/day
		new_datetime = time.struct_time((
			new_year, new_month, new_day,
			new_hour, new_minute, current_dt.tm_sec,
			new_weekday, new_yearday, current_dt.tm_isdst
		))
		
		rtc.datetime = new_datetime
		log_debug(f"RTC updated to {new_year:04d}/{new_month:02d}/{new_day:02d} {new_hour:02d}:{new_minute:02d}")
		return True
	except Exception as e:
		log_error(f"Failed to update RTC: {e}")
		return False


### MAIN PROGRAM - HELPER FUNCTIONS ###
		
def initialize_system(rtc):
	"""Initialize all hardware and load configuration"""
	log_info("=== STARTUP ===")
	
	# Log debug level
	level_names = {0: "NONE", 1: "ERROR", 2: "WARNING", 3: "INFO", 4: "DEBUG", 5: "VERBOSE"}
	log_info(f"Debug level: {level_names.get(CURRENT_DEBUG_LEVEL, 'UNKNOWN')} ({CURRENT_DEBUG_LEVEL})")
	
	# Initialize hardware
	initialize_display()

	# Initialize built-in buttons (optional)
	setup_buttons()

	# Detect matrix type and initialize colors
	matrix_type = detect_matrix_type()
	state.colors = get_matrix_colors()
	state.memory_monitor.check_memory("hardware_init_complete")
	
	# Handle test date if configured
	if display_config.use_test_date:
		update_rtc_datetime(rtc, TestData.TEST_YEAR, TestData.TEST_MONTH, TestData.TEST_DAY, TestData.TEST_HOUR, TestData.TEST_MINUTE)
	
	# Fetch events, schedules, and stocks from GitHub
	log_debug("Fetching data from GitHub...")
	github_events, github_schedules, schedule_source, github_stocks = fetch_github_data(rtc)

	# Initialize events - DON'T set state.cached_events yet, let load_all_events() handle it
	# But store github_events temporarily so load_all_events() can access it
	if github_events:
		# Store in a temporary location for load_all_events() to use
		state._github_events_temp = github_events
		log_debug(f"GitHub events: {len(github_events)} event dates")
	else:
		log_warning("Failed to fetch events from GitHub")
		state._github_events_temp = None

	# Initialize stocks
	if github_stocks:
		state.cached_stocks = github_stocks
		log_debug(f"GitHub stocks: {len(github_stocks)} ticker(s)")
	else:
		log_warning("Failed to fetch stocks from GitHub, loading local stocks.csv")
		state.cached_stocks = load_stocks_from_csv()
	
	# Load all events (this will merge GitHub + permanent and set counters)
	events = load_all_events()
	
	# Clear temporary storage
	state._github_events_temp = None
	
	# Cache the merged events
	state.cached_events = events
	
	# Initialize schedules and track source
	schedule_source_flag = ""
	if github_schedules:
		scheduled_display.schedules = github_schedules
		scheduled_display.schedules_loaded = True
		scheduled_display.last_fetch_date = f"{rtc.datetime.tm_year:04d}-{rtc.datetime.tm_mon:02d}-{rtc.datetime.tm_mday:02d}"
		
		# Set flag based on source
		if schedule_source == "date-specific":
			schedule_source_flag = " (imported)"
		elif schedule_source == "default":
			schedule_source_flag = " (default)"
		
		log_debug(f"GitHub schedules: {len(github_schedules)} schedule(s) ({schedule_source})")
	else:
		log_warning("Failed to fetch schedules from GitHub, trying local file")
		local_schedules = load_schedules_from_csv()
		if local_schedules:
			scheduled_display.schedules = local_schedules
			scheduled_display.schedules_loaded = True
			scheduled_display.last_fetch_date = f"{rtc.datetime.tm_year:04d}-{rtc.datetime.tm_mon:02d}-{rtc.datetime.tm_mday:02d}"
			schedule_source_flag = " (local)"
			log_debug(f"Local schedules: {len(local_schedules)} schedule(s)")
		else:
			log_warning("No schedules available")

	# Initialize stocks and track source
	stock_source_flag = ""
	if github_stocks:
		state.cached_stocks = github_stocks
		stock_source_flag = " (imported)"
		log_info(f"GitHub stocks: {len(github_stocks)} symbols")
	else:
		log_verbose("Failed to fetch stocks from GitHub, trying local file")
		local_stocks = load_stocks_from_csv()
		if local_stocks:
			state.cached_stocks = local_stocks
			stock_source_flag = " (local)"
			log_info(f"Local stocks: {len(local_stocks)} symbols")
		else:
			log_verbose("No stocks available")
			state.cached_stocks = []

	# Load display configuration
	log_debug("Loading display configuration...")

	# Try GitHub first
	github_config = fetch_display_config_from_github()
	if github_config:
		apply_display_config(github_config)
		log_debug(f"Display config loaded from GitHub")
	else:
		# Fallback to local file
		local_config = load_display_config_from_csv("display_config.csv")
		if local_config:
			apply_display_config(local_config)
			log_info(f"Display config loaded from local file")
		else:
			log_debug("No display config file found, using defaults")

	# Get event counts for today
	total_today, all_today_events = get_today_all_events_info(rtc)
	active_now, _ = get_today_events_info(rtc)
	
	# Format event count message
	if total_today == 0:
		today_msg = "No events"
	elif total_today == active_now:
		today_msg = f"{total_today} event{'s' if total_today > 1 else ''}"
	else:
		today_msg = f"{total_today} event{'s' if total_today > 1 else ''} ({active_now} active now)"
	
	# Format imported events count
	imported_str = f" ({state.ephemeral_event_count} imported)" if state.ephemeral_event_count > 0 else ""

	# Summary log
	schedule_count = len(scheduled_display.schedules) if scheduled_display.schedules_loaded else 0
	stock_count = len(state.cached_stocks) if state.cached_stocks else 0

	# Check market status for stocks display
	if stock_count > 0:
		_, should_display, market_reason = is_market_hours_or_cache_valid(rtc.datetime, False)
		if not should_display:
			# Provide specific message based on why markets are closed
			if "Weekend" in market_reason:
				stock_source_flag += f" (markets closed - weekend)"
			elif "holiday" in market_reason:
				stock_source_flag += f" (markets closed - holiday)"
			elif "Before market open" in market_reason:
				stock_source_flag += f" (markets open 9:30 AM ET)"
			else:
				stock_source_flag += f" (markets closed today)"

	log_info(f"Hardware ready | {schedule_count} schedules{schedule_source_flag} | {stock_count} stocks{stock_source_flag} | {state.total_event_count} events{imported_str} | Today: {today_msg}")
	state.memory_monitor.check_memory("initialization_complete")
	
	return events

def setup_network_and_time(rtc):
	"""Setup WiFi and synchronize time"""
	wifi_connected = setup_wifi_with_recovery()
	location_info = None  # Initialize at the start
	
	if wifi_connected and not display_config.use_test_date:
		location_info = sync_time_with_timezone(rtc)
	elif display_config.use_test_date:
		log_info(f"Manual Time Set: {rtc.datetime.tm_year:04d}/{rtc.datetime.tm_mon:02d}/{rtc.datetime.tm_mday:02d} {rtc.datetime.tm_hour:02d}:{rtc.datetime.tm_min:02d}")
		# location_info stays None
	else:
		log_warning("Starting without WiFi - using RTC time only")
		# location_info stays None
	
	return location_info  # Always return (either dict or None)

def handle_extended_failure_mode(rtc, time_since_success):
	"""Handle extended failure mode with periodic recovery attempts"""
	# Log entry into extended failure mode (only once)
	if not state.tracker.in_extended_failure_mode:
		log_warning(f"ENTERING extended failure mode after {int(time_since_success/System.SECONDS_PER_MINUTE)} minutes without success")
		state.tracker.in_extended_failure_mode = True
	
	log_debug(f"Extended failure mode active ({int(time_since_success/System.SECONDS_PER_MINUTE)}min since success) - showing clock only")
	show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
	
	# Periodically retry (every ~30 minutes)
	if int(time_since_success) % Timing.API_RECOVERY_RETRY_INTERVAL < Timing.DEFAULT_CYCLE:
		log_verbose("Attempting API recovery from extended failure mode...")
		current_data, forecast_data = fetch_current_and_forecast_weather()
		if current_data:
			log_info("API recovery successful!")
			return True  # Signal recovery
	
	return False  # Still in failure mode
	
def fetch_cycle_data(rtc):
	"""Fetch all data needed for this display cycle"""
	current_data = None
	forecast_data = None
	
	needs_fresh_forecast = should_fetch_forecast() and display_config.show_forecast
	
	if needs_fresh_forecast:
		current_data, forecast_data = fetch_current_and_forecast_weather()
		if forecast_data:
			state.cached_forecast_data = forecast_data
			state.last_forecast_fetch = time.monotonic()
	else:
		# Fetch current weather if needed for weather OR forecast display
		# (forecast needs current data for first column)
		if (display_config.show_weather or display_config.show_forecast) and not display_config.use_live_weather:
			current_data = TestData.DUMMY_WEATHER_DATA
			log_debug("Using DUMMY weather data")
		elif display_config.show_weather or display_config.show_forecast:
			# Fetch current weather (needed by both weather and forecast displays)
			current_data = fetch_current_weather()

		forecast_data = state.cached_forecast_data
	
	# Return fresh flag along with data
	return current_data, forecast_data, needs_fresh_forecast

def _check_rapid_cycling(cycle_count):
	"""Helper: Detect and handle rapid cycling (Category A2)"""
	if cycle_count <= 1:
		return False

	time_since_startup = time.monotonic() - state.startup_time
	avg_cycle_time = time_since_startup / cycle_count

	if avg_cycle_time >= Timing.FAST_CYCLE_THRESHOLD or cycle_count <= 10:
		return False

	log_error(f"Rapid cycling detected ({avg_cycle_time:.1f}s/cycle) - restarting")
	interruptible_sleep(Timing.RESTART_DELAY)
	supervisor.reload()
	return True

def _ensure_wifi_available(rtc):
	"""Helper: Check WiFi with recovery attempt (Category A2)"""
	if is_wifi_connected():
		return True

	log_debug("WiFi disconnected, attempting recovery...")
	if check_and_recover_wifi():
		return True

	log_warning("No WiFi - showing clock")
	show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
	return False

def _check_failure_mode(rtc):
	"""Helper: Check and handle extended failure mode (Category A2)"""
	time_since_success = time.monotonic() - state.tracker.last_successful_display
	in_failure_mode = time_since_success > Timing.EXTENDED_FAILURE_THRESHOLD

	# Exit failure mode if recovered
	if not in_failure_mode and state.tracker.in_extended_failure_mode:
		log_info("EXITING extended failure mode")
		state.tracker.in_extended_failure_mode = False
		return False

	if in_failure_mode:
		handle_extended_failure_mode(rtc, time_since_success)
		return True

	return False

def _run_scheduled_cycle(rtc, cycle_count, cycle_start_time):
	"""Helper: Handle scheduled display if active (Category A2)"""
	if not display_config.show_scheduled_displays:
		log_debug("Scheduled displays disabled due to errors")
		return False

	schedule_name, schedule_config = scheduled_display.get_active_schedule(rtc)
	if not schedule_name:
		return False

	# Fetch weather for segment (with smart caching)
	# Check cache first - only fetch if cache is stale (> 15 minutes)
	current_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)

	if current_data:
		log_debug("Using fresh cached weather for schedule cycle")
	else:
		log_debug("Cache stale or missing - fetching fresh weather for schedule cycle")
		current_data = fetch_current_weather_only()
		if current_data:
			state.tracker.record_weather_success()  # Weather-related display

	# Display schedule segment
	display_duration = get_remaining_schedule_time(rtc, schedule_config)
	segment_start = time.monotonic()

	show_scheduled_display(rtc, schedule_name, schedule_config, display_duration, current_data)

	# Fast cycle protection
	segment_elapsed = time.monotonic() - segment_start
	if segment_elapsed < Timing.FAST_CYCLE_THRESHOLD:
		log_error(f"Schedule cycle suspiciously fast ({segment_elapsed:.1f}s) - adding delay")
		time.sleep(Timing.ERROR_SAFETY_DELAY)

	# Check for events between schedules
	log_debug(f"LAST SEGMENT -> {state.schedule_just_ended}")
	if state.schedule_just_ended and display_config.show_events_in_between_schedules and display_config.show_events:
		cleanup_global_session()
		gc.collect()
		show_event_display(rtc, 30)
		cleanup_global_session()
		gc.collect()

	# Log cycle summary
	cycle_duration = time.monotonic() - cycle_start_time
	mem_stats = state.memory_monitor.get_memory_stats()
	log_info(f"Cycle #{cycle_count} (SCHEDULED) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | UT: {state.memory_monitor.get_runtime()} | Mem: {mem_stats['usage_percent']:.1f}% | API: {state.tracker.get_api_stats()}\n")
	return True

def _run_normal_cycle(rtc, cycle_count, cycle_start_time):
	"""Helper: Run normal display cycle (Category A2)"""
	something_displayed = False

	# Fetch data once
	current_data, forecast_data, forecast_is_fresh = fetch_cycle_data(rtc)
	current_duration, forecast_duration, event_duration = calculate_display_durations(rtc)

	# Forecast display
	forecast_shown = False
	if display_config.show_forecast and current_data and forecast_data:
		forecast_shown = show_forecast_display(current_data, forecast_data, forecast_duration, forecast_is_fresh)
		something_displayed = something_displayed or forecast_shown
		if forecast_shown:
			state.tracker.record_weather_success()  # Weather-related display

	if not forecast_shown:
		current_duration += forecast_duration

	# Weather display
	if display_config.show_weather and current_data:
		show_weather_display(rtc, current_duration, current_data)
		something_displayed = True
		state.tracker.record_weather_success()  # Weather-related display

	# Events display
	if display_config.show_events and event_duration > 0:
		event_shown = show_event_display(rtc, event_duration)
		something_displayed = something_displayed or event_shown
		if event_shown:
			state.tracker.record_display_success()
		else:
			interruptible_sleep(1)

	# Stocks display (with frequency control)
	if display_config.show_stocks:
		# Smart frequency: show every cycle if stocks are the only display, otherwise respect frequency
		other_displays_active = (display_config.show_weather or display_config.show_forecast or display_config.show_events)

		if other_displays_active:
			# Other displays active - respect frequency (e.g., frequency=3 means cycles 1, 4, 7, 10...)
			should_show_stocks = (cycle_count - 1) % display_config.stocks_display_frequency == 0
		else:
			# Stocks are the only display - show every cycle to avoid clock fallback
			should_show_stocks = True

		if should_show_stocks:
			# Smart rotation: Check if current stock is highlighted
			display_mode, ticker = get_stock_display_mode(state.cached_stocks, state.tracker.current_stock_offset)

			if display_mode == "chart":
				# Show single stock chart for highlighted stock
				stocks_shown = show_single_stock_chart(ticker, Timing.DEFAULT_EVENT, rtc)
				something_displayed = something_displayed or stocks_shown
				if stocks_shown:
					# Advance offset by 1 (move to next stock)
					state.tracker.current_stock_offset = (state.tracker.current_stock_offset + 1) % len(state.cached_stocks)
					state.tracker.record_display_success()
			else:
				# Show multi-stock rotation (3 stocks at a time)
				stocks_shown, next_offset = show_stocks_display(Timing.DEFAULT_EVENT, state.tracker.current_stock_offset, rtc)
				something_displayed = something_displayed or stocks_shown
				if stocks_shown:
					state.tracker.current_stock_offset = next_offset  # Update for next display
					state.tracker.record_display_success()

	# Test modes
	if display_config.show_color_test:
		show_color_test_display(Timing.COLOR_TEST)
		something_displayed = True

	if display_config.show_icon_test:
		show_icon_test_display(icon_numbers=TestData.TEST_ICONS)
		something_displayed = True

	# Fallback: show clock if nothing displayed
	if not something_displayed:
		log_warning("No displays active - showing clock as fallback")
		show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
		something_displayed = True

	# Cache stats logging
	if cycle_count % Timing.CYCLES_FOR_CACHE_STATS == 0:
		log_debug(state.image_cache.get_stats())

	# Safety check: ensure cycle took reasonable time
	cycle_duration = time.monotonic() - cycle_start_time
	if cycle_duration < Timing.FAST_CYCLE_THRESHOLD:
		log_error(f"Cycle completed too fast ({cycle_duration:.1f}s) - adding safety delay")
		time.sleep(Timing.ERROR_SAFETY_DELAY)
		cycle_duration = time.monotonic() - cycle_start_time

	# Log completion
	mem_stats = state.memory_monitor.get_memory_stats()
	log_info(f"Cycle #{cycle_count} complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | UT: {state.memory_monitor.get_runtime()} | Mem: {mem_stats['usage_percent']:.1f}% | API: {state.tracker.get_api_stats()}\n")

def _log_cycle_complete(cycle_count, cycle_start_time, mode):
	"""Helper: Log cycle completion (Category A2)"""
	cycle_duration = time.monotonic() - cycle_start_time
	mem_stats = state.memory_monitor.get_memory_stats()
	log_info(f"Cycle #{cycle_count} ({mode}) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min\n")

def run_display_cycle(rtc, cycle_count):
	"""Main display cycle - orchestrates weather, forecast, events, and schedules"""
	cycle_start_time = time.monotonic()

	# Early exit: rapid cycling detection
	if _check_rapid_cycling(cycle_count):
		return

	# Maintenance
	if cycle_count % Timing.CYCLES_FOR_MEMORY_REPORT == 0:
		state.memory_monitor.log_report()
	check_daily_reset(rtc)

	# Early exit: no WiFi
	if not _ensure_wifi_available(rtc):
		_log_cycle_complete(cycle_count, cycle_start_time, "NO WIFI")
		return

	# Early exit: extended failure mode
	if _check_failure_mode(rtc):
		return

	# Try scheduled display first (priority path)
	if _run_scheduled_cycle(rtc, cycle_count, cycle_start_time):
		return  # Schedule handled everything

	# Normal cycle
	_run_normal_cycle(rtc, cycle_count, cycle_start_time)
		

### ============================================ MAIN PROGRAM  =========================================== ###

def main():
	"""Main program execution"""
	# Initialize RTC FIRST for proper timestamps
	rtc = setup_rtc()
	
	# Validate configuration
	if not validate_configuration():
		log_error("Configuration validation failed - exiting")
		return
		
	try:
		# System initialization
		events = initialize_system(rtc)

		# Show startup message
		show_startup_message(duration=3)

		# Brief startup delay to prevent rapid API calls on boot loops
		if display_config.delayed_start:
			STARTUP_DELAY = System.STARTUP_DELAY_TIME
			log_info(f"Startup delay: {STARTUP_DELAY}s")
			show_clock_display(rtc, STARTUP_DELAY)
		
		# Network setup - CAPTURE the return value!
		location_info = setup_network_and_time(rtc)  # ← ADD location_info =
		
		# Set startup time
		state.startup_time = time.monotonic()
		state.tracker.last_successful_display = state.startup_time
		state.tracker.last_successful_weather = state.startup_time  # Initialize both timestamps
		state.memory_monitor.log_report()

		# Log active display features
		active_features = display_config.get_active_features()
		formatted_features = [feature.replace("_", " ") for feature in active_features]
		
		# Add location if available
		if location_info and "location" in location_info:
			log_info(f"Fetching time and weather for: {location_info['location']}")
		
		log_info(f"Active displays: {', '.join(formatted_features)}")
		log_info(f"== STARTING MAIN DISPLAY LOOP == \n")
		
		# Main display loop
		cycle_count = 0
		while True:
			try:
				cycle_count += 1
				log_info(f"## CYCLE {cycle_count} ##")
				run_display_cycle(rtc, cycle_count)
				
			except Exception as e:
				log_error(f"Display loop error: {e}")
				state.memory_monitor.check_memory("display_loop_error")

				# CRITICAL: Add delay to prevent rapid retry loops
				state.tracker.consecutive_failures += 1

				if state.tracker.consecutive_failures >= 3:
					log_error(f"Multiple consecutive failures ({state.tracker.consecutive_failures}) - longer delay")
					interruptible_sleep(30)  # 30 second delay after repeated failures
				else:
					interruptible_sleep(Timing.SLEEP_BETWEEN_ERRORS)
				
	except KeyboardInterrupt:
		log_info("Program interrupted by user")
		state.memory_monitor.log_report()
	
	except Exception as e:
		log_error(f"Critical system error: {e}")
		state.memory_monitor.log_report()
		time.sleep(Timing.RESTART_DELAY)
		supervisor.reload()
	
	finally:
		log_debug("Cleaning up before exit...")
		state.memory_monitor.log_report()
		clear_display()
		cleanup_global_session()

# Program entry point
if __name__ == "__main__":
	main()
