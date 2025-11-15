"""
Events module for Pantallita 2.0
Contains event loading, parsing, and schedule management
"""

import time
from config import Paths, Strings, Timing
from utils import log_info, log_error, log_warning, log_debug, log_verbose


# ===========================
# EVENT LOADING FUNCTIONS
# ===========================

def load_events_from_csv():
	"""
	Load events from local CSV file.
	Supports multiple events per day with optional time windows.

	Returns:
		dict: Events dictionary with date keys (MMDD format)
	"""
	events = {}
	try:
		log_verbose(f"Loading events from {Paths.EVENTS_CSV}...")
		with open(Paths.EVENTS_CSV, "r") as f:
			for line in f:
				line = line.strip()
				if line and not line.startswith("#"):
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 4:
						date = parts[0]
						top_line = parts[1]      # Shows on TOP
						bottom_line = parts[2]   # Shows on BOTTOM
						image = parts[3]
						color = parts[4] if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR

						# Optional time window (24-hour format)
						# Check if fields exist AND are not empty
						start_hour = int(parts[5]) if len(parts) > 5 and parts[5].strip() else Timing.EVENT_ALL_DAY_START
						end_hour = int(parts[6]) if len(parts) > 6 and parts[6].strip() else Timing.EVENT_ALL_DAY_END

						date_key = date.replace("-", "")

						if date_key not in events:
							events[date_key] = []

						# Store as: [top_line, bottom_line, image, color, start_hour, end_hour]
						events[date_key].append([top_line, bottom_line, image, color, start_hour, end_hour])

			return events

	except Exception as e:
		log_warning(f"Failed to load events.csv: {e}")
		log_warning("Using fallback hardcoded events")
		return {}


def fetch_ephemeral_events():
	"""
	Fetch ephemeral events from online source.
	NOTE: Events are fetched during initialization, this is just a wrapper.

	Returns:
		dict: Ephemeral events or empty dict
	"""
	from code import state

	try:
		# Check if events already cached from initialization
		if state.cached_events:
			log_debug("Using cached events from initialization")
			return state.cached_events

		# If not cached (shouldn't happen), fetch now
		log_info("Events not cached, fetching now...")
		events, _, _ = fetch_github_data(state.rtc_instance)

		if events:
			state.cached_events = events
			return events

		return {}

	except Exception as e:
		log_warning(f"Failed to fetch ephemeral events: {e}")
		return {}


def load_all_events():
	"""
	Load and merge all event sources (permanent + ephemeral).

	Returns:
		dict: Merged events dictionary
	"""
	from code import state

	# Load permanent events from local CSV
	permanent_events = {}
	permanent_count = 0

	try:
		with open(Paths.EVENTS_CSV, 'r') as f:
			for line_num, line in enumerate(f, 1):
				line = line.strip()
				if not line or line.startswith("#"):
					continue

				try:
					parts = [part.strip() for part in line.split(",")]

					if len(parts) < 4:
						log_warning(f"Line {line_num}: Not enough fields (need at least 4)")
						continue

					# Format: MM-DD,TopLine,BottomLine,ImageFile,Color[,StartHour,EndHour]
					date_str = str(parts[0])
					top_line = str(parts[1])
					bottom_line = str(parts[2])
					image = str(parts[3])
					color = str(parts[4]) if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR

					# Optional time window - no try/except needed (check before parsing)
					start_hour = Timing.EVENT_ALL_DAY_START
					end_hour = Timing.EVENT_ALL_DAY_END

					if len(parts) > 5 and parts[5].strip():
						hour_str = parts[5].strip().lstrip('-')  # Remove minus for isdigit check
						if hour_str.isdigit():
							start_hour = int(parts[5])

					if len(parts) > 6 and parts[6].strip():
						hour_str = parts[6].strip().lstrip('-')  # Remove minus for isdigit check
						if hour_str.isdigit():
							end_hour = int(parts[6])

					# Parse MM-DD to MMDD (without zfill)
					if '-' in date_str:
						date_parts = date_str.split('-')
						month = date_parts[0]
						day = date_parts[1]

						# Manual padding instead of zfill
						if len(month) == 1:
							month = '0' + month
						if len(day) == 1:
							day = '0' + day

						date_key = month + day
					else:
						# Fallback for MMDD format
						date_key = date_str
						# Manual padding to 4 digits
						while len(date_key) < 4:
							date_key = '0' + date_key

					if date_key not in permanent_events:
						permanent_events[date_key] = []

					permanent_events[date_key].append([top_line, bottom_line, image, color, start_hour, end_hour])
					permanent_count += 1
					log_verbose(f"Loaded: {date_key} - {top_line} {bottom_line}")

				except Exception as e:
					log_warning(f"Line {line_num} parse error: {e} | Line: {line}")
					continue

		state.permanent_event_count = permanent_count
		log_debug(f"Loaded {permanent_count} permanent events")

	except Exception as e:
		log_warning(f"Failed to load permanent events file: {e}")
		state.permanent_event_count = 0
		permanent_events = {}

	# Get ephemeral events - check temp storage first, then try fetching
	ephemeral_events = {}

	if hasattr(state, '_github_events_temp') and state._github_events_temp:
		# Use events fetched during initialization
		ephemeral_events = state._github_events_temp
		log_debug("Using GitHub events from initialization")
	else:
		# Fetch from GitHub (normal case for daily refresh)
		ephemeral_events = fetch_ephemeral_events()

	# Count ephemeral events
	ephemeral_count = sum(len(event_list) for event_list in ephemeral_events.values())
	state.ephemeral_event_count = ephemeral_count
	log_debug(f"Loaded {ephemeral_count} ephemeral events")

	# Merge events
	merged = {}

	# Add permanent events
	for date_key, event_list in permanent_events.items():
		merged[date_key] = list(event_list)

	# Add ephemeral events
	for date_key, event_list in ephemeral_events.items():
		if date_key in merged:
			merged[date_key].extend(event_list)
		else:
			merged[date_key] = list(event_list)

	# Update total count
	total_count = sum(len(event_list) for event_list in merged.values())
	state.total_event_count = total_count

	log_debug(f"Events merged: {permanent_count} permanent + {ephemeral_count} ephemeral = {total_count} total")

	return merged


def is_event_active(event_data, current_hour):
	"""
	Check if event should be displayed at current hour.

	Args:
		event_data (list): [top_line, bottom_line, image, color, start_hour, end_hour]
		current_hour (int): Current hour (0-23)

	Returns:
		bool: True if event is active, False otherwise
	"""
	# Check if event has time data (6 elements)
	if len(event_data) < 6:
		# Old format or missing times - treat as all-day
		return True

	start_hour = event_data[4]
	end_hour = event_data[5]

	# All-day event
	if start_hour == Timing.EVENT_ALL_DAY_START and end_hour == Timing.EVENT_ALL_DAY_END:
		return True

	# Check if current hour is within window
	return start_hour <= current_hour < end_hour


def get_events():
	"""
	Get cached events - loads from both sources only once.

	Returns:
		dict: Cached events dictionary
	"""
	from code import state

	if state.cached_events is None:
		state.cached_events = load_all_events()
		if not state.cached_events:
			log_warning("Warning: No events loaded, using minimal fallback")
			state.cached_events = {}

	return state.cached_events


# ===========================
# CSV PARSING FUNCTIONS
# ===========================

def parse_events_csv_content(csv_content, rtc):
	"""
	Parse events CSV content directly from string.

	Args:
		csv_content (str): CSV content as string
		rtc: RTC instance for date comparison

	Returns:
		dict: Parsed events dictionary
	"""
	events = {}
	skipped_count = 0

	try:
		# Get today's date for comparison
		if rtc:
			today_year = rtc.datetime.tm_year
			today_month = rtc.datetime.tm_mon
			today_day = rtc.datetime.tm_mday
		else:
			# Fallback if RTC not available - import all (year 1900 will be before any event)
			today_year = 1900
			today_month = 1
			today_day = 1

		for line in csv_content.split('\n'):
			line = line.strip()
			if line and not line.startswith("#"):
				parts = [part.strip() for part in line.split(",")]
				if len(parts) >= 4:
					date = parts[0]  # YYYY-MM-DD format
					top_line = parts[1]
					bottom_line = parts[2]
					image = parts[3]
					color = parts[4] if len(parts) > 4 else Strings.DEFAULT_EVENT_COLOR

					# Optional time window
					start_hour = int(parts[5]) if len(parts) > 5 and parts[5].strip() else Timing.EVENT_ALL_DAY_START
					end_hour = int(parts[6]) if len(parts) > 6 and parts[6].strip() else Timing.EVENT_ALL_DAY_END

					# Parse date to check if it's in the past
					try:
						date_parts = date.split("-")
						if len(date_parts) == 3:
							event_year = int(date_parts[0])
							event_month = int(date_parts[1])
							event_day = int(date_parts[2])

							# Skip if event is in the past
							if (event_year < today_year or
								(event_year == today_year and event_month < today_month) or
								(event_year == today_year and event_month == today_month and event_day < today_day)):
								skipped_count += 1
								log_verbose(f"Skipping past event: {date} - {top_line} {bottom_line}")
								continue

							# Convert YYYY-MM-DD to MMDD for lookup
							date_key = date_parts[1] + date_parts[2]  # MMDD only

							if date_key not in events:
								events[date_key] = []

							events[date_key].append([top_line, bottom_line, image, color, start_hour, end_hour])
					except (ValueError, IndexError):
						log_warning(f"Invalid date format in events: {date}")
						continue

		if skipped_count > 0:
			log_debug(f"Parsed {len(events)} event dates ({skipped_count} past events skipped)")
		else:
			log_debug(f"Parsed {len(events)} event dates")

		return events

	except Exception as e:
		log_error(f"Error parsing events CSV: {e}")
		return {}


def parse_schedule_csv_content(csv_content, rtc):
	"""
	Parse schedule CSV content directly from string (no file I/O).

	Args:
		csv_content (str): CSV content as string
		rtc: RTC instance (not currently used, kept for compatibility)

	Returns:
		dict: Parsed schedules dictionary
	"""
	schedules = {}

	try:
		lines = csv_content.strip().split('\n')

		if not lines:
			return schedules

		# Skip header row
		for line in lines[1:]:
			line = line.strip()
			if not line or line.startswith('#'):
				continue

			parts = [p.strip() for p in line.split(',')]

			if len(parts) >= 9:
				name = parts[0]
				enabled = parts[1] == "1"
				days_str = parts[2]
				start_hour = int(parts[3])
				start_min = int(parts[4])
				end_hour = int(parts[5])
				end_min = int(parts[6])
				image = parts[7]
				progressbar = parts[8] == "1"

				# Convert days string to list of day numbers (0=Mon, 6=Sun)
				days = [int(d) for d in days_str if d.isdigit()]

				schedules[name] = {
					"enabled": enabled,
					"days": days,
					"start_hour": start_hour,
					"start_min": start_min,
					"end_hour": end_hour,
					"end_min": end_min,
					"image": image,
					"progressbar": progressbar
				}

				log_verbose(f"Parsed schedule: {name} ({'enabled' if enabled else 'disabled'}, {len(days)} days)")

		return schedules

	except Exception as e:
		log_error(f"Error parsing schedule CSV: {e}")
		return {}


# ===========================
# GITHUB DATA FETCHING
# ===========================

def fetch_github_data(rtc):
	"""
	Fetch both events and schedules from GitHub in one operation.

	Args:
		rtc: RTC instance for date-specific schedule lookup

	Returns:
		tuple: (events_dict, schedules_dict, schedule_source)
			   schedule_source: "date-specific", "default", or None
	"""
	from network import get_requests_session

	session = get_requests_session()
	if not session:
		log_warning("No session available for GitHub fetch")
		return None, None, None

	cache_buster = int(time.monotonic())
	github_base = Strings.GITHUB_REPO_URL.rsplit('/', 1)[0]

	# ===== FETCH EVENTS =====
	events_url = f"{Strings.GITHUB_REPO_URL}?t={cache_buster}"
	events = {}
	response = None

	try:
		log_verbose(f"Fetching: {events_url}")
		response = session.get(events_url, timeout=10)

		try:
			if response.status_code == 200:
				events = parse_events_csv_content(response.text, rtc)
				log_verbose(f"Events fetched: {len(events)} event dates")
			else:
				log_warning(f"Failed to fetch events: HTTP {response.status_code}")
		finally:
			# CRITICAL: Close events response to release socket
			if response:
				try:
					response.close()
				except:
					pass  # Ignore close errors
	except Exception as e:
		log_warning(f"Failed to fetch events: {e}")

	# ===== FETCH SCHEDULE =====
	now = rtc.datetime
	date_str = f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}"

	schedules = {}
	schedule_source = None
	response = None

	try:
		# Try date-specific schedule first
		schedule_url = f"{github_base}/{Paths.GITHUB_SCHEDULE_FOLDER}/{date_str}.csv?t={cache_buster}"
		log_verbose(f"Fetching: {schedule_url}")

		response = session.get(schedule_url, timeout=10)

		try:
			if response.status_code == 200:
				schedules = parse_schedule_csv_content(response.text, rtc)
				schedule_source = "date-specific"
				log_verbose(f"Schedule fetched: {date_str}.csv ({len(schedules)} schedule(s))")

			elif response.status_code == 404:
				# No date-specific file, try default
				log_verbose(f"No schedule for {date_str}, trying default.csv")

				# CRITICAL: Close date-specific response before making second request
				try:
					response.close()
				except:
					pass

				default_url = f"{github_base}/{Paths.GITHUB_SCHEDULE_FOLDER}/default.csv?t={cache_buster}"
				response = session.get(default_url, timeout=10)

				try:
					if response.status_code == 200:
						schedules = parse_schedule_csv_content(response.text, rtc)
						schedule_source = "default"
						log_verbose(f"Schedule fetched: default.csv ({len(schedules)} schedule(s))")
					else:
						log_warning(f"No default schedule found: HTTP {response.status_code}")
				finally:
					# CRITICAL: Close default response
					if response:
						try:
							response.close()
						except:
							pass
			else:
				log_warning(f"Failed to fetch schedule: HTTP {response.status_code}")
		finally:
			# CRITICAL: Ensure date-specific response is closed
			# (May already be closed in 404 case, but safe to call again)
			if response:
				try:
					response.close()
				except:
					pass  # Already closed or error

	except Exception as e:
		log_warning(f"Failed to fetch schedule: {e}")

	return events, schedules, schedule_source


def load_schedules_from_csv():
	"""
	Load schedules from local CSV file.

	Returns:
		dict: Schedules dictionary
	"""
	schedules = {}
	try:
		log_verbose("Loading schedules from schedules.csv...")
		with open("schedules.csv", "r") as f:
			for line in f:
				line = line.strip()
				if line and not line.startswith("#"):
					parts = [part.strip() for part in line.split(",")]
					if len(parts) >= 8:
						name = parts[0]
						enabled = parts[1] == "1"
						days = [int(d) for d in parts[2]]
						schedules[name] = {
							"enabled": enabled,
							"days": days,
							"start_hour": int(parts[3]),
							"start_min": int(parts[4]),
							"end_hour": int(parts[5]),
							"end_min": int(parts[6]),
							"image": parts[7],
							"progressbar": parts[8] == "1" if len(parts) > 8 else True
						}

		# Log successful load
		if schedules:
			log_debug(f"{len(schedules)} schedules loaded")
		else:
			log_warning("No schedules found in schedules.csv")

		return schedules

	except Exception as e:
		log_warning(f"Failed to load schedules.csv: {e}")
		return {}


# ===========================
# SCHEDULED DISPLAY CLASS
# ===========================

class ScheduledDisplay:
	"""Configuration for time-based scheduled displays"""

	def __init__(self):
		self.schedules = {}
		self.schedules_loaded = False
		self.last_fetch_date = None

	def _load_local_schedules(self, current_date):
		"""
		Helper to load schedules from local CSV (DRY fix for duplicate code).

		Args:
			current_date (str): Current date string for tracking
		"""
		log_debug("Schedules not loaded, trying local fallback")
		local_schedules = load_schedules_from_csv()
		if local_schedules:
			self.schedules = local_schedules
			self.schedules_loaded = True
			self.last_fetch_date = current_date
			log_debug(f"Local fallback: {len(local_schedules)} schedules")
		else:
			log_warning("No schedules available")
			self.schedules_loaded = False

	def ensure_loaded(self, rtc):
		"""
		Ensure schedules are loaded, refresh if new day.

		Args:
			rtc: RTC instance
		"""
		from code import state

		current_date = f"{rtc.datetime.tm_year:04d}-{rtc.datetime.tm_mon:02d}-{rtc.datetime.tm_mday:02d}"

		# Check if we need daily refresh
		if self.last_fetch_date and self.last_fetch_date != current_date:
			log_info("New day - refreshing GitHub data")
			events, schedules, schedule_source = fetch_github_data(rtc)

			if schedules:
				self.schedules = schedules
				self.schedules_loaded = True
				self.last_fetch_date = current_date

				# Update cached events too
				if events:
					state.cached_events = events

				# Summary with counts
				event_count = len(events) if events else 0
				source_msg = f" ({schedule_source})" if schedule_source else ""
				log_debug(f"Refreshed: {event_count} event dates, {len(schedules)} schedules{source_msg}")

		# Fallback if still not loaded (safety net)
		if not self.schedules_loaded:
			self._load_local_schedules(current_date)

	def is_active(self, rtc, schedule_name):
		"""
		Check if a schedule is currently active.

		Args:
			rtc: RTC instance
			schedule_name (str): Name of schedule to check

		Returns:
			bool: True if schedule is active, False otherwise
		"""
		# Ensure schedules are loaded
		self.ensure_loaded(rtc)

		if schedule_name not in self.schedules:
			return False

		schedule = self.schedules[schedule_name]

		if not schedule["enabled"]:
			return False

		current = rtc.datetime

		# Check if current day is in schedule
		if current.tm_wday not in schedule["days"]:
			return False

		# Convert times to minutes for easier comparison
		current_mins = current.tm_hour * 60 + current.tm_min
		start_mins = schedule["start_hour"] * 60 + schedule["start_min"]
		end_mins = schedule["end_hour"] * 60 + schedule["end_min"]

		return start_mins <= current_mins < end_mins

	def get_active_schedule(self, rtc):
		"""
		Check if any schedule is currently active.

		Args:
			rtc: RTC instance

		Returns:
			tuple: (schedule_name, schedule_config) or (None, None) if no active schedule
		"""
		# Ensure schedules are loaded
		self.ensure_loaded(rtc)

		for schedule_name, schedule_config in self.schedules.items():
			if self.is_active(rtc, schedule_name):
				return schedule_name, schedule_config

		return None, None


# Create global instance
scheduled_display = ScheduledDisplay()
