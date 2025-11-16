"""
Configuration Module for Screeny 2.0
====================================

This module contains all configuration classes, constants, and settings.
It has no dependencies on other modules - it's the foundation of the config hierarchy.

Extracted in Phase 1 of controlled refactoring from v2.0.6.1
"""

import os

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
	FONT_BIG = "fonts/bigbit10-16.bdf"
	FONT_SMALL = "fonts/tinybit6-16.bdf"

	WEATHER_ICONS = "img/weather"
	EVENT_IMAGES = "img/events"
	COLUMN_IMAGES = "img/weather/columns"
	FALLBACK_EVENT_IMAGE = "img/events/blank_sq.bmp"
	BIRTHDAY_IMAGE = "img/events/cake.bmp"
	SCHEDULE_IMAGES = "img/schedules"

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

	# Environment variables
	WIFI_SSID_VAR = "CIRCUITPY_WIFI_SSID"
	WIFI_PASSWORD_VAR = "CIRCUITPY_WIFI_PASSWORD"

	# Event sources
	GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")

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

		# Display Elements
		self.show_weekday_indicator = True
		self.show_scheduled_displays = True
		self.show_events_in_between_schedules = True

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

		# Forecast requires weather
		if self.show_forecast and not self.show_weather:
			issues.append("Forecast display requires weather display to be enabled")

		# Warn about dummy modes
		if not self.use_live_weather:
			print("[CONFIG WARNING] Using DUMMY weather data (not fetching from API)")

		if not self.use_live_forecast:
			print("[CONFIG WARNING] Using DUMMY forecast data (not fetching from API)")

		if self.use_test_date:
			print("[CONFIG WARNING] Test date mode enabled - NTP sync will be skipped")


	def should_fetch_weather(self):
		"""Should we fetch current weather from API?"""
		return self.show_weather and self.use_live_weather

	def should_fetch_forecast(self):
		"""Should we fetch forecast from API?"""
		return self.show_forecast and self.use_live_forecast

	def get_active_features(self):
		"""Return list of enabled features"""
		features = []
		if self.show_weather: features.append("weather")
		if self.show_forecast: features.append("forecast")
		if self.show_events: features.append("events")
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
		# Simple print - logging handled by caller if needed
		print(f"[CONFIG INFO] Features: {', '.join(self.get_active_features())}")

# Global display configuration instance
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
		print("[CONFIG ERROR] === CONFIGURATION ERRORS ===")
		for issue in issues:
			print(f"[CONFIG ERROR]   - {issue}")
		print("[CONFIG ERROR] Fix these issues before running!")
		return False

	if warnings:
		print("[CONFIG WARNING] === CONFIGURATION WARNINGS ===")
		for warning in warnings:
			print(f"[CONFIG WARNING]   - {warning}")

	print("[CONFIG DEBUG] Configuration validation passed")
	return True
