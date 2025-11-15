"""
Network module for Pantallita 2.0
Contains WiFi, NTP, API, and session management functions
"""

import board
import os
import time
import gc
import ssl
import supervisor
import wifi
import socketpool
import adafruit_requests as requests
import adafruit_ds3231
import adafruit_ntp

from config import (
	System, Strings, Timing, Recovery, API, Memory,
	TIMEZONE_OFFSETS, CURRENT_DEBUG_LEVEL, DebugLevel, TestData
)
from utils import (
	log_info, log_error, log_warning, log_debug, log_verbose,
	interruptible_sleep
)


# ===========================
# GLOBAL SESSION MANAGEMENT
# ===========================

# Socket pool created ONCE and reused (CRITICAL for v2.0.5 socket pool fix)
_global_socket_pool = None
_global_session = None


def get_requests_session():
	"""
	Get or create the global requests session.

	IMPORTANT: Socket pool is created once globally and reused.
	Creating new pools was causing socket exhaustion (fixed in v2.0.5).

	Returns:
		requests.Session: Global session instance or None if creation fails
	"""
	global _global_session, _global_socket_pool

	if _global_session is None:
		try:
			# Create socket pool ONCE globally, reuse for all sessions
			if _global_socket_pool is None:
				_global_socket_pool = socketpool.SocketPool(wifi.radio)
				log_debug("Created global socket pool")

			_global_session = requests.Session(_global_socket_pool, ssl.create_default_context())
			log_debug("Created new global session (reusing socket pool)")
		except Exception as e:
			log_error(f"Failed to create session: {e}")
			return None

	return _global_session


def cleanup_sockets():
	"""Aggressive socket cleanup to prevent memory issues"""
	for _ in range(Memory.SOCKET_CLEANUP_CYCLES):
		gc.collect()


def cleanup_global_session():
	"""
	Clean up the global requests session and force socket release.

	IMPORTANT: We destroy the session but KEEP the socket pool.
	The socket pool is tied to wifi.radio and should be reused.
	Creating new pools every cleanup was causing socket exhaustion!
	"""
	global _global_session  # NOTE: We do NOT touch _global_socket_pool!

	# Import state here to avoid circular dependency
	from code import state

	if _global_session is not None:
		try:
			log_debug("Destroying global session (keeping socket pool)")
			state.session_cleanup_count += 1  # Track cleanups
			# Try to close gracefully first
			try:
				_global_session.close()
			except:
				pass

			# Set to None (will be recreated with same pool)
			_global_session = None

			# Aggressive garbage collection
			cleanup_sockets()
			gc.collect()

			# Brief pause to let sockets fully close
			time.sleep(0.5)

			log_debug("Global session destroyed (socket pool preserved for reuse)")
		except Exception as e:
			log_debug(f"Session cleanup error (non-critical): {e}")
			_global_session = None


# ===========================
# RTC INITIALIZATION
# ===========================

def setup_rtc():
	"""
	Initialize RTC with retry logic.

	Returns:
		adafruit_ds3231.DS3231: RTC instance or reloads supervisor on failure
	"""
	from code import state

	for attempt in range(System.MAX_RTC_ATTEMPTS):
		try:
			i2c = board.I2C()
			rtc = adafruit_ds3231.DS3231(i2c)
			state.rtc_instance = rtc
			log_debug(f"RTC initialized on attempt {attempt + 1}")
			return rtc
		except Exception as e:
			log_debug(f"RTC attempt {attempt + 1} failed: {e}")
			if attempt < 4:
				interruptible_sleep(Timing.RTC_RETRY_DELAY)

	log_error("RTC initialization failed, restarting...")
	supervisor.reload()


# ===========================
# WIFI FUNCTIONS
# ===========================

def setup_wifi_with_recovery():
	"""
	Enhanced WiFi connection with exponential backoff and reconnection.

	Returns:
		bool: True if connected, False otherwise
	"""
	ssid = os.getenv(Strings.WIFI_SSID_VAR, "").strip()
	password = os.getenv(Strings.WIFI_PASSWORD_VAR, "").strip()

	if not ssid:
		log_error("WiFi SSID missing or empty in settings.toml")
		return False

	if not password:
		log_error("WiFi password missing or empty in settings.toml")
		return False

	try:
		if wifi.radio.connected:
			log_debug("WiFi already connected")
			return True
	except AttributeError as e:
		log_debug(f"WiFi radio not ready: {e}")
	except Exception as e:
		log_error(f"Unexpected WiFi check error: {type(e).__name__}: {e}")

	for attempt in range(Recovery.MAX_WIFI_RETRY_ATTEMPTS):
		try:
			delay = min(
				Recovery.WIFI_RETRY_BASE_DELAY * (2 ** attempt),
				Recovery.WIFI_RETRY_MAX_DELAY
			)

			# Only log first and subsequent attempts differently:
			if attempt == 0:
				log_debug("Connecting to WiFi...")
			else:
				log_debug(f"WiFi retry {attempt}/{Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1} in {delay}s")

			wifi.radio.connect(ssid, password, timeout=System.WIFI_TIMEOUT)

			if wifi.radio.connected:
				# SUCCESS at INFO level:
				log_info(f"WiFi: {ssid[:8]}... ({wifi.radio.ipv4_address})")
				return True

		except ConnectionError as e:
			# Individual failures at DEBUG:
			log_debug(f"WiFi attempt {attempt + 1} failed")
			if attempt < Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1:
				interruptible_sleep(delay)

		except Exception as e:
			log_debug(f"WiFi error: {type(e).__name__}")
			if attempt < Recovery.MAX_WIFI_RETRY_ATTEMPTS - 1:
				interruptible_sleep(delay)

	# Complete failure at ERROR:
	log_error(f"WiFi failed after {Recovery.MAX_WIFI_RETRY_ATTEMPTS} attempts")
	return False


def check_and_recover_wifi():
	"""
	Check WiFi connection with cooldown protection.

	Returns:
		bool: True if connected, False otherwise
	"""
	from code import state

	try:
		if wifi.radio.connected:
			return True

		# Only attempt reconnection if enough time has passed
		current_time = time.monotonic()
		time_since_attempt = current_time - state.last_wifi_attempt

		if time_since_attempt < Recovery.WIFI_RECONNECT_COOLDOWN:
			return False

		log_warning("WiFi DISCONNECTED, attempting recovery...")
		state.last_wifi_attempt = current_time
		return setup_wifi_with_recovery()

	except Exception as e:
		log_error(f"WiFi check failed: {e}")
		return False


def is_wifi_connected():
	"""
	Simple WiFi status check without recovery attempt.

	Returns:
		bool: True if connected, False otherwise
	"""
	try:
		return wifi.radio.connected
	except:
		return False


# ===========================
# TIMEZONE FUNCTIONS
# ===========================

def get_timezone_offset(timezone_name, utc_datetime):
	"""
	Calculate timezone offset including DST for a given timezone.

	Args:
		timezone_name (str): Timezone name (e.g., "America/Chicago")
		utc_datetime: UTC datetime struct

	Returns:
		int: Timezone offset in hours
	"""
	if timezone_name not in TIMEZONE_OFFSETS:
		log_warning(f"Unknown timezone: {timezone_name}, using Chicago")
		timezone_name = Strings.TIMEZONE_DEFAULT

	tz_info = TIMEZONE_OFFSETS[timezone_name]

	# If timezone doesn't observe DST
	if tz_info["dst_start"] is None:
		return tz_info["std"]

	# Check if DST is active
	dst_active = is_dst_active_for_timezone(timezone_name, utc_datetime)
	return tz_info["dst"] if dst_active else tz_info["std"]


def is_dst_active_for_timezone(timezone_name, utc_datetime):
	"""
	Check if DST is active for a specific timezone and date.

	Args:
		timezone_name (str): Timezone name
		utc_datetime: UTC datetime struct

	Returns:
		bool: True if DST is active, False otherwise
	"""
	if timezone_name not in TIMEZONE_OFFSETS:
		return False

	tz_info = TIMEZONE_OFFSETS[timezone_name]

	# No DST for this timezone
	if tz_info["dst_start"] is None:
		return False

	month = utc_datetime.tm_mon
	day = utc_datetime.tm_mday

	dst_start_month, dst_start_day = tz_info["dst_start"]
	dst_end_month, dst_end_day = tz_info["dst_end"]

	# DST logic for Northern Hemisphere (US/Europe)
	if month < dst_start_month or month > dst_end_month:
		return False
	elif month > dst_start_month and month < dst_end_month:
		return True
	elif month == dst_start_month:
		return day >= dst_start_day
	elif month == dst_end_month:
		return day < dst_end_day

	return False


def get_timezone_from_location_api():
	"""
	Get timezone and location info from AccuWeather Location API.

	Returns:
		dict: Timezone info with name, offset, DST status, city, state, location
			  or None if API call fails
	"""
	response = None
	try:
		api_key = get_api_key()
		location_key = os.getenv(Strings.API_LOCATION_KEY)
		url = f"https://dataservice.accuweather.com/locations/v1/{location_key}?apikey={api_key}"

		session = get_requests_session()
		response = session.get(url)

		try:
			if response.status_code == 200:
				data = response.json()
				timezone_info = data.get("TimeZone", {})

				# Extract location details
				city = data.get("LocalizedName", "Unknown")
				state = data.get("AdministrativeArea", {}).get("ID", "")

				return {
					"name": timezone_info.get("Name", Strings.TIMEZONE_DEFAULT),
					"offset": int(timezone_info.get("GmtOffset", -6)),
					"is_dst": timezone_info.get("IsDaylightSaving", False),
					"city": city,
					"state": state,
					"location": f"{city}, {state}" if state else city
				}
			else:
				log_warning(f"Location API failed: {response.status_code}")
				return None
		finally:
			# CRITICAL: Always close response to release socket
			if response:
				try:
					response.close()
				except:
					pass  # Ignore errors during cleanup

	except Exception as e:
		log_warning(f"Location API error: {e}")
		return None


def sync_time_with_timezone(rtc):
	"""
	Enhanced NTP sync with Location API timezone detection.

	Args:
		rtc: RTC instance

	Returns:
		dict: Timezone info from API or None if sync fails
	"""
	# Try to get timezone from Location API
	tz_info = get_timezone_from_location_api()

	if tz_info:
		timezone_name = tz_info["name"]
		offset = tz_info["offset"]
		log_debug(f"Timezone from API: {timezone_name} (UTC{offset:+d})")
	else:
		# Fallback to hardcoded timezone
		timezone_name = Strings.TIMEZONE_DEFAULT
		log_warning(f"Using fallback timezone: {timezone_name}")

		# Use existing hardcoded logic
		try:
			cleanup_sockets()
			pool = socketpool.SocketPool(wifi.radio)
			ntp_utc = adafruit_ntp.NTP(pool, tz_offset=0)
			utc_time = ntp_utc.datetime
			offset = get_timezone_offset(timezone_name, utc_time)
		except Exception as e:
			log_error(f"NTP sync failed: {e}")
			return None  # IMPORTANT: Return None on failure

	try:
		cleanup_sockets()
		pool = socketpool.SocketPool(wifi.radio)
		ntp = adafruit_ntp.NTP(pool, tz_offset=offset)
		rtc.datetime = ntp.datetime

		log_info(f"Time synced to {timezone_name} (UTC{offset:+d})")

		return tz_info  # Return location info (or None if using fallback)

	except Exception as e:
		log_error(f"NTP sync failed: {e}")
		return None  # IMPORTANT: Return None on failure


# ===========================
# API KEY MANAGEMENT
# ===========================

def get_api_key():
	"""
	Get API key based on detected matrix type.

	Security note: Does not log any part of API key to prevent exposure.

	Returns:
		str: API key or None if not found
	"""
	from display import detect_matrix_type

	matrix_type = detect_matrix_type()

	# Select appropriate API key name based on matrix type
	if matrix_type == "type1":
		api_key_name = Strings.API_KEY_TYPE1
	elif matrix_type == "type2":
		api_key_name = Strings.API_KEY_TYPE2
	else:
		api_key_name = Strings.API_KEY_FALLBACK

	# Try primary key
	api_key = os.getenv(api_key_name)
	if api_key and api_key.strip():
		log_debug(f"API key loaded for {matrix_type}")
		return api_key.strip()

	# Fallback to default key
	api_key = os.getenv(Strings.API_KEY_FALLBACK)
	if api_key and api_key.strip():
		log_warning(f"Using fallback API key")
		return api_key.strip()

	log_error("No API key found in settings.toml")
	return None


# ===========================
# API REQUEST HANDLERS
# ===========================

def _handle_network_error(error, context, attempt, max_retries):
	"""
	Helper: Handle network errors - reduces nesting in fetch functions.

	Args:
		error: Exception that occurred
		context (str): Context string for logging
		attempt (int): Current attempt number
		max_retries (int): Maximum retry attempts

	Returns:
		str: Error message
	"""
	error_msg = str(error)

	if "pystack exhausted" in error_msg.lower():
		log_error(f"{context}: Stack exhausted - forcing cleanup")
	elif "already connected" in error_msg.lower():
		log_error(f"{context}: Socket stuck - forcing cleanup")
	elif "ETIMEDOUT" in error_msg or "104" in error_msg or "32" in error_msg:
		log_warning(f"{context}: Network timeout on attempt {attempt + 1}")
	else:
		log_warning(f"{context}: Network error on attempt {attempt + 1}: {error_msg}")

	# Nuclear cleanup for socket/stack issues
	if "pystack exhausted" in error_msg.lower() or "already connected" in error_msg.lower():
		cleanup_global_session()
		cleanup_sockets()
		gc.collect()
		time.sleep(Timing.SOCKET_ERROR_RECOVERY_DELAY)

	# Retry delay
	if attempt < max_retries:
		delay = API.RETRY_BASE_DELAY * (2 ** attempt)
		log_verbose(f"Retrying in {delay}s...")
		time.sleep(delay)

	return f"Network error: {error_msg}"


def _process_response_status(response, context):
	"""
	Helper: Process HTTP response status - returns data or None.

	Args:
		response: HTTP response object
		context (str): Context string for logging

	Returns:
		dict: JSON data if successful
		None: On permanent errors
		False: On retryable errors
	"""
	from code import state

	status = response.status_code

	# Success
	if status == API.HTTP_OK:
		log_verbose(f"{context}: Success")
		return response.json()

	# Permanent errors (return None to signal exit)
	permanent_errors = {
		API.HTTP_UNAUTHORIZED: "Unauthorized (401) - check API key",
		API.HTTP_NOT_FOUND: "Not found (404) - check location key",
		API.HTTP_BAD_REQUEST: "Bad request (400) - check URL/parameters",
		API.HTTP_FORBIDDEN: "Forbidden (403) - API key lacks permissions"
	}

	if status in permanent_errors:
		log_error(f"{context}: {permanent_errors[status]}")
		state.has_permanent_error = True
		return None

	# Retryable errors (return False to signal retry)
	if status == API.HTTP_SERVICE_UNAVAILABLE:
		log_warning(f"{context}: Service unavailable (503)")
		return False
	elif status == API.HTTP_INTERNAL_SERVER_ERROR:
		log_warning(f"{context}: Server error (500)")
		return False
	elif status == API.HTTP_TOO_MANY_REQUESTS:
		log_warning(f"{context}: Rate limited (429)")
		return False  # Caller will handle rate limit delay
	else:
		log_error(f"{context}: HTTP {status}")
		return False


def fetch_weather_with_retries(url, max_retries=None, context="API"):
	"""
	Fetch weather with retries - defensive error handling.

	Args:
		url (str): API URL to fetch
		max_retries (int, optional): Max retry attempts (default: API.MAX_RETRIES)
		context (str): Context string for logging

	Returns:
		dict: JSON response data or None on failure
	"""
	from code import state

	if max_retries is None:
		max_retries = API.MAX_RETRIES

	last_error = None

	for attempt in range(max_retries + 1):
		# Early exits - no nesting
		if not check_and_recover_wifi():
			log_error(f"{context}: WiFi unavailable")
			return None

		session = get_requests_session()
		if not session:
			log_error(f"{context}: No requests session available")
			return None

		log_verbose(f"{context} attempt {attempt + 1}/{max_retries + 1}")

		# Try to fetch - exception handling delegated to helper
		response = None
		try:
			state.http_requests_total += 1  # Track all attempts
			response = session.get(url)
		except (RuntimeError, OSError) as e:
			last_error = _handle_network_error(e, context, attempt, max_retries)
			state.http_requests_failed += 1  # Track failure
			continue  # Retry
		except Exception as e:
			log_error(f"{context} unexpected error: {type(e).__name__}: {e}")
			last_error = str(e)
			if attempt < max_retries:
				interruptible_sleep(API.RETRY_DELAY)
			continue  # Retry

		# Process and cleanup response
		try:
			# Process response - status handling delegated to helper
			result = _process_response_status(response, context)

			# Success or permanent error
			if result is not None and result is not False:
				state.http_requests_success += 1  # Track success
				return result

			# Permanent error (None from helper)
			if result is None:
				return None

			# Retryable error (False from helper)
			# Special case: rate limiting needs longer delay
			if response.status_code == API.HTTP_TOO_MANY_REQUESTS:
				if attempt < max_retries:
					delay = API.RETRY_DELAY * 3
					log_debug(f"Rate limit cooldown: {delay}s")
					interruptible_sleep(delay)
			else:
				# Standard exponential backoff
				if attempt < max_retries:
					delay = min(
						API.RETRY_DELAY * (2 ** attempt),
						Recovery.API_RETRY_MAX_DELAY
					)
					log_debug(f"Retrying in {delay}s...")
					interruptible_sleep(delay)

			last_error = f"HTTP {response.status_code}"
		finally:
			# Always close response to free socket
			if response:
				try:
					response.close()
				except:
					pass  # Ignore errors during cleanup

	log_error(f"{context}: All {max_retries + 1} attempts failed. Last error: {last_error}")
	return None


# ===========================
# WEATHER API FUNCTIONS
# ===========================

def fetch_current_and_forecast_weather():
	"""
	Fetch current and/or forecast weather with individual controls,
	detailed tracking, and improved error handling.

	Returns:
		tuple: (current_data dict, forecast_data list) or (None, None) on failure
	"""
	from code import state, display_config
	from display import show_clock_display

	state.memory_monitor.check_memory("weather_fetch_start")

	# Check what to fetch based on config
	if not display_config.should_fetch_weather() and not display_config.should_fetch_forecast():
		log_debug("All API fetching disabled")
		return None, None

	# Count expected API calls
	expected_calls = (1 if display_config.should_fetch_weather() else 0) + (1 if display_config.should_fetch_forecast() else 0)

	# Monitor memory just before planned restart
	if state.api_call_count + expected_calls >= API.MAX_CALLS_BEFORE_RESTART:
		log_warning(f"API call #{state.api_call_count + expected_calls} - restart imminent")

	try:
		# Get matrix-specific API key
		api_key = get_api_key()
		if not api_key:
			state.consecutive_failures += 1
			return None, None

		current_data = None
		forecast_data = None
		current_success = False
		forecast_success = False

		# Fetch current weather if enabled
		if display_config.should_fetch_weather():
			current_url = f"{API.BASE_URL}/{API.CURRENT_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&details=true"

			current_json = fetch_weather_with_retries(current_url, context="Current Weather")

			if current_json:
				state.current_api_calls += 1
				state.api_call_count += 1
				current_success = True

				# Process current weather
				current = current_json[0]
				temp_data = current.get("Temperature", {}).get("Metric", {})
				realfeel_data = current.get("RealFeelTemperature", {}).get("Metric", {})
				realfeel_shade_data = current.get("RealFeelTemperatureShade", {}).get("Metric", {})

				current_data = {
					"weather_icon": current.get("WeatherIcon", 0),
					"temperature": temp_data.get("Value", 0),
					"feels_like": realfeel_data.get("Value", 0),
					"feels_shade": realfeel_shade_data.get("Value", 0),
					"humidity": current.get("RelativeHumidity", 0),
					"uv_index": current.get("UVIndex", 0),
					"weather_text": current.get("WeatherText", "Unknown"),
					"is_day_time": current.get("IsDayTime", True),
					"has_precipitation": current.get("HasPrecipitation", False),
				}

				state.cached_current_weather = current_data  # Cache for fallback
				state.cached_current_weather_time = time.monotonic()

				log_verbose(f"CURRENT DATA: {current_data}")
				log_info(f"Weather: {current_data['weather_text']}, {current_data['feels_like']}°C")

			else:
				log_warning("Current weather fetch failed")

		# Fetch forecast weather if enabled and (current succeeded OR current disabled)
		if display_config.should_fetch_forecast():
			forecast_url = f"{API.BASE_URL}/{API.FORECAST_ENDPOINT}/{os.getenv(Strings.API_LOCATION_KEY)}?apikey={api_key}&metric=true&details=true"

			forecast_json = fetch_weather_with_retries(forecast_url, max_retries=1, context="Forecast")

			if forecast_json:  # Count the API call even if processing fails later
				state.forecast_api_calls += 1
				state.api_call_count += 1

			forecast_fetch_length = min(API.DEFAULT_FORECAST_HOURS, API.MAX_FORECAST_HOURS)

			if forecast_json and len(forecast_json) >= forecast_fetch_length:
				# Extract forecast data
				forecast_data = []
				for i in range(forecast_fetch_length):
					hour_data = forecast_json[i]
					forecast_data.append({
						"temperature": hour_data.get("Temperature", {}).get("Value", 0),
						"feels_like": hour_data.get("RealFeelTemperature", {}).get("Value", 0),
						"feels_shade": hour_data.get("RealFeelTemperatureShade", {}).get("Value", 0),
						"weather_icon": hour_data.get("WeatherIcon", 1),
						"weather_text": hour_data.get("IconPhrase", "Unknown"),
						"datetime": hour_data.get("DateTime", ""),
						"has_precipitation": hour_data.get("HasPrecipitation", False)
					})

				log_info(f"Forecast: {len(forecast_data)} hours (fresh) | Next: {forecast_data[0]['feels_like']}°C")
				if len(forecast_data) >= forecast_fetch_length and CURRENT_DEBUG_LEVEL >= DebugLevel.VERBOSE:
					for h, item in enumerate(forecast_data):
						log_verbose(f"  Hour {h+1}: {item['temperature']}°C, {item['weather_text']}")

				state.memory_monitor.check_memory("forecast_data_complete")
				forecast_success = True
			else:
				log_warning("12-hour forecast fetch failed or insufficient data")
				forecast_data = None

		# Log API call statistics
		log_debug(f"API Stats: Total={state.api_call_count}/{API.MAX_CALLS_BEFORE_RESTART}, Current={state.current_api_calls}, Forecast={state.forecast_api_calls}")

		# Determine overall success
		any_success = current_success or forecast_success

		if any_success:
			# Log recovery if coming out of extended failure mode
			if state.in_extended_failure_mode:
				recovery_time = int((time.monotonic() - state.last_successful_weather) / System.SECONDS_PER_MINUTE)
				log_info(f"Weather API recovered after {recovery_time} minutes of failures")

			state.consecutive_failures = 0
			state.last_successful_weather = time.monotonic()
			state.wifi_reconnect_attempts = 0  # Reset WiFi counter on success
			state.system_error_count = 0  # Reset system errors on success
		else:
			state.consecutive_failures += 1
			state.system_error_count += 1  # Increment across soft resets
			log_warning(f"Consecutive failures: {state.consecutive_failures}, System errors: {state.system_error_count}")

			# Soft reset on repeated failures
			if state.consecutive_failures >= Recovery.SOFT_RESET_THRESHOLD:
				log_warning("Soft reset: clearing network session")
				cleanup_global_session()
				state.consecutive_failures = 0

				# Enter temporary extended failure mode for cooldown
				was_in_extended_mode = state.in_extended_failure_mode
				state.in_extended_failure_mode = True

				# Show purple clock during cooldown
				log_info(f"Cooling down for {Timing.CRITICAL_FAILURE_DELAY} seconds before retry...")
				show_clock_display(state.rtc_instance, Timing.CRITICAL_FAILURE_DELAY)

				# Restore previous extended mode state
				state.in_extended_failure_mode = was_in_extended_mode

			# Hard reset if soft resets aren't helping
			if state.system_error_count >= Recovery.HARD_RESET_THRESHOLD:
				log_error(f"Hard reset after {state.system_error_count} system errors")
				interruptible_sleep(Timing.RESTART_DELAY)
				supervisor.reload()

		# Check for preventive restart
		if state.api_call_count >= API.MAX_CALLS_BEFORE_RESTART:
			log_warning(f"Preventive restart after {state.api_call_count} API calls")
			cleanup_global_session()
			interruptible_sleep(API.RETRY_DELAY)
			supervisor.reload()

		state.memory_monitor.check_memory("weather_fetch_complete")
		return current_data, forecast_data

	except Exception as e:
		log_error(f"Weather fetch critical error: {type(e).__name__}: {e}")
		state.memory_monitor.check_memory("weather_fetch_error")
		state.consecutive_failures += 1
		return None, None


def get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE):
	"""
	Get cached current weather if it's not too old.

	Args:
		max_age_seconds (int): Maximum age in seconds (default 15 minutes)

	Returns:
		dict: Cached weather data if fresh enough, None otherwise
	"""
	from code import state

	if not state.cached_current_weather:
		return None

	age = time.monotonic() - state.cached_current_weather_time

	if age <= max_age_seconds:
		log_debug(f"Cache is {int(age/60)} minutes old (acceptable)")
		return state.cached_current_weather
	else:
		log_debug(f"Cache is {int(age/60)} minutes old (too stale, discarding)")
		return None


def fetch_current_weather_only():
	"""
	Fetch only current weather (not forecast).

	Returns:
		dict: Current weather data or dummy data
	"""
	from code import state, display_config

	if display_config.use_live_weather:
		display_config.use_live_forecast = False
		current_data, _ = fetch_current_and_forecast_weather()
		display_config.use_live_forecast = True

		if current_data:
			state.last_successful_weather = time.monotonic()
		return current_data
	else:
		return TestData.DUMMY_WEATHER_DATA
