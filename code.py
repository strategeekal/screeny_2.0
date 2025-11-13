##### PANTALLITA #####

# === LIBRARIES ===
# Standard library
import board
import os
import supervisor
import gc
import time
import ssl
import microcontroller

# Display
import displayio
import framebufferio
import rgbmatrix
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
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
			log_warning("Using DUMMY weather data (not fetching from API)")
		
		if not self.use_live_forecast:
			log_warning("Using DUMMY forecast data (not fetching from API)")
		
		if self.use_test_date:
			log_warning("Test date mode enabled - NTP sync will be skipped")

	
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
		
	
## State Class
class WeatherDisplayState:
	def __init__(self):
		# Hardware instances
		self.rtc_instance = None
		self.display = None
		self.main_group = None
		self.matrix_type_cache = None
		
		# API tracking
		self.api_call_count = 0
		self.current_api_calls = 0
		self.forecast_api_calls = 0
		self.consecutive_failures = 0
		self.last_successful_weather = 0
		
		# Timing and cache
		self.startup_time = 0
		self.last_forecast_fetch = -Timing.FORECAST_UPDATE_INTERVAL
		self.cached_current_weather = None
		self.cached_current_weather_time = 0
		self.cached_forecast_data = None
		self.cached_events = None
		
		# Colors (set after matrix detection)
		self.colors = {}
		
		# Network session
		self.global_requests_session = None
		
		# Caches
		self.image_cache = ImageCache(max_size=12)
		self.text_cache = TextWidthCache()
		
		# Add memory monitor
		self.memory_monitor = MemoryMonitor()
		
		# WiFi Failure Management
		self.wifi_reconnect_attempts = 0
		self.last_wifi_attempt = 0
		self.system_error_count = 0
		
		self.in_extended_failure_mode = False
		self.scheduled_display_error_count = 0
		self.has_permanent_error = False  # Track 401/404 errors
		
		# Event tracking
		self.ephemeral_event_count = 0
		self.permanent_event_count = 0
		self.total_event_count = 0
		
		# Schedule session tracking (for segmented displays)
		self.active_schedule_name = None
		self.active_schedule_start_time = None  # monotonic time when schedule started
		self.active_schedule_end_time = None    # monotonic time when schedule should end
		self.schedule_just_ended = False
	
	def reset_api_counters(self):
		"""Reset API call tracking"""
		old_total = self.api_call_count
		self.api_call_count = 0
		self.current_api_calls = 0
		self.forecast_api_calls = 0
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
	"""Sleep that can be interrupted more easily"""
	end_time = time.monotonic() + duration
	while time.monotonic() < end_time:
		time.sleep(Timing.INTERRUPTIBLE_SLEEP_INTERVAL)  # Short sleep allows more interrupt opportunities

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
		time_since_attempt = current_time - state.last_wifi_attempt
		
		if time_since_attempt < Recovery.WIFI_RECONNECT_COOLDOWN:
			return False
		
		log_warning("WiFi DISCONNECTED, attempting recovery...")
		state.last_wifi_attempt = current_time
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
	try:
		api_key = get_api_key()
		location_key = os.getenv(Strings.API_LOCATION_KEY)
		url = f"http://dataservice.accuweather.com/locations/v1/{location_key}?apikey={api_key}"
		
		session = get_requests_session()
		response = session.get(url)
		
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

def cleanup_sockets():
	"""Aggressive socket cleanup to prevent memory issues"""
	for _ in range(Memory.SOCKET_CLEANUP_CYCLES):
		gc.collect()
		
# Global session management
_global_session = None

def get_requests_session():
	"""Get or create the global requests session"""
	global _global_session
	
	if _global_session is None:
		try:
			pool = socketpool.SocketPool(wifi.radio)
			_global_session = requests.Session(pool, ssl.create_default_context())
			log_debug("Created new global session")
		except Exception as e:
			log_error(f"Failed to create session: {e}")
			return None
	
	return _global_session


def cleanup_global_session():
	"""Clean up the global requests session and force socket release"""
	global _global_session  # ← Make sure this line is here!
	
	if _global_session is not None:
		try:
			log_debug("Destroying global session")
			# Try to close gracefully first
			try:
				_global_session.close()
			except:
				pass
			
			# Force delete the session object
			del _global_session
			_global_session = None
			
			# Aggressive socket cleanup
			cleanup_sockets()
			
			# Force garbage collection
			gc.collect()
			
			# Brief pause to let sockets fully close
			time.sleep(0.5)
			
			log_debug("Global session destroyed and sockets cleaned")
		except Exception as e:
			log_debug(f"Session cleanup error (non-critical): {e}")
			_global_session = None
		

### API FUNCTIONS ###

def fetch_weather_with_retries(url, max_retries=None, context="API"):
	"""Enhanced weather data fetch with detailed error handling"""
	if max_retries is None:
		max_retries = API.MAX_RETRIES
	
	last_error = None
	
	for attempt in range(max_retries + 1):
		try:
			# Check WiFi before attempting
			if not check_and_recover_wifi():
				log_error(f"{context}: WiFi unavailable")
				return None
			
			session = get_requests_session()
			if not session:
				log_error(f"{context}: No requests session available")
				return None
			
			log_verbose(f"{context} attempt {attempt + 1}/{max_retries + 1}")
			
			response = session.get(url)
			
			# Success case
			if response.status_code == API.HTTP_OK:
				log_verbose(f"{context}: Success")
				return response.json()
			
			# Handle specific HTTP errors
			elif response.status_code == API.HTTP_SERVICE_UNAVAILABLE:
				log_warning(f"{context}: Service unavailable (503)")
				last_error = "Service unavailable"
				
			elif response.status_code == API.HTTP_TOO_MANY_REQUESTS:
				log_warning(f"{context}: Rate limited (429)")
				last_error = "Rate limited"
				# Longer delay for rate limiting
				if attempt < max_retries:
					delay = API.RETRY_DELAY * 3
					log_debug(f"Rate limit cooldown: {delay}s")
					interruptible_sleep(delay)
					continue
					
			elif response.status_code == API.HTTP_UNAUTHORIZED:
				log_error(f"{context}: Unauthorized (401) - check API key")
				state.has_permanent_error = True  # Mark as permanent error
				return None
				
			elif response.status_code == API.HTTP_NOT_FOUND:
				log_error(f"{context}: Not found (404) - check location key")
				state.has_permanent_error = True
				return None
			
			elif response.status_code == API.HTTP_BAD_REQUEST:
				log_error(f"{context}: Bad request (400) - check URL/parameters")
				state.has_permanent_error = True
				return None
			
			elif response.status_code == API.HTTP_FORBIDDEN:
				log_error(f"{context}: Forbidden (403) - API key lacks permissions")
				state.has_permanent_error = True
				return None
			
			elif response.status_code == API.HTTP_INTERNAL_SERVER_ERROR:
				log_warning(f"{context}: Server error (500) - AccuWeather issue")
				last_error = "Server error (500)"
				# Will retry below
				
			else:
				log_error(f"{context}: HTTP {response.status_code}")
				last_error = f"HTTP {response.status_code}"
			
			# Exponential backoff for retryable errors
			if attempt < max_retries:
				delay = min(
					API.RETRY_DELAY * (2 ** attempt),
					Recovery.API_RETRY_MAX_DELAY
				)
				log_debug(f"Retrying in {delay}s...")
				interruptible_sleep(delay)
				
		except RuntimeError as e:
			error_msg = str(e)
			last_error = f"Runtime error: {error_msg}"
			
			if "pystack exhausted" in error_msg.lower():
				log_error(f"{context}: Stack exhausted - memory issue, forcing cleanup")
			elif "already connected" in error_msg.lower():
				log_error(f"{context}: Socket already connected - forcing cleanup")
			else:
				log_error(f"{context}: Runtime error on attempt {attempt + 1}: {error_msg}")
			
			# Nuclear cleanup for any RuntimeError
			cleanup_global_session()
			cleanup_sockets()
			gc.collect()
			time.sleep(2)
			
			if attempt < max_retries:
				delay = API.RETRY_BASE_DELAY * (2 ** attempt)
				log_verbose(f"Retrying in {delay}s...")
				time.sleep(delay)
		
		except OSError as e:
			error_msg = str(e)
			last_error = f"Network error: {error_msg}"
			
			# Detect socket issues
			if "already connected" in error_msg.lower() or "pystack exhausted" in error_msg.lower():
				log_error(f"{context}: Socket stuck - forcing nuclear cleanup")
				
				# Nuclear option: destroy everything
				cleanup_global_session()
				cleanup_sockets()
				gc.collect()
				
				# Longer delay to ensure sockets fully close
				time.sleep(2)
				
				# This will force session recreation on next attempt
			elif "ETIMEDOUT" in error_msg or "104" in error_msg or "32" in error_msg:
				log_warning(f"{context}: Network timeout on attempt {attempt + 1}")
			else:
				log_warning(f"{context}: Network error on attempt {attempt + 1}: {error_msg}")
			
			# Retry with delay
			if attempt < max_retries:
				delay = API.RETRY_BASE_DELAY * (2 ** attempt)
				log_verbose(f"Retrying in {delay}s...")
				time.sleep(delay)
				
					
		except Exception as e:
			log_error(f"{context} attempt {attempt + 1} unexpected error: {type(e).__name__}: {e}")
			last_error = str(e)
			if attempt < max_retries:
				interruptible_sleep(API.RETRY_DELAY)
	
	log_error(f"{context}: All {max_retries + 1} attempts failed. Last error: {last_error}")
	return None

def fetch_current_and_forecast_weather():
	"""Fetch current and/or forecast weather with individual controls, detailed tracking, and improved error handling"""
	state.memory_monitor.check_memory("weather_fetch_start")
	
	# Check what to fetch based on config
	if not display_config.should_fetch_weather() and not display_config.should_fetch_forecast():
		log_debug("All API fetching disabled")
		return None, None
	
	# Count expected API calls
	expected_calls = (1 if display_config.should_fetch_weather() else 0) + (1 if display_config.should_fetch_forecast() else 0)
	
	# Monitor memory just before planned restart
	if state.api_call_count + expected_calls >= API.MAX_CALLS_BEFORE_RESTART:
		log_warning(f"API call #{state.api_call_count + expected_calls} - restart imminent")
	
	try:
		# Get matrix-specific API key
		api_key = get_api_key()
		if not api_key:
			state.consecutive_failures += 1
			return None, None
		
		current_data = None
		forecast_data = None
		current_success = False
		forecast_success = False
		
		# Fetch current weather if enabled
		if display_config.should_fetch_weather():
			current_url = f"{API.BASE_URL}/{API.CURRENT_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&details=true"
			
			current_json = fetch_weather_with_retries(current_url, context="Current Weather")
			
			if current_json:
				state.current_api_calls += 1
				state.api_call_count += 1
				current_success = True
				
				# Process current weather
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
				
				state.cached_current_weather = current_data  # Cache for fallback
				state.cached_current_weather_time = time.monotonic()
				
				log_verbose(f"CURRENT DATA: {current_data}")
				log_info(f"Weather: {current_data['weather_text']}, {current_data['feels_like']}°C")
				
			else:
				log_warning("Current weather fetch failed")
		
		# Fetch forecast weather if enabled and (current succeeded OR current disabled)
		if display_config.should_fetch_forecast():
			forecast_url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&metric=true&details=true"
			
			forecast_json = fetch_weather_with_retries(forecast_url, max_retries=1, context="Forecast")
			
			if forecast_json:  # Count the API call even if processing fails later
				state.forecast_api_calls += 1
				state.api_call_count += 1
			
			forecast_fetch_length = min(API.DEFAULT_FORECAST_HOURS, API.MAX_FORECAST_HOURS)
			
			if forecast_json and len(forecast_json) >= forecast_fetch_length:
				# Extract forecast data
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
				
				state.memory_monitor.check_memory("forecast_data_complete")
				forecast_success = True
			else:
				log_warning("12-hour forecast fetch failed or insufficient data")
				forecast_data = None
		
		# Log API call statistics
		log_debug(f"API Stats: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}")
		
		# Determine overall success
		any_success = current_success or forecast_success
		
		if any_success:
			# Log recovery if coming out of extended failure mode
			if state.in_extended_failure_mode:
				recovery_time = int((time.monotonic() - state.last_successful_weather) / System.SECONDS_PER_MINUTE)
				log_info(f"Weather API recovered after {recovery_time} minutes of failures")
			
			state.consecutive_failures = 0
			state.last_successful_weather = time.monotonic()
			state.wifi_reconnect_attempts = 0  # Reset WiFi counter on success
			state.system_error_count = 0  # Reset system errors on success
		else:
			state.consecutive_failures += 1
			state.system_error_count += 1  # Increment across soft resets
			log_warning(f"Consecutive failures: {state.consecutive_failures}, System errors: {state.system_error_count}")
			
			# Soft reset on repeated failures
			if state.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD:
				log_warning("Soft reset: clearing network session")
				cleanup_global_session()
				state.consecutive_failures = 0
				
				# Enter temporary extended failure mode for cooldown
				was_in_extended_mode = state.in_extended_failure_mode
				state.in_extended_failure_mode = True
				
				# Show purple clock during 30s cooldown
				log_info("Cooling down for 30 seconds before retry...")
				show_clock_display(state.rtc_instance, 30)
				
				# Restore previous extended mode state
				state.in_extended_failure_mode = was_in_extended_mode
			
			# Hard reset if soft resets aren't helping
			if state.system_error_count >= Recovery.HARD_RESET_THRESHOLD:
				log_error(f"Hard reset after {state.system_error_count} system errors")
				interruptible_sleep(Timing.RESTART_DELAY)
				supervisor.reload()
		
		# Check for preventive restart
		if state.api_call_count >= API.MAX_CALLS_BEFORE_RESTART:
			log_warning(f"Preventive restart after {state.api_call_count} API calls")
			cleanup_global_session()
			interruptible_sleep(API.RETRY_DELAY)
			supervisor.reload()
		
		state.memory_monitor.check_memory("weather_fetch_complete")
		return current_data, forecast_data
		
	except Exception as e:
		log_error(f"Weather fetch critical error: {type(e).__name__}: {e}")
		state.memory_monitor.check_memory("weather_fetch_error")
		state.consecutive_failures += 1
		return None, None
		
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
	"""Fetch only current weather (not forecast)"""
	if display_config.use_live_weather:
		display_config.use_live_forecast = False
		current_data, _ = fetch_current_and_forecast_weather()
		display_config.use_live_forecast = True
		
		if current_data:
			state.last_successful_weather = time.monotonic()
		return current_data
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
	if state.in_extended_failure_mode:
		return "extended"  # PURPLE
	
	# Check for permanent configuration errors
	if hasattr(state, 'has_permanent_error') and state.has_permanent_error:
		return "general"  # WHITE
	
	# Check for WiFi issues
	if not is_wifi_connected():
		return "wifi"  # RED
	
	# Check for schedule display errors (file system issues)
	if state.scheduled_display_error_count >= 3:
		return "general"  # WHITE
	
	# Check for weather API failures (only after startup)
	time_since_success = time.monotonic() - state.last_successful_weather
	if state.last_successful_weather > 0 and time_since_success > 600:
		return "weather"  # YELLOW
	
	# Check for consecutive failures
	if state.consecutive_failures >= 3:
		return "weather"  # YELLOW
	
	# All OK
	return None  # MINT
	
def should_fetch_forecast():
	"""Check if forecast data needs to be refreshed"""
	current_time = time.monotonic()
	log_verbose(f"LAST FORECAST FETCH: {state.last_forecast_fetch} seconds ago. Needs Refresh? = {(current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL}")
	return (current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL
	
def get_today_events_info(rtc):
	"""Get information about today's ACTIVE events (filtered by time)"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	events = get_events()
	
	if month_day not in events:
		return 0, []
	
	current_hour = rtc.datetime.tm_hour
	
	# Filter events by current time
	active_events = [event for event in events[month_day] if is_event_active(event, current_hour)]
	
	return len(active_events), active_events
	
def get_today_all_events_info(rtc):
	"""Get ALL events for today (not filtered by time)"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	events = get_events()
	
	if month_day not in events:
		return 0, []
	
	# Return all events without time filtering
	return len(events[month_day]), events[month_day]

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

def load_events_from_csv():
	"""Load events from CSV file - supports multiple events per day with optional time windows"""
	events = {}
	try:
		log_verbose(f"Loading events from {Paths.EVENTS_CSV}...")
		with open(Paths.EVENTS_CSV, "r") as f:
			for line in f:
				line = line.strip()
				if line and not line.startswith("#"):
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 4:
						date = parts[0]
						top_line = parts[1]      # Shows on TOP
						bottom_line = parts[2]   # Shows on BOTTOM
						image = parts[3]
						color = parts[4] if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR
						
						# Optional time window (24-hour format)
						# Check if fields exist AND are not empty
						start_hour = int(parts[5]) if len(parts) > 5 and parts[5].strip() else Timing.EVENT_ALL_DAY_START
						end_hour = int(parts[6]) if len(parts) > 6 and parts[6].strip() else Timing.EVENT_ALL_DAY_END
						
						date_key = date.replace("-", "")
						
						if date_key not in events:
							events[date_key] = []
						
						# Store as: [top_line, bottom_line, image, color, start_hour, end_hour]
						events[date_key].append([top_line, bottom_line, image, color, start_hour, end_hour])
			
			return events
			
	except Exception as e:
		log_warning(f"Failed to load events.csv: {e}")
		log_warning("Using fallback hardcoded events")
		return {}

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
		events, _, _ = fetch_github_data(state.rtc_instance)  # ← Updated
		
		if events:
			state.cached_events = events
			return events
		
		return {}
		
	except Exception as e:
		log_warning(f"Failed to fetch ephemeral events: {e}")
		return {}
		
def load_all_events():
	"""Load and merge all event sources"""
	
	# Load permanent events from local CSV
	permanent_events = {}
	permanent_count = 0
	
	try:
		with open(Paths.EVENTS_CSV, 'r') as f:
			for line_num, line in enumerate(f, 1):
				line = line.strip()
				if not line or line.startswith("#"):
					continue
				
				try:
					parts = [part.strip() for part in line.split(",")]
					
					if len(parts) < 4:
						log_warning(f"Line {line_num}: Not enough fields (need at least 4)")
						continue
					
					# Format: MM-DD,TopLine,BottomLine,ImageFile,Color[,StartHour,EndHour]
					date_str = str(parts[0])
					top_line = str(parts[1])
					bottom_line = str(parts[2])
					image = str(parts[3])
					color = str(parts[4]) if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR
					
					# Optional time window
					try:
						start_hour = int(parts[5]) if len(parts) > 5 and parts[5].strip() else Timing.EVENT_ALL_DAY_START
						end_hour = int(parts[6]) if len(parts) > 6 and parts[6].strip() else Timing.EVENT_ALL_DAY_END
					except (ValueError, IndexError):
						start_hour = Timing.EVENT_ALL_DAY_START
						end_hour = Timing.EVENT_ALL_DAY_END
					
					# Parse MM-DD to MMDD (without zfill)
					if '-' in date_str:
						date_parts = date_str.split('-')
						month = date_parts[0]
						day = date_parts[1]
						
						# Manual padding instead of zfill
						if len(month) == 1:
							month = '0' + month
						if len(day) == 1:
							day = '0' + day
						
						date_key = month + day
					else:
						# Fallback for MMDD format
						date_key = date_str
						# Manual padding to 4 digits
						while len(date_key) < 4:
							date_key = '0' + date_key
					
					if date_key not in permanent_events:
						permanent_events[date_key] = []
					
					permanent_events[date_key].append([top_line, bottom_line, image, color, start_hour, end_hour])
					permanent_count += 1
					log_verbose(f"Loaded: {date_key} - {top_line} {bottom_line}")
					
				except Exception as e:
					log_warning(f"Line {line_num} parse error: {e} | Line: {line}")
					continue
		
		state.permanent_event_count = permanent_count
		log_debug(f"Loaded {permanent_count} permanent events")
		
	except Exception as e:
		log_warning(f"Failed to load permanent events file: {e}")
		state.permanent_event_count = 0
		permanent_events = {}
	
	# Get ephemeral events - check temp storage first, then try fetching
	ephemeral_events = {}
	
	if hasattr(state, '_github_events_temp') and state._github_events_temp:
		# Use events fetched during initialization
		ephemeral_events = state._github_events_temp
		log_debug("Using GitHub events from initialization")
	else:
		# Fetch from GitHub (normal case for daily refresh)
		ephemeral_events = fetch_ephemeral_events()
	
	# Count ephemeral events
	ephemeral_count = sum(len(event_list) for event_list in ephemeral_events.values())
	state.ephemeral_event_count = ephemeral_count
	log_debug(f"Loaded {ephemeral_count} ephemeral events")
	
	# Merge events
	merged = {}
	
	# Add permanent events
	for date_key, event_list in permanent_events.items():
		merged[date_key] = list(event_list)
	
	# Add ephemeral events
	for date_key, event_list in ephemeral_events.items():
		if date_key in merged:
			merged[date_key].extend(event_list)
		else:
			merged[date_key] = list(event_list)
	
	# Update total count
	total_count = sum(len(event_list) for event_list in merged.values())
	state.total_event_count = total_count
	
	log_debug(f"Events merged: {permanent_count} permanent + {ephemeral_count} ephemeral = {total_count} total")
	
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
					top_line = parts[1]
					bottom_line = parts[2]
					image = parts[3]
					color = parts[4] if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR
					
					# Optional time window
					start_hour = int(parts[5]) if len(parts) > 5 and parts[5].strip() else Timing.EVENT_ALL_DAY_START
					end_hour = int(parts[6]) if len(parts) > 6 and parts[6].strip() else Timing.EVENT_ALL_DAY_END
					
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
								log_verbose(f"Skipping past event: {date} - {top_line} {bottom_line}")
								continue
							
							# Convert YYYY-MM-DD to MMDD for lookup
							date_key = date_parts[1] + date_parts[2]  # MMDD only
							
							if date_key not in events:
								events[date_key] = []
							
							events[date_key].append([top_line, bottom_line, image, color, start_hour, end_hour])
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
			
			if len(parts) >= 9:
				name = parts[0]
				enabled = parts[1] == "1"
				days_str = parts[2]
				start_hour = int(parts[3])
				start_min = int(parts[4])
				end_hour = int(parts[5])
				end_min = int(parts[6])
				image = parts[7]
				progressbar = parts[8] == "1"
				
				# Convert days string to list of day numbers (0=Mon, 6=Sun)
				days = [int(d) for d in days_str if d.isdigit()]
				
				schedules[name] = {
					"enabled": enabled,
					"days": days,
					"start_hour": start_hour,
					"start_min": start_min,
					"end_hour": end_hour,
					"end_min": end_min,
					"image": image,
					"progressbar": progressbar
				}
				
				log_verbose(f"Parsed schedule: {name} ({'enabled' if enabled else 'disabled'}, {len(days)} days)")
		
		return schedules
		
	except Exception as e:
		log_error(f"Error parsing schedule CSV: {e}")
		return {}
	
def fetch_github_data(rtc):
	"""
	Fetch both events and schedules from GitHub in one operation
	Returns: (events_dict, schedules_dict, schedule_source)
		schedule_source: "date-specific", "default", or None
	"""
	
	session = get_requests_session()
	if not session:
		log_warning("No session available for GitHub fetch")
		return None, None, None
	
	import time
	cache_buster = int(time.monotonic())
	github_base = Strings.GITHUB_REPO_URL.rsplit('/', 1)[0]
	
	# ===== FETCH EVENTS =====
	events_url = f"{Strings.GITHUB_REPO_URL}?t={cache_buster}"
	events = {}
	
	try:
		log_verbose(f"Fetching: {events_url}")
		response = session.get(events_url, timeout=10)
		
		if response.status_code == 200:
			events = parse_events_csv_content(response.text, rtc)
			log_verbose(f"Events fetched: {len(events)} event dates")
		else:
			log_warning(f"Failed to fetch events: HTTP {response.status_code}")
	except Exception as e:
		log_warning(f"Failed to fetch events: {e}")
	
	# ===== FETCH SCHEDULE =====
	now = rtc.datetime
	date_str = f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}"
	
	schedules = {}
	schedule_source = None
	
	try:
		# Try date-specific schedule first
		schedule_url = f"{github_base}/{Paths.GITHUB_SCHEDULE_FOLDER}/{date_str}.csv?t={cache_buster}"
		log_verbose(f"Fetching: {schedule_url}")
		
		response = session.get(schedule_url, timeout=10)
		
		if response.status_code == 200:
			schedules = parse_schedule_csv_content(response.text, rtc)
			schedule_source = "date-specific"
			log_verbose(f"Schedule fetched: {date_str}.csv ({len(schedules)} schedule(s))")
			
		elif response.status_code == 404:
			# No date-specific file, try default
			log_verbose(f"No schedule for {date_str}, trying default.csv")
			default_url = f"{github_base}/{Paths.GITHUB_SCHEDULE_FOLDER}/default.csv?t={cache_buster}"
			
			response = session.get(default_url, timeout=10)
			
			if response.status_code == 200:
				schedules = parse_schedule_csv_content(response.text, rtc)
				schedule_source = "default"
				log_verbose(f"Schedule fetched: default.csv ({len(schedules)} schedule(s))")
			else:
				log_warning(f"No default schedule found: HTTP {response.status_code}")
		else:
			log_warning(f"Failed to fetch schedule: HTTP {response.status_code}")
			
	except Exception as e:
		log_warning(f"Failed to fetch schedule: {e}")
	
	return events, schedules, schedule_source
	
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
						name = parts[0]
						enabled = parts[1] == "1"
						days = [int(d) for d in parts[2]]
						schedules[name] = {
							"enabled": enabled,
							"days": days,
							"start_hour": int(parts[3]),
							"start_min": int(parts[4]),
							"end_hour": int(parts[5]),
							"end_min": int(parts[6]),
							"image": parts[7],
							"progressbar": parts[8] == "1" if len(parts) > 8 else True
						}
		
		# Log successful load
		if schedules:
			log_debug(f"{len(schedules)} schedules loaded")
		else:
			log_warning("No schedules found in schedules.csv")
		
		return schedules
		
	except Exception as e:
		log_warning(f"Failed to load schedules.csv: {e}")
		return {}
		
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
			events, schedules, schedule_source = fetch_github_data(rtc)  # ← Updated
			
			if schedules:
				self.schedules = schedules
				self.schedules_loaded = True
				self.last_fetch_date = current_date
				
				# Update cached events too
				if events:
					state.cached_events = events
				
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

### DISPLAY FUNCTIONS ###

def right_align_text(text, font, right_edge):
	return right_edge - get_text_width(text, font)

def center_text(text, font, area_x, area_width):
	return area_x + (area_width - get_text_width(text, font)) // 2

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

def add_day_indicator(main_group, rtc):
	"""Add 4x4 day-of-week color indicator at top right"""
	day_color = get_day_color(rtc)
	
	# Create 4x4 rectangle at top right (64-4=60 pixels from left)
	for x in range(DayIndicator.X, DayIndicator.X + DayIndicator.SIZE):
		for y in range(DayIndicator.Y, DayIndicator.Y + DayIndicator.SIZE):
			pixel_line = Line(x, y, x, y, day_color)
			main_group.append(pixel_line)
			
	# Add 1-pixel black margin to the left (x=59)
	for y in range(DayIndicator.Y, DayIndicator.MARGIN_BOTTOM_Y):
		black_pixel = Line(DayIndicator.MARGIN_LEFT_X, y, DayIndicator.MARGIN_LEFT_X, y, state.colors["BLACK"])
		main_group.append(black_pixel)
	
	# Add 1-pixel black margin to the bottom (y=4)
	for x in range(DayIndicator.MARGIN_LEFT_X, DayIndicator.X+DayIndicator.SIZE):  # Include the corner pixel at (59,4)
		black_pixel = Line(x, DayIndicator.MARGIN_BOTTOM_Y, x, DayIndicator.MARGIN_BOTTOM_Y, state.colors["BLACK"])
		main_group.append(black_pixel)

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
		
def add_indicator_bars(main_group, x_start, uv_index, humidity):
	"""Add UV and humidity indicator bars to display"""
	
	# UV bar (only if UV > 0)
	if uv_index > 0:
		uv_length = calculate_uv_bar_length(uv_index)
		main_group.append(Line(x_start, Layout.UV_BAR_Y, x_start - 1 + uv_length, Layout.UV_BAR_Y, state.colors["DIMMEST_WHITE"]))
		
		# UV spacing dots (black pixels every 3)
		for i in Visual.UV_SPACING_POSITIONS:
			if i < uv_length:
				main_group.append(Line(x_start + i, Layout.UV_BAR_Y, x_start + i, Layout.UV_BAR_Y, state.colors["BLACK"]))
	
	# Humidity bar
	if humidity > 0:
		humidity_length = calculate_humidity_bar_length(humidity)
		
		# Main humidity line
		main_group.append(Line(x_start, Layout.HUMIDITY_BAR_Y, x_start - 1 + humidity_length, Layout.HUMIDITY_BAR_Y, state.colors["DIMMEST_WHITE"]))
		
		# Humidity spacing dots (black pixels every 2 = every 20%)
		for i in Visual.HUMIDITY_SPACING_POSITIONS:  # Positions for 20%, 40%, 60%, 80%
			if i < humidity_length:
				main_group.append(Line(x_start + i, Layout.HUMIDITY_BAR_Y, x_start + i, Layout.HUMIDITY_BAR_Y, state.colors["BLACK"]))


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
	
	# Load weather icon ONCE
	try:
		bitmap, palette = state.image_cache.get_image(f"{Paths.WEATHER_ICONS}/{weather_data['weather_icon']}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		state.main_group.append(image_grid)
	except Exception as e:
		log_warning(f"Icon load failed: {e}")
	
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
	if display_config.show_weekday_indicator:
		add_day_indicator(state.main_group, rtc)
		log_verbose(f"Showing Weekday Color Indicator on Weather Display")
	else:
		log_verbose("Weekday Color Indicator Disabled")
	
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
			display_hour = hour % System.HOURS_IN_HALF_DAY if hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
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
	if display_config.show_weekday_indicator:
		add_day_indicator(state.main_group, rtc)
		log_verbose(f"Showing Weekday Color Indicator on Clock Display")
	else:
		log_verbose("Weekday Color Indicator Disabled")
	
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		dt = rtc.datetime
		date_str = f"{MONTHS[dt.tm_mon].upper()} {dt.tm_mday:02d}"
		
		hour = dt.tm_hour
		display_hour = hour % System.HOURS_IN_HALF_DAY if hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
		time_str = f"{display_hour}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
		
		date_text.text = date_str
		time_text.text = time_str
		interruptible_sleep(1)
	
	# Check for restart conditions ONLY if not in startup phase
	if state.startup_time > 0:  # Only check if we've completed initialization
		time_since_success = time.monotonic() - state.last_successful_weather
		
		# Hard reset after 1 hour of failures
		if time_since_success > System.SECONDS_PER_HOUR:
			log_error(f"Hard reset after {int(time_since_success/System.SECONDS_PER_MINUTE)} minutes without successful weather fetch")
			interruptible_sleep(Timing.RESTART_DELAY)
			supervisor.reload()
		
		# Warn after 30 minutes
		elif time_since_success > System.SECONDS_HALF_HOUR and state.consecutive_failures >= System.MAX_LOG_FAILURES_BEFORE_RESTART:
			log_warning(f"Extended failure: {int(time_since_success/System.SECONDS_PER_MINUTE)}min without success, {state.consecutive_failures} consecutive failures")
		
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
	
	try:
		if event_data[0] == "Birthday":  # Check bottom_line (was line1)
			# For birthday events, use the original cake image layout
			bitmap, palette = state.image_cache.get_image(Paths.BIRTHDAY_IMAGE)
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			state.main_group.append(image_grid)
		else:
			# Load event-specific image (25x28 positioned at top right)
			image_file = f"{Paths.EVENT_IMAGES}/{event_data[2]}"
			try:
				bitmap, palette = state.image_cache.get_image(image_file)
			except Exception as e:
				log_warning(f"Failed to load {image_file}: {e}")
				bitmap, palette = state.image_cache.get_image(Paths.FALLBACK_EVENT_IMAGE)
			
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
			if display_config.show_weekday_indicator:
				add_day_indicator(state.main_group, rtc)
				log_debug("Showing Weekday Color Indicator on Event Display")		
		
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
	
	# FLATTENED precipitation analysis (same logic, less stack depth)
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
		log_debug(f"Adjusted to skip duplicate hour {current_hour}")
	
	log_debug(f"Will show hours: {forecast_indices[0]+1} and {forecast_indices[1]+1}")
	
	clear_display()
	gc.collect()
	
	# LOG what we're about to display
	current_temp = round(current_data["feels_like"])
	next_temps = [round(h["feels_like"]) for h in forecast_data[:2]]
	status = "Fresh" if is_fresh else "Cached"
	log_info(f"Displaying Forecast: Current {current_temp}°C → Next: {next_temps[0]}°C, {next_temps[1]}°C ({display_duration/60:.0f} min) [{status}]")
	
	try:
		# Column 1 - current temperature with feels-like logic
		temp_col1 = current_data['temperature']
		
		if temp_col1 > Visual.FEELS_LIKE_TEMP_THRESHOLD:
			display_temp_col1 = current_data.get('feels_like', temp_col1)
		else:
			display_temp_col1 = current_data.get('feels_shade', temp_col1)
		
		col1_temp = f"{round(display_temp_col1)}°"
		col1_icon = f"{current_data['weather_icon']}.bmp"
		
		# Column 2 - temperature with feels-like logic
		temp_col2 = forecast_data[forecast_indices[0]]['temperature']
		
		if temp_col2 > Visual.FEELS_LIKE_TEMP_THRESHOLD:
			# Warm: show feels-like
			display_temp_col2 = forecast_data[forecast_indices[0]].get('feels_like', temp_col2)
		else:
			# Cool: show feels-like shade
			display_temp_col2 = forecast_data[forecast_indices[0]].get('feels_shade', temp_col2)
		
		col2_temp = f"{round(display_temp_col2)}°"
		
		# Column 3 - temperature with feels-like logic
		temp_col3 = forecast_data[forecast_indices[1]]['temperature']
		
		if temp_col3 > Visual.FEELS_LIKE_TEMP_THRESHOLD:
			# Warm: show feels-like
			display_temp_col3 = forecast_data[forecast_indices[1]].get('feels_like', temp_col3)
		else:
			# Cool: show feels-like shade
			display_temp_col3 = forecast_data[forecast_indices[1]].get('feels_shade', temp_col3)
		
		col3_temp = f"{round(display_temp_col3)}°"
		
		# Get column icons
		col2_icon = f"{forecast_data[forecast_indices[0]]['weather_icon']}.bmp"
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
		if col2_hours_ahead <= 1:
			col2_color = state.colors["DIMMEST_WHITE"]  # Immediate
			# If col2 is immediate, check col3
			if col3_hours_ahead <= 2:
				col3_color = state.colors["DIMMEST_WHITE"]  # Also immediate
			else:
				col3_color = state.colors["MINT"]  # Col3 jumped ahead
		else:
			# Col2 jumped ahead, so col3 definitely did too
			col2_color = state.colors["MINT"]
			col3_color = state.colors["MINT"]
		
		# Generate static time labels for columns 2 and 3
		def format_hour(hour):
			if hour == 0:
				return Strings.NOON_12AM
			elif hour < System.HOURS_IN_HALF_DAY:
				return f"{hour}{Strings.AM_SUFFIX}"
			elif hour == System.HOURS_IN_HALF_DAY:
				return Strings.NOON_12PM
			else:
				return f"{hour-System.HOURS_IN_HALF_DAY}{Strings.PM_SUFFIX}"
		
		col2_time = format_hour(hour_plus_1)
		col3_time = format_hour(hour_plus_2)
		
		# Column positioning constants
		column_y = Layout.FORECAST_COLUMN_Y
		column_width = Layout.FORECAST_COLUMN_WIDTH
		time_y = Layout.FORECAST_TIME_Y
		temp_y = Layout.FORECAST_TEMP_Y
		
		# Load and position weather icon columns ONCE
		columns_data = [
			{"image": col1_icon, "x": Layout.FORECAST_COL1_X, "temp": col1_temp},
			{"image": col2_icon, "x": Layout.FORECAST_COL2_X, "temp": col2_temp},
			{"image": col3_icon, "x": Layout.FORECAST_COL3_X, "temp": col3_temp}
		]
		
		for i, col in enumerate(columns_data):
			try:
				# Try actual weather icons first
				try:
					bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{col['image']}")
				except:
					# Fallback to column images
					bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{i+1}.bmp")
					log_warning(f"Used fallback column image for column {i+1}")
				
				col_img = displayio.TileGrid(bitmap, pixel_shader=palette)
				col_img.x = col["x"]
				col_img.y = column_y
				state.main_group.append(col_img)
			except Exception as e:
				log_warning(f"Failed to load column {i+1} image: {e}")

		
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
		if display_config.show_weekday_indicator:
			add_day_indicator(state.main_group, state.rtc_instance)
		
		
		# Optimized display update loop - ONLY update column 1 time
		start_time = time.monotonic()
		loop_count = 0
		last_minute = -1
		
		while time.monotonic() - start_time < display_duration:
			loop_count += 1
			
			# Update first column time only when minute changes
			if state.rtc_instance:
				current_hour = state.rtc_instance.datetime.tm_hour
				current_minute = state.rtc_instance.datetime.tm_min
				
				if current_minute != last_minute:
					display_hour = current_hour % System.HOURS_IN_HALF_DAY if current_hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
					new_time = f"{display_hour}:{current_minute:02d}"
					
					# Update ONLY the first column time text
					col1_time_label.text = new_time
					# Recenter the text
					col1_time_label.x = max(center_text(new_time, font, Layout.FORECAST_COL1_X, column_width), 1)
					
					last_minute = current_minute
			
			# Memory monitoring and cleanup
			if loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:  # Every 30 seconds
				if display_duration > Timing.GC_INTERVAL and loop_count % Timing.GC_INTERVAL == 0:  # Only GC for longer durations
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
		elapsed = 0
		full_duration = total_duration
		progress = 0
		
		log_info(f"Starting schedule session: {schedule_name} ({total_duration}s total)")
	
	else:
		log_debug(f"Continuing schedule: {schedule_name} (elapsed: {elapsed:.0f}s / {full_duration:.0f}s)")
	
	# This segment duration: min(5 minutes, remaining time)
	remaining = full_duration - elapsed
	segment_duration = min(Timing.SCHEDULE_SEGMENT_DURATION, remaining)
	
	log_debug(f"Segment duration: {segment_duration}s (remaining: {remaining:.0f}s)")
	
	# Light cleanup before segment (keep session alive for connection reuse)
	gc.collect()
	clear_display()
	
	try:
		# Fetch weather if not provided
		if not current_data:
			current_data = fetch_current_weather_only()
		
		if not current_data:
			log_warning("No weather data for scheduled display segment")
			
			# Try cached current weather before giving up (max 15 minutes old)
			current_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)
			
			if current_data:
				log_debug("Using cached current weather as fallback")
				is_cached = True
			else:
				# No weather data, skip weather section
				log_warning("No weather data - Display schedule + clock only")
				is_cached = False
				
		else:
			is_cached = False
			
		# === WEATHER SECTION (CONDITIONAL) ===
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
			
			# Load weather icon
			try:
				bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{weather_icon}")
				weather_img = displayio.TileGrid(bitmap, pixel_shader=palette)
				weather_img.x = Layout.SCHEDULE_LEFT_MARGIN_X
				weather_img.y = Layout.SCHEDULE_W_IMAGE_Y + y_offset
				state.main_group.append(weather_img)
			except Exception as e:
				log_error(f"Failed to load weather icon: {e}")
				
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
		
		# === SCHEDULE IMAGE (ALWAYS) ===
		try:
			bitmap, palette = load_bmp_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
			schedule_img = displayio.TileGrid(bitmap, pixel_shader=palette)
			schedule_img.x = Layout.SCHEDULE_IMAGE_X
			schedule_img.y = Layout.SCHEDULE_IMAGE_Y
			state.main_group.append(schedule_img)
		except Exception as e:
			log_error(f"Failed to load schedule image: {e}")
			state.scheduled_display_error_count += 1
			if state.scheduled_display_error_count >= 3:
				display_config.show_scheduled_displays = False
			show_clock_display(rtc, segment_duration)
			return
		
		state.scheduled_display_error_count = 0
		
		# === CLOCK LABEL (ALWAYS) ===
		time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.FORECAST_TIME_Y
		)
		state.main_group.append(time_label)
		
		# === WEEKDAY INDICATOR (IF ENABLED) ===
		if display_config.show_weekday_indicator:
			add_day_indicator(state.main_group, rtc)
			log_verbose("Showing Weekday Color Indicator on Schedule Display")
			
		# LOG what's being displayed this segment
		segment_num = int(elapsed / Timing.SCHEDULE_SEGMENT_DURATION) + 1
		total_segments = int(full_duration / Timing.SCHEDULE_SEGMENT_DURATION) + (1 if full_duration % Timing.SCHEDULE_SEGMENT_DURATION else 0)

		state.schedule_just_ended = (segment_num >= total_segments)
		
		if current_data:
			cache_indicator = " [CACHED]" if is_cached else ""
			log_info(f"Displaying Schedule: {schedule_name} - Segment {segment_num}/{total_segments} ({temperature}, {segment_duration/60:.1f} min, progress: {progress*100:.0f}%){cache_indicator}")
		else:
			log_info(f"Displaying Schedule: {schedule_name} - Segment {segment_num}/{total_segments} (Weather Skipped, progress: {progress*100:.0f}%)")
		
		# Override success tracking
		state.last_successful_weather = time.monotonic()
		state.consecutive_failures = 0
		
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
				display_hour = hour % System.HOURS_IN_HALF_DAY or System.HOURS_IN_HALF_DAY
				time_label.text = f"{display_hour}:{current_minute:02d}"
				last_minute = current_minute
			
			time.sleep(sleep_interval)
		
		log_debug(f"Segment complete")
		
	except Exception as e:
		log_error(f"Scheduled display segment error: {e}")
		
		# CRITICAL: Add delay to prevent runaway loops on errors
		
		# Safety: If too many errors in a row, take a break
		if state.consecutive_display_errors >= 5:
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
	
	# Detect matrix type and initialize colors
	matrix_type = detect_matrix_type()
	state.colors = get_matrix_colors()
	state.memory_monitor.check_memory("hardware_init_complete")
	
	# Handle test date if configured
	if display_config.use_test_date:
		update_rtc_datetime(rtc, TestData.TEST_YEAR, TestData.TEST_MONTH, TestData.TEST_DAY, TestData.TEST_HOUR, TestData.TEST_MINUTE)
	
	# Fetch events and schedules from GitHub
	log_debug("Fetching data from GitHub...")
	github_events, github_schedules, schedule_source = fetch_github_data(rtc)
	
	# Initialize events - DON'T set state.cached_events yet, let load_all_events() handle it
	# But store github_events temporarily so load_all_events() can access it
	if github_events:
		# Store in a temporary location for load_all_events() to use
		state._github_events_temp = github_events
		log_debug(f"GitHub events: {len(github_events)} event dates")
	else:
		log_warning("Failed to fetch events from GitHub")
		state._github_events_temp = None
	
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
	log_info(f"Hardware ready | {schedule_count} schedules{schedule_source_flag} | {state.total_event_count} events{imported_str} | Today: {today_msg}")
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
	if not state.in_extended_failure_mode:
		log_warning(f"ENTERING extended failure mode after {int(time_since_success/System.SECONDS_PER_MINUTE)} minutes without success")
		state.in_extended_failure_mode = True
	
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
		if display_config.show_weather and not display_config.use_live_weather:
			current_data = TestData.DUMMY_WEATHER_DATA
			log_debug("Using DUMMY weather data")
		elif display_config.show_weather:
			display_config.use_live_forecast = False
			current_data, _ = fetch_current_and_forecast_weather()
			display_config.use_live_forecast = True
		
		forecast_data = state.cached_forecast_data
	
	# Return fresh flag along with data
	return current_data, forecast_data, needs_fresh_forecast

def run_display_cycle(rtc, cycle_count):
	cycle_start_time = time.monotonic()
	
	# Detect rapid cycling (completing in < 10 seconds suggests errors)
	if cycle_count > 1:
		time_since_startup = time.monotonic() - state.startup_time
		avg_cycle_time = time_since_startup / cycle_count
		
		if avg_cycle_time < Timing.FAST_CYCLE_THRESHOLD and cycle_count > 10:
			log_error(f"Rapid cycling detected ({avg_cycle_time:.1f}s/cycle) - restarting")
			interruptible_sleep(Timing.RESTART_DELAY)
			supervisor.reload()
	
	# Memory monitoring and maintenance
	if cycle_count % Timing.CYCLES_FOR_MEMORY_REPORT == 0:
		state.memory_monitor.log_report()
	check_daily_reset(rtc)
	
	# Check WiFi and attempt recovery if needed
	wifi_available = is_wifi_connected()
	
	if not wifi_available:
		# Try to recover (respects cooldown)
		log_debug("WiFi disconnected, attempting recovery...")
		wifi_available = check_and_recover_wifi()
	
	if not wifi_available:
		log_warning("No WiFi - showing clock")
		show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
		
		cycle_duration = time.monotonic() - cycle_start_time
		mem_stats = state.memory_monitor.get_memory_stats()
		log_info(f"Cycle #{cycle_count} (NO WIFI) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min\n")
		return  # Exit early
	
	# WiFi is available - check for extended failure mode
	time_since_success = time.monotonic() - state.last_successful_weather
	in_failure_mode = time_since_success > Timing.EXTENDED_FAILURE_THRESHOLD
	
	if not in_failure_mode and state.in_extended_failure_mode:
		log_info("EXITING extended failure mode")
		state.in_extended_failure_mode = False
	
	if in_failure_mode:
		handle_extended_failure_mode(rtc, time_since_success)
		return
	
	# CHECK FOR SCHEDULED DISPLAY FIRST
	if display_config.show_scheduled_displays:
		schedule_name, schedule_config = scheduled_display.get_active_schedule(rtc)
		
		if schedule_name:
			# Fetch weather for this segment
			current_data = fetch_current_weather_only()
			
			if current_data:
				state.last_successful_weather = time.monotonic()
				state.consecutive_failures = 0
			
			# Get remaining time for schedule
			display_duration = get_remaining_schedule_time(rtc, schedule_config)
			
			# PROTECTION: Ensure minimum cycle time
			cycle_start = time.monotonic()
			
			# Show ONE segment (max 5 minutes)
			show_scheduled_display(rtc, schedule_name, schedule_config, display_duration, current_data)
			
			# Fast cycle protection
			cycle_elapsed = time.monotonic() - cycle_start
			if cycle_elapsed < Timing.FAST_CYCLE_THRESHOLD:
				log_error(f"Schedule cycle completed suspiciously fast ({cycle_elapsed:.1f}s) - adding safety delay")
				time.sleep(Timing.ERROR_SAFETY_DELAY)  # Force 30-second delay
			
			log_debug(f"LAST SEGMENT -> {state.schedule_just_ended}")
			# Always check events before showing schedule (no tracking needed)
			if state.schedule_just_ended and display_config.show_events_in_between_schedules and display_config.show_events:
				cleanup_global_session()
				gc.collect()
				show_event_display(rtc, 30)  # Quick 30-second check
				cleanup_global_session()
				gc.collect()
			
			# Log cycle summary
			cycle_duration = time.monotonic() - cycle_start_time
			mem_stats = state.memory_monitor.get_memory_stats()
			log_info(f"Cycle #{cycle_count} (SCHEDULED) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | UT: {state.memory_monitor.get_runtime()} | Mem: {mem_stats['usage_percent']:.1f}% | API: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}\n")
			return
			
	else:
		log_debug("Scheduled displays disabled due to errors")
	
	# Track if anything was displayed this cycle
	something_displayed = False
	
	# NORMAL CYCLE - Fetch data once
	current_data, forecast_data, forecast_is_fresh = fetch_cycle_data(rtc)
	
	current_duration, forecast_duration, event_duration = calculate_display_durations(rtc)
	
	# Forecast display
	forecast_shown = False
	if display_config.show_forecast and current_data and forecast_data:
		forecast_shown = show_forecast_display(current_data, forecast_data, forecast_duration, forecast_is_fresh)
		if forecast_shown:
			something_displayed = True
	
	if not forecast_shown:
		current_duration += forecast_duration
	
	# Current weather display
	if display_config.show_weather and current_data:
		show_weather_display(rtc, current_duration, current_data)
		something_displayed = True
	
	# Events display
	if display_config.show_events and event_duration > 0:
		event_shown = show_event_display(rtc, event_duration)
		if event_shown:
			something_displayed = True
		else:
			interruptible_sleep(1)
	
	# Color test (if enabled)
	if display_config.show_color_test:
		show_color_test_display(Timing.COLOR_TEST)
		something_displayed = True
	
	# Icon test (if enabled)
	if display_config.show_icon_test:
		show_icon_test_display(icon_numbers=TestData.TEST_ICONS)
		something_displayed = True
	
	# FALLBACK: If nothing was displayed, show clock
	if not something_displayed:
		log_warning("No displays active - showing clock as fallback")
		show_clock_display(rtc, Timing.CLOCK_DISPLAY_DURATION)
		something_displayed = True  # Clock counts as something!
	
	# Cache stats logging
	if cycle_count % Timing.CYCLES_FOR_CACHE_STATS == 0:
		log_debug(state.image_cache.get_stats())
	
	# SAFETY CHECK: Ensure cycle took reasonable time
	cycle_duration = time.monotonic() - cycle_start_time
	
	if cycle_duration < Timing.FAST_CYCLE_THRESHOLD:
		log_error(f"Cycle completed too fast ({cycle_duration:.1f}s) - adding safety delay")
		time.sleep(Timing.ERROR_SAFETY_DELAY)
		cycle_duration = time.monotonic() - cycle_start_time
	
	# Calculate cycle duration and log
	mem_stats = state.memory_monitor.get_memory_stats()
	
	log_info(f"Cycle #{cycle_count} complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | UT: {state.memory_monitor.get_runtime()} | Mem: {mem_stats['usage_percent']:.1f}% | API: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}\n")
		

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
		
		# Brief startup delay to prevent rapid API calls on boot loops
		if display_config.delayed_start:
			STARTUP_DELAY = System.STARTUP_DELAY_TIME
			log_info(f"Startup delay: {STARTUP_DELAY}s")
			show_clock_display(rtc, STARTUP_DELAY)
		
		# Network setup - CAPTURE the return value!
		location_info = setup_network_and_time(rtc)  # ← ADD location_info =
		
		# Set startup time
		state.startup_time = time.monotonic()
		state.last_successful_weather = state.startup_time
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
				state.consecutive_failures += 1
				
				if state.consecutive_failures >= 3:
					log_error(f"Multiple consecutive failures ({state.consecutive_failures}) - longer delay")
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

