##### TIME AND WEATHER SCREENY #####

### Import Libraries ###

# Main Libraries
import board # Portal Matrix S3 main board library
import os # OS functions. used to read setting file

# Network Libraries
import wifi # Provides necessary low-level functionality for managing wifi connections
import ipaddress # Provides types for IP addresses
import ssl # Provides SSL contexts to wrap sockets in
import socketpool # Provides sockets through a pool to communicate over the network
import adafruit_requests # Requests-like library for web interfacing

# Real Time Clock Libraries
import adafruit_ds3231 # RTC board library
import time # Time and timing related functions
import adafruit_ntp # Network Time Protocol (NTP) helper for CircuitPython.

# Set up Real Time Clock
i2c = board.I2C()
rtc = adafruit_ds3231.DS3231(i2c)
current = rtc.datetime

# Get Wi-Fi Credentials
WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")

# Initialize connection components
radio = wifi.radio
pool = socketpool.SocketPool(radio)
ssl_context = ssl.create_default_context()
requests = adafruit_requests.Session(pool, ssl_context)

ntp = adafruit_ntp.NTP(pool, tz_offset=-5)

# Functions

def connect_wifi():
	"""Simple WiFi connection using radio.connect()"""
	try:
		if radio.connected:
			print("Already connected to WiFi")
			return True
			
		print(f"Connecting to {WIFI_SSID}...")
		radio.connect(WIFI_SSID, WIFI_PASSWORD)
		print(f"Connected! IP: {radio.ipv4_address}")
		return True
		
	except Exception as e:
		print(f"WiFi connection failed: {e}")
		return False

def fetch_ntp_time():
	"""Fetch current time using NTP"""
	try:
		print("Fetching time from NTP server...")
		current_time = ntp.datetime
		
		if current_time:
			# Set the system RTC to NTP time
			rtc.RTC().datetime = current_time
			print(f"NTP time received: {current_time}")
			return current_time
		else:
			print("No time data received from NTP")
			return None
			
	except Exception as e:
		print(f"NTP request failed: {e}")
		return None
		


# Check WiFi connection
if connect_wifi():
	# WiFi is connected - fetch NTP time
	print("Online mode: Fetching NTP time...")
	
	rtc.datetime = time.struct_time(ntp.datetime)
	current_time = rtc.datetime
	
	if current_time:
		# Format and display the time
		print('The current time is: {}/{}/{} {:02}:{:02}:{:02}'.format(current.tm_mon, current.tm_mday, current.tm_year, current.tm_hour, current.tm_min, current.tm_sec))
		
	else:
		print("Failed to get NTP time - using system time")
		# Fallback to system RTC
		system_time = time.localtime()
		print(f"System time: {system_time.tm_hour:02d}:{system_time.tm_min:02d}")
		
else:
	# WiFi failed - run offline mode
	print("Offline mode: Using system RTC time")
	system_time = time.localtime()
	formatted_time = f"{system_time.tm_hour:02d}:{system_time.tm_min:02d}:{system_time.tm_sec:02d}"
	print(f"Offline time: {formatted_time}")


