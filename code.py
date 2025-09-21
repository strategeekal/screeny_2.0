##### TIME AND WEATHER SCREENY - OPTIMIZED #####

### Import Libraries ###
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

### CONSTANTS AND CONFIGURATION ###

# Display Control Configuration
DISPLAY_CONFIG = {
	"weather": False,
	"dummy_weather": True,
	"events": False,
	"clock_fallback": True,
	"color_test": True,
	"weather_duration": 10,
	"event_duration": 10,
	"clock_fallback_duration": 300,
	"color_test_duration": 300
}

# Debugging
ESTIMATED_TOTAL_MEMORY = 2000000
DEBUG_MODE = False
LOG_TO_FILE = False  # Set to True if filesystem becomes writable
LOG_MEMORY_STATS = True  # Include memory info in logs
LOG_FILE = "weather_log.txt"

# Dummy Weather Control
DUMMY_WEATHER_DATA = {
	"weather_icon": 34,
	"temperature": -12,
	"feels_like": -13.6,
	"feels_shade": -14.6,
	"humidity": 90,
	"uv_index":7,
	"weather_text": "DUMMY",
	"is_day_time": True,
}

# Base colors - used by both matrix types for most colors
_BASE_COLORS = {
	"BLACK": 0x000000,
	"DIMMEST_WHITE": 0x101010,
	"MINT": 0x080816,
	"BUGAMBILIA": 0x101000,
	"LILAC": 0x161408,
}

# Corrections for colors that differ on second display
_COLOR_CORRECTIONS = {
	"type2": {
		"MINT": 0x081608,
		"BUGAMBILIA": 0x011000,  
		"LILAC": 0x141608,
	}
	# type1 uses base colors (no corrections needed)
}


# Temporary placeholder values (will be overwritten by initialize_colors())
BLACK = 0x000000
DIMMEST_WHITE = 0x101010
MINT = 0x080816
BUGAMBILIA = 0x101000
LILAC = 0x161408

DEFAULT_TEXT_COLOR = DIMMEST_WHITE

# API Configuration
ACCUWEATHER_LOCATION_KEY = "2626571"
MAX_API_CALLS_BEFORE_RESTART = 8

# System Configuration
DAILY_RESET_ENABLED = True
DAILY_RESET_HOUR = 3

# Event Configuration
CSV_EVENTS_FILE = "events.csv"
DEFAULT_EVENT_COLOR = "MINT"

TIMEZONE_CONFIG = {
	"timezone": "America/Chicago",
}

# Timezone offset table
TIMEZONE_OFFSETS = {
	"America/New_York": {"std": -5, "dst": -4, "dst_start": (3, 8), "dst_end": (11, 7)},
	"America/Chicago": {"std": -6, "dst": -5, "dst_start": (3, 8), "dst_end": (11, 7)},
	"America/Denver": {"std": -7, "dst": -6, "dst_start": (3, 8), "dst_end": (11, 7)},
	"America/Los_Angeles": {"std": -8, "dst": -7, "dst_start": (3, 8), "dst_end": (11, 7)},
	"Europe/London": {"std": 0, "dst": 1, "dst_start": (3, 25), "dst_end": (10, 25)},
	"Europe/Paris": {"std": 1, "dst": 2, "dst_start": (3, 25), "dst_end": (10, 25)},
	"Asia/Tokyo": {"std": 9, "dst": 9, "dst_start": None, "dst_end": None},  # No DST
}

### GLOBAL STATE ###

# Hardware instances
rtc_instance = None
display = None
main_group = None
_matrix_type_cache = None # Matrix type cache - loaded once at startup
cached_events = None # Event cache - loaded once at startup

# API tracking
api_call_count = 0
consecutive_failures = 0
last_successful_weather = 0
startup_time = 0

# Load fonts once at startup
bg_font = bitmap_font.load_font("fonts/bigbit10-16.bdf")
font = bitmap_font.load_font("fonts/tinybit6-16.bdf")

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
			mem_percent = ((ESTIMATED_TOTAL_MEMORY - free_mem) / ESTIMATED_TOTAL_MEMORY) * 100
			log_line += f" (Mem: {free_mem//1024}KB/{mem_percent:.1f}%)"
		
		print(log_line)
		
		# File logging if enabled
		if LOG_TO_FILE:
			try:
				with open(LOG_FILE, "a") as f:
					f.write(f"{log_line}\n")
			except OSError:
				if not hasattr(log_entry, '_fs_warning_shown'):
					print("[LOG] Warning: Filesystem read-only, file logging disabled")
					log_entry._fs_warning_shown = True
	
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

### HARDWARE INITIALIZATION ###

def initialize_display():
	"""Initialize RGB matrix display"""
	global display, main_group
	
	displayio.release_displays()
	
	matrix = rgbmatrix.RGBMatrix(
		width=64, height=32, bit_depth=6,
		rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1, 
				 board.MTX_R2, board.MTX_G2, board.MTX_B2],
		addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, 
				  board.MTX_ADDRC, board.MTX_ADDRD],
		clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, 
		output_enable_pin=board.MTX_OE,
		serpentine=True, doublebuffer=True,
	)
	
	display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
	display.brightness = 0.1
	main_group = displayio.Group()
	display.root_group = main_group
	log_info("Display initiated successfully")

def setup_rtc():
	"""Initialize RTC with retry logic"""
	global rtc_instance
	
	for attempt in range(5):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			rtc_instance = rtc
			log_info(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			log_warning(f"RTC attempt {attempt + 1} failed: {e}")
			if attempt < 4:
				time.sleep(2)
	
	log_error("RTC initialization failed, restarting...")
	supervisor.reload()

### NETWORK FUNCTIONS ###

def setup_wifi():
	"""Connect to WiFi with simplified retry logic"""
	ssid = os.getenv("CIRCUITPY_WIFI_SSID")
	password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
	
	if not ssid or not password:
		log_warning("WiFi credentials missing")
		return False
	
	for attempt in range(3):
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
				time.sleep(2)
	
	log_error("WiFi connection failed")
	return False

def get_timezone_offset(timezone_name, utc_datetime):
	"""Calculate timezone offset including DST for a given timezone"""
	
	if timezone_name not in TIMEZONE_OFFSETS:
		log_warning(f"Unknown timezone: {timezone_name}, using Chicago")
		timezone_name = "America/Chicago"
	
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
	
	timezone_name = TIMEZONE_CONFIG["timezone"]
	
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
	for _ in range(3):
		gc.collect()

def fetch_weather_data():
	"""Fetch current weather data with matrix-specific API keys"""
	global consecutive_failures, last_successful_weather, api_call_count
	
	# Increment API call counter
	api_call_count += 1
	
	# Monitor memory just before planned restart
	if api_call_count >= MAX_API_CALLS_BEFORE_RESTART - 1:
		log_warning(f"API call #{api_call_count} - restart imminent", include_memory = True)
	
	# Resource cleanup variables
	pool = None
	requests = None
	response = None
	
	try:
		# Get matrix-specific API key
		api_key = None
		matrix_type = detect_matrix_type()
		
		# Define which API key variable to look for based on matrix type
		if matrix_type == "type1":
			api_key_name = "ACCUWEATHER_API_KEY_TYPE1"
		elif matrix_type == "type2":
			api_key_name = "ACCUWEATHER_API_KEY_TYPE2"
		else:
			# Fallback to original key for unknown types
			api_key_name = "ACCUWEATHER_API_KEY"
		
		# Read the appropriate API key from settings
		try:
			with open("settings.toml", "r") as f:
				for line in f:
					if line.startswith(api_key_name):
						api_key = line.split("=")[1].strip().strip('"').strip("'")
						log_debug(f"Using {api_key_name} for {matrix_type}")
						break
		except Exception as e:
			log_warning(f"Failed to read API key: {e}")
			
		# Fallback to original key if matrix-specific key not found
		if not api_key:
			log_warning(f"{api_key_name} not found, trying fallback key")
			try:
				with open("settings.toml", "r") as f:
					for line in f:
						if line.startswith("ACCUWEATHER_API_KEY"):
							api_key = line.split("=")[1].strip().strip('"').strip("'")
							log_warning("Using fallback ACCUWEATHER_API_KEY")
							break
			except Exception as e:
				log_error(f"Failed to read fallback API key: {e}")
			
		if not api_key:
			log_error("No API key found")
			consecutive_failures += 1
			return None
		
		# Build request URL
		url = f"https://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_LOCATION_KEY}?apikey={api_key}&details=true"
		
		# Setup and execute request
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		requests = adafruit_requests.Session(pool, ssl.create_default_context())
		response = requests.get(url)
		
		if response.status_code != 200:
			log_error(f"API error: {response.status_code}")
			consecutive_failures += 1
			return None
		
		# Parse response
		weather_json = response.json()
		if not weather_json:
			log_warning("Empty weather response")
			consecutive_failures += 1
			return None
		
		# Extract weather data
		current = weather_json[0]
		temp_data = current.get("Temperature", {}).get("Metric", {})
		realfeel_data = current.get("RealFeelTemperature", {}).get("Metric", {})
		realfeel_shade_data = current.get("RealFeelTemperatureShade", {}).get("Metric", {})
		
		weather_data = {
			"weather_icon": current.get("WeatherIcon", 0),
			"temperature": temp_data.get("Value", 0),
			"feels_like": realfeel_data.get("Value", 0),
			"feels_shade": realfeel_shade_data.get("Value", 0),
			"humidity": current.get("RelativeHumidity", 0),
			"uv_index": current.get("UVIndex", 0),
			"weather_text": current.get("WeatherText", "Unknown"),
			"is_day_time": current.get("IsDayTime", True),
		}
		
		# Log successful weather fetch with current count
		m, s = divmod(DISPLAY_CONFIG["weather_duration"], 60)
		log_info(f"Displaying Weather for {m} minutes {s} seconds: {weather_data['weather_text']}, {weather_data['temperature']}°C (API #{api_call_count}/{MAX_API_CALLS_BEFORE_RESTART})", include_memory=True)
		
		# Reset failure tracking on success
		consecutive_failures = 0
		last_successful_weather = time.monotonic()
		
		# Check for preventive restart
		if api_call_count >= MAX_API_CALLS_BEFORE_RESTART:
			log_warning(f"Preventive restart after {api_call_count} API calls", include_memory=True)
			time.sleep(2)
			supervisor.reload()
		
		return weather_data
		
	except Exception as e:
		log_error(f"Weather fetch error: {e}")
		consecutive_failures += 1
		return None
		
	finally:
		# Cleanup resources in reverse order
		for resource in [response, requests, pool]:
			if resource:
				try:
					if hasattr(resource, 'close'):
						resource.close()
					del resource
				except:
					pass
		cleanup_sockets()

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
		"2236c5": "type1",
		"f78b47": "type2", # BIG MATRIX
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

# Initialize colors after matrix detection (this will be called in main())
def initialize_colors():
	"""Initialize color constants based on matrix type"""
	global BLACK, DIMMEST_WHITE, MINT, BUGAMBILIA, LILAC, DEFAULT_TEXT_COLOR
	
	colors = get_matrix_colors()
	BLACK = colors["BLACK"]
	DIMMEST_WHITE = colors["DIMMEST_WHITE"] 
	MINT = colors["MINT"]
	BUGAMBILIA = colors["BUGAMBILIA"]
	LILAC = colors["LILAC"]
	DEFAULT_TEXT_COLOR = DIMMEST_WHITE
	
	log_debug(f"Colors initialized for matrix type: {detect_matrix_type()}")
	log_debug(f"MINT color: 0x{MINT:06X}")

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
	"""Load events from CSV file - called only once at startup"""
	events = {}
	try:
		log_debug(f"Loading events from {CSV_EVENTS_FILE}...")
		with open(CSV_EVENTS_FILE, "r") as f:
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
						color = parts[4] if len(parts) > 4 else DEFAULT_EVENT_COLOR  # Default to MINT
						
						# Convert MM-DD to MMDD format for lookup
						date_key = date.replace("-", "")
						events[date_key] = [line1, line2, image, color]
						line_count += 1
			
			log_info(f"Loaded {line_count} events successfully from CSV", include_memory = True)
			return events
			
	except Exception as e:
		log_warning(f"Failed to load events.csv: {e}")
		log_warning("Using fallback hardcoded events")
		# Return your current hardcoded events as fallback
		return {
			"0101": ["New Year", "Happy", "new_year.bmp", "BUGAMBILIA"],
			"0210": ["Emilio", "Birthday", "cake.bmp", "MINT"],
			"0703": ["Gaby", "Birthday", "cake.bmp", "MINT"],
			"0704": ["July", "4th of", "us_flag.bmp", "BUGAMBILIA"],
			"0825": ["Diego", "Birthday", "cake.bmp", "MINT"],
			"0916": ["Mexico", "Viva", "mexico_flag_v3.bmp", "BUGAMBILIA"],
			"0922": ["Puchis", "Cumple", "panzon.bmp", "MINT"],
			"1031": ["Halloween", "Happy", "halloween.bmp", "BUGAMBILIA"],
			"1101": ["Muertos", "Dia de", "day_of_the_death.bmp", "BUGAMBILIA"],
			"1109": ["Tiago", "Birthday", "cake.bmp", "MINT"],
			"1127": ["Thanksgiving", "Happy", "thanksgiving.bmp", "BUGAMBILIA"],
			"1225": ["X-MAS", "Merry", "xmas.bmp", "BUGAMBILIA"],
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
	descender_chars = {'g', 'j', 'p', 'q', 'y'}
	has_descenders = any(char in descender_chars for char in line2_text)
	
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

def calculate_uv_bar_length(uv_index):
	"""Calculate UV bar length with spacing for readability"""
	if uv_index <= 3:
		return uv_index
	elif uv_index <= 6:
		return uv_index + 1
	elif uv_index <= 9:
		return uv_index + 2
	else:
		return uv_index + 3

def calculate_humidity_bar_length(humidity):
	"""Calculate humidity bar length (10% per pixel) with spacing every 20%"""
	pixels = round(humidity / 10)  # 10% per pixel, so max 10 pixels at 100%
	
	# Add spacing pixels (black dots every 2 pixels = every 20%)
	if pixels <= 2:
		return pixels
	elif pixels <= 4:
		return pixels + 1  # Add 1 spacing pixel
	elif pixels <= 6:
		return pixels + 2  # Add 2 spacing pixels  
	elif pixels <= 8:
		return pixels + 3  # Add 3 spacing pixels
	else:
		return pixels + 4  # Add 4 spacing pixels
		
def add_indicator_bars(main_group, x_start, uv_index, humidity):
	"""Add UV and humidity indicator bars to display"""
	
	# UV bar (only if UV > 0)
	if uv_index > 0:
		uv_length = calculate_uv_bar_length(uv_index)
		main_group.append(Line(x_start, 27, x_start - 1 + uv_length, 27, DEFAULT_TEXT_COLOR))
		
		# UV spacing dots (black pixels every 3)
		for i in [3, 7, 11]:
			if i < uv_length:
				main_group.append(Line(x_start + i, 27, x_start + i, 27, BLACK))
	
	# Humidity bar 
	if humidity > 0:
		humidity_length = calculate_humidity_bar_length(humidity)
		
		# Main humidity line
		main_group.append(Line(x_start, 29, x_start - 1 + humidity_length, 29, DEFAULT_TEXT_COLOR))
		
		# Humidity spacing dots (black pixels every 2 = every 20%)
		for i in [2, 5, 8, 11]:  # Positions for 20%, 40%, 60%, 80%
			if i < humidity_length:
				main_group.append(Line(x_start + i, 29, x_start + i, 29, BLACK))


def show_weather_display(rtc, duration=DISPLAY_CONFIG["weather_duration"]):
	"""Display weather information and time"""
	log_debug("Displaying weather...", include_memory = True)
	
	# Fetch fresh weather data
	if DISPLAY_CONFIG["dummy_weather"]:
		weather_data = DUMMY_WEATHER_DATA
		# Log successful weather fetch with current count
		m, s = divmod(DISPLAY_CONFIG["weather_duration"], 60)
		log_info(f"Displaying DUMMY Weather for {m} minutes {s} seconds: {weather_data['weather_text']}, {weather_data['temperature']}°C", include_memory=True)
	else:
		weather_data = fetch_weather_data()
	
	if not weather_data:
		log_warning("Weather unavailable, showing clock")
		show_clock_display(rtc, duration)
		return
	
	clear_display()
	
	# Create display elements
	temp_text = bitmap_label.Label(bg_font, color=DEFAULT_TEXT_COLOR, x=2, y=20, background_color = BLACK, padding_top =-5, padding_bottom = 1, padding_left = 1,)
	feels_like_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, y=16, background_color = BLACK, padding_top=-5, padding_bottom=-2, padding_left = 1,)
	feels_shade_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, y=24, background_color = BLACK, padding_top=-5, padding_bottom=-2, padding_left = 1,)
	time_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, x=15, y=24, background_color = BLACK, padding_top=-5, padding_bottom=-2, padding_left = 1,)
	
	# Load weather icon
	try:
		bitmap, palette = load_bmp_image(f"img/weather/{weather_data['weather_icon']}.bmp")
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
		feels_like_text.x = 64 - 1 - get_text_width(feels_like_text.text, font)
		main_group.append(feels_like_text)
	
	if feels_shade_rounded != feels_like_rounded:
		feels_shade_text.text = f"{feels_shade_rounded}°"
		feels_shade_text.x = 64 - 1 - get_text_width(feels_shade_text.text, font)
		main_group.append(feels_shade_text)
	
	main_group.append(time_text)
	
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
			time_text.x = (64 - get_text_width(current_time, font)) // 2
		else:
			time_text.x = 64 - 1 - get_text_width(current_time, font)
		
		time.sleep(1)

def show_clock_display(rtc, duration=DISPLAY_CONFIG["clock_fallback_duration"]):
	"""Display clock as fallback when weather unavailable"""
	log_warning("Displaying clock...", include_memory = True)
	clear_display()
	
	date_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, x=5, y=7)
	time_text = bitmap_label.Label(bg_font, color=MINT, x=5, y=20)
	
	main_group.append(date_text)
	main_group.append(time_text)
	
	months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
			  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		dt = rtc.datetime
		date_str = f"{months[dt.tm_mon].upper()} {dt.tm_mday:02d}"
		
		hour = dt.tm_hour
		display_hour = hour % 12 if hour % 12 != 0 else 12
		time_str = f"{display_hour}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
		
		date_text.text = date_str
		time_text.text = time_str
		time.sleep(1)
	
	# Check for restart conditions
	time_since_success = time.monotonic() - last_successful_weather
	if consecutive_failures >= 3 or time_since_success > 600:  # 10 minutes
		log_warning("Restarting due to weather failures")
		time.sleep(2)
		supervisor.reload()

def show_event_display(rtc, duration=DISPLAY_CONFIG["event_duration"]):
	"""Display special calendar events using cached CSV data"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	
	# Get events from cache (loaded only once at startup)
	events = get_events()
	
	if month_day not in events:
		log_info("No events to display today")
		return False
	
	event_data = events[month_day]
	log_info(f"Showing event: {event_data[1]}", include_memory = True)
	clear_display()
	
	# Force garbage collection before loading images
	gc.collect()
	
	try:
		if event_data[1] == "Birthday":
			# For birthday events, use the original cake image layout
			bitmap, palette = load_bmp_image("img/events/cake.bmp")
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			main_group.append(image_grid)
		else:
			# Load event-specific image (25x28 positioned at top right)
			image_file = f"img/events/{event_data[2]}"
			try:
				bitmap, palette = load_bmp_image(image_file)
			except Exception as e:
				log_warning(f"Failed to load {image_file}: {e}")
				bitmap, palette = load_bmp_image("img/events/blank_sq.bmp")
			
			# Position 25px wide image at top right
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			image_grid.x = 37  # Right-aligned for 25px wide image
			image_grid.y = 2   # Start at y = 2 as requested
			
			# Calculate optimal text positions dynamically
			line1_text = event_data[1]  # e.g., "Cumple"
			line2_text = event_data[0]  # e.g., "Puchis"
			text_color = event_data[3] if len(event_data) > 3 else "MINT"  # Get color from CSV
			
			# Convert color name to actual color value
			color_map = {
				"MINT": MINT,
				"BUGAMBILIA": BUGAMBILIA, 
				"LILAC": LILAC,
				"DIMMEST_WHITE": DIMMEST_WHITE,
				"BLACK": BLACK
			}
			line2_color = color_map.get(text_color.upper(), MINT)  # Default to MINT if color not found
			
			# Get dynamic positions with 1px bottom margin and 1px line spacing
			line1_y, line2_y = calculate_bottom_aligned_positions(
				font, 
				line1_text, 
				line2_text,
				display_height=32,
				bottom_margin=2,  # Very tight bottom margin
				line_spacing=1    # Minimal spacing between lines
			)
			
			# Create text labels with calculated positions
			text1 = bitmap_label.Label(
				font,
				color=DEFAULT_TEXT_COLOR, 
				text=line1_text,
				x=2,
				y=line1_y
			)
			
			text2 = bitmap_label.Label(
				font,
				color=line2_color,  # Use color from CSV
				text=line2_text,
				x=2,
				y=line2_y
			)
			
			# Add elements to display
			main_group.append(image_grid)
			main_group.append(text1)
			main_group.append(text2)
			
	except Exception as e:
		log_error(f"Event display error: {e}")
	
	# Wait for specified duration
	time.sleep(duration)
	
	# Optional: Clean up after event display
	gc.collect()
	return True
	
def show_color_test_display(duration=DISPLAY_CONFIG["color_test_duration"]):
	log_info(f"Displaying Color Test", include_memory=True)
	clear_display()
	gc.collect()
	
	try:
		# Define colors with their names for better logging
		color_data = [
			(MINT, "MINT"),
			(BUGAMBILIA, "BUGAMBILIA"), 
			(LILAC, "LILAC"),
			(0x3F0000, "RED"),
			(0x003F00, "GREEN"),
			(0x00003F, "BLUE"),
			(0x3F1F00, "ORANGE"),
			(0x3F3F00, "YELLOW"),
			(0x003F3F, "CYAN"),
			(0x100010, "PURPLE"),
			(0x3F1F1F, "PINK"),
			(0x002020, "AQUA")
		]
		
		texts = ["Aa", "Bb", "Cc", "Dd", "Ee", "Ff", "Gg", "Hh", "Ii", "Jj", "Kk", "Ll"]
		
		key_text = "Color Key: "
		
		for i, ((color, color_name), text) in enumerate(zip(color_data, texts)):
			col = i // 3  # Column (0, 1, 2, 3)
			row = i % 3   # Row (0, 1, 2)
			
			label = bitmap_label.Label(
				font, color=color, text=text,
				x=2 + col * 16, y=2 + row * 11
			)
			main_group.append(label)
			
			# Add color name and hex value to key
			key_text += f"{text}={color_name}(0x{color:06X}) | "
	
	except Exception as e:
		log_error(f"Color Test display error: {e}")
	
	log_info(key_text)
	
	# Wait for specified duration
	time.sleep(duration)
	
	# Optional: Clean up after event display
	gc.collect()
	return True

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
		hours_running > 24 or
		(hours_running > 1 and 
		 rtc.datetime.tm_hour == DAILY_RESET_HOUR and 
		 rtc.datetime.tm_min < 5)
	)
	
	if should_restart:
		log_info(f"Daily restart triggered ({hours_running:.1f}h runtime)", include_memory = True)
		time.sleep(2)
		supervisor.reload()

### MAIN PROGRAM ###

def main():
	"""Main program execution"""
	global last_successful_weather, startup_time
	
	# Initialize RTC FIRST for proper timestamps
	rtc = setup_rtc()
	
	log_info("=== WEATHER DISPLAY STARTUP ===", include_memory=True)
	
	try:
		
		# Initialize hardware
		initialize_display()
		
		# Detect matrix type and initialize colors
		matrix_type = detect_matrix_type()
		initialize_colors()
		
		# Load events
		events = get_events()
		log_debug(f"System initialized - {len(events)} events loaded")
		
		# Network operations (can be slower/fail)
		wifi_connected = setup_wifi()
		
		if wifi_connected:
			sync_time_with_timezone(rtc)
			log_info("Time synchronized with NTP")
		else:
			log_warning("Starting without WiFi - using RTC time only")
		
		# Set startup time
		startup_time = time.monotonic()
		last_successful_weather = startup_time
		
		log_info("Entering main display loop", include_memory=True)
		
		# Main display loop
		while True:
			try:
				# System maintenance
				check_daily_reset(rtc)
				
				# Display weather
				if DISPLAY_CONFIG["weather"]:
					show_weather_display(rtc, DISPLAY_CONFIG["weather_duration"])
				else:
					log_debug("Weather display disabled")
				
				# Show event if scheduled
				if DISPLAY_CONFIG["events"]:
					event_shown = show_event_display(rtc, DISPLAY_CONFIG["event_duration"])
					
					# Brief pause if no event
					if not event_shown:
						log_info("No event to show today")
						time.sleep(1)
						
				else:
					log_debug("event display disabled")
					
				# Show color test
				if DISPLAY_CONFIG["color_test"]:
					show_color_test_display(DISPLAY_CONFIG["color_test_duration"])
				else:
					log_debug("Color Test Disabled")
					
			except Exception as e:
				log_error(f"Display loop error: {e}", include_memory = True)
				time.sleep(5)  # Brief recovery pause
				
	except Exception as e:
		log_error(f"Critical system error: {e}", include_memory = True)
		time.sleep(10)
		supervisor.reload()

# Program entry point
if __name__ == "__main__":
	main()