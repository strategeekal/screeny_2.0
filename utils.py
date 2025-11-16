"""
Utilities Module for Screeny 2.0
=================================

This module contains logging functions and basic utilities.
Depends on: config.py

Extracted in Phase 2 of controlled refactoring from v2.0.6.1
"""

import time
import board
import displayio
import framebufferio
import rgbmatrix

# Import configuration
from config import (
	DebugLevel, CURRENT_DEBUG_LEVEL, System, MONTHS, Strings, Display, Timing
)

### LOGGING UTILITIES ###

def log_entry(message, level="INFO"):
	"""
	Unified logging with timestamp and level filtering
	"""
	# Import state here to avoid circular dependency at module load time
	from code import state

	# Map string levels to numeric levels
	level_map = {
		"DEBUG": DebugLevel.DEBUG,
		"INFO": DebugLevel.INFO,
		"WARNING": DebugLevel.WARNING,
		"ERROR": DebugLevel.ERROR
	}

	# Check if this message should be logged based on current debug level
	message_level = level_map.get(level, DebugLevel.INFO)
	if message_level > CURRENT_DEBUG_LEVEL:
		return  # Skip this message

	try:
		# Try RTC first, fallback to system time
		if state.rtc_instance:
			try:
				dt = state.rtc_instance.datetime
				timestamp = f"{dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d} {dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
				time_source = ""
			except Exception:
				monotonic_time = time.monotonic()
				timestamp = f"SYS+{int(monotonic_time)}"
				time_source = " [SYS]"
		else:
			monotonic_time = time.monotonic()
			hours = int(monotonic_time // System.SECONDS_PER_HOUR)
			minutes = int((monotonic_time % System.SECONDS_PER_HOUR) // System.SECONDS_PER_MINUTE)
			seconds = int(monotonic_time % System.SECONDS_PER_MINUTE)
			timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
			time_source = " [UPTIME]"

		# Build log entry
		log_line = f"[{timestamp}{time_source}] {level}: {message}"
		print(log_line)

	except Exception as e:
		print(f"[LOG-ERROR] Failed to log: {message} (Error: {e})")

def log_info(message):
	"""Log info message"""
	log_entry(message, "INFO")

def log_error(message):
	"""Log error message"""
	log_entry(message, "ERROR")

def log_warning(message):
	"""Log warning message"""
	log_entry(message, "WARNING")

def log_debug(message):
	"""Log debug message"""
	log_entry(message, "DEBUG")

def log_verbose(message):
	"""Log verbose message (extra detail)"""
	if CURRENT_DEBUG_LEVEL >= DebugLevel.VERBOSE:
		log_entry(message, "DEBUG")  # Use DEBUG level for formatting

def duration_message(seconds):
	"""Convert seconds to a readable duration string"""
	h, remainder = divmod(seconds, System.SECONDS_PER_HOUR)
	m, s = divmod(remainder, System.SECONDS_PER_MINUTE)

	parts = []
	if h > 0:
		parts.append(f"{h} hour{'s' if h != 1 else ''}")
	if m > 0:
		parts.append(f"{m} minute{'s' if m != 1 else ''}")
	if s > 0:
		parts.append(f"{s} second{'s' if s != 1 else ''}")

	return " ".join(parts) if parts else "0 seconds"


### PARSING FUNCTIONS ###

def parse_iso_datetime(iso_string):
	"""Parse ISO datetime string to components"""
	# Parse "2025-09-25T01:00:00-05:00"
	date_part, time_part = iso_string.split('T')

	# Parse date
	year, month, day = map(int, date_part.split('-'))

	# Parse time (ignoring timezone for now)
	time_with_tz = time_part.split('-')[0] if '-' in time_part else time_part.split('+')[0]
	hour, minute, second = map(int, time_with_tz.split(':'))

	return year, month, day, hour, minute, second

def format_datetime(iso_string):
	"""Format ISO datetime to human-readable string"""
	year, month, day, hour, minute, second = parse_iso_datetime(iso_string)

	# Format time
	if hour == 0:
		time_str = "12am"
	elif hour < 12:
		time_str = f"{hour}am"
	elif hour == 12:
		time_str = "12pm"
	else:
		time_str = f"{hour - 12}pm"

	return f"{MONTHS[month]} {day}, {time_str}"

def format_hour(hour):
	"""Format hour (0-23) to 12-hour format with am/pm suffix"""
	if hour == 0:
		return Strings.NOON_12AM
	elif hour < System.HOURS_IN_HALF_DAY:
		return f"{hour}{Strings.AM_SUFFIX}"
	elif hour == System.HOURS_IN_HALF_DAY:
		return Strings.NOON_12PM
	else:
		return f"{hour-System.HOURS_IN_HALF_DAY}{Strings.PM_SUFFIX}"

### HARDWARE INITIALIZATION ###

def initialize_display():
	"""Initialize RGB matrix display"""
	# Import state here to avoid circular dependency at module load time
	from code import state

	displayio.release_displays()

	matrix = rgbmatrix.RGBMatrix(
		width=Display.WIDTH, height=Display.HEIGHT, bit_depth=Display.BIT_DEPTH,
		rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1,
				board.MTX_R2, board.MTX_G2, board.MTX_B2],
		addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB,
				board.MTX_ADDRC, board.MTX_ADDRD],
		clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT,
		output_enable_pin=board.MTX_OE,
		serpentine=True, doublebuffer=True,
	)

	state.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
	state.main_group = displayio.Group()
	state.display.root_group = state.main_group


def interruptible_sleep(duration):
	"""Sleep that can be interrupted more easily"""
	end_time = time.monotonic() + duration
	while time.monotonic() < end_time:
		time.sleep(Timing.INTERRUPTIBLE_SLEEP_INTERVAL)  # Short sleep allows more interrupt opportunities
