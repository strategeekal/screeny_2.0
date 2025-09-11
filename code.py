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

### CONSTANTS AND VARIABLES ###

# Colors (6-bit values for your matrix)
BLACK = 0x000000
DIMMEST_WHITE = 0x101010
MINT = 0x080816
BUGAMBILIA = 0x101000
LILAC = 0x161408

default_text_color = DIMMEST_WHITE

# Load Fonts
bg_font = bitmap_font.load_font("fonts/bigbit10-16.bdf")
font = bitmap_font.load_font("fonts/tinybit6-16.bdf")

# Calendar (only BMP files since you're optimizing for BMP only)
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
	"0915": ["Mexico", "Viva", "mexico_flag_v3.bmp"],
	"0704": ["July", "4th of", "us_flag.bmp"],
	"0301": ["", "Spring", "spring.bmp"],
	"0601": ["", "Summer", "summer.bmp"],
	"0901": ["", "Fall", "fall.bmp"],
	"1031": ["Halloween", "Happy", "halloween.bmp"],
	"1101": ["Muertos", "Dia de", "day_of_the_death.bmp"],
	"1201": ["", "Winter", "winter.bmp"],
}

# Weather constants
ACCUWEATHER_LOCATION_KEY = "2626571"

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
		# Swap green and blue channels for your specific setup
		red_8bit = (original_color >> 16) & 0xFF
		blue_8bit = (original_color >> 8) & 0xFF
		green_8bit = original_color & 0xFF
		
		# Convert to 6-bit
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

def get_meridian(hour):
	"""Get AM/PM indicator"""
	return "AM" if hour < 12 else "PM"

def get_month_name(month_num):
	"""Get short month name"""
	months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
			  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	return months[month_num]

def clear_display():
	"""Clear all elements from display"""
	while len(main_group):
		main_group.pop()

### TIME AND NETWORK SETUP ###

def setup_rtc():
	"""Initialize RTC with retry logic"""
	for attempt in range(10):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			print(f"RTC initialized: {rtc.datetime}")
			return rtc
		except Exception as e:
			print(f"RTC attempt {attempt + 1} failed: {e}")
			time.sleep(2)
	
	print("RTC initialization failed, restarting...")
	supervisor.reload()

def setup_wifi():
	"""Connect to WiFi with retry logic"""
	ssid = os.getenv("CIRCUITPY_WIFI_SSID")
	password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
	
	if not ssid or not password:
		print("WiFi credentials missing")
		return False
	
	for attempt in range(5):
		try:
			wifi.radio.connect(ssid, password)
			print(f"Connected to {ssid}")
			return True
		except ConnectionError as e:
			print(f"WiFi attempt {attempt + 1} failed: {e}")
			time.sleep(2)
	
	print("WiFi connection failed")
	return False
	
def fetch_weather_data():
	"""Fetch current weather data from AccuWeather API"""
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
		except:
			api_key = None
			
		if not api_key:
			print("AccuWeather API key not found in settings.toml")
			return None
		
		# Build API URL with query parameters manually
		url = f"https://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_LOCATION_KEY}?apikey={api_key}&details=true"
		
		# Setup request
		pool = socketpool.SocketPool(wifi.radio)
		requests = adafruit_requests.Session(pool, ssl.create_default_context())
		
		# Make API call
		print("Fetching weather data...")
		response = requests.get(url)
		
		if response.status_code != 200:
			print(f"Weather API error: {response.status_code}")
			return None
		
		# Parse JSON response
		weather_json = response.json()
		response.close()
		
		if not weather_json or len(weather_json) == 0:
			print("Empty weather response")
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
		
		print(f"Weather: {weather_data['weather_text']}, {weather_data['temperature']}°C")
		print(f"Feels like: {weather_data['feels_like']}°C, Shade: {weather_data['feels_shade']}°C")
		return weather_data
		
	except Exception as e:
		print(f"Weather fetch error: {e}")
		return None

def sync_time_ntp(rtc):
	"""Sync RTC with NTP server"""
	try:
		pool = socketpool.SocketPool(wifi.radio)
		ntp = adafruit_ntp.NTP(pool, tz_offset=-6)  # Central Time
		rtc.datetime = ntp.datetime
		print(f"Time synced: {rtc.datetime}")
	except Exception as e:
		print(f"NTP sync failed: {e}")

### DISPLAY FUNCTIONS ###

def show_weather_display(rtc, duration=30):
	"""Display weather and time"""
	print("Displaying weather...")
	
	# Fetch fresh weather data
	weather_data = fetch_weather_data()
	
	if not weather_data:
		print("Weather data unavailable, showing clock instead")
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
		print(f"Weather icon load failed: {e}")
	
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
	
	# Update loop (refresh weather every 5 minutes)
	start_time = time.monotonic()
	last_weather_update = start_time
	
	while time.monotonic() - start_time < duration:
		# Refresh weather data every 5 minutes (300 seconds)
		current_time_mono = time.monotonic()
		if current_time_mono - last_weather_update > 300:
			print("Refreshing weather data...")
			new_weather = fetch_weather_data()
			if new_weather:
				weather_data = new_weather
				print("fetching new weather data")
				# Update temperature displays
				temp_text.text = temp_format(weather_data['temperature'])
				if round(weather_data['feels_like']) != round(weather_data['temperature']):
					feels_like_text.text = temp_format(weather_data['feels_like'])
					feels_like_text.x = 64 - 1 - get_text_width(feels_like_text.text, font)
				if round(weather_data['feels_shade']) != round(weather_data['feels_like']):
					feels_shade_text.text = temp_format(weather_data['feels_shade'])
					feels_shade_text.x = 64 - 1 - get_text_width(feels_shade_text.text, font)
			last_weather_update = current_time_mono
		
		# Update time display
		current_time = f"{twelve_hour_format(rtc.datetime.tm_hour)}:{rtc.datetime.tm_min:02d}:{rtc.datetime.tm_sec:02d}"
		time_text.text = current_time
		if round(weather_data['feels_shade']) != round(weather_data['feels_like']):
			time_text.x = math.floor((64 - get_text_width(current_time, font)) / 2)
		else:
			time_text.x = 64 - 1 - get_text_width(current_time, font)
		time.sleep(1)

def show_clock_display(rtc, duration=30):
	"""Display clock only (fallback)"""
	print("Displaying clock...")
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

def show_event_display(rtc, duration=10):
	"""Display special events"""
	month_day = f"{rtc.datetime.tm_mon:02d}{rtc.datetime.tm_mday:02d}"
	
	if month_day not in calendar:
		return False
	
	event_data = calendar[month_day]
	print(f"Showing event: {event_data[1]}")
	clear_display()
	
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
	
	# Wait for duration
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		time.sleep(0.1)
	
	return True

### MAIN PROGRAM ###

def main():
	"""Main program loop"""
	# Initialize hardware
	rtc = setup_rtc()
	wifi_connected = setup_wifi()
	
	if wifi_connected:
		sync_time_ntp(rtc)
	
	# Test date override (remove for production)
	test_time = list(rtc.datetime)
	test_time[1] = 9  # September
	test_time[2] = 1  # 1st
	rtc.datetime = time.struct_time(tuple(test_time))
	print(f"Test date set: {rtc.datetime}")
	
	# Main display loop
	print("Starting display loop...")
	while True:
		try:
			# Show weather (30 seconds)
			show_weather_display(rtc, duration=30)
			
			# Show event if exists (10 seconds)
			event_shown = show_event_display(rtc, duration=10)
			
			if not event_shown:
				time.sleep(1)  # Brief pause if no event
				
		except Exception as e:
			print(f"Main loop error: {e}")
			time.sleep(5)

# Start program
if __name__ == "__main__":
	main()