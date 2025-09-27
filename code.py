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
	DEFAULT_CYCLE = 330         # DISPLAY_CONFIG["cycle_duration"]
	DEFAULT_FORECAST = 60       # DISPLAY_CONFIG["forecast_duration"]
	DEFAULT_EVENT = 30          # DISPLAY_CONFIG["event_duration"]
	MIN_EVENT_DURATION = 10     # DISPLAY_CONFIG["minimum_event_duration"]
	CLOCK_FALLBACK = 300      
	COLOR_TEST = 300            # DISPLAY_CONFIG["color_test_duration"]
	
	FORECAST_UPDATE_INTERVAL = 900  # 15 minutes
	DAILY_RESET_HOUR = 3
	CLOCK_FALLBACK_THRESHOLD = 600  # 10 minutes   DUPLICATED?
	INTERRUPTIBLE_SLEEP_INTERVAL = 0.1
	
	# Retry delays
	RTC_RETRY_DELAY = 2
	WIFI_RETRY_DELAY = 2
	
	SLEEP_BETWEEN_ERRORS = 5
	RESTART_DELAY = 10
	
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
	COLOR_TEST_GRID_COLS = 3      # From: col = i // 3
	COLOR_TEST_COL_SPACING = 16   # From: x=2 + col * 16
	COLOR_TEST_ROW_SPACING = 11   # From: y=2 + row * 11
	
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

_global_requests_session = None

cached_forecast_data = None
last_forecast_fetch = - Timing.FORECAST_UPDATE_INTERVAL 

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
	"YELLOW": 0x3F3F00,
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
		"YELLOW": 0x3F003F,    # 0x3F3F00 with green/blue swapped
		"PURPLE": 0x082500,    # 0x3F003F with green/blue swapped
		"PINK": 0x7F5F1F,      # 0x3F1F5F with green/blue swapped
	}
	# type2 uses base colors as-is (no corrections needed)
}

# Global Colors Object
COLORS = {}

# System Configuration
DAILY_RESET_ENABLED = True

### GLOBAL STATE ###

# Hardware instances
rtc_instance = None
display = None
main_group = None
_matrix_type_cache = None # Matrix type cache - loaded once at startup
cached_events = None # Event cache - loaded once at startup

# API tracking
api_call_count = 0
current_api_calls = 0
forecast_api_calls = 0
consecutive_failures = 0
last_successful_weather = 0
startup_time = 0

# Load fonts once at startup
bg_font = bitmap_font.load_font(Paths.FONT_BIG)
font = bitmap_font.load_font(Paths.FONT_SMALL)

### LOGGING UTILITIES ###

def log_entry(message, level="INFO", include_memory=False):
	"""
	Unified logging with timestamp and optional memory stats
	"""
	try:
		# Try RTC first, fallback to system time
		if rtc_instance:
			try:
				dt = rtc_instance.datetime
				timestamp = f"{dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d} {dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
				time_source = ""  # RTC time is most reliable
			except Exception:
				# RTC exists but failed to read
				import time
				monotonic_time = time.monotonic()
				timestamp = f"SYS+{int(monotonic_time)}"
				time_source = " [SYS]"
		else:
			# No RTC available, use system monotonic time
			import time
			monotonic_time = time.monotonic()
			# Convert to more readable format (hours:minutes since startup)
			hours = int(monotonic_time // 3600)
			minutes = int((monotonic_time % 3600) // 60)
			seconds = int(monotonic_time % 60)
			timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
			time_source = " [UPTIME]"
		
		# Build log entry
		log_line = f"[{timestamp}{time_source}] {level}: {message}"
		
		# Add memory info if requested
		if include_memory and LOG_MEMORY_STATS:
			import gc
			free_mem = gc.mem_free()
			mem_percent = ((Memory.ESTIMATED_TOTAL - free_mem) / Memory.ESTIMATED_TOTAL) * 100
			log_line += f" (Mem: {free_mem//1024}KB/{mem_percent:.1f}%)"
		
		print(log_line)
		
	except Exception as e:
		print(f"[LOG-ERROR] Failed to log: {message} (Error: {e})")

def log_info(message, include_memory=False):
	"""Log info message"""
	log_entry(message, "INFO", include_memory)

def log_error(message, include_memory=True):
	"""Log error message with memory stats"""
	log_entry(message, "ERROR", include_memory)

def log_warning(message, include_memory=False):
	"""Log warning message"""
	log_entry(message, "WARNING", include_memory)

def log_debug(message, include_memory=False):
	"""Log debug message"""
	if DEBUG_MODE:
		log_entry(message, "DEBUG", include_memory)
		
def duration_message(seconds):
	"""Convert seconds to a readable duration string"""
	h, remainder = divmod(seconds, 3600)
	m, s = divmod(remainder, 60)
	
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
	global display, main_group
	
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
	
	display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
	main_group = displayio.Group()
	display.root_group = main_group
	log_info("Display initiated successfully")

def interruptible_sleep(duration):
	"""Sleep that can be interrupted more easily"""
	end_time = time.monotonic() + duration
	while time.monotonic() < end_time:
		time.sleep(Timing.INTERRUPTIBLE_SLEEP_INTERVAL)  # Short sleep allows more interrupt opportunities

def setup_rtc():
	"""Initialize RTC with retry logic"""
	global rtc_instance
	
	for attempt in range(System.MAX_RTC_ATTEMPTS):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			rtc_instance = rtc
			log_info(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			log_warning(f"RTC attempt {attempt + 1} failed: {e}")
			if attempt < 4:
				interruptible_sleep(Timing.RTC_RETRY_DELAY)
	
	log_error("RTC initialization failed, restarting...")
	supervisor.reload()

### NETWORK FUNCTIONS ###

def setup_wifi():
	"""Connect to WiFi with simplified retry logic"""
	ssid = os.getenv(Strings.WIFI_SSID_VAR)
	password = os.getenv(Strings.WIFI_PASSWORD_VAR)
	
	if not ssid or not password:
		log_warning("WiFi credentials missing")
		return False
	
	for attempt in range(System.MAX_WIFI_ATTEMPTS):
		try:
			wifi.radio.connect(ssid, password)
			if DEBUG_MODE:
				log_debug(f"Connected to {ssid}")
			else:
				log_info(f"WiFi connected to {ssid[:8]}...")
			return True
		except ConnectionError as e:
			log_warning(f"WiFi attempt {attempt + 1} failed")
			if attempt < 2:
				interruptible_sleep(Timing.WIFI_RETRY_DELAY)
	
	log_error("WiFi connection failed")
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
	global _global_requests_session
	
	if _global_requests_session is None:
		try:
			cleanup_sockets()
			pool = socketpool.SocketPool(wifi.radio)
			
			# Optional: Configure socket timeout at pool level if supported
			try:
				# This may not be available in all CircuitPython versions
				pool.socket_timeout = API.TIMEOUT
			except (AttributeError, NotImplementedError):
				log_debug("Socket timeout configuration not available")
			
			_global_requests_session = adafruit_requests.Session(
				pool, 
				ssl.create_default_context()
			)
			log_debug("Created new persistent requests session")
		except Exception as e:
			log_error(f"Failed to create requests session: {e}")
			return None
	
	return _global_requests_session

def cleanup_global_session():
	"""Clean up the global session"""
	global _global_requests_session
	
	if _global_requests_session:
		try:
			_global_requests_session.close()
			del _global_requests_session
			_global_requests_session = None
			log_debug("Global session cleaned up")
		except:
			pass
		
		cleanup_sockets()

def fetch_weather_with_retries(url, max_retries=None):
	"""Fetch weather data with exponential backoff retry logic"""
	if max_retries is None:
		max_retries = API.MAX_RETRIES
	
	for attempt in range(max_retries + 1):
		try:
			session = get_requests_session()
			if not session:
				log_error("No requests session available")
				return None
			
			log_debug(f"API attempt {attempt + 1}/{max_retries + 1}")
			
			# Make the request - timeout is handled by the underlying socket
			# adafruit_requests doesn't expose timeout parameter in get()
			response = session.get(url)
			
			if response.status_code == API.HTTP_OK:
				return response.json()
			elif response.status_code == API.HTTP_SERVICE_UNAVAILABLE:
				# Service unavailable - worth retrying
				log_warning(f"API service unavailable (503), attempt {attempt + 1}")
				if attempt < max_retries:
					delay = API.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
					log_debug(f"Retrying in {delay} seconds...")
					interruptible_sleep(delay)
					continue
			else:
				log_error(f"API error: {response.status_code}")
				return None
				
		except Exception as e:
			log_warning(f"Request attempt {attempt + 1} failed: {e}")
			if attempt < max_retries:
				delay = API.RETRY_DELAY * (2 ** attempt)
				log_debug(f"Retrying in {delay} seconds...")
				interruptible_sleep(delay)
				continue
			else:
				log_error(f"All {max_retries + 1} attempts failed")
				return None
	
	return None

def fetch_current_and_forecast_weather():
	"""Fetch current and/or forecast weather with individual controls and detailed tracking"""
	global consecutive_failures, last_successful_weather, api_call_count, current_api_calls, forecast_api_calls
	
	# Check what to fetch based on config
	fetch_current = DISPLAY_CONFIG.get("fetch_current", True)
	fetch_forecast = DISPLAY_CONFIG.get("fetch_forecast", True)
	
	if not fetch_current and not fetch_forecast:
		log_info("Both current and forecast APIs disabled in config")
		return None, None
	
	# Count expected API calls
	expected_calls = (1 if fetch_current else 0) + (1 if fetch_forecast else 0)
	
	# Monitor memory just before planned restart
	if api_call_count + expected_calls >= API.MAX_CALLS_BEFORE_RESTART:
		log_warning(f"API call #{api_call_count + expected_calls} - restart imminent", include_memory=True)
	
	try:
		# Get matrix-specific API key
		api_key = get_api_key()
		if not api_key:
			consecutive_failures += 1
			return None, None
		
		current_data = None
		forecast_data = None
		current_success = False
		forecast_success = False
		
		# Fetch current weather if enabled
		if fetch_current:
			current_url = f"{API.BASE_URL}/{API.CURRENT_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&details=true"
			
			log_debug("Fetching current weather...")
			current_json = fetch_weather_with_retries(current_url)
			
			if current_json:
				current_api_calls += 1
				api_call_count += 1
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
				
				log_info(f"Current weather: {current_data['weather_text']}, {current_data['temperature']}°C (API #{api_call_count}/{API.MAX_CALLS_BEFORE_RESTART})", include_memory=True)

			else:
				log_warning("Current weather fetch failed")
		
		# Fetch forecast weather if enabled and (current succeeded OR current disabled)
		if fetch_forecast and (current_success or not fetch_current):
			forecast_url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&metric=true"
			
			log_debug("Fetching forecast weather...")
			forecast_json = fetch_weather_with_retries(forecast_url, max_retries=1)
			
			if forecast_json:  # Count the API call even if processing fails later
				forecast_api_calls += 1
				api_call_count += 1
				
			forecast_fetch_length = min(API.DEFAULT_FORECAST_HOURS,API.MAX_FORECAST_HOURS)
			
			if forecast_json and len(forecast_json) >= forecast_fetch_length:
				# Extract first 3 hours of forecast data
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
				
				forecast_success = True
			
			else:
				log_warning("12-hour forecast fetch failed or insufficient data")
				forecast_data = None
		
		# Log API call statistics
		log_info(f"API Stats: Total={api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={current_api_calls}, Forecast={forecast_api_calls}", include_memory=True)
		
		# Determine overall success
		any_success = current_success or forecast_success
		
		if any_success:
			# Reset failure tracking on any success
			consecutive_failures = 0
			last_successful_weather = time.monotonic()
		else:
			consecutive_failures += 1
		
		# Check for preventive restart
		if api_call_count >= API.MAX_CALLS_BEFORE_RESTART:
			log_warning(f"Preventive restart after {api_call_count} API calls", include_memory=True)
			cleanup_global_session()
			interruptible_sleep(API.RETRY_DELAY)
			supervisor.reload()
		
		return current_data, forecast_data
		
	except Exception as e:
		log_error(f"Weather fetch error: {e}")
		consecutive_failures += 1
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
	global api_call_count, current_api_calls, forecast_api_calls
	
	return {
		"total_calls": api_call_count,
		"current_calls": current_api_calls,
		"forecast_calls": forecast_api_calls,
		"remaining_calls": API.MAX_CALLS_BEFORE_RESTART - api_call_count,
		"restart_threshold": API.MAX_CALLS_BEFORE_RESTART
	}
	
def should_fetch_forecast():
	"""Check if forecast data needs to be refreshed"""
	global last_forecast_fetch
	current_time = time.monotonic()  # 15 minutes
	log_debug(f"LAST FORECAST FETCH: {last_forecast_fetch} seconds ago. Needs Refresh? = {(current_time - last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL}")
	return (current_time - last_forecast_fetch) >= Timing.FORECAST_UPDATE_INTERVAL


### DISPLAY UTILITIES ###

def detect_matrix_type():
	"""Auto-detect matrix wiring type (cached for performance)"""
	global _matrix_type_cache
	
	if _matrix_type_cache is not None:
		return _matrix_type_cache
	
	import microcontroller
	uid = microcontroller.cpu.uid
	device_id = "".join([f"{b:02x}" for b in uid[-3:]])
	
	device_mappings = {
		System.DEVICE_TYPE1_ID: "type1",
		System.DEVICE_TYPE2_ID: "type2", # BIG MATRIX
	}
	
	_matrix_type_cache = device_mappings.get(device_id, "type1")
	log_info(f"Device ID: {device_id}, Matrix type: {_matrix_type_cache}")
	return _matrix_type_cache
	
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
	"""Calculate pixel width of text"""
	if not text:
		return 0
	temp_label = bitmap_label.Label(font, text=text)
	bbox = temp_label.bounding_box
	return bbox[2] if bbox else 0
	
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
			
			log_info(f"Loaded {line_count} events successfully from CSV", include_memory = True)
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
	global cached_events
	
	if cached_events is None:
		cached_events = load_events_from_csv()
		# Ensure we always have events even if CSV and fallback both fail
		if not cached_events:
			log_warning("Warning: No events loaded, using minimal fallback")
			cached_events = {}
	
	return cached_events


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
	while len(main_group):
		main_group.pop()

### DISPLAY FUNCTIONS ###

def right_align_text(text, font, right_edge):
	return right_edge - get_text_width(text, font)

def center_text(text, font, area_x, area_width):  
	return area_x + (area_width - get_text_width(text, font)) // 2

def get_day_color(rtc):
	"""Get color for day of week indicator"""
	day_colors = {
		0: COLORS["RED"],      # Monday
		1: COLORS["ORANGE"],   # Tuesday  
		2: COLORS["YELLOW"],   # Wednesday
		3: COLORS["GREEN"],    # Thursday
		4: COLORS["AQUA"],     # Friday
		5: COLORS["PURPLE"],   # Saturday
		6: COLORS["PINK"]      # Sunday
	}
	
	weekday = rtc.datetime.tm_wday  # 0=Monday, 6=Sunday
	return day_colors.get(weekday, COLORS["WHITE"])  # Default to white if error

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
		black_pixel = Line(DayIndicator.MARGIN_LEFT_X, y, DayIndicator.MARGIN_LEFT_X, y, COLORS["BLACK"])
		main_group.append(black_pixel)
	
	# Add 1-pixel black margin to the bottom (y=4)
	for x in range(DayIndicator.MARGIN_LEFT_X, DayIndicator.X+DayIndicator.SIZE):  # Include the corner pixel at (59,4)
		black_pixel = Line(x, DayIndicator.MARGIN_BOTTOM_Y, x, DayIndicator.MARGIN_BOTTOM_Y, COLORS["BLACK"])
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
		main_group.append(Line(x_start, Layout.UV_BAR_Y, x_start - 1 + uv_length, Layout.UV_BAR_Y, COLORS["DIMMEST_WHITE"]))
		
		# UV spacing dots (black pixels every 3)
		for i in Visual.UV_SPACING_POSITIONS:
			if i < uv_length:
				main_group.append(Line(x_start + i, Layout.UV_BAR_Y, x_start + i, Layout.UV_BAR_Y, COLORS["BLACK"]))
	
	# Humidity bar 
	if humidity > 0:
		humidity_length = calculate_humidity_bar_length(humidity)
		
		# Main humidity line
		main_group.append(Line(x_start, Layout.HUMIDITY_BAR_Y, x_start - 1 + humidity_length, Layout.HUMIDITY_BAR_Y, COLORS["DIMMEST_WHITE"]))
		
		# Humidity spacing dots (black pixels every 2 = every 20%)
		for i in Visual.HUMIDITY_SPACING_POSITIONS:  # Positions for 20%, 40%, 60%, 80%
			if i < humidity_length:
				main_group.append(Line(x_start + i, Layout.HUMIDITY_BAR_Y, x_start + i, Layout.HUMIDITY_BAR_Y, COLORS["BLACK"]))


def show_weather_display(rtc, duration, weather_data=None):
	"""Display weather information and time"""
	log_debug("Displaying weather...", include_memory=True)
	
	# Use provided data or fetch fresh data
	if weather_data is None:
		# Fetch fresh weather data (existing behavior)
		if DISPLAY_CONFIG["dummy_weather"]:
			weather_data = TestData.DUMMY_WEATHER_DATA
		else:
			weather_data = fetch_weather_data()
	
	# Log with duration information
	if weather_data:
		log_info(f"Displaying Current Weather for {duration_message(duration)}: {weather_data['weather_text']}, {weather_data['temperature']}°C", include_memory=True)
	
	if not weather_data:
		log_warning("Weather unavailable, showing clock")
		show_clock_display(rtc, duration)
		return
	
	# Rest of your existing function code stays exactly the same...
	clear_display()
	
	# Create display elements
	temp_text = bitmap_label.Label(bg_font, color=COLORS["DIMMEST_WHITE"], x=Layout.WEATHER_TEMP_X, y=Layout.WEATHER_TEMP_Y, background_color = COLORS["BLACK"], padding_top =Layout.BG_PADDING_TOP, padding_bottom = 1, padding_left = 1,)
	feels_like_text = bitmap_label.Label(font, color=COLORS["DIMMEST_WHITE"], y=Layout.FEELSLIKE_Y, background_color = COLORS["BLACK"], padding_top=Layout.BG_PADDING_TOP, padding_bottom=-2, padding_left = 1,)
	feels_shade_text = bitmap_label.Label(font, color=COLORS["DIMMEST_WHITE"], y=Layout.FEELSLIKE_SHADE_Y, background_color = COLORS["BLACK"], padding_top=Layout.BG_PADDING_TOP, padding_bottom=-2, padding_left = 1,)
	time_text = bitmap_label.Label(font, color=COLORS["DIMMEST_WHITE"], x=Layout.WEATHER_TIME_X, y=Layout.WEATHER_TIME_Y, background_color = COLORS["BLACK"], padding_top=Layout.BG_PADDING_TOP, padding_bottom=-2, padding_left = 1,)
	
	# Load weather icon
	try:
		bitmap, palette = load_bmp_image(f"{Paths.WEATHER_ICONS}/{weather_data['weather_icon']}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		main_group.append(image_grid)
	except Exception as e:
		log_warning(f"Icon load failed: {e}")
	
	# Setup temperature display
	temp_text.text = f"{round(weather_data['temperature'])}°"
	main_group.append(temp_text)
	
	# Add UV and humidity indicator bars
	add_indicator_bars(main_group, temp_text.x, weather_data['uv_index'], weather_data['humidity'])
	
	# Add feels-like temperatures if different
	temp_rounded = round(weather_data['temperature'])
	feels_like_rounded = round(weather_data['feels_like'])
	feels_shade_rounded = round(weather_data['feels_shade'])
	
	if feels_like_rounded != temp_rounded:
		feels_like_text.text = f"{feels_like_rounded}°"
		feels_like_text.x = right_align_text(feels_like_text.text, font, Layout.RIGHT_EDGE)
		main_group.append(feels_like_text)
	
	if feels_shade_rounded != feels_like_rounded:
		feels_shade_text.text = f"{feels_shade_rounded}°"
		feels_shade_text.x = right_align_text(feels_shade_text.text, font, Layout.RIGHT_EDGE)
		main_group.append(feels_shade_text)
	
	main_group.append(time_text)
	
	# Add day indicator
	if DISPLAY_CONFIG["weekday_color"]:
		add_day_indicator(main_group, rtc)
		log_debug(f"Showing Weekday Color Indicator on Weather Display for {get_day_color(rtc)}")
	else:
		log_debug("Weekday Color Indicator Disabled")

	# Display update loop
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		# Update time display
		hour = rtc.datetime.tm_hour
		display_hour = hour % 12 if hour % 12 != 0 else 12
		current_time = f"{display_hour}:{rtc.datetime.tm_min:02d}"
		time_text.text = current_time
		
		# Position time text
		if feels_shade_rounded != feels_like_rounded:
			time_text.x = center_text(current_time, font, 0, Display.WIDTH)
		else:
			time_text.x = right_align_text(current_time, font, Layout.RIGHT_EDGE)
		
		interruptible_sleep(1)

def show_clock_display(rtc, duration=Timing.CLOCK_FALLBACK):
	"""Display clock as fallback when weather unavailable"""
	log_warning(f"Displaying clock for {duration_message(Timing.CLOCK_FALLBACK)}...", include_memory = True)
	clear_display()
	
	date_text = bitmap_label.Label(font, color=COLORS["DIMMEST_WHITE"], x=Layout.CLOCK_DATE_X, y=Layout.CLOCK_DATE_Y)
	time_text = bitmap_label.Label(bg_font, color=COLORS[Strings.DEFAULT_EVENT_COLOR], x=Layout.CLOCK_TIME_X, y=Layout.CLOCK_TIME_Y)
	
	main_group.append(date_text)
	main_group.append(time_text)
			  
	# Add day indicator after other elements
	if DISPLAY_CONFIG["weekday_color"]:
		add_day_indicator(main_group, rtc)
		log_debug(f"Showing Weekday Color Indicator on Clock Display")
	else:
		log_debug("Weekday Color Indicator Disabled")
	
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		dt = rtc.datetime
		date_str = f"{MONTHS[dt.tm_mon].upper()} {dt.tm_mday:02d}"
		
		hour = dt.tm_hour
		display_hour = hour % 12 if hour % 12 != 0 else 12
		time_str = f"{display_hour}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
		
		date_text.text = date_str
		time_text.text = time_str
		interruptible_sleep(1)
	
	# Check for restart conditions
	time_since_success = time.monotonic() - last_successful_weather
	if consecutive_failures >= System.MAX_LOG_FAILURES_BEFORE_RESTART or time_since_success > Timing.CLOCK_FALLBACK_THRESHOLD:  # 10 minutes
		log_warning("Restarting due to weather failures")
		interruptible_sleep(API.RETRY_DELAY)
		supervisor.reload()
		
def show_event_display(rtc, duration):
		"""Display special calendar events - cycles through multiple events if present"""
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
			log_info(f"Showing event: {event_data[1]}, for {duration_message(duration)}", include_memory=True)
			_display_single_event(event_data, rtc, duration)
		else:
			# Multiple events - split time between them
			event_duration = max(duration // num_events, Timing.MIN_EVENT_DURATION)
			log_info(f"Showing {num_events} events, {duration_message(duration)} each", include_memory=True)
			
			for i, event_data in enumerate(event_list):
				log_info(f"Event {i+1}/{num_events}: {event_data[1]}")
				_display_single_event(event_data, rtc, event_duration)
		
		return True

def _display_single_event(event_data, rtc, duration):
		"""Helper function to display a single event"""
		clear_display()
		
		# Force garbage collection before loading images
		gc.collect()
		
		try:
			if event_data[1] == "Birthday":
				# For birthday events, use the original cake image layout
				bitmap, palette = load_bmp_image(Paths.BIRTHDAY_IMAGE)
				image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
				main_group.append(image_grid)
			else:
				# Load event-specific image (25x28 positioned at top right)
				image_file = f"{Paths.EVENT_IMAGES}/{event_data[2]}"
				try:
					bitmap, palette = load_bmp_image(image_file)
				except Exception as e:
					log_warning(f"Failed to load {image_file}: {e}")
					bitmap, palette = load_bmp_image(Paths.FALLBACK_EVENT_IMAGE)
				
				# Position 25px wide image at top right
				image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
				image_grid.x = 37  # Right-aligned for 25px wide image
				image_grid.y = 2   # Start at y = 2 as requested
				
				# Calculate optimal text positions dynamically
				line1_text = event_data[1]  # e.g., "Cumple"
				line2_text = event_data[0]  # e.g., "Puchis"
				text_color = event_data[3] if len(event_data) > 3 else Strings.DEFAULT_EVENT_COLOR  # Get color from CSV
				
				# Color_map through dictionary access:
				line2_color = COLORS.get(text_color.upper(), COLORS[Strings.DEFAULT_EVENT_COLOR])
				
				# Get dynamic positions with 1px bottom margin and 1px line spacing
				line1_y, line2_y = calculate_bottom_aligned_positions(
					font, 
					line1_text, 
					line2_text,
					display_height=Display.HEIGHT,
					bottom_margin=Layout.BOTTOM_MARGIN,  # Very tight bottom margin
					line_spacing=Layout.LINE_SPACING    # Minimal spacing between lines
				)
				
				# Create text labels with calculated positions
				text1 = bitmap_label.Label(
					font,
					color=COLORS["DIMMEST_WHITE"],
					text=line1_text,
					x=Layout.TEXT_MARGIN, y=line1_y
				)
				
				text2 = bitmap_label.Label(
					font,
					color=line2_color,  # Use color from CSV
					text=line2_text,
					x=Layout.TEXT_MARGIN,
					y=line2_y
				)
				
				# Add elements to display
				main_group.append(image_grid)
				main_group.append(text1)
				main_group.append(text2)
				
				# Add day indicator after other elements
				if DISPLAY_CONFIG["weekday_color"]:
					add_day_indicator(main_group, rtc)
					log_debug(f"Showing Weekday Color Indicator on Event Display")
				else:
					log_debug("Weekday Color Indicator Disabled")
				
		except Exception as e:
			log_error(f"Event display error: {e}")
		
		# Wait for specified duration
		interruptible_sleep(duration)
		
		# Optional: Clean up after event display
		gc.collect()
	
def show_color_test_display(duration=Timing.COLOR_TEST):
	log_info(f"Displaying Color Test for {duration_message(Timing.COLOR_TEST)}", include_memory=True)
	clear_display()
	gc.collect()
	
	try:
		# Get test colors dynamically from COLORS dictionary
		test_color_names = ["MINT", "BUGAMBILIA", "LILAC", "RED", "GREEN", "BLUE", 
						   "ORANGE", "YELLOW", "CYAN", "PURPLE", "PINK", "AQUA"]
		texts = ["Aa", "Bb", "Cc", "Dd", "Ee", "Ff", "Gg", "Hh", "Ii", "Jj", "Kk", "Ll"]
		
		key_text = "Color Key: "
		
		for i, (color_name, text) in enumerate(zip(test_color_names, texts)):
			color = COLORS[color_name]
			col = i // Visual.COLOR_TEST_GRID_COLS
			row = i % Visual.COLOR_TEST_GRID_ROWS
			
			label = bitmap_label.Label(
				font, color=color, text=text,
				x=Layout.COLOR_TEST_TEXT_X + col * Visual.COLOR_TEST_COL_SPACING , y=Layout.COLOR_TEST_TEXT_Y + row * Visual.COLOR_TEST_ROW_SPACING
			)
			main_group.append(label)
			key_text += f"{text}={color_name}(0x{color:06X}) | "
	
	except Exception as e:
		log_error(f"Color Test display error: {e}")
	
	log_info(key_text)
	interruptible_sleep(duration)
	gc.collect()
	return True
	
def show_forecast_display(current_data=None, forecast_data=None, duration=30):
	"""Display 3-column forecast: Current time, +1 hour, +2 hours"""
	
	# Check if we have real data - skip display if not
	if not current_data or not forecast_data or len(forecast_data) < 3:
		log_warning(f"Skipping forecast display - insufficient data (current: {current_data is not None}, forecast: {forecast_data is not None and len(forecast_data) >= 3 if forecast_data else False})")
		return False
	
	# Log with real data
	log_info(f"Displaying Forecast for {duration_message(duration)}: Current {current_data['temperature']}°C, +1hr {forecast_data[0]['temperature']}°C, +2hr {forecast_data[1]['temperature']}°C", include_memory=True)
	
	clear_display()
	gc.collect()
	
	try:
		# Use real data only (no fallbacks)
		col1_temp = f"{round(current_data['temperature'])}°"
		col1_icon = f"{current_data['weather_icon']}.bmp"
		
		col2_temp = f"{round(forecast_data[0]['temperature'])}°"
		col3_temp = f"{round(forecast_data[1]['temperature'])}°"
		col2_icon = f"{forecast_data[0]['weather_icon']}.bmp"
		col3_icon = f"{forecast_data[1]['weather_icon']}.bmp"
		
		hour_plus_1 = int(forecast_data[0]['datetime'][11:13]) % System.HOURS_IN_DAY
		hour_plus_2 = int(forecast_data[1]['datetime'][11:13]) % System.HOURS_IN_DAY
		
		# Generate time labels FIRST
		if rtc_instance:
			current_hour = rtc_instance.datetime.tm_hour
			current_minute = rtc_instance.datetime.tm_min
			
			display_hour = current_hour % System.HOURS_IN_HALF_DAY if current_hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
			col1_time = f"{display_hour}:{current_minute:02d}"
			
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
		else:
			log_error("RTC ERROR - No data to show forecast headers")
		
		# NOW define columns with all the data
		columns = [
			{"image": col1_icon, "x": Layout.FORECAST_COL1_X, "time": col1_time, "temp": col1_temp},
			{"image": col2_icon, "x": Layout.FORECAST_COL2_X, "time": col2_time, "temp": col2_temp},
			{"image": col3_icon, "x": Layout.FORECAST_COL3_X, "time": col3_time, "temp": col3_temp}
		]
		
		# Column positioning
		column_y = Layout.FORECAST_COLUMN_Y
		column_width = Layout.FORECAST_COLUMN_WIDTH
		time_y = Layout.FORECAST_TIME_Y
		temp_y = Layout.FORECAST_TEMP_Y
		first_time_label = None
		
		# Load and position weather icon columns
		for i, col in enumerate(columns):
			try:
				# Try actual weather icons first
				try:
					bitmap, palette = load_bmp_image(f"{Paths.COLUMN_IMAGES}/{col['image']}")
				except:
					# Fallback to column images
					bitmap, palette = load_bmp_image(f"{Paths.COLUMN_IMAGES}/{i+1}.bmp")
					log_warning(f"Used fallback column image for column {i+1}")
				
				col_img = displayio.TileGrid(bitmap, pixel_shader=palette)
				col_img.x = col["x"]
				col_img.y = column_y
				main_group.append(col_img)
			except Exception as e:
				log_warning(f"Failed to load column {i+1} image: {e}")
		
		# Add time labels with dynamic centering
		for i, col in enumerate(columns):
			centered_x = max(center_text(col["time"], font, col["x"], column_width),1)
			
			time_label = bitmap_label.Label(
				font,
				color=COLORS["DIMMEST_WHITE"],
				text=col["time"],
				x=centered_x,
				y=time_y
			)
			main_group.append(time_label)
			
			# Store reference to first column's time label
			if i == 0:
				first_time_label = time_label
		
		# Add temperature labels with dynamic centering
		for col in columns:
			centered_x = center_text(col["temp"], font, col["x"], column_width) + 1
			
			temp_label = bitmap_label.Label(
				font,
				color=COLORS["DIMMEST_WHITE"],
				text=col["temp"],
				x=centered_x,
				y=temp_y
			)
			main_group.append(temp_label)
		
		# Add day indicator if enabled
		if DISPLAY_CONFIG["weekday_color"]:
			add_day_indicator(main_group, rtc_instance)
			log_debug("Showing Weekday Color Indicator on Forecast Display")
		
		# Display update loop with live time - REMOVE duplicate sleep
		start_time = time.monotonic()
		while time.monotonic() - start_time < duration:
			# Update first column time every second
			if rtc_instance and first_time_label:
				current_hour = rtc_instance.datetime.tm_hour
				current_minute = rtc_instance.datetime.tm_min
				display_hour = current_hour % 12 if current_hour % 12 != 0 else 12
				new_time = f"{display_hour}:{current_minute:02d}"
				
				if first_time_label.text != new_time:
					first_time_label.text = new_time
					# Recenter the text
					first_time_label.x = max(center_text(new_time, font, columns[0]["x"], column_width),1)
			
			interruptible_sleep(1)
	
	except Exception as e:
		log_error(f"Forecast display error: {e}")
		return False
	
	gc.collect()
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
	global startup_time
	
	if not DAILY_RESET_ENABLED:
		return
	
	current_time = time.monotonic()
	hours_running = (current_time - startup_time) / 3600
	
	# Scheduled restart conditions
	should_restart = (
		hours_running > System.HOURS_BEFORE_DAILY_RESTART or
		(hours_running > 1 and 
		 rtc.datetime.tm_hour == Timing.DAILY_RESET_HOUR and 
		 rtc.datetime.tm_min < System.RESTART_GRACE_MINUTES)
	)
	
	if should_restart:
		log_info(f"Daily restart triggered ({hours_running:.1f}h runtime)", include_memory = True)
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


### MAIN PROGRAM ###

def main():
	"""Main program execution"""
	global last_successful_weather, startup_time, last_forecast_fetch, cached_forecast_data, COLORS
	
	# Initialize RTC FIRST for proper timestamps
	rtc = setup_rtc()
	
	log_info("=== WEATHER DISPLAY STARTUP ===", include_memory=True)
	
	try:
		# Initialize hardware
		initialize_display()
		
		# Detect matrix type and initialize colors
		matrix_type = detect_matrix_type()
		COLORS = get_matrix_colors()
		
		# Load events
		events = get_events()
		log_debug(f"System initialized - {len(events)} events loaded")
		
		if DISPLAY_CONFIG["test_date"]:
			update_rtc_date(rtc, TestData.TEST_YEAR, TestData.TEST_MONTH, TestData.TEST_DAY)
		
		# Network operations (can be slower/fail)
		wifi_connected = setup_wifi()
		
		if wifi_connected and not DISPLAY_CONFIG["test_date"]:
			sync_time_with_timezone(rtc)
			log_info("Time synchronized with NTP")
		elif DISPLAY_CONFIG["test_date"]:
			log_debug(f"Skipping NTP sync - using test date: {rtc.datetime.tm_year:04d}/{rtc.datetime.tm_mon:02d}/{rtc.datetime.tm_mday:02d}")
		else:
			log_warning("Starting without WiFi - using RTC time only")
		
		# Set startup time
		startup_time = time.monotonic()
		last_successful_weather = startup_time
		
		log_info("Entering main display loop (Press CTRL+C to stop)", include_memory=True)
		
		# Main display loop
		while True:
			try:
				# System maintenance
				check_daily_reset(rtc)
				
				# Calculate display durations
				current_duration, forecast_duration, event_duration = calculate_display_durations()
				
				# Initialize variables to avoid "referenced before assignment" error
				forecast_shown = False
				current_data = None
				forecast_data = None
				
				# Forecast caching logic
				if DISPLAY_CONFIG["forecast"]:
					if should_fetch_forecast():
						# Fetch both current and forecast
						current_data, forecast_data = fetch_current_and_forecast_weather()
						if forecast_data:  # Only cache if successful
							cached_forecast_data = forecast_data
							last_forecast_fetch = time.monotonic()
							log_debug("Fetched fresh forecast data")
					else:
						# Fetch only current weather, use cached forecast
						DISPLAY_CONFIG["fetch_forecast"] = False
						current_data, _ = fetch_current_and_forecast_weather()  # FIXED THIS LINE
						DISPLAY_CONFIG["fetch_forecast"] = True  # Reset for next time
						forecast_data = cached_forecast_data
						log_debug("Using cached forecast data")
					
					if current_data and forecast_data:
						forecast_shown = show_forecast_display(current_data, forecast_data, forecast_duration)
					
					if not forecast_shown:
						log_info("Forecast skipped - extending current weather time")
						current_duration += forecast_duration
				else:
					log_debug("Forecast display disabled")
				
				# Current weather (with potentially extended duration)
				if DISPLAY_CONFIG["weather"]:
					if not current_data:  # Only fetch if we don't already have it
						current_data = fetch_current_and_forecast_weather()
					show_weather_display(rtc, current_duration, current_data)
				else:
					log_debug("Weather display disabled")
				
				# Events
				if DISPLAY_CONFIG["events"]:
					event_shown = show_event_display(rtc, event_duration)
					if not event_shown:
						interruptible_sleep(1)
				else:
					log_debug("Event display disabled")
				
				# Remove color test from main loop or keep it separate
				if DISPLAY_CONFIG["color_test"]:
					show_color_test_display(Timing.COLOR_TEST)
					
			except Exception as e:
				log_error(f"Display loop error: {e}", include_memory=True)
				interruptible_sleep(Timing.SLEEP_BETWEEN_ERRORS)
				
	except KeyboardInterrupt:
		log_info("Program interrupted by user")
	
	except Exception as e:
		log_error(f"Critical system error: {e}", include_memory=True)
		time.sleep(Timing.RESTART_DELAY)
		supervisor.reload()
	
	finally:
		# Cleanup code
		log_info("Cleaning up before exit...")
		clear_display()
		cleanup_global_session()

# Program entry point
if __name__ == "__main__":
	main()