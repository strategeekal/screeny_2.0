##### TIME AND WEATHER SCREENY #####

### Import Libraries ###

# Main Libraries
import board  # Portal Matrix S3 main board library
import os  # OS functions. used to read setting file
import supervisor  # Soft restart board
import gc

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
DIMMEST_WHITE = 0x080808  # White night
DIM_WHITE = 0x202020  # White Day
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
	"1123" : ["Ric", "Cumple", "cake_sq.bmp"],
	"0811" : ["Alan", "Cumple", "cake_sq.bmp"],
	"0715" : ["Mexico", "Viva", "mexico_flag.bmp"],
	"0704" : ["July", "4th of", "us_flag.bmp"],
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
	doublebuffer = True,
)

display = framebufferio.FramebufferDisplay(matrix)

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
	
# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### OTHER FUNCTIONS ###

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

# print(f"Original Time:{rtc.datetime}")
# 
# chi_time = list(rtc.datetime)
# chi_time[1] = 08 #Month
# chi_time[2] = 11 #Day
# rtc.datetime = time.struct_time(tuple(chi_time))
# 
# print(f"Updated Time:{rtc.datetime}")


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


## DISPLAY MESSAGE LOOP ##

# Loop time parameters
start_time = time.monotonic()  # monotonic(ß) is better than time() for timing
duration = 2  # seconds >> Limits loop for testing
i = 1
while time.monotonic() - start_time < duration:

	current_time = (
		"%s%02d %d:%02d:%02d%2s"
		% (
			month_namer(rtc.datetime.tm_mon, "short").upper(),
			rtc.datetime.tm_mday,
			twelve_hour_clock(rtc.datetime.tm_hour),
			rtc.datetime.tm_min,
			rtc.datetime.tm_sec,
			meridian(rtc.datetime.tm_hour)
		)
	)
	
	month_and_day = (
		"%s %02d"
		% (
			month_namer(rtc.datetime.tm_mon, "short").upper(),
			rtc.datetime.tm_mday)
		)
		
	time_of_day = (
		"%d:%02d:%02d"
		% (
			twelve_hour_clock(rtc.datetime.tm_hour),
			rtc.datetime.tm_min,
			rtc.datetime.tm_sec
		)
	)
	
	time_meridian = meridian(rtc.datetime.tm_hour)
		
	# print(current_time)
	print(f"{i}/15 {month_and_day} - {time_of_day} {time_meridian}")
	time_line_text.text = time_of_day
	date_line_text.text = month_and_day
	#meridian_line_text.text = time_meridian
	i - i + 1
	time.sleep(1)
	
##### SECOND LOOP 

# current_month = tc.datetime.tm_mon
# current_day = rtc.datetime.tm_mday
month_day_combo = str(f"{rtc.datetime.tm_mon:02d}" + f"{rtc.datetime.tm_mday:02d}")

print(f"Month day Combo: {month_day_combo}")

if month_day_combo in calendar:
	
	print(calendar[month_day_combo][1])
	
	# Clear Display
	while len(main_group):
		main_group.pop()
		
	# Create a display group for your elements
	main_group = displayio.Group()
	display.root_group = main_group
	
	# Check if event is household birthday 
	if calendar[month_day_combo][1] == "Birthday":
		# Load the image (make sure "image.bmp" exists in your CIRCUITPY drive root)
		bitmap, palette = adafruit_imageload.load("img/cake.bmp")
		
		# Create a TileGrid to hold the image
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		
		# Add the image to the display group
		main_group.append(image_grid)
		
	else:
		t1 = calendar[month_day_combo][0]
		t2 = calendar[month_day_combo][1]
		image = calendar[month_day_combo][2]
		
		image_link = "img/" + str(image)
		
		if image in os.listdir("img"):
			# Load the image (make sure "image.bmp" exists in your CIRCUITPY drive root)
			bitmap, palette = adafruit_imageload.load(image_link)
		else:
			# Load the image (make sure "image.bmp" exists in your CIRCUITPY drive root)
			bitmap, palette = adafruit_imageload.load("img/blank_sq.bmp")
		
		# Create a TileGrid to hold the image
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		image_grid.x = 36
		
		# Create a bitmap_label object
		text_label_line_1 = bitmap_label.Label(
			bg_font,  # Use a built-in font or load a custom font
			color=default_text_color,  # Default Color
			text=t2,
			x=2,  # X-coordinate => 0 starts on first pixel with default font
			y=5,  # Y-coordinate => 4 starts at first pixel with default font
		)
		
		text_label_line_2 = bitmap_label.Label(
			bg_font,  # Use a built-in font or load a custom font
			color=MINT,  # Green color
			text=t1,
			x=2,  # X-coordinate => 0 starts on first pixel with default font
			y=19,  # Y-coordinate => 4 starts at first pixel with default font
		)
		
		# Add the image to the display group
		main_group.append(image_grid)
		main_group.append(text_label_line_1)
		main_group.append(text_label_line_2)
		
	start_time = time.monotonic()  # monotonic(ß) is better than time() for timing
	duration = 15  # seconds >> Limits loop for testing
	
	while time.monotonic() - start_time < duration:
		pass
	
else:
	print("No Special Event Today")

print("Display loop finished")

