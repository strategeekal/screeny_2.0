##### TIME AND WEATHER SCREENY - ENHANCED #####

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

### CONSTANTS AND VARIABLES ###

# Hardware
MATRIX_TYPE = "type2"  # Change to "type1" for second display

# Colors (6-bit values for your matrix)
BLACK = 0x000000
DIMMEST_WHITE = 0x101010
MINT = 0x080816
BUGAMBILIA = 0x101000
LILAC = 0x161408

default_text_color = DIMMEST_WHITE

# Weather constants
ACCUWEATHER_LOCATION_KEY = "2626571"

# Global RTC instance for logging
rtc_instance = None

# Tracking variables
api_call_count = 0
consecutive_failures = 0
last_successful_weather = 0

# Periodic and Daily reset variables
MAX_API_CALLS_BEFORE_RESTART = 20  # Conservative - restart every ~100 minutes
DAILY_RESET_ENABLED = True
DAILY_RESET_HOUR = 3
startup_time = 0

# Load Fonts
bg_font = bitmap_font.load_font("fonts/bigbit10-16.bdf")
font = bitmap_font.load_font("fonts/tinybit6-16.bdf")

# Calendar
calendar = {
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

### INITIALIZE SCREEN ###
displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
	width=64, height=32, bit_depth=6,
	rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1, board.MTX_R2, board.MTX_G2, board.MTX_B2],
	addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
	clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE,
	serpentine=True, doublebuffer=True,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
display.brightness = 0.1
main_group = displayio.Group()
display.root_group = main_group

### LOGGING FUNCTIONS ###

def log_entry(message, error=False):
	"""Write log entry with timestamp from RTC"""
	global rtc_instance
	try:
		if rtc_instance:
			current_time = rtc_instance.datetime
		else:
			current_time = time.localtime()  # Fallback if RTC not available
			
		timestamp = f"{current_time.tm_year}-{current_time.tm_mon:02d}-{current_time.tm_mday:02d} {current_time.tm_hour:02d}:{current_time.tm_min:02d}:{current_time.tm_sec:02d}"
		log_type = "ERROR" if error else "INFO"
		
		# Try to write to file, but don't fail if filesystem is read-only
		try:
			with open("weather_log.txt", "a") as f:
				f.write(f"[{timestamp}] {log_type}: {message}\n")
		except OSError:
			# Filesystem is read-only (USB connected), just print to console
			pass
		
		print(f"[{timestamp}] {log_type}: {message}")
	except Exception as e:
		print(f"Logging failed: {e}")

def log_api_call():
	"""Log API call and increment daily counter"""
	global api_call_count
	try:
		api_call_count += 1
		
		# Try to update daily counter file
		daily_count = api_call_count  # Fallback to session count
		try:
			with open("daily_calls.txt", "r") as f:
				daily_count = int(f.read().strip())
			daily_count += 1
			with open("daily_calls.txt", "w") as f:
				f.write(str(daily_count))
		except OSError:
			# Filesystem is read-only, use session count only
			daily_count = api_call_count
		
		log_entry(f"API Call #{api_call_count} (Daily: {daily_count}/500)")
		
	except Exception as e:
		log_entry(f"Failed to log API call: {e}", error=True)

### UTILITY FUNCTIONS ###

def convert_bmp_palette(palette):
	"""Convert BMP palette from 8-bit to 6-bit with BGR->RGB swap"""
	if not palette or 'ColorConverter' in str(type(palette)):
		return palette
	
	try:
		palette_len = len(palette)
	except TypeError:
		return palette
	
	converted_palette = displayio.Palette(palette_len)
	
	for i in range(palette_len):
		original_color = palette[i]
		
		if MATRIX_TYPE == "type1":
			# Current working setup
			red_8bit = (original_color >> 16) & 0xFF
			blue_8bit = (original_color >> 8) & 0xFF
			green_8bit = original_color & 0xFF
		else:  # type2
			# Alternative wiring
			red_8bit = (original_color >> 16) & 0xFF
			green_8bit = (original_color >> 8) & 0xFF
			blue_8bit = original_color & 0xFF          # Blue stays (no swap)
		
		red_6bit = red_8bit >> 2
		green_6bit = green_8bit >> 2
		blue_6bit = blue_8bit >> 2
		
		converted_palette[i] = (red_6bit << 16) | (green_6bit << 8) | blue_6bit
	
	return converted_palette

def load_bmp_image(filepath):
	"""Load and convert BMP image for matrix display"""
	bitmap, palette = adafruit_imageload.load(filepath)
	if palette and 'Palette' in str(type(palette)):
		palette = convert_bmp_palette(palette)
	return bitmap, palette

def get_text_width(text, font):
	"""Get pixel width of text"""
	if not text:
		return 0
	temp_label = bitmap_label.Label(font, text=text)
	bbox = temp_label.bounding_box
	return bbox[2] if bbox else 0

def choose_font_for_text(text, max_width=34):
	"""Choose appropriate font based on text width"""
	if get_text_width(text, bg_font) <= max_width:
		return bg_font
	return font

def temp_format(temp):
	"""Format temperature with degree symbol"""
	return f"{round(temp)}°"

def twelve_hour_format(hour):
	"""Convert 24-hour to 12-hour format"""
	return hour - 12 if hour > 12 else hour

def get_month_name(month_num):
	"""Get short month name"""
	months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
			  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	return months[month_num]

def clear_display():
	"""Clear all elements from display"""
	while len(main_group):
		main_group.pop()
		
def check_daily_reset(rtc):
	global startup_time
	
	if not DAILY_RESET_ENABLED:
		return
	
	current_time = time.monotonic()
	hours_running = (current_time - startup_time) / 3600
	
	if (hours_running > 24 or
		(hours_running > 1 and rtc.datetime.tm_hour == DAILY_RESET_HOUR and rtc.datetime.tm_min < 5)):
		
		log_entry(f"Daily reset triggered (running {hours_running:.1f} hours)")
		
		# Add log rotation here - BEFORE the reset
		rotate_log_file()
		
		# Clear daily counter file if writable
		try:
			with open("daily_calls.txt", "w") as f:
				f.write("0")
		except OSError:
			pass
		
		time.sleep(2)
		supervisor.reload()

def rotate_log_file():
	"""Rotate log file daily and clean up old logs"""
	try:
		if rtc_instance:
			current_date = f"{rtc_instance.datetime.tm_year}{rtc_instance.datetime.tm_mon:02d}{rtc_instance.datetime.tm_mday:02d}"
			
			# Check if we need to rotate
			try:
				with open("current_log_date.txt", "r") as f:
					last_date = f.read().strip()
			except:
				last_date = ""
			
			if current_date != last_date:
				log_entry("Rotating log files...")
				
				# Archive old log
				try:
					with open("weather_log.txt", "r") as old:
						content = old.read()
					if content:
						with open(f"weather_log_{last_date}.txt", "w") as archive:
							archive.write(content)
					
					# Clear current log
					with open("weather_log.txt", "w") as f:
						pass
					
					# Clean up old log files (keep only last 7 days)
					cleanup_old_logs(current_date)
					
					# Update date tracker
					with open("current_log_date.txt", "w") as f:
						f.write(current_date)
						
				except OSError:
					pass
	except Exception as e:
		print(f"Log rotation failed: {e}")

def cleanup_old_logs(current_date):
	"""Remove log files older than 7 days"""
	try:
		import os
		files = os.listdir("/")
		
		current_date_int = int(current_date)
		
		for filename in files:
			if filename.startswith("weather_log_") and filename.endswith(".txt"):
				try:
					# Extract date from filename like "weather_log_20241215.txt"
					date_str = filename[12:20]  # Extract YYYYMMDD
					file_date_int = int(date_str)
					
					# Remove if older than 7 days (rough calculation)
					if current_date_int - file_date_int > 7:
						os.remove(filename)
						print(f"Deleted old log: {filename}")
						
				except (ValueError, OSError):
					continue  # Skip files that don't match pattern or can't be deleted
					
	except Exception as e:
		print(f"Log cleanup failed: {e}")

def cleanup_sockets():
		"""Enhanced socket cleanup"""
		import gc
		
		# Force multiple garbage collection cycles
		for _ in range(3):
			gc.collect()
		
		log_entry("Enhanced socket cleanup performed")

### TIME AND NETWORK SETUP ###

def setup_rtc():
	"""Initialize RTC with retry logic"""
	global rtc_instance
	for attempt in range(10):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			rtc_instance = rtc  # Set global instance
			log_entry(f"RTC initialized: {rtc.datetime}")
			return rtc
		except Exception as e:
			log_entry(f"RTC attempt {attempt + 1} failed: {e}", error=True)
			time.sleep(2)
	
	log_entry("RTC initialization failed, restarting...", error=True)
	supervisor.reload()

def setup_wifi():
	"""Connect to WiFi with retry logic"""
	ssid = os.getenv("CIRCUITPY_WIFI_SSID")
	password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
	
	if not ssid or not password:
		log_entry("WiFi credentials missing", error=True)
		return False
	
	for attempt in range(5):
		try:
			wifi.radio.connect(ssid, password)
			log_entry(f"Connected to {ssid}")
			return True
		except ConnectionError as e:
			log_entry(f"WiFi attempt {attempt + 1} failed: {e}", error=True)
			time.sleep(2)
	
	log_entry("WiFi connection failed", error=True)
	return False

def fetch_weather_data():
	"""Fetch current weather data from AccuWeather API"""
	global consecutive_failures, last_successful_weather
	
	try:
		# Get API key from settings.toml file
		try:
			with open("settings.toml", "r") as f:
				for line in f:
					if line.startswith("ACCUWEATHER_API_KEY"):
						api_key = line.split("=")[1].strip().strip('"').strip("'")
						break
				else:
					api_key = None
		except Exception as e:
			log_entry(f"Failed to read API key: {e}", error=True)
			api_key = None
			
		if not api_key:
			log_entry("AccuWeather API key not found in settings.toml", error=True)
			consecutive_failures += 1
			return None
		
		# Log the API call
		log_api_call()
		
		# Build API URL with query parameters manually
		url = f"https://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_LOCATION_KEY}?apikey={api_key}&details=true"
		
		# Clean up sockets before making request
		cleanup_sockets()
		
		# Setup request
		pool = socketpool.SocketPool(wifi.radio)
		requests = adafruit_requests.Session(pool, ssl.create_default_context())
		
		response = requests.get(url)
		
		if response.status_code != 200:
			log_entry(f"Weather API error: {response.status_code}", error=True)
			response.close()
			consecutive_failures += 1
			return None
		
		# Parse JSON response
		weather_json = response.json()
		response.close()
		
		if not weather_json or len(weather_json) == 0:
			log_entry("Empty weather response", error=True)
			consecutive_failures += 1
			return None
		
		# Extract data from first (current) condition
		current = weather_json[0]
		
		# Extract temperature data in Metric (Celsius)
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
			"success": True
		}
		
		log_entry(f"Weather: {weather_data['weather_text']}, {weather_data['temperature']}°C")
		
		# Reset failure counter on success
		consecutive_failures = 0
		last_successful_weather = time.monotonic()
			
		# ADD THE RESTART CHECK HERE - after successful API call but before return
		if api_call_count >= MAX_API_CALLS_BEFORE_RESTART:
			log_entry(f"Preventive restart after {api_call_count} API calls")
			time.sleep(2)
			supervisor.reload()
		
		return weather_data
			
	except Exception as e:
		log_entry(f"Weather fetch error: {e}", error=True)
		consecutive_failures += 1
		cleanup_sockets()
		return None
		
def is_dst_us_central(dt):
	"""
	Determine if a given UTC datetime falls within US Central Daylight Time.

	DST Rules for US Central Time:
	- Starts: 2nd Sunday in March at 2:00 AM local time (becomes 3:00 AM)
	- Ends: 1st Sunday in November at 2:00 AM local time (becomes 1:00 AM)

	Args:
		dt: time struct from time.localtime() or similar (UTC time)

	Returns:
		bool: True if DST is active, False otherwise
	"""
	year = dt.tm_year
	month = dt.tm_mon
	day = dt.tm_mday
	hour = dt.tm_hour

	# Find the 2nd Sunday in March
	march_1st_weekday = (dt.tm_wday - (day - 1)) % 7
	first_sunday_march = 7 - march_1st_weekday if march_1st_weekday != 6 else 0
	if first_sunday_march == 0:
		first_sunday_march = 7
	second_sunday_march = first_sunday_march + 7

	# Find the 1st Sunday in November
	# Create a time struct for November 1st of the same year
	nov_1st = time.struct_time((year, 11, 1, 0, 0, 0, 0, 0, 0))
	nov_1st_weekday = time.localtime(time.mktime(nov_1st)).tm_wday
	first_sunday_november = 7 - nov_1st_weekday if nov_1st_weekday != 6 else 0
	if first_sunday_november == 0:
		first_sunday_november = 7

	# Check if we're in DST period
	if month < 3 or month > 11:
		return False
	elif month > 3 and month < 11:
		return True
	elif month == 3:
		# March - check if we're past the 2nd Sunday at 2 AM
		if day < second_sunday_march:
			return False
		elif day > second_sunday_march:
			return True
		else:
			# It's the 2nd Sunday - check if it's past 2 AM local time
			# Since we're working with UTC, we need to account for standard time offset
			# 2 AM CST = 8 AM UTC
			return hour >= 8
	elif month == 11:
		# November - check if we're before the 1st Sunday at 2 AM
		if day < first_sunday_november:
			return True
		elif day > first_sunday_november:
			return False
		else:
			# It's the 1st Sunday - check if it's before 2 AM local time
			# 2 AM CDT = 7 AM UTC (because we're still in DST until 2 AM)
			return hour < 7

def sync_time_ntp(rtc):
	try:
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		
		# Get UTC time first to check DST
		ntp_utc = adafruit_ntp.NTP(pool, tz_offset=0)
		utc_time = ntp_utc.datetime
		
		# Use your existing DST logic
		dst_active = is_dst_us_central(utc_time)
		offset = -5 if dst_active else -6
		
		ntp = adafruit_ntp.NTP(pool, tz_offset=offset)
		rtc.datetime = ntp.datetime
		log_entry(f"Time synced with offset {offset}: {rtc.datetime}")
	except Exception as e:
		log_entry(f"NTP sync failed: {e}", error=True)

### DISPLAY FUNCTIONS ###

def show_weather_display(rtc, duration=300):
	"""Display weather and time"""
	global last_successful_weather
	
	log_entry("Displaying weather...")
	
	# Fetch fresh weather data at the start of each cycle
	weather_data = fetch_weather_data()
	
	if not weather_data:
		log_entry("Weather data unavailable, showing clock instead", error=True)
		show_clock_display(rtc, duration)
		return
	
	clear_display()
	
	# Create display elements
	temp_text = bitmap_label.Label(bg_font, color=default_text_color, x=2, y=20)
	feels_like_text = bitmap_label.Label(font, color=default_text_color, y=16)
	feels_shade_text = bitmap_label.Label(font, color=default_text_color, y=24)
	time_text = bitmap_label.Label(font, color=default_text_color, x=15, y=24)
	
	# Load weather icon
	try:
		bitmap, palette = load_bmp_image(f"img/{weather_data['weather_icon']}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		main_group.append(image_grid)
	except Exception as e:
		log_entry(f"Weather icon load failed: {e}", error=True)
	
	# Setup temperature display
	temp_text.text = temp_format(weather_data['temperature'])
	main_group.append(temp_text)
	
	# Add feels-like temperatures if different
	if round(weather_data['feels_like']) != round(weather_data['temperature']):
		feels_like_text.text = temp_format(weather_data['feels_like'])
		feels_like_text.x = 64 - 1 - get_text_width(feels_like_text.text, font)
		main_group.append(feels_like_text)
	
	if round(weather_data['feels_shade']) != round(weather_data['feels_like']):
		feels_shade_text.text = temp_format(weather_data['feels_shade'])
		feels_shade_text.x = 64 - 1 - get_text_width(feels_shade_text.text, font)
		main_group.append(feels_shade_text)
	
	main_group.append(time_text)
	
	# Update loop (refresh weather every // minutes defined by main section)
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		
		# Update time display
		current_time = f"{twelve_hour_format(rtc.datetime.tm_hour)}:{rtc.datetime.tm_min:02d}"
		time_text.text = current_time
		if round(weather_data['feels_shade']) != round(weather_data['feels_like']):
			time_text.x = math.floor((64 - get_text_width(current_time, font)) / 2)
		else:
			time_text.x = 64 - 1 - get_text_width(current_time, font)
		time.sleep(1)

def show_clock_display(rtc, duration=30):
	"""Display clock only (fallback)"""
	global consecutive_failures, last_successful_weather
	
	log_entry("Displaying clock...")
	clear_display()
	
	date_text = bitmap_label.Label(font, color=default_text_color, x=5, y=7)
	time_text = bitmap_label.Label(bg_font, color=MINT, x=5, y=20)
	
	main_group.append(date_text)
	main_group.append(time_text)
	
	start_time = time.monotonic()
	
	while time.monotonic() - start_time < duration:
		date_str = f"{get_month_name(rtc.datetime.tm_mon).upper()} {rtc.datetime.tm_mday:02d}"
		time_str = f"{twelve_hour_format(rtc.datetime.tm_hour)}:{rtc.datetime.tm_min:02d}:{rtc.datetime.tm_sec:02d}"
		
		date_text.text = date_str
		time_text.text = time_str
		
		time.sleep(1)
	
	# Check if we should restart due to persistent weather failures
	time_since_success = time.monotonic() - last_successful_weather
	if consecutive_failures >= 3 or time_since_success > 600:  # 10 minutes
		log_entry(f"Restarting due to weather failures (failures: {consecutive_failures}, time since success: {time_since_success:.0f}s)", error=True)
		time.sleep(2)
		supervisor.reload()

def show_event_display(rtc, duration=10):
	"""Display special events"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	
	if month_day not in calendar:
		return False
	
	event_data = calendar[month_day]
	log_entry(f"Showing event: {event_data[1]}")
	clear_display()
	
	try:
		if event_data[1] == "Birthday":
			bitmap, palette = load_bmp_image("img/cake.bmp")
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			main_group.append(image_grid)
		else:
			# Load event image
			image_file = f"img/{event_data[2]}"
			if event_data[2] in os.listdir("img"):
				bitmap, palette = load_bmp_image(image_file)
			else:
				bitmap, palette = load_bmp_image("img/blank_sq.bmp")
			
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			image_grid.x = 36
			image_grid.y = 2
			
			# Create text labels
			line1_font = choose_font_for_text(event_data[1])
			line2_font = choose_font_for_text(event_data[0])
			
			text1 = bitmap_label.Label(line1_font, color=default_text_color, text=event_data[1], x=2, y=5)
			text2 = bitmap_label.Label(line2_font, color=MINT, text=event_data[0], x=2, y=19)
			
			main_group.append(image_grid)
			main_group.append(text1)
			main_group.append(text2)
	except Exception as e:
		log_entry(f"Event display error: {e}", error=True)
	
	# Wait for duration
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		time.sleep(0.1)
	
	return True

### MAIN PROGRAM ###

def main():
	"""Main program loop"""
	global last_successful_weather, rtc_instance, startup_time
	
	log_entry("=== PROGRAM STARTED ===")
	
	try:
		# Initialize hardware
		rtc = setup_rtc()  # This sets rtc_instance globally
		wifi_connected = setup_wifi()
		
		if wifi_connected:
			sync_time_ntp(rtc)
		
		# Initialize timing
		last_successful_weather = time.monotonic()
		startup_time = time.monotonic()
		
		# Main display loop
		log_entry("Starting display loop...")
		while True:
			try:
				# Check for daily reset
				check_daily_reset(rtc)
				
				# Show weather (30 seconds)
				show_weather_display(rtc, duration=300)
				
				# Show event if exists (10 seconds)
				event_shown = show_event_display(rtc, duration=30)
				
				if not event_shown:
					time.sleep(1)  # Brief pause if no event
					
			except Exception as e:
				log_entry(f"Main loop error: {e}", error=True)
				time.sleep(5)
				
	except Exception as e:
		log_entry(f"Critical error: {e}", error=True)
		time.sleep(10)
		supervisor.reload()

# Start program
if __name__ == "__main__":
	main()
