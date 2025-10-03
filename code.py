
##### PANTALLITA #####

# === LIBRARIES ===
import board
import os
import supervisor
import gc
import displayio
import framebufferio
import rgbmatrix
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
import adafruit_imageload
import wifi
import ssl
import socketpool
import adafruit_requests
import adafruit_ds3231
import time
import adafruit_ntp
import microcontroller

gc.collect()

# === CONSTANTS ===

## Display Hardware 

class Display:
	WIDTH = 64
	HEIGHT = 32
	BIT_DEPTH = 6

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
	
class DayIndicator:
	SIZE = 4
	X = 60              # 64 - 4
	Y = 0
	MARGIN_LEFT_X = 59  # X - 1
	MARGIN_BOTTOM_Y = 4 # Y + SIZE
	
## Timing (all in seconds)

class Timing:
	DEFAULT_CYCLE = 330         
	DEFAULT_FORECAST = 60       
	DEFAULT_EVENT = 30          
	MIN_EVENT_DURATION = 10     
	CLOCK_DISPLAY_DURATION = 300
	COLOR_TEST = 300 
	SCHEDULE_WEATHER_REFRESH_INTERVAL = 300  
	SCHEDULE_GC_INTERVAL = 600   
	
	FORECAST_UPDATE_INTERVAL = 900  # 15 minutes
	DAILY_RESET_HOUR = 3
	EXTENDED_FAILURE_THRESHOLD = 600  # 10 minutes   When to enter clock-only mode for recovery
	INTERRUPTIBLE_SLEEP_INTERVAL = 0.1
	
	# Retry delays
	RTC_RETRY_DELAY = 2
	WIFI_RETRY_DELAY = 2
	
	SLEEP_BETWEEN_ERRORS = 5
	RESTART_DELAY = 10
	
	WEATHER_UPDATE_INTERVAL = 60
	MEMORY_CHECK_INTERVAL = 30
	GC_INTERVAL = 60
	
	CYCLES_TO_MONITOR_MEMORY = 10
	CYCLES_FOR_FORCE_CLEANUP = 25
	CYCLES_FOR_MEMORY_REPORT = 100
	CYCLES_FOR_CACHE_STATS = 10
	
	EVENT_CHUNK_SIZE = 60
	EVENT_MEMORY_MONITORING = 600 # For long events (e.g. all day)
	
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
	RETRY_DELAY = 2                     
	MAX_CALLS_BEFORE_RESTART = 204  
	
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
	EXTENDED_FAILURE_THRESHOLD = 3600 
	
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
	SCHEDULE_IMAGES = "img/schedule"
	
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
	
## Test Data Constants

class TestData:
	# Move TEST_DATE_DATA values here
	TEST_YEAR = None                    
	TEST_MONTH = None                      
	TEST_DAY =  None                       
	TEST_HOUR = 19
	TEST_MINUTE = 22
	
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
	
## String Constants
class Strings:
	DEFAULT_EVENT_COLOR = "MINT"
	TIMEZONE_DEFAULT = "America/Chicago"    # TIMEZONE_CONFIG["timezone"]
	
	# API key names
	API_KEY_TYPE1 = "ACCUWEATHER_API_KEY_TYPE1"
	API_KEY_TYPE2 = "ACCUWEATHER_API_KEY_TYPE2"
	API_KEY_FALLBACK = "ACCUWEATHER_API_KEY"
	API_LOCATION_KEY = "ACCUWEATHER_LOCATION_KEY"
	
	# Environment variables
	WIFI_SSID_VAR = "CIRCUITPY_WIFI_SSID"
	WIFI_PASSWORD_VAR = "CIRCUITPY_WIFI_PASSWORD"
	
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
	
	def __init__(self):
		# Core displays (always try to show if data available)
		self.show_weather = True
		self.show_forecast = False
		self.show_events = False
		
		# Display Elements
		self.show_weekday_indicator = True
		self.show_scheduled_displays = True
		
		# API controls (fetch real data vs use dummy data)
		self.use_live_weather = True      # False = use dummy data
		self.use_live_forecast = True     # False = use dummy data
		
		# Test/debug modes
		self.use_test_date = True
		self.show_color_test = False
	
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
		if self.use_test_date: features.append("test_date")
		if self.show_color_test: features.append("color_test")
		
		return features
	
	def log_status(self):
		"""Log current configuration status"""
		log_info(f"Features: {', '.join(self.get_active_features())}")
		
display_config = DisplayConfig()

class ScheduledDisplay:
	"""Configuration for time-based scheduled displays"""
	# Schedule images should be placed in img/schedule/
	# Weather column images (13x23px) should be in img/weather/columns/
	
	def __init__(self):
		self.schedules = {
			#Morning Routine
			"Get Dressed": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 7,
				"start_min": 0,
				"end_hour": 7,
				"end_min": 20,
				"image": "get_dressed.bmp"
			},
			
			"Eat Breakfast": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 7,
				"start_min": 20,
				"end_hour": 7,
				"end_min": 50,
				"image": "breakfast.bmp"
			},
			
			"Go to School": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4],  # All days (0=Monday, 6=Sunday)
				"start_hour": 7,
				"start_min": 50,
				"end_hour": 8,
				"end_min": 15,
				"image": "go_to_school.bmp"
			},
			
			# Nighttime Routine
			
			"Eat Dinner": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 19,
				"start_min": 0,
				"end_hour": 19,
				"end_min": 30,
				"image": "dinner.bmp"
			},
			
			"Bath Time": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 19,
				"start_min": 30,
				"end_hour": 20,
				"end_min": 0,
				"image": "bath_time.bmp"
			},
			
			"Pijamas On": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 20,
				"start_min": 0,
				"end_hour": 20,
				"end_min": 15,
				"image": "get_dressed_night.bmp"
			},
			
			"Toilet and Teeth": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 20,
				"start_min": 15,
				"end_hour": 20,
				"end_min": 30,
				"image": "toilet_and_teeth.bmp"
			},
			
			"Story and Sleep": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 20,
				"start_min": 30,
				"end_hour": 20,
				"end_min": 45,
				"image": "story_and_bed.bmp"
			},
			
			"Sleep": {
				"enabled": True,
				"days": [0, 1, 2, 3, 4, 5, 6],  # All days (0=Monday, 6=Sunday)
				"start_hour": 20,
				"start_min": 45,
				"end_hour": 21,
				"end_min": 30,
				"image": "bed.bmp"
			},
			
		}
	
	def is_active(self, rtc, schedule_name):
		"""Check if a schedule is currently active"""
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
		"""Get the currently active schedule, if any"""
		for name, schedule in self.schedules.items():
			if self.is_active(rtc, name):
				return name, schedule
		return None, None

# Create instance
scheduled_display = ScheduledDisplay()

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

# Base colors use standard RGB (works correctly on type2)
_BASE_COLORS = {
	"BLACK": 0x000000,
	"DIMMEST_WHITE": 0x101010,
	"MINT": 0x081608,
	"BUGAMBILIA": 0x100010,
	"LILAC": 0x160814,
	"RED": 0x3F0000,
	"GREEN": 0x003F00,
	"BLUE": 0x00003F,
	"ORANGE": 0x7F1F00,
	"YELLOW": 0x3F2F00,
	"CYAN": 0x003F3F,
	"PURPLE": 0x080025,
	"PINK": 0x7F1F5F,
	"AQUA": 0x002020,
	"WHITE": 0x3F3F3F,
	"GRAY": 0x1F1F1F,
}

# Only correct for the non-standard type1 matrix (green↔blue swap)
_COLOR_CORRECTIONS = {
	"type1": {
		# Green↔Blue swap for type1 matrix
		"MINT": 0x080816,      # 0x081608 with green/blue swapped
		"BUGAMBILIA": 0x101000, # 0x100010 with green/blue swapped
		"LILAC": 0x161408,     # 0x160814 with green/blue swapped
		"GREEN": 0x00003F,     # 0x003F00 with green/blue swapped
		"BLUE": 0x003F00,      # 0x00003F with green/blue swapped
		"ORANGE": 0x7F001F,    # 0x5F1F00 with green/blue swapped
		"YELLOW": 0x3F002F,    # 0x3F3F00 with green/blue swapped
		"PURPLE": 0x082500,    # 0x3F003F with green/blue swapped
		"PINK": 0x7F5F1F,      # 0x3F1F5F with green/blue swapped
	}
	# type2 uses base colors as-is (no corrections needed)
}

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

def sync_time_with_timezone(rtc):
	"""Enhanced NTP sync with configurable timezone support"""
	
	timezone_name = Strings.TIMEZONE_DEFAULT
	
	try:
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		
		# Get UTC time first
		ntp_utc = adafruit_ntp.NTP(pool, tz_offset=0)
		utc_time = ntp_utc.datetime
		
		# Calculate timezone offset
		offset = get_timezone_offset(timezone_name, utc_time)
		
		# Apply timezone offset
		ntp = adafruit_ntp.NTP(pool, tz_offset=offset)
		rtc.datetime = ntp.datetime
		
		log_info(f"Time synced to {timezone_name} (UTC{offset:+d})")
		
	except Exception as e:
		log_error(f"NTP sync failed: {e}")

def cleanup_sockets():
	"""Aggressive socket cleanup to prevent memory issues"""
	for _ in range(Memory.SOCKET_CLEANUP_CYCLES):
		gc.collect()

def get_requests_session():
	"""Get or create a persistent requests session for connection reuse"""
	if state.global_requests_session is None:
		try:
			cleanup_sockets()
			pool = socketpool.SocketPool(wifi.radio)
			
			try:
				pool.socket_timeout = API.TIMEOUT
			except (AttributeError, NotImplementedError):
				log_verbose("Socket timeout configuration not available")
			
			state.global_requests_session = adafruit_requests.Session(
				pool, 
				ssl.create_default_context()
			)
			log_verbose("Created new persistent requests session")
		except Exception as e:
			log_error(f"Failed to create requests session: {e}")
			return None
	
	return state.global_requests_session

def cleanup_global_session():
	"""Clean up the global session"""
	if state.global_requests_session:
		try:
			state.global_requests_session.close()
			del state.global_requests_session
			state.global_requests_session = None
			log_verbose("Global session cleaned up")
		except:
			pass
		
		cleanup_sockets()
		

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
				return None  # Don't retry auth failures
				
			elif response.status_code == API.HTTP_NOT_FOUND:
				log_error(f"{context}: Not found (404) - check location key")
				return None  # Don't retry not found
				
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
				
		except OSError as e:
			# Network/socket errors
			log_warning(f"{context} attempt {attempt + 1} network error: {type(e).__name__}")
			last_error = "Network error"
			if attempt < max_retries:
				delay = API.RETRY_DELAY * (2 ** attempt)
				interruptible_sleep(delay)
				
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
					"has_precipitation": current.get("HasPrecipitation:", False),
				}
				log_verbose(f"CURRENT DATA: {current_data}")
				
				log_info(f"Weather: {current_data['weather_text']}, {current_data['temperature']}°C")
				
			else:
				log_warning("Current weather fetch failed")
		
		# Fetch forecast weather if enabled and (current succeeded OR current disabled)
		if display_config.should_fetch_forecast():
			forecast_url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&metric=true"
			
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
						"weather_icon": hour_data.get("WeatherIcon", 1),
						"weather_text": hour_data.get("IconPhrase", "Unknown"),
						"datetime": hour_data.get("DateTime", ""),
						"has_precipitation": hour_data.get("HasPrecipitation", False)
					})
				
				log_info(f"Forecast: {len(forecast_data)} hours (fresh) | Next: {forecast_data[0]['temperature']}°C")
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
				state.consecutive_failures = 0  # Reset consecutive, but keep system_error_count
			
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
	
def should_fetch_forecast():
	"""Check if forecast data needs to be refreshed"""
	current_time = time.monotonic()
	log_verbose(f"LAST FORECAST FETCH: {state.last_forecast_fetch} seconds ago. Needs Refresh? = {(current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL}")
	return (current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL
	
def get_today_events_info(rtc):
	"""Get information about today's events without displaying them"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	events = get_events()
	
	if month_day not in events:
		return 0, []
	
	event_list = events[month_day]
	return len(event_list), event_list


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
	colors = _BASE_COLORS.copy()  # Start with base colors
	
	# Apply corrections if they exist for this matrix type
	if matrix_type in _COLOR_CORRECTIONS:
		colors.update(_COLOR_CORRECTIONS[matrix_type])
	
	return colors

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
	
	for i in range(palette_len):
		original_color = palette[i]
		
		if matrix_type == "type1":
			# BGR to RGB conversion for type1
			red_8bit = (original_color >> 16) & 0xFF
			blue_8bit = (original_color >> 8) & 0xFF
			green_8bit = original_color & 0xFF
		else:
			# Standard RGB for type2
			red_8bit = (original_color >> 16) & 0xFF
			green_8bit = (original_color >> 8) & 0xFF
			blue_8bit = original_color & 0xFF
		
		# Convert to 6-bit values
		red_6bit = red_8bit >> 2
		green_6bit = green_8bit >> 2
		blue_6bit = blue_8bit >> 2
		
		converted_palette[i] = (red_6bit << 16) | (green_6bit << 8) | blue_6bit
	
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
	"""Load events from CSV file - supports multiple events per day"""
	events = {}
	try:
		log_verbose(f"Loading events from {Paths.EVENTS_CSV}...")
		with open(Paths.EVENTS_CSV, "r") as f:
			for line in f:  # Just remove line_count completely
				line = line.strip()
				if line and not line.startswith("#"):
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 4:
						date = parts[0]
						line1 = parts[1] 
						line2 = parts[2]
						image = parts[3]
						color = parts[4] if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR
						
						date_key = date.replace("-", "")
						
						if date_key not in events:
							events[date_key] = []
						events[date_key].append([line1, line2, image, color])
			
			return events
			
	except Exception as e:
		log_warning(f"Failed to load events.csv: {e}")
		log_warning("Using fallback hardcoded events")
		# Return fallback events as lists
		return {
			"0101": [["New Year", "Happy", "new_year.bmp", "BUGAMBILIA"]],
			"0210": [["Emilio", "Birthday", "cake.bmp", "MINT"]],
			"0703": [["Gaby", "Birthday", "cake.bmp", "MINT"]],
			"0704": [["July", "4th of", "us_flag.bmp", "BUGAMBILIA"]],
			"0825": [["Diego", "Birthday", "cake.bmp", "MINT"]],
			"0916": [["Mexico", "Viva", "mexico_flag_v3.bmp", "BUGAMBILIA"]],
			"0922": [["Puchis", "Cumple", "panzon.bmp", "MINT"]],
			"1031": [["Halloween", "Happy", "halloween.bmp", "BUGAMBILIA"]],
			"1101": [["Muertos", "Dia de", "day_of_the_death.bmp", "BUGAMBILIA"]],
			"1109": [["Tiago", "Birthday", "cake.bmp", "MINT"]],
			"1127": [["Thanksgiving", "Happy", "thanksgiving.bmp", "BUGAMBILIA"]],
			"1225": [["X-MAS", "Merry", "xmas.bmp", "BUGAMBILIA"]],
		}
		
def get_events():
	"""Get cached events - loads from CSV only once"""
	if state.cached_events is None:
		state.cached_events = load_events_from_csv()
		if not state.cached_events:
			log_warning("Warning: No events loaded, using minimal fallback")
			state.cached_events = {}
	
	return state.cached_events

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
		log_warning("Weather unavailable, showing clock")
		show_clock_display(rtc, duration)
		return
	
	log_debug(f"Displaying weather for {duration_message(duration)}")
	
	# Clear display and setup static elements ONCE
	clear_display()
	
	# Create all static display elements ONCE
	temp_text = bitmap_label.Label(
		bg_font, 
		color=state.colors["DIMMEST_WHITE"], 
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
			color=state.colors["DIMMEST_WHITE"], 
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
			color=state.colors["DIMMEST_WHITE"], 
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
	last_minute = -1  # Track minute changes to reduce updates
	
	while time.monotonic() - start_time < duration:
		loop_count += 1
		
		# Memory monitoring and cleanup
		if loop_count % Timing.GC_INTERVAL == 0:  # Every 60 seconds
			gc.collect()
			state.memory_monitor.check_memory(f"weather_display_gc_{loop_count//System.SECONDS_PER_MINUTE}")
		elif loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:  # Every 30 seconds, just check
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
	
	date_text = bitmap_label.Label(font, color=state.colors["DIMMEST_WHITE"], x=Layout.CLOCK_DATE_X, y=Layout.CLOCK_DATE_Y)
	time_text = bitmap_label.Label(bg_font, color=state.colors[Strings.DEFAULT_EVENT_COLOR], x=Layout.CLOCK_TIME_X, y=Layout.CLOCK_TIME_Y)
	
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
	
	# Check for restart conditions
	time_since_success = time.monotonic() - state.last_successful_weather
	
	# Hard reset after 1 hour of failures (gives plenty of time for transient issues)
	if time_since_success > System.SECONDS_PER_HOUR:  # 1 hour
		log_error(f"Hard reset after {int(time_since_success/System.SECONDS_PER_MINUTE)} minutes without successful weather fetch")
		interruptible_sleep(Timing.RESTART_DELAY)
		supervisor.reload()
	
	# Warn after 30 minutes
	elif time_since_success > System.SECONDS_HALF_HOUR and state.consecutive_failures >= System.MAX_LOG_FAILURES_BEFORE_RESTART:
		log_warning(f"Extended failure: {int(time_since_success/System.SECONDS_PER_MINUTE)}min without success, {state.consecutive_failures} consecutive failures")
		
def show_event_display(rtc, duration):
	"""Display special calendar events - cycles through multiple events if present"""
	state.memory_monitor.check_memory("event_display_start")
	
	num_events, event_list = get_today_events_info(rtc)
	
	if num_events == 0:
		return False
	
	if num_events == 1:
		# Single event - use full duration
		event_data = event_list[0]
		log_info(f"Showing event: {event_data[1]} {event_data[0]}")
		log_debug(f"Showing event display for {duration_message(duration)}")
		_display_single_event_optimized(event_data, rtc, duration)
	else:
		# Multiple events - split time between them
		event_duration = max(duration // num_events, Timing.MIN_EVENT_DURATION)
		log_verbose(f"Showing {num_events} events, {duration_message(event_duration)} each")
		
		for i, event_data in enumerate(event_list):
			state.memory_monitor.check_memory(f"event_{i+1}_start")
			log_info(f"Event {i+1}/{num_events}: {event_data[1]} {event_data[0]}")
			_display_single_event_optimized(event_data, rtc, event_duration)
	
	state.memory_monitor.check_memory("event_display_complete")
	return True

def _display_single_event_optimized(event_data, rtc, duration):
	"""Optimized helper function to display a single event - optimized for typical 30-second events"""
	clear_display()
	
	# Force garbage collection before loading images
	gc.collect()
	state.memory_monitor.check_memory("single_event_start")
	
	try:
		if event_data[1] == "Birthday":
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
			line1_text = event_data[1]  # e.g., "Cumple"
			line2_text = event_data[0]  # e.g., "Puchis"
			text_color = event_data[3] if len(event_data) > 3 else Strings.DEFAULT_EVENT_COLOR
			
			# Color map through dictionary access:
			line2_color = state.colors.get(text_color.upper(), state.colors[Strings.DEFAULT_EVENT_COLOR])
			
			# Get dynamic positions
			line1_y, line2_y = calculate_bottom_aligned_positions(
				font, 
				line1_text, 
				line2_text,
				display_height=Display.HEIGHT,
				bottom_margin=Layout.BOTTOM_MARGIN,
				line_spacing=Layout.LINE_SPACING
			)
			
			# Create text labels
			text1 = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=line1_text,
				x=Layout.TEXT_MARGIN, y=line1_y
			)
			
			text2 = bitmap_label.Label(
				font,
				color=line2_color,
				text=line2_text,
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
		
		
		# Simple strategy optimized for your usage patterns
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
						   "ORANGE", "YELLOW", "CYAN", "PURPLE", "PINK", "AQUA"]
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
	
def show_forecast_display(current_data=None, forecast_data=None, duration=30):
	"""Optimized forecast display - only update time text in column 1"""
	
	# Check if we have real data - skip display if not
	if not current_data or not forecast_data or len(forecast_data) < 3:
		log_warning(f"Skipping forecast display - insufficient data")
		return False
	
	# Log with real data
	log_debug(f"Displaying Forecast for {duration_message(duration)}: Current {current_data['temperature']}°C, +1hr {forecast_data[0]['temperature']}°C, +2hr {forecast_data[1]['temperature']}°C")
	
	clear_display()
	gc.collect()
	
	try:
		# Prepare all data ONCE
		col1_temp = f"{round(current_data['temperature'])}°"
		col1_icon = f"{current_data['weather_icon']}.bmp"
		
		col2_temp = f"{round(forecast_data[0]['temperature'])}°"
		col3_temp = f"{round(forecast_data[1]['temperature'])}°"
		col2_icon = f"{forecast_data[0]['weather_icon']}.bmp"
		col3_icon = f"{forecast_data[1]['weather_icon']}.bmp"
		
		hour_plus_1 = int(forecast_data[0]['datetime'][11:13]) % System.HOURS_IN_DAY
		hour_plus_2 = int(forecast_data[1]['datetime'][11:13]) % System.HOURS_IN_DAY
		
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
		
		# Static time labels for columns 2 and 3
		col2_time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			text=col2_time,
			x=max(center_text(col2_time, font, Layout.FORECAST_COL2_X, column_width), 1),
			y=time_y
		)
		
		col3_time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
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
		
		while time.monotonic() - start_time < duration:
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
				if duration > Timing.GC_INTERVAL and loop_count % Timing.GC_INTERVAL == 0:  # Only GC for longer durations
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
	# Create bitmap with extra height for tick marks (2px bar + 2px above + 1px below = 5px total)
	progress_bitmap = displayio.Bitmap(
		Layout.PROGRESS_BAR_HORIZONTAL_WIDTH, 
		5,  # Increased height for tick marks
		4  # 4 colors: background, elapsed, remaining, and tick marks
	)
	
	# Create palette
	progress_palette = displayio.Palette(4)
	progress_palette[0] = state.colors["BLACK"]  # Background
	progress_palette[1] = state.colors["LILAC"]  # Elapsed (darker)
	progress_palette[2] = state.colors["MINT"]  # Remaining (lighter)
	progress_palette[3] = state.colors["WHITE"]  # Tick marks (brightest)
	
	# Initialize entire bitmap with black background
	for y in range(5):
		for x in range(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH):
			progress_bitmap[x, y] = 0  # Black background everywhere
	
	# Fill only the bar area (rows 2-3) with remaining color
	for y in range(2, 4):  # Bar is at rows 2-3
		for x in range(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH):
			progress_bitmap[x, y] = 2  # Start with all "remaining"
	
	# Add tick marks: 0% (start), 25%, 50%, 75%, 100% (end)
	tick_positions = [0, 10, 20, 30, 39]
	
	for pos in tick_positions:
		if pos == 0 or pos == 20 or pos == 39:  # Start, middle, end get 2px above
			progress_bitmap[pos, 0] = 3  # Top row
			progress_bitmap[pos, 1] = 3  # Second row
		else:  # 25% and 75% get 1px above
			progress_bitmap[pos, 1] = 3  # Second row only
		
		# All ticks get 1px below
		progress_bitmap[pos, 4] = 3  # Bottom row
	
	# Create TileGrid
	progress_grid = displayio.TileGrid(
		progress_bitmap, 
		pixel_shader=progress_palette,
		x=Layout.PROGRESS_BAR_HORIZONTAL_X,
		y=Layout.PROGRESS_BAR_HORIZONTAL_Y - 2
	)
	
	return progress_grid, progress_bitmap

def update_progress_bar_bitmap(progress_bitmap, elapsed_seconds, total_seconds):
	"""Update only the bitmap values, preserving tick marks"""
	if total_seconds <= 0:
		return
	
	# Calculate elapsed pixels (fills left to right)
	elapsed_ratio = min(1.0, elapsed_seconds / total_seconds)
	elapsed_width = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * elapsed_ratio)
	
	# Update bitmap: 0=background, 1=elapsed, 2=remaining, 3=tick marks
	# Only update rows 2-3 (the bar itself)
	for y in range(2, 4):  # Bar area only
		for x in range(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH):
			if x < elapsed_width:
				progress_bitmap[x, y] = 1  # Elapsed (gray) - left side
			else:
				progress_bitmap[x, y] = 2  # Remaining (light) - right side
	
def show_scheduled_display(rtc, schedule_name, schedule_config, duration, current_data=None):
	"""Display scheduled message with live weather and clock"""
	log_info(f"Showing scheduled display: {schedule_name}")
	clear_display()
	gc.collect()
	
	try:
		# Fetch weather data if not provided
		if not current_data:
			# Fetch current weather data only
			current_data = fetch_current_weather_only()
		
		if not current_data:
			log_warning("No weather data for scheduled display")
			show_clock_display(rtc, duration)
			return
		
		# Extract initial weather data
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
		
		# Vertical offset for elements when UV bar present
		y_offset = Layout.SCHEDULE_X_OFFSET if uv_index > 0 else 0
		
		# Weather icon (left column)
		try:
			bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{weather_icon}")
			weather_img = displayio.TileGrid(bitmap, pixel_shader=palette)
			weather_img.x = Layout.SCHEDULE_LEFT_MARGIN_X
			weather_img.y = Layout.SCHEDULE_W_IMAGE_Y + y_offset
		except Exception as e:
			log_error(f"Failed to load weather icon {weather_icon}: {e}")
			state.scheduled_display_error_count += 1
			
			if state.scheduled_display_error_count >= 3:
				log_error("Disabling scheduled displays due to repeated errors")
				display_config.show_scheduled_displays = False
			
			show_clock_display(rtc, duration)
			return
			
		try:
			bitmap, palette = load_bmp_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
			schedule_img = displayio.TileGrid(bitmap, pixel_shader=palette)
			schedule_img.x = Layout.SCHEDULE_IMAGE_X
			schedule_img.y = Layout.SCHEDULE_IMAGE_Y
		except Exception as e:
			log_error(f"Failed to load schedule image {schedule_config['image']}: {e}")
			state.scheduled_display_error_count += 1
			
			if state.scheduled_display_error_count >= 3:
				log_error("Disabling scheduled displays due to repeated errors")
				display_config.show_scheduled_displays = False
			
			show_clock_display(rtc, duration)
			return
		
		# Success - reset error counter
		state.scheduled_display_error_count = 0
		
		# Time label (updates in loop)
		time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.FORECAST_TIME_Y
		)
		
		# Temperature label (static)
		temp_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			text=temperature,
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.SCHEDULE_TEMP_Y + y_offset
		)
		
		# Add all elements
		state.main_group.append(weather_img)
		state.main_group.append(schedule_img)
		state.main_group.append(time_label)
		state.main_group.append(temp_label)
		
		if display_config.show_weekday_indicator:
			add_day_indicator(state.main_group, rtc)
		
		if current_data:
			state.last_successful_weather = time.monotonic()
		
		# Track number of static elements (everything before progress bar)
		static_elements_count = len(state.main_group)
		
		# Create progress bar TileGrid
		progress_grid, progress_bitmap = create_progress_bar_tilegrid()
		state.main_group.append(progress_grid)
		
		# Display loop with live clock, weather refresh, and progress bar
		start_time = time.monotonic()
		last_minute = -1
		last_weather_update = start_time
		last_gc = start_time
		last_displayed_column = -1  # Track which column was last updated
		
		while time.monotonic() - start_time < duration:
			current_minute = rtc.datetime.tm_min
			current_time = time.monotonic()
			elapsed = current_time - start_time  # ADD THIS LINE
			
			# Calculate current column for progress bar
			elapsed_ratio = elapsed / duration
			current_column = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * (1 - elapsed_ratio))
			
			# Update progress bar only when column changes
			if current_column != last_displayed_column:
				update_progress_bar_bitmap(progress_bitmap, elapsed, duration)
				last_displayed_column = current_column
			
			# Garbage collect every 10 minutes
			if current_time - last_gc >= Timing.SCHEDULE_GC_INTERVAL:
				gc.collect()
				log_verbose("GC during scheduled display")
				last_gc = current_time

			
			# Refresh weather every 5 minutes
			if current_time - last_weather_update >= Timing.SCHEDULE_WEATHER_REFRESH_INTERVAL:
				fresh_data = fetch_current_weather_only()
				
				if fresh_data:
					new_temp = f"{round(fresh_data['feels_like'])}°"
					temp_label.text = new_temp
					
					new_icon = f"{fresh_data['weather_icon']}.bmp"
					if new_icon != weather_icon:
						try:
							bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{new_icon}")
							weather_img.bitmap = bitmap
							weather_img.pixel_shader = palette
							weather_icon = new_icon
						except:
							pass
					
					log_debug(f"Refreshed weather during scheduled display: {new_temp}")
				
				last_weather_update = current_time
			
			# Update time when minute changes
			if current_minute != last_minute:
				hour = rtc.datetime.tm_hour
				display_hour = hour % System.HOURS_IN_HALF_DAY or System.HOURS_IN_HALF_DAY
				
				time_label.text = f"{display_hour}:{current_minute:02d}"
				last_minute = current_minute
			
			interruptible_sleep(1)
			
	except Exception as e:
		log_error(f"Scheduled display error: {e}")
		show_clock_display(rtc, duration)
	
	gc.collect()
	
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
		(hours_running > 1 and 
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
		
	# Load events
	events = get_events()
	event_count, _ = get_today_events_info(rtc)
	
	if event_count == 0:
		event_count = "No"
		
	log_info(f"Hardware ready | {len(events)} events loaded | Events Today: {event_count}")
	state.memory_monitor.check_memory("events_loaded")
	
	return events

def setup_network_and_time(rtc):
	"""Setup WiFi and synchronize time"""
	wifi_connected = setup_wifi_with_recovery()
	
	if wifi_connected and not display_config.use_test_date:
		sync_time_with_timezone(rtc)
	elif display_config.use_test_date:
		log_info(f"Manual Time Set: {rtc.datetime.tm_year:04d}/{rtc.datetime.tm_mon:02d}/{rtc.datetime.tm_mday:02d} {rtc.datetime.tm_hour:02d}:{rtc.datetime.tm_min:02d}")
	else:
		log_warning("Starting without WiFi - using RTC time only")
	
	return wifi_connected

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
	
	return current_data, forecast_data

def run_display_cycle(rtc, cycle_count):
	cycle_start_time = time.monotonic()
	
	# Detect rapid cycling (completing in < 10 seconds suggests errors)
	if cycle_count > 1:
		time_since_startup = time.monotonic() - state.startup_time
		avg_cycle_time = time_since_startup / cycle_count
		
		if avg_cycle_time < 10 and cycle_count > 10:
			log_error(f"Rapid cycling detected ({avg_cycle_time:.1f}s/cycle) - restarting")
			interruptible_sleep(Timing.RESTART_DELAY)
			supervisor.reload()
	
	# Memory monitoring and maintenance
	if cycle_count % Timing.CYCLES_FOR_MEMORY_REPORT == 0:
		state.memory_monitor.log_report(level="DEBUG")
	check_daily_reset(rtc)
	
	# Check for extended failure mode
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
			
			# Fetch only current weather (not forecast) for scheduled display
			current_data = fetch_current_weather_only()
			
			display_duration = get_remaining_schedule_time(rtc, schedule_config)
			show_scheduled_display(rtc, schedule_name, schedule_config, display_duration, current_data)
			
			# Log cycle summary WITH API stats
			cycle_duration = time.monotonic() - cycle_start_time
			mem_stats = state.memory_monitor.get_memory_stats()
			log_info(f"Cycle #{cycle_count} (SCHEDULED) complete in {cycle_duration/System.SECONDS_PER_MINUTE:.2f} min | UT: {state.memory_monitor.get_runtime()} | Mem: {mem_stats['usage_percent']:.1f}% | API: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}\n")
			return
	else:
		log_debug("Scheduled displays disabled due to errors")
	
	# NORMAL CYCLE - Fetch data once
	current_data, forecast_data = fetch_cycle_data(rtc)
	current_duration, forecast_duration, event_duration = calculate_display_durations(rtc)
	
	# Forecast display
	forecast_shown = False
	if display_config.show_forecast and current_data and forecast_data:
		forecast_shown = show_forecast_display(current_data, forecast_data, forecast_duration)
	
	if not forecast_shown:
		current_duration += forecast_duration
	
	# Current weather display
	if display_config.show_weather and current_data:
		show_weather_display(rtc, current_duration, current_data)
	
	# Events display
	if display_config.show_events and event_duration > 0:
		event_shown = show_event_display(rtc, event_duration)
		if not event_shown:
			interruptible_sleep(1)
	
	# Color test (if enabled)
	if display_config.show_color_test:
		show_color_test_display(Timing.COLOR_TEST)
	
	# Cache stats logging
	if cycle_count % Timing.CYCLES_FOR_CACHE_STATS == 0:
		log_debug(state.image_cache.get_stats())
	
	# Calculate cycle duration and log
	cycle_duration = time.monotonic() - cycle_start_time
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
		
		# Network setup
		setup_network_and_time(rtc)
		
		# Set startup time
		state.startup_time = time.monotonic()
		state.last_successful_weather = state.startup_time
		state.memory_monitor.log_report()
		
		log_info(f"== STARTING MAIN DISPLAY LOOP == \n")
		log_verbose(f"Image cache initialized: {state.image_cache.get_stats()}")
		
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

