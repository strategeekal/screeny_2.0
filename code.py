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

print("Hello!!!")