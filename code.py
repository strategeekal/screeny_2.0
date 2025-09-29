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

gc.collect()

# === CONSTANTS ===

## Display Hardware 

class Display:
	WIDTH = 64
	HEIGHT = 32
	BIT_DEPTH = 6

## Layout & Positioning

class Layout:
	RIGHT_EDGE = 63           # 64 - 1
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
	
	EVENT_CHUCK_SIZE = 60
	EVENT_MEMORY_MONITORING = 600 # For long events (e.g. all day)
	
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
	EVENTS_CSV = "events.csv"           # CSV_EVENTS_FILE
	FONT_BIG = "fonts/bigbit10-16.bdf"
	FONT_SMALL = "fonts/tinybit6-16.bdf"
	
	WEATHER_ICONS = "img/weather"
	EVENT_IMAGES = "img/events"
	COLUMN_IMAGES = "img/weather/columns"
	FALLBACK_EVENT_IMAGE = "img/events/blank_sq.bmp"
	BIRTHDAY_IMAGE = "img/events/cake.bmp"
	
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
	TEST_YEAR = 2026                    # TEST_DATE_DATA["new_year"]
	TEST_MONTH = 7                      # TEST_DATE_DATA["new_month"] 
	TEST_DAY = 4                        # TEST_DATE_DATA["new_day"]
	
	# Dummy weather values
	DUMMY_WEATHER_DATA = {
		"weather_icon": 19,
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

DISPLAY_CONFIG = {
	"weather": True,		  
	"fetch_current": True,    
	"fetch_forecast": True,   
	"dummy_weather": False,
	"dummy_forecast": False,   
	"test_date": False,		  
	"events": True,           
	"clock_fallback": True,   
	"forecast": True,
	"color_test": False,      
	"weekday_color": True,	  
}

# Debugging
DEBUG_MODE = True
LOG_MEMORY_STATS = True  # Include memory info in logs

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
				log_debug(f"Image cache full, removed: {oldest_key}")
			
			self.cache[filepath] = (bitmap, palette)
			log_debug(f"Cached image: {filepath}")
			return bitmap, palette
			
		except Exception as e:
			log_error(f"Failed to load image {filepath}: {e}")
			return None, None
	
	def clear_cache(self):
		self.cache.clear()
		log_debug("Image cache cleared")
	
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
		"""Check memory and log"""
		stats = self.get_memory_stats()
		runtime = self.get_runtime()
		
		# Update peak usage tracking
		if stats["used_bytes"] > self.peak_usage:
			self.peak_usage = stats["used_bytes"]
		
		# Store measurement
		self.measurements.append({
			"name": checkpoint_name,
			"used_percent": stats["usage_percent"],
			"runtime": runtime
		})
		if len(self.measurements) > self.max_measurements:
			self.measurements.pop(0)
		
		# Always log as debug (since your memory is healthy)
		log_debug(f"Memory: {stats['usage_percent']:.1f}% used at {checkpoint_name} [{runtime}]")
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
			log_info(line)
		
	
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
	
	def reset_api_counters(self):
		"""Reset API call tracking"""
		old_total = self.api_call_count
		self.api_call_count = 0
		self.current_api_calls = 0
		self.forecast_api_calls = 0
		log_info(f"API counters reset (was {old_total} total calls)")
	
	def get_api_stats(self):
		"""Get current API statistics"""
		return {
			"total_calls": self.api_call_count,
			"current_calls": self.current_api_calls,
			"forecast_calls": self.forecast_api_calls,
			"remaining_calls": API.MAX_CALLS_BEFORE_RESTART - self.api_call_count,
			"restart_threshold": API.MAX_CALLS_BEFORE_RESTART
		}
	
	def cleanup_session(self):
		"""Clean up network session"""
		if self.global_requests_session:
			try:
				self.global_requests_session.close()
				del self.global_requests_session
				self.global_requests_session = None
				log_debug("Global session cleaned up")
			except:
				pass

### GLOBAL STATE ###
state = WeatherDisplayState()

# Load fonts once at startup
bg_font = bitmap_font.load_font(Paths.FONT_BIG)
font = bitmap_font.load_font(Paths.FONT_SMALL)


### LOGGING UTILITIES ###

def log_entry(message, level="INFO"):
	"""
	Unified logging with timestamp (memory monitoring now handled by MemoryMonitor class)
	"""
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
		
		# Build log entry (no memory calculation)
		log_line = f"[{timestamp}{time_source}] {level}: {message}"
		print(log_line)
			
	except Exception as e:
		print(f"[LOG-ERROR] Failed to log: {message} (Error: {e})")

def log_info(message):
	"""Log info message"""
	log_entry(message, "INFO")

def log_error(message):
	"""Log error message with memory stats"""
	log_entry(message, "ERROR")

def log_warning(message):
	"""Log warning message"""
	log_entry(message, "WARNING")

def log_debug(message):
	"""Log debug message"""
	if DEBUG_MODE:
		log_entry(message, "DEBUG")
		
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
	state.memory_monitor.check_memory("display_init_start")
	
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
	
	state.memory_monitor.check_memory("display_init_complete")
	log_info("Display initiated successfully")


def interruptible_sleep(duration):
	"""Sleep that can be interrupted more easily"""
	end_time = time.monotonic() + duration
	while time.monotonic() < end_time:
		time.sleep(Timing.INTERRUPTIBLE_SLEEP_INTERVAL)  # Short sleep allows more interrupt opportunities

def setup_rtc():
	"""Initialize RTC with retry logic"""
	state.memory_monitor.check_memory("rtc_init_start")
	
	for attempt in range(System.MAX_RTC_ATTEMPTS):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			state.rtc_instance = rtc
			state.memory_monitor.check_memory("rtc_init_success")
			log_info(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			log_warning(f"RTC attempt {attempt + 1} failed: {e}")
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
	
	# Check if already connected
	try:
		if wifi.radio.connected:
			log_debug("WiFi already connected")
			return True
	except:
		pass
	
	for attempt in range(Recovery.MAX_WIFI_RETRY_ATTEMPTS):
		try:
			delay = min(
				Recovery.WIFI_RETRY_BASE_DELAY * (2 ** attempt),
				Recovery.WIFI_RETRY_MAX_DELAY
			)
			
			log_info(f"WiFi connection attempt {attempt + 1}/{Recovery.MAX_WIFI_RETRY_ATTEMPTS}")
			wifi.radio.connect(ssid, password, timeout=10)
			
			if wifi.radio.connected:
				log_info(f"Connected to {ssid[:8]}... (IP: {wifi.radio.ipv4_address})")
				return True
				
		except ConnectionError as e:
			log_warning(f"WiFi attempt {attempt + 1} failed: Connection error")
			if attempt < Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1:
				log_debug(f"Retrying in {delay}s...")
				interruptible_sleep(delay)
				
		except Exception as e:
			log_error(f"WiFi attempt {attempt + 1} unexpected error: {type(e).__name__}")
			if attempt < Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1:
				interruptible_sleep(delay)
	
	log_error(f"WiFi connection failed after {Recovery.MAX_WIFI_RETRY_ATTEMPTS} attempts")
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
		
		log_warning("WiFi disconnected, attempting recovery...")
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
				log_debug("Socket timeout configuration not available")
			
			state.global_requests_session = adafruit_requests.Session(
				pool, 
				ssl.create_default_context()
			)
			log_debug("Created new persistent requests session")
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
			log_debug("Global session cleaned up")
		except:
			pass
		
		cleanup_sockets()

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
			
			log_debug(f"{context} attempt {attempt + 1}/{max_retries + 1}")
			
			response = session.get(url)
			
			# Success case
			if response.status_code == API.HTTP_OK:
				log_debug(f"{context}: Success")
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
	fetch_current = DISPLAY_CONFIG.get("fetch_current", True)
	fetch_forecast = DISPLAY_CONFIG.get("fetch_forecast", True)
	
	if not fetch_current and not fetch_forecast:
		log_info("Both current and forecast APIs disabled in config")
		return None, None
	
	# Count expected API calls
	expected_calls = (1 if fetch_current else 0) + (1 if fetch_forecast else 0)
	
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
		if fetch_current:
			current_url = f"{API.BASE_URL}/{API.CURRENT_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&details=true"
			
			log_debug("Fetching current weather...")
			current_json = fetch_weather_with_retries(current_url, context="Current Weather")
			
			if current_json:
				state.memory_monitor.check_memory("current_data_processing")
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
				log_debug(f"CURRENT DATA: {current_data}")
				
				log_info(f"Current weather: {current_data['weather_text']}, {current_data['temperature']}°C (API #{state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART})")
				
				state.memory_monitor.check_memory("current_data_complete")
			else:
				log_warning("Current weather fetch failed")
		
		# Fetch forecast weather if enabled and (current succeeded OR current disabled)
		if fetch_forecast and (current_success or not fetch_current):
			forecast_url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&metric=true"
			
			log_debug("Fetching forecast weather...")
			forecast_json = fetch_weather_with_retries(forecast_url, max_retries=1, context="Forecast")
			
			if forecast_json:  # Count the API call even if processing fails later
				state.forecast_api_calls += 1
				state.api_call_count += 1
			
			forecast_fetch_length = min(API.DEFAULT_FORECAST_HOURS, API.MAX_FORECAST_HOURS)
			
			if forecast_json and len(forecast_json) >= forecast_fetch_length:
				state.memory_monitor.check_memory("forecast_data_processing")
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
				
				log_info(f"12-hour forecast: {len(forecast_data)} hours processed")
				if len(forecast_data) >= forecast_fetch_length:
					h = 0
					for item in forecast_data:
						log_debug(f"Hour {h+1} ({format_datetime(forecast_data[h]['datetime'])}): {forecast_data[h]['temperature']}°C, {forecast_data[h]['weather_text']} (Icon {forecast_data[h]['weather_icon']})")
						h += 1
				
				state.memory_monitor.check_memory("forecast_data_complete")
				forecast_success = True
			else:
				log_warning("12-hour forecast fetch failed or insufficient data")
				forecast_data = None
		
		# Log API call statistics
		log_info(f"API Stats: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}")
		
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
		log_debug(f"Using key with ending: {api_key[-5:]} for {matrix_type}")
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

def has_forecast_data():
	"""Check if forecast data is available without making API calls"""
	# This is a placeholder - you could implement forecast data caching
	return DISPLAY_CONFIG.get("fetch_forecast", True) and not DISPLAY_CONFIG["dummy_weather"]

def get_api_call_stats():
	"""Get detailed API call statistics"""
	
	return {
		"total_calls": state.api_call_count,
		"current_calls": state.current_api_calls,
		"forecast_calls": state.forecast_api_calls,
		"remaining_calls": API.MAX_CALLS_BEFORE_RESTART - state.api_call_count,
		"restart_threshold": API.MAX_CALLS_BEFORE_RESTART
	}
	
def should_fetch_forecast():
	"""Check if forecast data needs to be refreshed"""
	current_time = time.monotonic()
	log_debug(f"LAST FORECAST FETCH: {state.last_forecast_fetch} seconds ago. Needs Refresh? = {(current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL}")
	return (current_time - state.last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL


### DISPLAY UTILITIES ###

def detect_matrix_type():
	"""Auto-detect matrix wiring type (cached for performance)"""
	if state.matrix_type_cache is not None:
		return state.matrix_type_cache
	
	import microcontroller
	uid = microcontroller.cpu.uid
	device_id = "".join([f"{b:02x}" for b in uid[-3:]])
	
	device_mappings = {
		System.DEVICE_TYPE1_ID: "type1",
		System.DEVICE_TYPE2_ID: "type2",
	}
	
	state.matrix_type_cache = device_mappings.get(device_id, "type1")
	log_info(f"Device ID: {device_id}, Matrix type: {state.matrix_type_cache}")
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
		log_debug(f"Loading events from {Paths.EVENTS_CSV}...")
		with open(Paths.EVENTS_CSV, "r") as f:
			line_count = 0
			for line in f:
				line = line.strip()
				if line and not line.startswith("#"):  # Skip empty lines and comments
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 4:
						date = parts[0]  # MM-DD format
						line1 = parts[1] 
						line2 = parts[2]
						image = parts[3]
						color = parts[4] if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR
						
						# Convert MM-DD to MMDD format for lookup
						date_key = date.replace("-", "")
						
						# Store as list to support multiple events per day
						if date_key not in events:
							events[date_key] = []
						events[date_key].append([line1, line2, image, color])
						line_count += 1
			
			log_info(f"Loaded {line_count} events successfully from CSV")
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
	
	# Debug output
	if DEBUG_MODE:
		log_debug(f"Text positioning: '{line1_text}' at y={line1_y}, '{line2_text}' at y={line2_y}")
		log_debug(f"  Has descenders: {has_descenders}, bottom margin: {adjusted_bottom_margin}")
	
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
	log_debug("Displaying weather...")
	
	# Use provided data or fetch fresh data
	if weather_data is None:
		if DISPLAY_CONFIG["dummy_weather"]:
			weather_data = TestData.DUMMY_WEATHER_DATA
		else:
			current_data, _ = fetch_current_and_forecast_weather()
			weather_data = current_data
	
	# Log with duration information
	if weather_data:
		log_info(f"Displaying Current Weather for {duration_message(duration)}: {weather_data['weather_text']}, {weather_data['temperature']}°C")
	
	if not weather_data:
		log_warning("Weather unavailable, showing clock")
		show_clock_display(rtc, duration)
		return
	
	# Clear display and setup static elements ONCE
	clear_display()
	state.memory_monitor.check_memory("weather_display_cleared")
	
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
	if DISPLAY_CONFIG["weekday_color"]:
		add_day_indicator(state.main_group, rtc)
		log_debug(f"Showing Weekday Color Indicator on Weather Display")
	else:
		log_debug("Weekday Color Indicator Disabled")
	
	state.memory_monitor.check_memory("weather_display_static_complete")
	
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
	if DISPLAY_CONFIG["weekday_color"]:
		add_day_indicator(state.main_group, rtc)
		log_debug(f"Showing Weekday Color Indicator on Clock Display")
	else:
		log_debug("Weekday Color Indicator Disabled")
	
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
	
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	
	# Get events from cache (loaded only once at startup)
	events = get_events()
	
	if month_day not in events:
		log_info("No events to display today")
		return False
	
	event_list = events[month_day]
	num_events = len(event_list)
	
	if num_events == 1:
		# Single event - use full duration
		event_data = event_list[0]
		log_info(f"Showing event: {event_data[1]}, for {duration_message(duration)}")
		_display_single_event_optimized(event_data, rtc, duration)
	else:
		# Multiple events - split time between them
		event_duration = max(duration // num_events, Timing.MIN_EVENT_DURATION)
		log_info(f"Showing {num_events} events, {duration_message(event_duration)} each")
		
		for i, event_data in enumerate(event_list):
			state.memory_monitor.check_memory(f"event_{i+1}_start")
			log_info(f"Event {i+1}/{num_events}: {event_data[1]}")
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
			state.memory_monitor.check_memory("birthday_image_loaded")
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
			
			state.memory_monitor.check_memory("event_image_loaded")
			
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
			
			state.memory_monitor.check_memory("event_text_created")
			
			# Add day indicator
			if DISPLAY_CONFIG["weekday_color"]:
				add_day_indicator(state.main_group, rtc)
				log_debug("Showing Weekday Color Indicator on Event Display")
		
		state.memory_monitor.check_memory("event_display_static_complete")
		
		# Simple strategy optimized for your usage patterns
		if duration <= Timing.EVENT_CHUCK_SIZE:
			# Most common case: 10-60 second events, just sleep
			interruptible_sleep(duration)
		else:
			# Rare case: all-day events, use 60-second chunks with minimal monitoring
			elapsed = 0
			chunk_size = Timing.EVENT_CHUCK_SIZE  # 1-minute chunks for long events
			
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
	log_info(f"Displaying Color Test for {duration_message(Timing.COLOR_TEST)}")
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
	state.memory_monitor.check_memory("forecast_display_start")
	
	# Check if we have real data - skip display if not
	if not current_data or not forecast_data or len(forecast_data) < 3:
		log_warning(f"Skipping forecast display - insufficient data")
		return False
	
	# Log with real data
	log_info(f"Displaying Forecast for {duration_message(duration)}: Current {current_data['temperature']}°C, +1hr {forecast_data[0]['temperature']}°C, +2hr {forecast_data[1]['temperature']}°C")
	
	clear_display()
	gc.collect()
	state.memory_monitor.check_memory("forecast_display_cleared")
	
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
		if DISPLAY_CONFIG["weekday_color"]:
			add_day_indicator(state.main_group, state.rtc_instance)
			log_debug("Showing Weekday Color Indicator on Forecast Display")
		
		state.memory_monitor.check_memory("forecast_display_static_complete")
		
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
	
def calculate_display_durations():
	"""Calculate current weather duration based on cycle and forecast times"""
	
	# Current weather gets the remaining time
	current_weather_time = Timing.DEFAULT_CYCLE - Timing.DEFAULT_FORECAST - Timing.DEFAULT_EVENT
	
	# Ensure minimum time for current weather
	if current_weather_time < Timing.DEFAULT_EVENT:
		current_weather_time = Timing.MIN_EVENT_DURATION
		log_warning(f"Current weather time adjusted to minimum: {current_weather_time}s")
	
	return current_weather_time, Timing.DEFAULT_FORECAST, Timing.DEFAULT_EVENT

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
		
def update_rtc_date(rtc, new_year, new_month, new_day):
	"""
	Update only the year, month and day of the RTC, preserving all other values
	
	Args:
		rtc: The DS3231 RTC instance
		new_year: New year
		new_month: New month (1-12)
		new_day: New day (1-31)
	"""
	try:
		# Get current datetime
		current_dt = rtc.datetime
		
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
		import time
		new_datetime = time.struct_time((
			new_year,    # Keep current year
			new_month,             # New month
			new_day,               # New day
			current_dt.tm_hour,    # Keep current hour
			current_dt.tm_min,     # Keep current minute
			current_dt.tm_sec,     # Keep current second
			new_weekday,           # Calculated weekday
			new_yearday,           # Calculated yearday
			current_dt.tm_isdst    # Keep current DST flag
		))
		
		# Update the RTC
		rtc.datetime = new_datetime
		
		weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		weekday_name = weekday_names[new_weekday]
			
		log_info(f"RTC date MANUALLY updated to {new_year:04d}/{new_month:02d}/{new_day:02d} ({weekday_name})")
		return True
			
	except Exception as e:
		log_error(f"Failed to update RTC date: {e}")
		return False


### MAIN PROGRAM - HELPER FUNCTIONS ###
		
def initialize_system(rtc):
	"""Initialize all hardware and load configuration"""
	log_info("=== WEATHER DISPLAY STARTUP ===")
	
	# Initialize hardware
	initialize_display()
	
	# Detect matrix type and initialize colors
	matrix_type = detect_matrix_type()
	state.colors = get_matrix_colors()
	state.memory_monitor.check_memory("hardware_init_complete")
	
	# Load events
	events = get_events()
	log_debug(f"System initialized - {len(events)} events loaded")
	state.memory_monitor.check_memory("events_loaded")
	
	# Handle test date if configured
	if DISPLAY_CONFIG["test_date"]:
		update_rtc_date(rtc, TestData.TEST_YEAR, TestData.TEST_MONTH, TestData.TEST_DAY)
	
	return events

def setup_network_and_time(rtc):
	"""Setup WiFi and synchronize time"""
	wifi_connected = setup_wifi_with_recovery()
	
	if wifi_connected and not DISPLAY_CONFIG["test_date"]:
		sync_time_with_timezone(rtc)
		log_info("Time synchronized with NTP")
	elif DISPLAY_CONFIG["test_date"]:
		log_debug(f"Skipping NTP sync - using test date: {rtc.datetime.tm_year:04d}/{rtc.datetime.tm_mon:02d}/{rtc.datetime.tm_mday:02d}")
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
	if int(time_since_success) % System.SECONDS_HALF_HOUR < Timing.DEFAULT_CYCLE:
		log_info("Attempting API recovery from extended failure mode...")
		current_data, forecast_data = fetch_current_and_forecast_weather()
		if current_data:
			log_info("API recovery successful!")
			return True  # Signal recovery
	
	return False  # Still in failure mode

def display_forecast_cycle(current_duration, forecast_duration):
	"""Handle forecast display with caching logic"""
	current_data = None
	forecast_data = None
	
	if should_fetch_forecast():
		# Fetch both current and forecast
		current_data, forecast_data = fetch_current_and_forecast_weather()
		if forecast_data:
			state.cached_forecast_data = forecast_data
			state.last_forecast_fetch = time.monotonic()
			log_debug("Fetched fresh forecast data")
	else:
		# Fetch only current weather, use cached forecast
		DISPLAY_CONFIG["fetch_forecast"] = False
		current_data, _ = fetch_current_and_forecast_weather()
		DISPLAY_CONFIG["fetch_forecast"] = True
		forecast_data = state.cached_forecast_data
		log_debug("Using cached forecast data")
	
	forecast_shown = False
	if current_data and forecast_data:
		forecast_shown = show_forecast_display(current_data, forecast_data, forecast_duration)
	
	if not forecast_shown:
		log_info("Forecast skipped - extending current weather time")
		current_duration += forecast_duration
	
	return current_data, current_duration

def run_display_cycle(rtc, cycle_count):
	"""Execute one complete display cycle"""
	# Memory monitoring
	if cycle_count % Timing.CYCLES_TO_MONITOR_MEMORY == 0:
		state.memory_monitor.check_memory(f"cycle_{cycle_count}")
	
	if cycle_count % Timing.CYCLES_FOR_MEMORY_REPORT == 0:
		state.memory_monitor.log_report()
	
	# System maintenance
	check_daily_reset(rtc)
	
	# Check for extended failure mode
	time_since_success = time.monotonic() - state.last_successful_weather
	in_failure_mode = time_since_success > Timing.EXTENDED_FAILURE_THRESHOLD
	
	# Log exit from extended failure mode (only once)
	if not in_failure_mode and state.in_extended_failure_mode:
		log_info(f"EXITING extended failure mode - weather API recovered")
		state.in_extended_failure_mode = False
	
	if in_failure_mode:
		handle_extended_failure_mode(rtc, time_since_success)
		return  # Skip normal display cycle
	
	# Calculate display durations
	current_duration, forecast_duration, event_duration = calculate_display_durations()
	
	# Forecast display
	current_data = None
	if DISPLAY_CONFIG["forecast"]:
		current_data, current_duration = display_forecast_cycle(current_duration, forecast_duration)
	else:
		log_debug("Forecast display disabled")
	
	# Current weather display
	if DISPLAY_CONFIG["weather"]:
		if not current_data:
			current_data, _ = fetch_current_and_forecast_weather()
		show_weather_display(rtc, current_duration, current_data)
	else:
		log_debug("Weather display disabled")
	
	# Events display
	if DISPLAY_CONFIG["events"]:
		event_shown = show_event_display(rtc, event_duration)
		if not event_shown:
			interruptible_sleep(1)
	else:
		log_debug("Event display disabled")
	
	# Color test (if enabled)
	if DISPLAY_CONFIG["color_test"]:
		show_color_test_display(Timing.COLOR_TEST)
	
	# Cache stats logging
	if cycle_count % Timing.CYCLES_FOR_CACHE_STATS == 0:
		log_debug(state.image_cache.get_stats())

### MAIN PROGRAM ###

def main():
	"""Main program execution"""
	# Initialize RTC FIRST for proper timestamps
	rtc = setup_rtc()
	
	try:
		# System initialization
		events = initialize_system(rtc)
		
		# Network setup
		setup_network_and_time(rtc)
		
		# Set startup time
		state.startup_time = time.monotonic()
		state.last_successful_weather = state.startup_time
		state.memory_monitor.log_report()
		
		log_info("Entering main display loop (Press CTRL+C to stop)")
		log_debug(f"Image cache initialized: {state.image_cache.get_stats()}")
		
		# Main display loop
		cycle_count = 0
		while True:
			try:
				cycle_count += 1
				run_display_cycle(rtc, cycle_count)
				
			except Exception as e:
				log_error(f"Display loop error: {e}")
				state.memory_monitor.check_memory("display_loop_error")
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
		log_info("Cleaning up before exit...")
		state.memory_monitor.log_report()
		clear_display()
		cleanup_global_session()

# Program entry point
if __name__ == "__main__":
	main()

