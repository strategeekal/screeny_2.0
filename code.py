##### TIME AND WEATHER SCREENY #####

### Import Libraries ###

# Main Libraries
import board # Portal Matrix S3 main board library
import os # OS functions. used to read setting file
import supervisor # Soft restart board

# Network Libraries
import wifi # Provides necessary low-level functionality for managing wifi connections
import ipaddress # Provides types for IP addresses
import ssl # Provides SSL contexts to wrap sockets in
import socketpool # Provides sockets through a pool to communicate over the network
import adafruit_requests # Requests-like library for web interfacing

# Real Time Clock Libraries
import adafruit_ds3231 # RTC board library
import time # Time and timing related functions
import adafruit_ntp # Network Time Protocol (NTP) helper for CircuitPython

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### INITIALIZE REAL TIME CLOCK ###

## Initialize the I2C Bus (For RTC functionality connected via STEMA from DS3231 Board):
i2c = board.I2C()

## Create an instance of the Real Time Clock (RTC) class using the I2C interface and the DS3231 board
for attempt in range(10):
	try:
		rtc = adafruit_ds3231.DS3231(i2c)
		print(rtc.datetime)
		break
	except ValueError:
		# welcome_label.text = "Tik Tok!!"
		time.sleep(360) # Try every 6 minutes for 10 times before soft reset
		print("Attempt {} of 10 rtc board not found".format(attempt))
		continue
else:
	supervisor.reload()

# ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== # # ====== #

### CONNECT TO INTERNET ###

## GET AND CONFIRM CREDENTIALS 

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = os.getenv("ADAFRUIT_AIOS_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")
timezone = os.getenv("TIMEZONE")
TIME_URL = f"https://io.adafruit.com/api/v2/{aio_username}/integrations/time/strftime?x-aio-key={aio_key}&tz={timezone}"
TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"

## CHECK CREDENTIALS
if any(var is None for var in (ssid, password, aio_username, aio_key, timezone)):
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

# ping_ip = ipaddress.IPv4Address("8.8.8.8")
# ping = wifi.radio.ping(ip=ping_ip)
# 
# if ping is None:
# 	ping = wifi.radio.ping(ip=ping_ip)
# 
# if ping is None:
# 	print("Couldn't ping 'google.com' successfully")
# else:
# 	# convert s to ms
# 	print(f"Pinging 'google.com' took: {ping * 1000} ms")