"""
Utilities module for Pantallita 2.0
Contains logging, parsing, memory monitoring, and helper functions
"""

import gc
import time
from config import DebugLevel, CURRENT_DEBUG_LEVEL, System, Timing, Memory, MONTHS


# ===========================
# MEMORY MONITORING
# ===========================

class MemoryMonitor:
	"""Monitor memory usage and track peak usage over time"""

	def __init__(self):
		self.baseline_memory = gc.mem_free()
		self.startup_time = time.monotonic()
		self.peak_usage = 0
		self.measurements = []
		self.max_measurements = 5

	def get_memory_stats(self):
		"""
		Get current memory statistics with percentages.

		Returns:
			dict: Memory statistics including free/used bytes and percentages
		"""
		current_free = gc.mem_free()
		current_used = Memory.ESTIMATED_TOTAL - current_free
		usage_percent = (current_used / Memory.ESTIMATED_TOTAL) * 100
		free_percent = (current_free / Memory.ESTIMATED_TOTAL) * 100

		return {
			"free_bytes": current_free,
			"used_bytes": current_used,
			"usage_percent": usage_percent,
			"free_percent": free_percent,
		}

	def get_runtime(self):
		"""
		Get runtime since startup.

		Returns:
			str: Formatted runtime string (HH:MM:SS)
		"""
		elapsed = time.monotonic() - self.startup_time
		hours = int(elapsed // System.SECONDS_PER_HOUR)
		minutes = int((elapsed % System.SECONDS_PER_HOUR) // System.SECONDS_PER_MINUTE)
		seconds = int(elapsed % System.SECONDS_PER_MINUTE)
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

	def check_memory(self, checkpoint_name=""):
		"""
		Check memory and log only if there's an issue.

		Args:
			checkpoint_name (str): Name of checkpoint for tracking

		Returns:
			str: "ok" status
		"""
		stats = self.get_memory_stats()
		runtime = self.get_runtime()

		if stats["used_bytes"] > self.peak_usage:
			self.peak_usage = stats["used_bytes"]

		self.measurements.append({
			"name": checkpoint_name,
			"used_percent": stats["usage_percent"],
			"runtime": runtime
		})
		if len(self.measurements) > self.max_measurements:
			self.measurements.pop(0)

		# Only log if memory usage is concerning (>50%) or at VERBOSE level
		if stats["usage_percent"] > 50:
			log_warning(f"High memory: {stats['usage_percent']:.1f}% at {checkpoint_name}")
		else:
			log_verbose(f"Memory: {stats['usage_percent']:.1f}% at {checkpoint_name}")

		return "ok"

	def get_memory_report(self):
		"""
		Generate a simplified memory report.

		Returns:
			str: Formatted memory report
		"""
		stats = self.get_memory_stats()
		runtime = self.get_runtime()
		peak_percent = (self.peak_usage / Memory.ESTIMATED_TOTAL) * 100

		report = [
			"=== MEMORY REPORT ===",
			f"Runtime: {runtime}",
			f"Current: {stats['usage_percent']:.1f}% used",
			f"Peak usage: {peak_percent:.1f}%",
		]

		if self.measurements:
			report.append("Recent measurements:")
			for measurement in self.measurements:
				name = measurement["name"] or "unnamed"
				used_pct = measurement["used_percent"]
				runtime = measurement["runtime"]
				report.append(f"  {name}: {used_pct:.1f}% used [{runtime}]")

		return "\n".join(report)

	def log_report(self):
		"""Log the memory report"""
		report = self.get_memory_report()
		for line in report.split("\n"):
			log_debug(line)


# ===========================
# LOGGING UTILITIES
# ===========================

# Global reference to state for logging (will be set from main code.py)
_log_state = None

def set_log_state(state):
	"""Set the global state reference for logging"""
	global _log_state
	_log_state = state


def log_entry(message, level="INFO"):
	"""
	Unified logging with timestamp and level filtering.

	Args:
		message (str): Message to log
		level (str): Log level (INFO, ERROR, WARNING, DEBUG)
	"""
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
		if _log_state and _log_state.rtc_instance:
			try:
				dt = _log_state.rtc_instance.datetime
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
	"""
	Convert seconds to a readable duration string.

	Args:
		seconds (int): Duration in seconds

	Returns:
		str: Human-readable duration (e.g., "2 hours 30 minutes 15 seconds")
	"""
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


# ===========================
# PARSING FUNCTIONS
# ===========================

def parse_iso_datetime(iso_string):
	"""
	Parse ISO 8601 datetime string to individual components.

	Args:
		iso_string (str): ISO format string (e.g., "2025-09-25T01:00:00-05:00")

	Returns:
		tuple: (year, month, day, hour, minute, second)
	"""
	# Parse "2025-09-25T01:00:00-05:00"
	date_part, time_part = iso_string.split('T')

	# Parse date
	year, month, day = map(int, date_part.split('-'))

	# Parse time (ignoring timezone for now)
	time_with_tz = time_part.split('-')[0] if '-' in time_part else time_part.split('+')[0]
	hour, minute, second = map(int, time_with_tz.split(':'))

	return year, month, day, hour, minute, second


def format_datetime(iso_string):
	"""
	Format ISO datetime string to human-readable format.

	Args:
		iso_string (str): ISO format string

	Returns:
		str: Formatted datetime (e.g., "Sep 25, 1pm")
	"""
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


# ===========================
# TIME UTILITIES
# ===========================

def calculate_weekday(year, month, day):
	"""
	Calculate day of the week using Zeller's congruence algorithm.

	Args:
		year (int): Year
		month (int): Month (1-12)
		day (int): Day of month

	Returns:
		int: Day of week (0=Monday, 1=Tuesday, ..., 6=Sunday)
	"""
	# Zeller's congruence requires January and February to be counted as months 13 and 14 of the previous year
	if month < 3:
		month += 12
		year -= 1

	# Zeller's formula
	q = day
	m = month
	k = year % 100
	j = year // 100

	h = (q + ((13 * (m + 1)) // 5) + k + (k // 4) + (j // 4) - 2 * j) % 7

	# Convert Zeller's result (0=Saturday) to tm_wday format (0=Monday)
	# Zeller: 0=Sat, 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri
	# tm_wday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
	weekday_map = [5, 6, 0, 1, 2, 3, 4]  # Map Zeller to tm_wday
	return weekday_map[h]


def calculate_yearday(year, month, day):
	"""
	Calculate day of year (1-366).

	Args:
		year (int): Year
		month (int): Month (1-12)
		day (int): Day of month

	Returns:
		int: Day of year (1-366)
	"""
	days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

	# Check for leap year
	if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
		days_in_month[1] = 29

	return sum(days_in_month[:month-1]) + day


def update_rtc_datetime(rtc, new_year=None, new_month=None, new_day=None, new_hour=None, new_minute=None):
	"""
	Update RTC date and optionally time.

	Args:
		rtc: RTC instance
		new_year (int, optional): New year
		new_month (int, optional): New month
		new_day (int, optional): New day
		new_hour (int, optional): New hour
		new_minute (int, optional): New minute

	Returns:
		bool: True if successful, False otherwise
	"""
	try:
		current_dt = rtc.datetime

		# Use current time if not specified
		new_year = new_year if new_year is not None else current_dt.tm_year
		new_month = new_month if new_month is not None else current_dt.tm_mon
		new_day = new_day if new_day is not None else current_dt.tm_mday
		new_hour = new_hour if new_hour is not None else current_dt.tm_hour
		new_minute = new_minute if new_minute is not None else current_dt.tm_min

		# Validate inputs
		if not (1 <= new_month <= 12):
			log_error(f"Invalid month: {new_month}. Must be 1-12.")
			return False

		if not (1 <= new_day <= 31):
			log_error(f"Invalid day: {new_day}. Must be 1-31.")
			return False

		# Calculate weekday and yearday
		weekday = calculate_weekday(new_year, new_month, new_day)
		yearday = calculate_yearday(new_year, new_month, new_day)

		# Create new time struct (including seconds from current time)
		import time as time_module
		new_time = time_module.struct_time((
			new_year,
			new_month,
			new_day,
			new_hour,
			new_minute,
			current_dt.tm_sec,  # Keep current seconds
			weekday,
			yearday,
			-1  # DST flag
		))

		rtc.datetime = new_time
		log_info(f"RTC updated: {new_year}-{new_month:02d}-{new_day:02d} {new_hour:02d}:{new_minute:02d}")
		return True

	except Exception as e:
		log_error(f"Failed to update RTC: {e}")
		return False


def interruptible_sleep(duration):
	"""
	Sleep that can be interrupted more easily.

	Args:
		duration (float): Duration to sleep in seconds
	"""
	end_time = time.monotonic() + duration
	while time.monotonic() < end_time:
		time.sleep(Timing.INTERRUPTIBLE_SLEEP_INTERVAL)  # Short sleep allows more interrupt opportunities
