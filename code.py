##### TIME AND WEATHER SCREENY - OPTIMIZED #####

### Import Libraries ###
import board
import os
import supervisor
import gc
import math
import displayio
import framebufferio
import rgbmatrix
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
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

# Display Colors (6-bit values for RGB matrix)
BLACK = 0x000000
DIMMEST_WHITE = 0x101010
MINT = 0x080816
BUGAMBILIA = 0x101000
LILAC = 0x161408

DEFAULT_TEXT_COLOR = DIMMEST_WHITE

# API Configuration
ACCUWEATHER_LOCATION_KEY = "2626571"
MAX_API_CALLS_BEFORE_RESTART = 8
DAILY_API_LIMIT = 500
API_LIMIT_WARNING_THRESHOLD = 400

# System Configuration
DAILY_RESET_ENABLED = True
DAILY_RESET_HOUR = 3
WEATHER_DISPLAY_DURATION = 300  # 5 minutes
EVENT_DISPLAY_DURATION = 30
CLOCK_FALLBACK_DURATION = 300

### GLOBAL STATE ###

# Hardware instances
rtc_instance = None
display = None
main_group = None

# API tracking
api_call_count = 0
daily_api_count = 0
last_count_date = ""
consecutive_failures = 0
last_successful_weather = 0
startup_time = 0

# Load fonts once at startup
bg_font = bitmap_font.load_font("fonts/bigbit10-16.bdf")
font = bitmap_font.load_font("fonts/tinybit6-16.bdf")

# Calendar events (MM/DD format)
CALENDAR_EVENTS = {
	"0825": ["Diego", "Birthday", "cake.bmp"],
	"0703": ["Gaby", "Birthday", "cake.bmp"],
	"1109": ["Tiago", "Birthday", "cake.bmp"],
	"0210": ["Emilio", "Birthday", "cake.bmp"],
	"1225": ["X-MAS", "Merry", "xmas.bmp"],
	"0214": ["Didiculo", "Dia", "valentines.bmp"],
	"0824": ["Abuela", "Cumple", "cake_sq.bmp"],
	"0101": ["New Year", "Happy", "new_year.bmp"],
	"1123": ["Ric", "Cumple", "cake_sq.bmp"],
	"0811": ["Alan", "Cumple", "cake_sq.bmp"],
	"0916": ["Mexico", "Viva", "mexico_flag_v3.bmp"],
	"0704": ["July", "4th of", "us_flag.bmp"],
	"0301": ["", "Spring", "spring.bmp"],
	"0601": ["", "Summer", "summer.bmp"],
	"0901": ["", "Fall", "fall.bmp"],
	"1031": ["Halloween", "Happy", "halloween.bmp"],
	"1101": ["Muertos", "Dia de", "day_of_the_death.bmp"],
	"1201": ["", "Winter", "winter.bmp"],
}

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

def setup_rtc():
	"""Initialize RTC with retry logic"""
	global rtc_instance
	
	for attempt in range(5):  # Reduced from 10 attempts
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			rtc_instance = rtc
			log_entry(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			log_entry(f"RTC attempt {attempt + 1} failed: {e}", error=True)
			if attempt < 4:  # Don't sleep on last attempt
				time.sleep(2)
	
	log_entry("RTC initialization failed, restarting...", error=True)
	supervisor.reload()

### LOGGING SYSTEM ###

def log_entry(message, error=False):
	"""Unified logging with timestamp"""
	try:
		if rtc_instance:
			dt = rtc_instance.datetime
			timestamp = f"{dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d} {dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
		else:
			timestamp = "NO-RTC"
		
		log_type = "ERROR" if error else "INFO"
		log_line = f"[{timestamp}] {log_type}: {message}"
		
		# Try to write to file, fail silently if read-only
		try:
			with open("weather_log.txt", "a") as f:
				f.write(f"{log_line}\n")
		except OSError:
			pass  # Filesystem read-only
		
		print(log_line)
	except Exception:
		print(f"LOG-ERROR: {message}")

### API CALL TRACKING ###

def get_current_date_string():
	"""Get current date as YYYY-MM-DD string"""
	try:
		if rtc_instance:
			dt = rtc_instance.datetime
			return f"{dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d}"
		return "unknown"
	except Exception:
		return "unknown"

def load_daily_counter():
	"""Load daily API counter from file"""
	global daily_api_count, last_count_date
	
	current_date = get_current_date_string()
	
	try:
		with open("daily_calls.txt", "r") as f:
			content = f.read().strip()
			
			if "|" in content:
				stored_date, stored_count = content.split("|", 1)
				if stored_date == current_date:
					daily_api_count = int(stored_count)
					last_count_date = stored_date
					log_entry(f"Restored daily count: {daily_api_count}")
					return
		
		# File doesn't exist, wrong format, or new day
		daily_api_count = 0
		last_count_date = current_date
		log_entry(f"Starting fresh counter for {current_date}")
		
	except (OSError, ValueError):
		daily_api_count = 0
		last_count_date = current_date
		log_entry("Counter file unavailable, starting fresh")

def save_daily_counter():
	"""Save daily API counter to file"""
	try:
		content = f"{last_count_date}|{daily_api_count}"
		with open("daily_calls.txt", "w") as f:
			f.write(content)
		return True
	except OSError:
		return False  # Read-only filesystem

def log_api_call():
	"""Track and log API calls"""
	global api_call_count, daily_api_count, last_count_date
	
	api_call_count += 1
	current_date = get_current_date_string()
	
	# Handle midnight rollover
	if current_date != last_count_date:
		daily_api_count = 0
		last_count_date = current_date
		log_entry(f"Date changed to {current_date}, reset daily count")
	
	daily_api_count += 1
	save_daily_counter()
	
	log_entry(f"API Call #{api_call_count} (Daily: {daily_api_count}/{DAILY_API_LIMIT})")
	
	# Warning near daily limit
	if daily_api_count >= API_LIMIT_WARNING_THRESHOLD:
		log_entry(f"WARNING: Near daily API limit ({daily_api_count}/{DAILY_API_LIMIT})", error=True)

### NETWORK FUNCTIONS ###

def setup_wifi():
	"""Connect to WiFi with simplified retry logic"""
	ssid = os.getenv("CIRCUITPY_WIFI_SSID")
	password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
	
	if not ssid or not password:
		log_entry("WiFi credentials missing", error=True)
		return False
	
	for attempt in range(3):  # Reduced retry attempts
		try:
			wifi.radio.connect(ssid, password)
			log_entry(f"Connected to {ssid}")
			return True
		except ConnectionError as e:
			log_entry(f"WiFi attempt {attempt + 1} failed", error=True)
			if attempt < 2:
				time.sleep(2)
	
	log_entry("WiFi connection failed", error=True)
	return False

def is_dst_active(dt):
	"""Simplified DST check for US Central Time"""
	month, day = dt.tm_mon, dt.tm_mday
	
	# DST is roughly March 8 - November 7 (conservative estimate)
	if month < 3 or month > 11:
		return False
	if month > 3 and month < 11:
		return True
	if month == 3:
		return day >= 8
	if month == 11:
		return day < 7
	return False

def sync_time_ntp(rtc):
	"""Sync RTC with NTP server"""
	try:
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		
		# Get UTC time to determine DST
		ntp_utc = adafruit_ntp.NTP(pool, tz_offset=0)
		utc_time = ntp_utc.datetime
		
		# Apply Central Time offset
		offset = -5 if is_dst_active(utc_time) else -6
		ntp = adafruit_ntp.NTP(pool, tz_offset=offset)
		rtc.datetime = ntp.datetime
		
		log_entry(f"Time synced (UTC{offset:+d})")
	except Exception as e:
		log_entry(f"NTP sync failed: {e}", error=True)

def cleanup_sockets():
	"""Aggressive socket cleanup to prevent memory issues"""
	for _ in range(3):
		gc.collect()

def fetch_weather_data():
	"""Fetch current weather data with improved error handling"""
	global consecutive_failures, last_successful_weather
	
	# Resource cleanup variables
	pool = None
	requests = None
	response = None
	
	try:
		# Get API key
		api_key = None
		try:
			with open("settings.toml", "r") as f:
				for line in f:
					if line.startswith("ACCUWEATHER_API_KEY"):
						api_key = line.split("=")[1].strip().strip('"').strip("'")
						break
		except Exception as e:
			log_entry(f"Failed to read API key: {e}", error=True)
			
		if not api_key:
			log_entry("API key not found", error=True)
			consecutive_failures += 1
			return None
		
		# Log API call
		log_api_call()
		
		# Build request URL
		url = f"https://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_LOCATION_KEY}?apikey={api_key}&details=true"
		
		# Setup and execute request
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		requests = adafruit_requests.Session(pool, ssl.create_default_context())
		response = requests.get(url)
		
		if response.status_code != 200:
			log_entry(f"API error: {response.status_code}", error=True)
			consecutive_failures += 1
			return None
		
		# Parse response
		weather_json = response.json()
		if not weather_json:
			log_entry("Empty weather response", error=True)
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
		
		log_entry(f"Weather: {weather_data['weather_text']}, {weather_data['temperature']}°C")
		
		# Reset failure tracking on success
		consecutive_failures = 0
		last_successful_weather = time.monotonic()
		
		# Check for preventive restart
		if api_call_count >= MAX_API_CALLS_BEFORE_RESTART:
			log_entry(f"Preventive restart after {api_call_count} API calls")
			time.sleep(2)
			supervisor.reload()
		
		return weather_data
		
	except Exception as e:
		log_entry(f"Weather fetch error: {e}", error=True)
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
	"""Auto-detect matrix wiring type"""
	import microcontroller
	uid = microcontroller.cpu.uid
	device_id = "".join([f"{b:02x}" for b in uid[-3:]])
	
	device_mappings = {
		"2236c5": "type1",
		"f78b47": "type2",
	}
	return device_mappings.get(device_id, "type1")

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

def clear_display():
	"""Clear all display elements"""
	while len(main_group):
		main_group.pop()

### DISPLAY FUNCTIONS ###

def show_weather_display(rtc, duration=WEATHER_DISPLAY_DURATION):
	"""Display weather information and time"""
	log_entry("Displaying weather...")
	
	# Fetch fresh weather data
	weather_data = fetch_weather_data()
	if not weather_data:
		log_entry("Weather unavailable, showing clock", error=True)
		show_clock_display(rtc, duration)
		return
	
	clear_display()
	
	# Create display elements
	temp_text = bitmap_label.Label(bg_font, color=DEFAULT_TEXT_COLOR, x=2, y=20)
	feels_like_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, y=16)
	feels_shade_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, y=24)
	time_text = bitmap_label.Label(font, color=DEFAULT_TEXT_COLOR, x=15, y=24)
	
	# Load weather icon
	try:
		bitmap, palette = load_bmp_image(f"img/{weather_data['weather_icon']}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		main_group.append(image_grid)
	except Exception as e:
		log_entry(f"Icon load failed: {e}", error=True)
	
	# Setup temperature display
	temp_text.text = f"{round(weather_data['temperature'])}°"
	main_group.append(temp_text)
	
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
		display_hour = hour - 12 if hour > 12 else hour
		current_time = f"{display_hour}:{rtc.datetime.tm_min:02d}"
		time_text.text = current_time
		
		# Position time text
		if feels_shade_rounded != feels_like_rounded:
			time_text.x = (64 - get_text_width(current_time, font)) // 2
		else:
			time_text.x = 64 - 1 - get_text_width(current_time, font)
		
		time.sleep(1)

def show_clock_display(rtc, duration=CLOCK_FALLBACK_DURATION):
	"""Display clock as fallback when weather unavailable"""
	log_entry("Displaying clock...")
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
		display_hour = hour - 12 if hour > 12 else hour
		time_str = f"{display_hour}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
		
		date_text.text = date_str
		time_text.text = time_str
		time.sleep(1)
	
	# Check for restart conditions
	time_since_success = time.monotonic() - last_successful_weather
	if consecutive_failures >= 3 or time_since_success > 600:  # 10 minutes
		log_entry(f"Restarting due to weather failures", error=True)
		time.sleep(2)
		supervisor.reload()

def show_event_display(rtc, duration=EVENT_DISPLAY_DURATION):
	"""Display special calendar events"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	
	if month_day not in CALENDAR_EVENTS:
		return False
	
	event_data = CALENDAR_EVENTS[month_day]
	log_entry(f"Showing event: {event_data[1]}")
	clear_display()
	
	try:
		if event_data[1] == "Birthday":
			bitmap, palette = load_bmp_image("img/cake.bmp")
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			main_group.append(image_grid)
		else:
			# Load event-specific image
			image_file = f"img/{event_data[2]}"
			try:
				bitmap, palette = load_bmp_image(image_file)
			except:
				bitmap, palette = load_bmp_image("img/blank_sq.bmp")
			
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			image_grid.x = 36
			image_grid.y = 2
			
			# Choose appropriate fonts based on text length
			line1_font = bg_font if get_text_width(event_data[1], bg_font) <= 34 else font
			line2_font = bg_font if get_text_width(event_data[0], bg_font) <= 34 else font
			
			text1 = bitmap_label.Label(line1_font, color=DEFAULT_TEXT_COLOR, 
									 text=event_data[1], x=2, y=5)
			text2 = bitmap_label.Label(line2_font, color=MINT, 
									 text=event_data[0], x=2, y=19)
			
			main_group.append(image_grid)
			main_group.append(text1)
			main_group.append(text2)
			
	except Exception as e:
		log_entry(f"Event display error: {e}", error=True)
	
	# Wait for specified duration
	time.sleep(duration)
	return True

### SYSTEM MANAGEMENT ###

def check_daily_reset(rtc):
	"""Handle daily reset and cleanup operations"""
	global startup_time, daily_api_count, last_count_date
	
	if not DAILY_RESET_ENABLED:
		return
	
	current_time = time.monotonic()
	hours_running = (current_time - startup_time) / 3600
	current_date = get_current_date_string()
	
	# Handle natural midnight rollover
	if current_date != last_count_date:
		log_entry(f"Natural daily reset: {current_date}")
		daily_api_count = 0
		last_count_date = current_date
		save_daily_counter()
	
	# Scheduled restart conditions
	should_restart = (
		hours_running > 24 or
		(hours_running > 1 and 
		 rtc.datetime.tm_hour == DAILY_RESET_HOUR and 
		 rtc.datetime.tm_min < 5)
	)
	
	if should_restart:
		log_entry(f"Daily restart triggered ({hours_running:.1f}h runtime)")
		save_daily_counter()  # Preserve counter before restart
		time.sleep(2)
		supervisor.reload()

### MAIN PROGRAM ###

def main():
	"""Main program execution"""
	global last_successful_weather, startup_time
	
	log_entry("=== SYSTEM STARTUP ===")
	
	try:
		# Initialize hardware
		initialize_display()
		rtc = setup_rtc()
		wifi_connected = setup_wifi()
		
		# Sync time if WiFi available
		if wifi_connected:
			sync_time_ntp(rtc)
		
		# Initialize API tracking
		load_daily_counter()
		
		# Set startup time
		startup_time = time.monotonic()
		last_successful_weather = startup_time
		
		log_entry("Entering main display loop...")
		
		# Main display loop
		while True:
			try:
				# System maintenance
				check_daily_reset(rtc)
				
				# Display weather (5 minutes)
				show_weather_display(rtc, WEATHER_DISPLAY_DURATION)
				
				# Show event if scheduled (30 seconds)
				event_shown = show_event_display(rtc, EVENT_DISPLAY_DURATION)
				
				# Brief pause if no event
				if not event_shown:
					time.sleep(1)
					
			except Exception as e:
				log_entry(f"Display loop error: {e}", error=True)
				time.sleep(5)  # Brief recovery pause
				
	except Exception as e:
		log_entry(f"Critical system error: {e}", error=True)
		time.sleep(10)
		supervisor.reload()

# Program entry point
if __name__ == "__main__":
	main()