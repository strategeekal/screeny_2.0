##### TIME AND WEATHER SCREENY #####

### Import Libraries ###

# Main Libraries
import board  # Portal Matrix S3 main board library
import os  # OS functions. used to read setting file
import supervisor  # Soft restart board
import gc
import math

# RGB Matrix Libraries
import terminalio
import displayio # High level, display object compositing system -> Place items on the display
import framebufferio # Native frame buffer display driving
import rgbmatrix # library to Initialize and Control RGB Matrix -> Drive the display
from adafruit_display_text import bitmap_label # Text graphics handling, including text boxes
from adafruit_bitmap_font import bitmap_font # Decoding .pcf or .bdf font files into Bitmap objects
import adafruit_imageload # process and display images

# Network Libraries
import wifi  # Provides necessary low-level functionality for managing wifi connections
import ipaddress  # Provides types for IP addresses
import ssl  # Provides SSL contexts to wrap sockets in
import socketpool  # Provides sockets through a pool to communicate over the network
import adafruit_requests  # Requests-like library for web interfacing

# Real Time Clock Libraries
import adafruit_ds3231  # RTC board library
import time  # Time and timing related functions
import adafruit_ntp  # Network Time Protocol (NTP) helper for CircuitPython

gc.collect()  # Clear up memory after imports

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### CONSTANTS AND VARIABLES ###

## Colors
BLACK = 0x000000  # Black
WHITE = 0xFFFFFF  # Pure White
DIMMEST_WHITE = 0x101010  # White night
DIM_WHITE = 0x303030  # White Day
DARK_GREEN = 0x000800  # Green Darkest)
DARK_RED = 0x080000  # Red Darkest)
DARK_BLUE = 0x050500 # Blue Darkest)
DARK_PURPLE = 0x080008  # Purple Darkest)
DARK_YELLOW = 0x080800  # Yellow Darkest)
RADIOACTIVE_GREEN = 0x160866 # Nuclear Green Bright
TURQUOISE = 0x000808  # Turquoise Darkest)
PINK = 0x160808  # Pink)
LIME = 0x081608
MINT = 0x080816
BUGAMBILIA = 0x101000  # Bugambilia)
ORANGE = 0x200800  # Orange)
LILAC = 0x161408
BABY_BLUE = 0x081012  # Baby Blue)
MID_WHITE = 0x888888  # White Mid Bright)

default_text_color = DIMMEST_WHITE

## Load Fonts
bg_font_file = "fonts/bigbit10-16.bdf"
bg_font = bitmap_font.load_font(bg_font_file)
font_file = "fonts/tinybit6-16.bdf"
font = bitmap_font.load_font(font_file)

## Important Dates
calendar = {
	"0825" : ["Diego", "Birthday", "cake.bmp"],
	"0703" : ["Gaby", "Birthday", "cake.bmp"],
	"1109" : ["Tiago", "Birthday", "cake.bmp"],
	"0210" : ["Emilio", "Birthday", "cake.bmp"],
	"1225" : ["X-MAS", "Merry", "xmas.bmp"],
	"0214" : ["Didiculo", "Dia", "valentines.bmp"],
	"0824" : ["Abuela", "Cumple", "cake_sq.bmp"],
	"0101" : ["New Year", "Happy", "new_year.bmp"],
	"1123" : ["Ric", "Cumple", "cake_sq.bmp"],
	"0811" : ["Alan", "Cumple", "cake_sq.bmp"],
	"0915" : ["Mexico", "Viva", "mexico_flag_v3.bmp"],
	"0704" : ["July", "4th of", "us_flag.bmp"],
	"0301" : ["", "Spring", "spring.bmp"],
	"0601" : ["", "Summer", "summer.bmp"],
	"0901" : ["", "Fall", "fall.bmp"],
	"1031" : ["Halloween", "Happy", "halloween.bmp"],
	"1101" : ["Muertos", "Dia de", "day_of_the_death.bmp"],
	"1201" : ["", "Winter", "winter.bmp"],
}

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #
	
### INITIALIZE SCREEN ###

## Release any actively used displays so their buses and pins can be used again.
displayio.release_displays()

## Create the RGB Matrix object using the native RGB Matrix class
matrix = rgbmatrix.RGBMatrix(
	width = 64,
	height = 32,
	bit_depth = 6,
	rgb_pins = [
		board.MTX_R1,
		board.MTX_G1,
		board.MTX_B1,
		board.MTX_R2,
		board.MTX_G2,
		board.MTX_B2,
	],
	addr_pins = [
		board.MTX_ADDRA,
		board.MTX_ADDRB,
		board.MTX_ADDRC,
		board.MTX_ADDRD,
	],
	clock_pin = board.MTX_CLK,
	latch_pin = board.MTX_LAT,
	output_enable_pin = board.MTX_OE,
	serpentine=True,
	doublebuffer = True,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
display.brightness = 0.1

## WELCOME MESSAGE ##

# Create a display group to hold display elements
main_group = displayio.Group()
display.root_group = main_group

# Create a bitmap_label objects
welcome_label = bitmap_label.Label(
	bg_font,  # Use a built-in font or load a custom font
	color=LILAC,  # Red color
	text="HOLA!!",
	x=15,  # X-coordinate => 0 starts on first pixel with default font
	y=15,  # Y-coordinate => 4 starts at first pixel with default font
)

main_group.append(welcome_label)

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### TIME FUNCTIONS ###

## DAYLIGHT SAVINGS TIME ADJUST FUNCTIONS ##

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


def utc_to_chicago_robust(utc_dt):
	"""
	Convert UTC time to Chicago time with robust DST handling.

	Args:
		utc_dt: UTC time struct

	Returns:
		time.struct_time: Chicago local time
	"""
	# Determine if DST is active
	dst_active = is_dst_us_central(utc_dt)

	# Central Standard Time (CST) = UTC - 6 hours
	# Central Daylight Time (CDT) = UTC - 5 hours
	offset_hours = -5 if dst_active else -6

	# Convert to timestamp, apply offset, convert back
	utc_timestamp = time.mktime(utc_dt)
	chicago_timestamp = utc_timestamp + (offset_hours * 3600)

	return time.localtime(chicago_timestamp)


def get_chicago_time_from_ntp():
	"""
	Complete function to get Chicago time from NTP server.
	Use this in your CircuitPython project.
	"""

	# Ensure WiFi is connected
	if not wifi.radio.connected:
		print("WiFi not connected!")
		return None

	try:
		pool = socketpool.SocketPool(wifi.radio)
		ntp = adafruit_ntp.NTP(pool, tz_offset=0)  # Get UTC
		utc_time = ntp.datetime

		# Convert to Chicago time
		chicago_time = utc_to_chicago_robust(utc_time)

		# Set the DS3231/RTC
		rtc.datetime = chicago_time
		

		print(f"Set clock to Chicago time: {chicago_time}")
		return chicago_time

	except Exception as e:
		print(f"Error getting time: {e}")
		return None
		
		
# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### FORMATTING FUNCTIONS ###

def meridian(hod):
	if hod < 12:
		time_meridian = "AM"
	else:
		time_meridian = "PM"
	return time_meridian
	
def twelve_hour_clock(hod):
	if hod > 12:
		h = hod - 12
	else:
		h = hod
	return h
	
months = {1:["January", "Jan"], 2:["February", "Feb"], 3:["March", "Mar"], 4:["April", "Apr"], 5:["May", "May"], 6:["June", "Jun"], 7:["July","Jul"], 8:["August", "Aug"], 9:["September", "Sep"], 10:["October", "Oct"], 11:["November", "Nov"], 12:["December", "Dec"] }

def month_namer(month_number, month_format="short"):
	if month_format == "short":
		m = months[month_number][1]  # Get the short name (index 1)
	else:
		m = months[month_number][0]  # Get the full name (index 0)
	return m
	
## COLOR CONVERSION FUNTIONS ##

def convert_bmp_palette(palette):
	"""
	Convert BMP palette from 8-bit BGR to 6-bit RGB for matrix display
	"""
	if palette is None:
		return None
	
	# Check if it's a ColorConverter - if so, return as-is and let the matrix handle it
	if hasattr(palette, '__name__') and 'ColorConverter' in str(type(palette)):
		return palette
	
	# Handle standard displayio.Palette
	try:
		palette_len = len(palette)
	except TypeError:
		# If len() fails, it might be a ColorConverter or other type - return as-is
		return palette
	
	#print(f"Converting palette with {palette_len} colors...")
	
	# Create new palette for converted colors
	converted_palette = displayio.Palette(palette_len)
	
	for i in range(palette_len):
		# Get original color (24-bit color from palette)
		original_color = palette[i]
		
		# Debug: Print first few colors
		#if i < 5:
			#print(f"  Original Color {i}: 0x{original_color:06X}")
		
		# Your BMP files need green and blue swapped
		red_8bit = (original_color >> 16) & 0xFF    # Red is correct
		blue_8bit = (original_color >> 8) & 0xFF    # Blue comes from green position
		green_8bit = original_color & 0xFF          # Green comes from blue position
		
		# Convert from 8-bit to 6-bit
		red_6bit = red_8bit >> 2
		green_6bit = green_8bit >> 2
		blue_6bit = blue_8bit >> 2
		
		# For a 6-bit matrix, combine as RGB (not shifted to 24-bit positions)
		# Just use the 6-bit values directly
		converted_color = (red_6bit << 16) | (green_6bit << 8) | blue_6bit
		
		#if i < 5:
			#print(f"    RGB_8bit: ({red_8bit},{green_8bit},{blue_8bit})")
			#print(f"    RGB_6bit: ({red_6bit},{green_6bit},{blue_6bit}) = 0x{converted_color:06X}")
		
		converted_palette[i] = converted_color
	
	return converted_palette

def convert_png_palette(palette):
	"""
	Convert PNG palette from 8-bit to 6-bit for matrix display
	PNG already has correct RGB order, just needs bit depth scaling
	"""
	if palette is None:
		return None
	
	# Check if it's a ColorConverter - if so, return as-is
	if hasattr(palette, '__name__') and 'ColorConverter' in str(type(palette)):
		return palette
	
	# Handle standard displayio.Palette
	try:
		palette_len = len(palette)
	except TypeError:
		# If len() fails, it might be a ColorConverter - return as-is
		return palette
	
	converted_palette = displayio.Palette(palette_len)
	
	for i in range(palette_len):
		original_color = palette[i]
		
		# PNG palette is already RGB order
		red_8bit = (original_color >> 16) & 0xFF
		green_8bit = (original_color >> 8) & 0xFF
		blue_8bit = original_color & 0xFF
		
		# Convert from 8-bit to 6-bit (no channel swapping needed)
		red_6bit = red_8bit >> 2
		green_6bit = green_8bit >> 2
		blue_6bit = blue_8bit >> 2
		
		# Combine back into 18-bit color for 6-bit matrix
		converted_color = (red_6bit << 12) | (green_6bit << 6) | blue_6bit
		
		converted_palette[i] = converted_color
	
	return converted_palette

# Enhanced universal image loading function with ColorConverter handling
def load_and_convert_image(filepath):
	"""
	Load image (BMP or PNG) and apply appropriate color conversion for matrix display
	"""
	bitmap, palette = adafruit_imageload.load(filepath)
	
	# Check file extension to determine conversion needed
	file_ext = filepath.lower().split('.')[-1]
	
	#print(f"Loading {filepath}: {file_ext} format")
	#print(f"Palette type: {type(palette)}")
	
	# Handle ColorConverter (direct color images)
	if palette and 'ColorConverter' in str(type(palette)):
		#print("Image uses ColorConverter (direct color)")
		#print("ColorConverter images can't be easily modified - use indexed-color BMPs instead")
		# Return as-is - colors may be wrong but won't crash
		return bitmap, palette
	
	# Handle palette-based images
	if file_ext == 'bmp':
		# BMP needs BGR->RGB conversion AND bit depth conversion
		#print("Applying BMP conversion...")
		if palette:
			converted_palette = convert_bmp_palette(palette)
			return bitmap, converted_palette
		else:
			return bitmap, palette
	
	elif file_ext == 'png':
		# Many PNG files also need BGR->RGB conversion
		#print("Applying BMP-style conversion to PNG...")
		if palette:
			converted_palette = convert_bmp_palette(palette)  # Use BMP conversion for PNG too
			return bitmap, converted_palette
		else:
			return bitmap, palette
	
	else:
		# Unknown format, load as-is
		print("Unknown format, loading as-is...")
		return bitmap, palette

def create_bgr_swapped_converter():
	"""
	Create a custom ColorConverter that swaps BGR to RGB
	"""
	# This is a simple approach - create a palette with swapped colors
	# For more complex images, this might need more sophisticated handling
	
	# Create a basic converter that handles common flag colors
	converted_palette = displayio.Palette(8)  # Small palette for common colors
	
	# Define some common colors with BGR->RGB swap applied
	# These are 6-bit colors (0-63 range)
	converted_palette[0] = 0x000000  # Black
	converted_palette[1] = 0x3F3F3F  # White (63,63,63 in 6-bit)
	converted_palette[2] = 0x3F0000  # Red (was blue in BGR)
	converted_palette[3] = 0x003F00  # Green (stays green)
	converted_palette[4] = 0x00003F  # Blue (was red in BGR)
	converted_palette[5] = 0x3F3F00  # Yellow
	converted_palette[6] = 0x3F003F  # Magenta
	converted_palette[7] = 0x003F3F  # Cyan
	
	return converted_palette

# Alternative function to force BGR->RGB conversion on PNG if needed
def load_and_convert_image_force_bgr(filepath):
	"""
	Force BGR->RGB conversion on all images (use this if PNG colors are still wrong)
	"""
	bitmap, palette = adafruit_imageload.load(filepath)
	
	print(f"Loading {filepath} with forced BGR conversion")
	print(f"Palette type: {type(palette)}")
	
	# Apply BMP-style conversion to all images
	if palette:
		converted_palette = convert_bmp_palette(palette)
		return bitmap, converted_palette
	else:
		return bitmap, palette
		
## TEXT LENGTH FUNCTIONS ##

def get_text_width(text, font):
	"""Get pixel width of text using CircuitPython bitmap_label"""
	if not text:  # Handle empty strings
		return 0
	
	# Create a temporary label to measure
	temp_label = bitmap_label.Label(font, text=text)
	
	# Get bounding box - returns (x, y, width, height)
	bbox = temp_label.bounding_box
	if bbox:
		return bbox[2]  # width is at index 2
	else:
		return 0

def choose_font_for_text(text, max_width=35):
	"""Choose big or small font based on text width"""
	
	# Try big font first
	big_width = get_text_width(text, bg_font)
	if big_width <= max_width:
		return bg_font
	
	# Fall back to small font
	small_width = get_text_width(text, font)
	if small_width <= max_width:
		return font
	
	# Return small font even if too wide
	return font
	
def fit_text_to_width(text, font, max_width):
	"""Truncate text with ellipsis if too long"""
	
	# Check if full text fits
	full_width = get_text_width(text, font)
	if full_width <= max_width:
		return text
	
	# Find how many characters fit with "..."
	ellipsis_width = get_text_width("...", font)
	available_width = max_width - ellipsis_width
	
	truncated = ""
	for i, char in enumerate(text):
		test_text = truncated + char
		if get_text_width(test_text, font) > available_width:
			break
		truncated = test_text
	
	return truncated + "..."

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### OTHER FUNCTIONS ###

def temp_format(temp):
	temp = round(temp)
	temp = str(temp)
	temp = temp + "°"
	return temp

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### INITIALIZE REAL TIME CLOCK ###

## Create an instance of the Real Time Clock (RTC) class using the I2C interface and the DS3231 board
for attempt in range(20):
	try:
		## Initialize the I2C Bus (For RTC functionality connected via STEMA from DS3231 Board):
		i2c = board.I2C()
		
		rtc = adafruit_ds3231.DS3231(i2c)
		print(rtc.datetime)
		break
	except Exception as e:  # Catch specific exception and store it
		welcome_label.color = "DARK_RED"
		welcome_label.text = "Tik Tok!!"
		print(f"Error: {e}")
		print("Attempt {} of 10 rtc board not found".format(attempt + 1))  # +1 for human-readable counting
		time.sleep(30)
		continue
else:
	supervisor.reload()	
	
# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### CONNECT TO INTERNET ###

## GET AND CONFIRM CREDENTIALS

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

## CHECK CREDENTIALS
if any(var is None for var in (ssid, password)):
	recurr_message = "WiFI Key"
	welcome_label.text = recurr_message
else:
	recurr_message = "Keys Imported"


print(recurr_message)

## ESTABLISH A CONNECTION
for attempt in range(10):
	try:
		wifi.radio.connect(ssid, password)
		print(f"Connected to {ssid}")
		print(f"My IP address: {wifi.radio.ipv4_address}")
		break
	except ConnectionError as e:
		print(f"Connection Error: {e}")
		print("Attempt {} of 10, Retrying in 5 seconds...".format(attempt))
		
		## Show clock while waiting
		
		# Clear existing labels
		while len(main_group):
			main_group.pop()
			
		# Create a bitmap_label objects
		date_line_text = bitmap_label.Label(
			font,  # Use a built-in font or load a custom font
			color=default_text_color,  # Red color
			text="",
			x=5,  # X-coordinate => 0 starts on first pixel with default font
			y=7,  # Y-coordinate => 4 starts at first pixel with default font
		)
		
		time_line_text = bitmap_label.Label(
			bg_font,  # Use a built-in font or load a custom font
			color=BUGAMBILIA,  # Pink color
			text="",
			x=5,  # X-coordinate => 0 starts on first pixel with default font
			y=20,  # Y-coordinate => 4 starts at first pixel with default font
		)
		
		error_line_text = bitmap_label.Label(
			font,  # Use a built-in font or load a custom font
			color=BUGAMBILIA,  # Pink color
			text="W",
			x=57,  # X-coordinate => 0 starts on first pixel with default font
			y=1,  # Y-coordinate => 4 starts at first pixel with default font
		)
		
		# Add the label to the display group
		main_group.append(date_line_text)
		main_group.append(time_line_text)
		main_group.append(error_line_text)
		
		# Loop time parameters
		start_time = time.monotonic()  # monotonic(ß) is better than time() for timing
		duration = 5  # seconds >> Limits loop for testing

		while time.monotonic() - start_time < duration:
			
			month_and_day = (
				"%s %02d"
				% (
					month_namer(rtc.datetime.tm_mon, "short").upper(),
					rtc.datetime.tm_mday)
				)
				
			time_of_day = (
				"%d:%02d"
				% (
					twelve_hour_clock(rtc.datetime.tm_hour),
					rtc.datetime.tm_min
				)
			)
			
			# print(current_time)
			time_line_text.text = time_of_day
			date_line_text.text = month_and_day
			time.sleep(1)
		
		continue
		
else:
	supervisor.reload()

## INITIALIZE WIFI ##
pool = socketpool.SocketPool(wifi.radio)

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #
		
### PREPARE MESSAGE ###

## UPDATE RTC ##

# rtc.datetime = time.struct_time((2017, 1, 1, 0, 0, 0, 6, 1, -1)) # FOR TEST
# print(rtc.datetime) # FOR TEST

chicago_time = get_chicago_time_from_ntp()

# Change Date to test event functionality

print(f"Original Time:{rtc.datetime}")

chi_time = list(rtc.datetime)
#chi_time[1] = 09 #Month
#chi_time[2] = 1 #Day
#rtc.datetime = time.struct_time(tuple(chi_time))

print(f"Updated Time:{rtc.datetime}")

## SET WEATHER VARIABLES ##

weatherIcon = 0
humidity = 0
temperature = 00
feelsLike = 00
feelsLikeShade = 00
uvIndex = 0

## PREPARE MATRIX MESSAGE ##

# Clear Display
while len(main_group):
	main_group.pop()

# Create a bitmap_label objects
date_line_text = bitmap_label.Label(
	font,  # Use a built-in font or load a custom font
	color=default_text_color,  # Red color
	text="",
	x=5,  # X-coordinate => 0 starts on first pixel with default font
	y=7,  # Y-coordinate => 4 starts at first pixel with default font
)

time_line_text = bitmap_label.Label(
	bg_font,  # Use a built-in font or load a custom font
	color=MINT,  # Pink color
	text="",
	x=5,  # X-coordinate => 0 starts on first pixel with default font
	y=20,  # Y-coordinate => 4 starts at first pixel with default font
)

meridian_line_text = bitmap_label.Label(
	bg_font,  # Use a built-in font or load a custom font
	color=default_text_color,  # Pink color
	text="",
	x=45,  # X-coordinate => 0 starts on first pixel with default font
	y=20,  # Y-coordinate => 4 starts at first pixel with default font
)

error_line_text = bitmap_label.Label(
	font,  # Use a built-in font or load a custom font
	color=BUGAMBILIA,  # Pink color
	text="",
	x=57,  # X-coordinate => 0 starts on first pixel with default font
	y=1,  # Y-coordinate => 4 starts at first pixel with default font
)

# Add the label to the display group
main_group.append(date_line_text)
main_group.append(time_line_text)
main_group.append(meridian_line_text)
main_group.append(error_line_text)


def show_weather_display(duration, weather_available=True):
	"""Display weather and time for specified duration"""
	global main_group

	if not weather_available:
		print("Weather unavailable, falling back to clock display")
		show_clock_display(duration)
		return

	print("Displaying weather...")

	# Clear Display
	while len(main_group):
		main_group.pop()

	# Create weather display elements (based on your weather code)
	temp_text = bitmap_label.Label(
		bg_font,
		color=default_text_color,
		x=2, y=20
	)

	feelsLike_text = bitmap_label.Label(
		font,
		color=default_text_color,
		y=16
	)

	feelsLikeShade_text = bitmap_label.Label(
		font,
		color=default_text_color,
		y=24
	)

	time_line_text = bitmap_label.Label(
		font,
		color=default_text_color,
		text="",
		x=15, y=24
	)
	
	### GET WEATHER DATA ##
	
	# Mock weather data (replace with your actual data source later)
	weatherIcon = 1.1
	temperature = 72.3
	feelsLike = 74.2
	feelsLikeShade = 71.7
			
	# Clear previous display elements
	while len(main_group):
		main_group.pop()

	# Load and display weather image
	try:
		bitmap, palette = load_and_convert_image(f"img/{weatherIcon}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		main_group.append(image_grid)
	except Exception as e:
		print(f"Failed to load weather image: {e}")

	# Display temperature
	temp_text.text = temp_format(temperature)
	main_group.append(temp_text)

	# Display feels like temperature if different
	if (round(feelsLike) != round(feelsLikeShade) or
		round(feelsLike) != round(temperature)):
		feelsLike_text.text = temp_format(feelsLike)
		feelsLike_text.x = 64 - 1 - get_text_width(temp_format(feelsLike), font)
		main_group.append(feelsLike_text)

	if round(feelsLike) != round(feelsLikeShade):
		feelsLikeShade_text.text = temp_format(feelsLikeShade)
		feelsLikeShade_text.x = 64 - 1 - get_text_width(temp_format(feelsLikeShade), font)
		main_group.append(feelsLikeShade_text)
	else:
		time_line_text.x = 64 - 1 - (get_text_width(time_line_text.text, font))

	main_group.append(time_line_text)
	
	print(5+5)


	# Show weather display for specified duration
	start_time = time.monotonic()
	update_counter = 1

	while time.monotonic() - start_time < duration:
		try:
			
					# Update time display
			time_of_day = (
				"%d:%02d" % (
					twelve_hour_clock(rtc.datetime.tm_hour),
					rtc.datetime.tm_min,
				)
			)

			time_line_text.text = time_of_day
			time_line_text.x = math.floor((64 - (get_text_width(time_line_text.text, font)-1))/2)
			
			update_counter += 1
			time.sleep(1)  # Update display every 5 seconds

		except Exception as e:
			print(f"Error in weather display: {e}")

def show_clock_display(duration):
	"""Display clock-only for specified duration"""
	global main_group

	print("Displaying clock...")

	# Clear Display
	while len(main_group):
		main_group.pop()

	# Create clock labels
	date_line_text = bitmap_label.Label(
		font,
		color=default_text_color,
		text="",
		x=5, y=7,
	)

	time_line_text = bitmap_label.Label(
		bg_font,
		color=MINT,
		text="",
		x=5, y=20,
	)

	meridian_line_text = bitmap_label.Label(
		bg_font,
		color=default_text_color,
		text="",
		x=45, y=20,
	)

	# Add labels to display group
	main_group.append(date_line_text)
	main_group.append(time_line_text)
	main_group.append(meridian_line_text)

	# Show clock for specified duration
	start_time = time.monotonic()
	counter = 1

	while time.monotonic() - start_time < duration:
		month_and_day = (
			"%s %02d" % (
				month_namer(rtc.datetime.tm_mon, "short").upper(),
				rtc.datetime.tm_mday
			)
		)

		time_of_day = (
			"%d:%02d:%02d" % (
				twelve_hour_clock(rtc.datetime.tm_hour),
				rtc.datetime.tm_min,
				rtc.datetime.tm_sec
			)
		)

		time_meridian = meridian(rtc.datetime.tm_hour)

		# Update display
		time_line_text.text = time_of_day
		date_line_text.text = month_and_day

		print(f"Clock {counter}: {month_and_day} - {time_of_day} {time_meridian}")
		counter += 1
		time.sleep(1)

def show_special_event_display(month_day_combo, duration):
	"""Display special event for specified duration"""
	print(f"Showing event: {calendar[month_day_combo][1]}")
	
	# Clear Display
	while len(main_group):
		main_group.pop()
	
	# No need to create a new group, just use the existing one
	
	# Check if event is household birthday
	if calendar[month_day_combo][1] == "Birthday":
		bitmap, palette = load_and_convert_image("img/cake.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		main_group.append(image_grid)
		
	else:
		t1 = calendar[month_day_combo][0]
		t2 = calendar[month_day_combo][1]
		
		# Choose fonts based on text width
		chosen_font_1 = choose_font_for_text(t2, max_width=34)
		chosen_font_2 = choose_font_for_text(t1, max_width=34)
		
		image = calendar[month_day_combo][2]
		image_link = "img/" + str(image)
		
		if image in os.listdir("img"):
			bitmap, palette = load_and_convert_image(image_link)
		else:
			bitmap, palette = load_and_convert_image("img/blank_sq.bmp")
		
		# Create image grid
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		image_grid.x = 36
		image_grid.y = 2
		
		# Create text labels
		text_label_line_1 = bitmap_label.Label(
			chosen_font_1,
			color=default_text_color,
			text=t2,
			x=2, y=5,
		)
		
		text_label_line_2 = bitmap_label.Label(
			chosen_font_2,
			color=MINT,
			text=t1,
			x=2, y=19,
		)
		
		# Add elements to display
		main_group.append(image_grid)
		main_group.append(text_label_line_1)
		main_group.append(text_label_line_2)
	
	# Show event for specified duration
	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		time.sleep(0.1)  # Just wait, no updates needed

def main_display_loop():
	"""Main loop: alternates between weather/clock (30s) and events (10s)"""
	print("Starting main display loop with weather integration...")

	while True:
		try:
			# Try weather display first, fall back to clock if needed
			# Set weather_available=False to test clock fallback
			weather_available = True  # Change this to False to test clock fallback
			show_weather_display(duration=20, weather_available=weather_available)

			# Check for special events and show if exists
			month_day_combo = str(f"{rtc.datetime.tm_mon:02d}" + f"{rtc.datetime.tm_mday:02d}")
			print(f"Checking for events on: {month_day_combo}")

			if month_day_combo in calendar:
				print(f"Found event: {calendar[month_day_combo]}")
				show_special_event_display(month_day_combo, duration=10)
			else:
				print("No special event today")
				time.sleep(1)  # Brief pause before next cycle

		except Exception as e:
			print(f"Error in main loop: {e}")
			time.sleep(5)  # Wait before retrying
			continue

# Start the integrated display system
print("Starting weather-integrated display...")
main_display_loop()
