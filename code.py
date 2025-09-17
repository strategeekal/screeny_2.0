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

# System Configuration
DAILY_RESET_ENABLED = True
DAILY_RESET_HOUR = 3
WEATHER_DISPLAY_DURATION = 300  # 5 minutes
EVENT_DISPLAY_DURATION = 30
CLOCK_FALLBACK_DURATION = 300

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

# API tracking
api_call_count = 0
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
	
	for attempt in range(5):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			rtc_instance = rtc
			print(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			print(f"RTC attempt {attempt + 1} failed: {e}")
			if attempt < 4:
				time.sleep(2)
	
	print("RTC initialization failed, restarting...")
	supervisor.reload()

### API CALL TRACKING ###
		
def log_api_call():
		"""Track API calls and restart when needed"""
		global api_call_count
		
		api_call_count += 1
		print(f"API Call #{api_call_count}")
		
		# Full restart every 8 calls for reliable socket cleanup
		if api_call_count >= MAX_API_CALLS_BEFORE_RESTART:
			print(f"Preventive restart after {api_call_count} API calls")
			time.sleep(2)
			supervisor.reload()

### NETWORK FUNCTIONS ###

def setup_wifi():
	"""Connect to WiFi with simplified retry logic"""
	ssid = os.getenv("CIRCUITPY_WIFI_SSID")
	password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
	
	if not ssid or not password:
		print("WiFi credentials missing")
		return False
	
	for attempt in range(3):
		try:
			wifi.radio.connect(ssid, password)
			print(f"Connected to {ssid}")
			return True
		except ConnectionError as e:
			print(f"WiFi attempt {attempt + 1} failed")
			if attempt < 2:
				time.sleep(2)
	
	print("WiFi connection failed")
	return False

def get_timezone_offset(timezone_name, utc_datetime):
	"""Calculate timezone offset including DST for a given timezone"""
	
	if timezone_name not in TIMEZONE_OFFSETS:
		print(f"Unknown timezone: {timezone_name}, using Chicago")
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
		
		print(f"Time synced to {timezone_name} (UTC{offset:+d})")
		
	except Exception as e:
		print(f"NTP sync failed: {e}")

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
			print(f"Failed to read API key: {e}")
			
		if not api_key:
			print("API key not found")
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
			print(f"API error: {response.status_code}")
			consecutive_failures += 1
			return None
		
		# Parse response
		weather_json = response.json()
		if not weather_json:
			print("Empty weather response")
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
		
		print(f"Weather: {weather_data['weather_text']}, {weather_data['temperature']}°C")
		
		# Reset failure tracking on success
		consecutive_failures = 0
		last_successful_weather = time.monotonic()
		
		# Log the API call
		log_api_call()
		
		# Check for preventive restart
		if api_call_count >= MAX_API_CALLS_BEFORE_RESTART:
			print(f"Preventive restart after {api_call_count} API calls")
			time.sleep(2)
			supervisor.reload()
		
		return weather_data
		
	except Exception as e:
		print(f"Weather fetch error: {e}")
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


def show_weather_display(rtc, duration=WEATHER_DISPLAY_DURATION):
	"""Display weather information and time"""
	print("Displaying weather...")
	
	# Fetch fresh weather data
	weather_data = fetch_weather_data()
	if not weather_data:
		print("Weather unavailable, showing clock")
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
		bitmap, palette = load_bmp_image(f"img/{weather_data['weather_icon']}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		main_group.append(image_grid)
	except Exception as e:
		print(f"Icon load failed: {e}")
	
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

def show_clock_display(rtc, duration=CLOCK_FALLBACK_DURATION):
	"""Display clock as fallback when weather unavailable"""
	print("Displaying clock...")
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
		print("Restarting due to weather failures")
		time.sleep(2)
		supervisor.reload()

def show_event_display(rtc, duration=EVENT_DISPLAY_DURATION):
	"""Display special calendar events"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	
	if month_day not in CALENDAR_EVENTS:
		return False
	
	event_data = CALENDAR_EVENTS[month_day]
	print(f"Showing event: {event_data[1]}")
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
		print(f"Event display error: {e}")
	
	# Wait for specified duration
	time.sleep(duration)
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
		print(f"Daily restart triggered ({hours_running:.1f}h runtime)")
		time.sleep(2)
		supervisor.reload()

### MAIN PROGRAM ###

def main():
	"""Main program execution"""
	global last_successful_weather, startup_time
	
	print("=== WEATHER DISPLAY STARTUP ===")
	
	try:
		# Initialize hardware
		initialize_display()
		rtc = setup_rtc()
		
		# Initialize WiFi
		wifi_connected = setup_wifi()
		
		# Sync time if WiFi available
		if wifi_connected:
			sync_time_with_timezone(rtc)
		
		# Set startup time
		startup_time = time.monotonic()
		last_successful_weather = startup_time
		
		print("Entering main display loop...")
		
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
				print(f"Display loop error: {e}")
				time.sleep(5)  # Brief recovery pause
				
	except Exception as e:
		print(f"Critical system error: {e}")
		time.sleep(10)
		supervisor.reload()

# Program entry point
if __name__ == "__main__":
	main()