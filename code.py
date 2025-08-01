##### TIME AND WEATHER SCREENY #####

### Import Libraries ###

# Main Libraries
import board  # Portal Matrix S3 main board library
import os  # OS functions. used to read setting file
import supervisor  # Soft restart board
import gc

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

### INITIALIZE REAL TIME CLOCK ###

## Initialize the I2C Bus (For RTC functionality connected via STEMA from DS3231 Board):
i2c = board.I2C()

## Create an instance of the Real Time Clock (RTC) class using the I2C interface and the DS3231 board
for attempt in range(10):
	try:
		rtc = adafruit_ds3231.DS3231(i2c)
		print(rtc.datetime)
		clock_updated = False
		break
	except ValueError:
		# welcome_label.text = "Tik Tok!!"
		time.sleep(360)  # Try every 6 minutes for 10 times before soft reset
		print("Attempt {} of 10 rtc board not found".format(attempt))
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
else:
	recurr_message = "Keys Imported"

# welcome_label.text = recurr_message
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
		time.sleep(5)
		continue
else:
	supervisor.reload()

## INITIALIZE WIFI ##
pool = socketpool.SocketPool(wifi.radio)

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### SET REAL TIME CLOCK ###

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
		clock_updated = True
		

		print(f"Set clock to Chicago time: {chicago_time}")
		return chicago_time, clock_updated

	except Exception as e:
		print(f"Error getting time: {e}")
		return None


## UPDATE RTC ##

# rtc.datetime = time.struct_time((2017, 1, 1, 0, 0, 0, 6, 1, -1)) # FOR TEST
# print(rtc.datetime) # FOR TEST
print(f"Clok Updated: {clock_updated}")

chicago_time, clock_updated = get_chicago_time_from_ntp()

print(f"Clok Updated: {clock_updated}")

start_time = time.monotonic()  # monotonic() is better than time() for timing
duration = 15  # seconds

while time.monotonic() - start_time < duration:
	print(
		"%02d/%02d %02d:%02d:%02d"
		% (
			rtc.datetime.tm_mon,
			rtc.datetime.tm_mday,
			rtc.datetime.tm_hour,
			rtc.datetime.tm_min,
			rtc.datetime.tm_sec,
		)
	)
	time.sleep(1)

print("Display loop finished")
