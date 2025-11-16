"""
Display module for Pantallita 2.0
Contains all display rendering and hardware interface functions

NOTE: This is a stub module created during refactoring.
The full implementation should be extracted from code.py lines 980-3760.
Due to the large size (~1,500 lines), this requires careful extraction of:
- Hardware initialization (initialize_display)
- Matrix detection and color management
- BMP image loading and palette conversion
- Text rendering utilities
- All show_*_display() functions
- Progress bar utilities
- Weather, clock, event, forecast, and scheduled displays

TODO: Complete extraction of all display functions from original code.py
"""

import board
import displayio
import framebufferio
import rgbmatrix
import microcontroller
import time
import supervisor
import gc
import adafruit_imageload
from adafruit_display_text import bitmap_label
from adafruit_display_shapes.line import Line

from config import (
    Display, Layout, DayIndicator, Visual, System, Timing, Paths,
    Strings, ColorManager, MONTHS
)
from utils import (
    log_info, log_error, log_warning, log_debug, log_verbose,
    duration_message, interruptible_sleep
)
from network import is_wifi_connected, get_cached_weather_if_fresh, fetch_current_weather_only


# ===========================
# HARDWARE INITIALIZATION
# ===========================

def initialize_display(state=None):
	"""Initialize RGB matrix display"""
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
	
	log_info(f"Display initialized: {Display.WIDTH}x{Display.HEIGHT} @ {Display.BIT_DEPTH}-bit")
	return state.display


# ===========================
# MATRIX DETECTION & COLORS
# ===========================

def detect_matrix_type(state=None):
	"""Auto-detect matrix wiring type (cached for performance)"""
	# Check cache if state is provided
	if state is not None and state.matrix_type_cache is not None:
		return state.matrix_type_cache

	uid = microcontroller.cpu.uid
	device_id = "".join([f"{b:02x}" for b in uid[-3:]])

	device_mappings = {
		System.DEVICE_TYPE1_ID: "type1",
		System.DEVICE_TYPE2_ID: "type2",
	}

	matrix_type = device_mappings.get(device_id, "type1")

	# Cache if state is provided
	if state is not None:
		state.matrix_type_cache = matrix_type

	log_debug(f"Device ID: {device_id}, Matrix type: {matrix_type}")
	return matrix_type


def get_matrix_colors(state=None):
	"""Get color constants with corrections applied"""
	matrix_type = detect_matrix_type(state)
	bit_depth = Display.BIT_DEPTH

	return ColorManager.generate_colors(matrix_type, bit_depth)


# ===========================
# IMAGE UTILITIES
# ===========================

def convert_bmp_palette(palette):
	"""Convert BMP palette for RGB matrix display"""
	if not palette or 'ColorConverter' in str(type(palette)):
		return palette
	
	try:
		palette_len = len(palette)
	except TypeError:
		return palette
	
	converted_palette = displayio.Palette(palette_len)
	matrix_type = detect_matrix_type()
	bit_depth = Display.BIT_DEPTH
	
	for i in range(palette_len):
		original_color = palette[i]
		
		# Extract 8-bit RGB
		r = (original_color >> 16) & 0xFF
		g = (original_color >> 8) & 0xFF
		b = original_color & 0xFF
		
		# Swap for type1
		if matrix_type == "type1":
			r, g, b = ColorManager.swap_green_blue(r, g, b)
		
		# Quantize to bit depth
		r_quantized = ColorManager.quantize_channel(r, bit_depth)
		g_quantized = ColorManager.quantize_channel(g, bit_depth)
		b_quantized = ColorManager.quantize_channel(b, bit_depth)
		
		# Pack as RGB888
		converted_palette[i] = (r_quantized << 16) | (g_quantized << 8) | b_quantized
	
	return converted_palette


def load_bmp_image(filepath):
	"""Load and convert BMP image for display"""
	bitmap, palette = adafruit_imageload.load(filepath)
	if palette and 'Palette' in str(type(palette)):
		palette = convert_bmp_palette(palette)
	return bitmap, palette


# ===========================
# TEXT UTILITIES
# ===========================

def get_text_width(text, font, state=None):
	"""Get text width using cache if available, otherwise calculate directly"""
	if not text:
		return 0

	# Use cache if state is provided
	if state is not None and hasattr(state, 'text_cache'):
		return state.text_cache.get_text_width(text, font)

	# Calculate width directly without cache
	temp_label = bitmap_label.Label(font, text=text)
	bbox = temp_label.bounding_box
	return bbox[2] if bbox else 0


def get_font_metrics(font, text="Aygjpq"):
	"""
	Calculate font metrics including ascenders and descenders.
	Uses test text with both tall and descending characters.
	"""
	try:
		temp_label = bitmap_label.Label(font, text=text)
		bbox = temp_label.bounding_box
		
		if bbox and len(bbox) >= 4:
			# bbox format: (x, y, width, height)
			font_height = bbox[3]  # Total height including ascenders/descenders
			baseline_offset = abs(bbox[1]) if bbox[1] < 0 else 0  # How much above baseline
			return font_height, baseline_offset
		else:
			# Fallback if bbox is invalid
			return 8, 2
	except Exception as e:
		log_error(f"Font metrics error: {e}")
		# Safe fallback values for small font
		return 8, 2


def calculate_bottom_aligned_positions(font, line1_text, line2_text, display_height=32, bottom_margin=2, line_spacing=1):
	"""
	Calculate optimal y positions for two lines of text aligned to bottom.
	Enhanced to account for descender characters (g, j, p, q, y).
	
	Returns:
		tuple: (line1_y, line2_y) positions
	"""
	# Get font metrics
	font_height, baseline_offset = get_font_metrics(font, line1_text + line2_text)
	
	# Check if ONLY the second line (bottom line) has lowercase descender characters
	has_descenders = any(char in Strings.DESCENDER_CHARS for char in line2_text)
	
	# Add extra bottom margin if descenders are present
	adjusted_bottom_margin = bottom_margin + (Layout.DESCENDER_EXTRA_MARGIN if has_descenders else 0)
	
	# Calculate positions working backwards from bottom
	bottom_edge = display_height - adjusted_bottom_margin
	line2_y = bottom_edge - font_height
	line1_y = line2_y - font_height - line_spacing
	
	return line1_y, line2_y


# ===========================
# DISPLAY UTILITIES
# ===========================

def clear_display(state=None):
	"""Clear the display"""
	while len(state.main_group) > 0:
		state.main_group.pop()


def right_align_text(text, font, right_edge, state=None):
	"""Calculate x position for right-aligned text"""
	return right_edge - get_text_width(text, font, state)


def center_text(text, font, area_x, area_width, state=None):
	"""Calculate x position for centered text"""
	text_width = get_text_width(text, font, state)
	return area_x + (area_width - text_width) // 2


def get_day_color(rtc, state=None):
	"""Get color for current day of week"""
	day_colors = [
		state.colors["LIME"],      # Monday
		state.colors["BUGAMBILIA"],  # Tuesday
		state.colors["ORANGE"],    # Wednesday
		state.colors["MINT"],      # Thursday
		state.colors["PURPLE"],    # Friday
		state.colors["PINK"],      # Saturday
		state.colors["CYAN"]       # Sunday
	]
	
	return day_colors[rtc.datetime.tm_wday]


def add_day_indicator(main_group, rtc, state=None):
	"""Add colored day-of-week indicator to display"""
	import displayio

	# Day indicator square (top right)
	day_palette = displayio.Palette(2)
	day_palette[0] = state.colors["BLACK"]
	day_palette[1] = get_day_color(rtc, state)
	
	day_bitmap = displayio.Bitmap(DayIndicator.SIZE, DayIndicator.SIZE, 2)
	for y in range(DayIndicator.SIZE):
		for x in range(DayIndicator.SIZE):
			day_bitmap[x, y] = 1
	
	day_tilegrid = displayio.TileGrid(day_bitmap, pixel_shader=day_palette, x=DayIndicator.X, y=DayIndicator.Y)
	main_group.append(day_tilegrid)
	
	# Add vertical margin line
	margin_line = Line(DayIndicator.MARGIN_LEFT_X, DayIndicator.Y, DayIndicator.MARGIN_LEFT_X, DayIndicator.MARGIN_BOTTOM_Y, state.colors["BLACK"])
	main_group.append(margin_line)


# ===========================
# WEATHER INDICATORS
# ===========================

def calculate_uv_bar_length(uv_index):
	"""Calculate UV bar length based on UV index"""
	if uv_index < Visual.UV_BREAKPOINT_1:
		return 0
	elif uv_index < Visual.UV_BREAKPOINT_2:
		return 5
	elif uv_index < Visual.UV_BREAKPOINT_3:
		return 10
	else:
		return min(15, uv_index)


def calculate_humidity_bar_length(humidity):
	"""Calculate humidity bar length based on percentage"""
	return min(humidity // Visual.HUMIDITY_PERCENT_PER_PIXEL, 14)


def add_indicator_bars(main_group, x_start, uv_index, humidity, state=None):
	"""Add UV and humidity indicator bars to display"""
	# UV bar
	uv_length = calculate_uv_bar_length(uv_index)
	for i in range(uv_length):
		if i in Visual.UV_SPACING_POSITIONS:
			continue
		uv_line = Line(x_start + i, Layout.UV_BAR_Y, x_start + i, Layout.UV_BAR_Y, state.colors["ORANGE"])
		main_group.append(uv_line)
	
	# Humidity bar
	humidity_length = calculate_humidity_bar_length(humidity)
	for i in range(humidity_length):
		if i in Visual.HUMIDITY_SPACING_POSITIONS:
			continue
		humidity_line = Line(x_start + i, Layout.HUMIDITY_BAR_Y, x_start + i, Layout.HUMIDITY_BAR_Y, state.colors["CYAN"])
		main_group.append(humidity_line)


# ===========================
# ERROR STATE HELPERS
# ===========================

def get_current_error_state(state=None):
	"""Determine current error state based on system status"""
	# During startup (before first weather attempt), show OK
	if state.startup_time == 0:
		return None

	# Extended failure mode takes priority over permanent errors
	# (shows system is degraded, even if error is permanent)
	if state.in_extended_failure_mode:
		return "extended"  # PURPLE

	# Check for permanent configuration errors
	if hasattr(state, 'has_permanent_error') and state.has_permanent_error:
		return "general"  # WHITE

	# Check for WiFi issues
	if not is_wifi_connected():
		return "wifi"  # RED

	# Check for schedule display errors (file system issues)
	if state.scheduled_display_error_count >= 3:
		return "general"  # WHITE

	# Check for weather API failures (only after startup)
	time_since_success = time.monotonic() - state.last_successful_weather
	if state.last_successful_weather > 0 and time_since_success > 600:
		return "weather"  # YELLOW

	# Check for consecutive failures
	if state.consecutive_failures >= 3:
		return "weather"  # YELLOW

	# All OK
	return None  # MINT


# ===========================
# DISPLAY FUNCTIONS
# ===========================

def show_clock_display(rtc, duration=Timing.CLOCK_DISPLAY_DURATION, state=None, font=None, bg_font=None, display_config=None):
	"""Display clock as fallback when weather unavailable"""
	log_warning(f"Displaying clock for {duration_message(duration)}...")
	clear_display(state)

	# Determine clock color based on error state
	error_state = get_current_error_state(state)

	clock_colors = {
		None: state.colors[Strings.DEFAULT_EVENT_COLOR],  # MINT = All OK
		"wifi": state.colors["RED"],                      # WiFi failure
		"weather": state.colors["YELLOW"],                # Weather API failure
		"extended": state.colors["PURPLE"],               # Extended failure
		"general": state.colors["WHITE"]                  # Unknown error
	}

	clock_color = clock_colors.get(error_state, state.colors["MINT"])

	date_text = bitmap_label.Label(
		font,
		color=state.colors["DIMMEST_WHITE"],
		x=Layout.CLOCK_DATE_X,
		y=Layout.CLOCK_DATE_Y
	)
	time_text = bitmap_label.Label(
		bg_font,
		color=clock_color,  # Use error-based color
		x=Layout.CLOCK_TIME_X,
		y=Layout.CLOCK_TIME_Y
	)

	state.main_group.append(date_text)
	state.main_group.append(time_text)

	# Add day indicator after other elements
	if display_config.show_weekday_indicator:
		add_day_indicator(state.main_group, rtc, state)
		log_verbose(f"Showing Weekday Color Indicator on Clock Display")
	else:
		log_verbose("Weekday Color Indicator Disabled")

	start_time = time.monotonic()
	while time.monotonic() - start_time < duration:
		dt = rtc.datetime
		date_str = f"{MONTHS[dt.tm_mon].upper()} {dt.tm_mday:02d}"

		hour = dt.tm_hour
		display_hour = hour % System.HOURS_IN_HALF_DAY if hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
		time_str = f"{display_hour}:{dt.tm_min:02d}:{dt.tm_sec:02d}"

		date_text.text = date_str
		time_text.text = time_str
		interruptible_sleep(1)

	# Check for restart conditions ONLY if not in startup phase
	if state.startup_time > 0:  # Only check if we've completed initialization
		time_since_success = time.monotonic() - state.last_successful_weather

		# Hard reset after 1 hour of failures
		if time_since_success > System.SECONDS_PER_HOUR:
			log_error(f"Hard reset after {int(time_since_success/System.SECONDS_PER_MINUTE)} minutes without successful weather fetch")
			interruptible_sleep(Timing.RESTART_DELAY)
			supervisor.reload()

		# Warn after 30 minutes
		elif time_since_success > System.SECONDS_HALF_HOUR and state.consecutive_failures >= System.MAX_LOG_FAILURES_BEFORE_RESTART:
			log_warning(f"Extended failure: {int(time_since_success/System.SECONDS_PER_MINUTE)}min without success, {state.consecutive_failures} consecutive failures")


# ===========================
# STUB: REMAINING DISPLAY FUNCTIONS
# ===========================
# The following functions need to be extracted from code.py:
# - show_weather_display() (lines ~2551-2708)
# - show_event_display() (lines ~2777-2956)
# - _display_single_event_optimized() (lines ~2836-2956)
# - show_color_test_display() (lines ~2957-2989)
# - show_icon_test_display() (lines ~2990-3109)
# - _display_icon_batch() (lines ~3055-3109)
# - show_forecast_display() (lines ~3110-3400)
# - create_progress_bar_tilegrid() (lines ~3418-3474)
# - update_progress_bar_bitmap() (lines ~3475-3495)
# - get_schedule_progress() (lines ~3496-3521)
# - show_scheduled_display() (lines ~3522-3759)

# TODO: Extract these functions from original code.py
# Each function is 50-200+ lines and requires careful extraction
# to maintain all functionality, error handling, and logging.

def show_weather_display(rtc, duration, weather_data=None, state=None, font=None, bg_font=None, display_config=None):
	"""Optimized weather display - only update time text in loop"""
	state.memory_monitor.check_memory("weather_display_start")

	# Require weather_data to be provided
	if not weather_data:
		# Try cached weather as fallback (max 30 min old)
		weather_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)

		if weather_data:
			log_debug("Using cached current weather for weather display")
			is_cached = True
		else:
			log_warning("Weather unavailable, showing clock")
			show_clock_display(rtc, duration)
			return
	else:
		is_cached = False

	log_debug(f"Displaying weather for {duration_message(duration)}")

	# Clear display and setup static elements ONCE
	clear_display(state)

	# LOG what we're displaying
	temp = round(weather_data["feels_like"])
	condition = weather_data.get("weather_text", "Unknown")
	cache_indicator = " [CACHED]" if is_cached else ""
	log_info(f"Displaying Weather: {condition}, {temp}°C ({duration/60:.0f} min){cache_indicator}")

	# Set temperature color based on cache status
	temp_color = state.colors["LILAC"] if is_cached else state.colors["DIMMEST_WHITE"]

	# Create all static display elements ONCE
	temp_text = bitmap_label.Label(
		bg_font,
		color=temp_color,  # ← FIXED: Use dynamic color
		text=f"{round(weather_data['temperature'])}°",
		x=Layout.WEATHER_TEMP_X,
		y=Layout.WEATHER_TEMP_Y,
		background_color=state.colors["BLACK"],
		padding_top=Layout.BG_PADDING_TOP,
		padding_bottom=1,
		padding_left=1
	)

	# Create time text - this is the ONLY element we'll update
	time_text = bitmap_label.Label(
		font,
		color=state.colors["DIMMEST_WHITE"],
		x=Layout.WEATHER_TIME_X,
		y=Layout.WEATHER_TIME_Y,
		background_color=state.colors["BLACK"],
		padding_top=Layout.BG_PADDING_TOP,
		padding_bottom=-2,
		padding_left=1
	)

	# Create feels-like temperatures if different (static)
	temp_rounded = round(weather_data['temperature'])
	feels_like_rounded = round(weather_data['feels_like'])
	feels_shade_rounded = round(weather_data['feels_shade'])

	feels_like_text = None
	feels_shade_text = None

	if feels_like_rounded != temp_rounded:
		feels_like_text = bitmap_label.Label(
			font,
			color=temp_color,  # ← Already correct
			text=f"{feels_like_rounded}°",
			y=Layout.FEELSLIKE_Y,
			background_color=state.colors["BLACK"],
			padding_top=Layout.BG_PADDING_TOP,
			padding_bottom=-2,
			padding_left=1
		)
		feels_like_text.x = right_align_text(feels_like_text.text, font, Layout.RIGHT_EDGE, state)

	if feels_shade_rounded != feels_like_rounded:
		feels_shade_text = bitmap_label.Label(
			font,
			color=temp_color,  # ← Already correct
			text=f"{feels_shade_rounded}°",
			y=Layout.FEELSLIKE_SHADE_Y,
			background_color=state.colors["BLACK"],
			padding_top=Layout.BG_PADDING_TOP,
			padding_bottom=-2,
			padding_left=1
		)
		feels_shade_text.x = right_align_text(feels_shade_text.text, font, Layout.RIGHT_EDGE, state)

	# Load weather icon ONCE
	try:
		bitmap, palette = state.image_cache.get_image(f"{Paths.WEATHER_ICONS}/{weather_data['weather_icon']}.bmp")
		image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
		state.main_group.append(image_grid)
	except Exception as e:
		log_warning(f"Icon load failed: {e}")

	# Add all static elements to display ONCE
	state.main_group.append(temp_text)
	state.main_group.append(time_text)

	if feels_like_text:
		state.main_group.append(feels_like_text)
	if feels_shade_text:
		state.main_group.append(feels_shade_text)

	# Add UV and humidity indicator bars ONCE (they're static)
	add_indicator_bars(state.main_group, temp_text.x, weather_data['uv_index'], weather_data['humidity'], state)

	# Add day indicator ONCE
	if display_config.show_weekday_indicator:
		add_day_indicator(state.main_group, rtc, state)
		log_verbose(f"Showing Weekday Color Indicator on Weather Display")
	else:
		log_verbose("Weekday Color Indicator Disabled")

	# Optimized display update loop - ONLY update time text
	start_time = time.monotonic()
	loop_count = 0
	last_minute = -1

	while time.monotonic() - start_time < duration:
		loop_count += 1

		# Memory monitoring and cleanup
		if loop_count % Timing.GC_INTERVAL == 0:
			gc.collect()
			state.memory_monitor.check_memory(f"weather_display_gc_{loop_count//System.SECONDS_PER_MINUTE}")
		elif loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:
			state.memory_monitor.check_memory(f"weather_display_loop_{loop_count}")

		# Get current time
		hour = rtc.datetime.tm_hour
		minute = rtc.datetime.tm_min

		# Only update display when minute changes (not every second)
		if minute != last_minute:
			display_hour = hour % System.HOURS_IN_HALF_DAY if hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
			current_time = f"{display_hour}:{minute:02d}"

			# Update ONLY the time text content
			time_text.text = current_time

			# Position time text based on other elements
			if feels_shade_text:
				time_text.x = center_text(current_time, font, 0, Display.WIDTH, state)
			else:
				time_text.x = right_align_text(current_time, font, Layout.RIGHT_EDGE, state)

			last_minute = minute

		interruptible_sleep(1)

	state.memory_monitor.check_memory("weather_display_complete")


def show_event_display(rtc, duration, state=None, font=None, display_config=None, get_today_events_info=None, get_today_all_events_info=None):
	"""Display special calendar events - cycles through multiple events if present"""
	state.memory_monitor.check_memory("event_display_start")

	# Get currently active events
	num_events, event_list = get_today_events_info(rtc)

	# Check if there are ANY events today (even if not active now)
	total_events_today, all_today_events = get_today_all_events_info(rtc)

	if total_events_today > 0 and num_events == 0:
		# Events exist but none are currently active
		current_hour = rtc.datetime.tm_hour

		# Find when next event becomes active
		next_event_time = None
		for event in all_today_events:
			if len(event) >= 6:  # Has time window
				start_hour = int(event[4])
				if start_hour > current_hour:
					if next_event_time is None or start_hour < next_event_time:
						next_event_time = start_hour

		if next_event_time:
			log_verbose(f"Event inactive: {total_events_today} event(s) today, next active at {next_event_time}:00")
		else:
			log_verbose(f"Event inactive: {total_events_today} event(s) today, time window passed")

		return False

	if num_events == 0:
		return False

	# Log activation for time-windowed events
	for event in event_list:
		if len(event) >= 6:  # Has time window
			start_hour = event[4]
			end_hour = event[5]
			log_debug(f"Event active: {event[1]} {event[0]} (time window: {start_hour}:00-{end_hour}:00)")

	if num_events == 1:
		# Single event - use full duration
		event_data = event_list[0]
		log_info(f"Showing event: {event_data[0]} {event_data[1]}")
		log_debug(f"Showing event display for {duration_message(duration)}")
		_display_single_event_optimized(event_data, rtc, duration, state, font, display_config)
	else:
		# Multiple events - split time between them
		event_duration = max(duration // num_events, Timing.MIN_EVENT_DURATION)
		log_verbose(f"Showing {num_events} events, {duration_message(event_duration)} each")

		for i, event_data in enumerate(event_list):
			state.memory_monitor.check_memory(f"event_{i+1}_start")
			log_info(f"Event {i+1}/{num_events}: {event_data[0]} {event_data[1]}")
			_display_single_event_optimized(event_data, rtc, event_duration, state, font, display_config)

	state.memory_monitor.check_memory("event_display_complete")
	return True


def _display_single_event_optimized(event_data, rtc, duration, state=None, font=None, display_config=None):
	"""Optimized helper function to display a single event"""
	clear_display(state)

	# Force garbage collection before loading images
	gc.collect()
	state.memory_monitor.check_memory("single_event_start")

	# Load image first (sequential try blocks, not nested)
	bitmap = None
	palette = None

	if event_data[0] == "Birthday":  # Check bottom_line (was line1)
		# For birthday events, use the original cake image layout
		try:
			bitmap, palette = state.image_cache.get_image(Paths.BIRTHDAY_IMAGE)
		except Exception as e:
			log_warning(f"Failed to load birthday image: {e}")
			return False
	else:
		# Load event-specific image (25x28 positioned at top right) - sequential fallback
		image_file = f"{Paths.EVENT_IMAGES}/{event_data[2]}"
		try:
			bitmap, palette = state.image_cache.get_image(image_file)
		except Exception as e:
			log_warning(f"Failed to load {image_file}: {e}")
			bitmap = None  # Mark for fallback

		# Try fallback if primary failed (sequential, not nested)
		if bitmap is None:
			try:
				bitmap, palette = state.image_cache.get_image(Paths.FALLBACK_EVENT_IMAGE)
			except Exception as e2:
				log_warning(f"Failed to load fallback event image: {e2}")
				return False

	# Now display the loaded image
	try:
		if event_data[0] == "Birthday":
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			state.main_group.append(image_grid)
		else:

			# Position 25px wide image at top right
			image_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
			image_grid.x = Layout.EVENT_IMAGE_X
			image_grid.y = Layout.EVENT_IMAGE_Y

			# Calculate optimal text positions dynamically
			# NEW: Swapped indices - [0] is top, [1] is bottom
			top_text = event_data[0]     # e.g., "Puchis" - shows on TOP
			bottom_text = event_data[1]  # e.g., "Cumple" - shows on BOTTOM
			text_color = event_data[3] if len(event_data) > 3 else Strings.DEFAULT_EVENT_COLOR

			# Color map through dictionary access:
			line2_color = state.colors.get(text_color.upper(), state.colors[Strings.DEFAULT_EVENT_COLOR])

			# Get dynamic positions
			line1_y, line2_y = calculate_bottom_aligned_positions(
				font,
				top_text,
				bottom_text,
				display_height=Display.HEIGHT,
				bottom_margin=Layout.BOTTOM_MARGIN,
				line_spacing=Layout.LINE_SPACING
			)

			# Create text labels (line1 = top, line2 = bottom)
			text1 = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=top_text,
				x=Layout.TEXT_MARGIN, y=line1_y
			)

			text2 = bitmap_label.Label(
				font,
				color=line2_color,
				text=bottom_text,
				x=Layout.TEXT_MARGIN,
				y=line2_y
			)

			# Add elements to display
			state.main_group.append(image_grid)
			state.main_group.append(text1)
			state.main_group.append(text2)

			# Add day indicator
			if display_config.show_weekday_indicator:
				add_day_indicator(state.main_group, rtc, state)
				log_debug("Showing Weekday Color Indicator on Event Display")

		# Simple strategy optimized for usage patterns
		if duration <= Timing.EVENT_CHUNK_SIZE:
			# Most common case: 10-60 second events, just sleep
			interruptible_sleep(duration)
		else:
			# Rare case: all-day events, use 60-second chunks with minimal monitoring
			elapsed = 0
			chunk_size = Timing.EVENT_CHUNK_SIZE  # 1-minute chunks for long events

			while elapsed < duration:
				remaining = duration - elapsed
				sleep_time = min(chunk_size, remaining)

				interruptible_sleep(sleep_time)
				elapsed += sleep_time

				# Very minimal monitoring for all-day events (every 10 minutes)
				if elapsed % Timing.EVENT_MEMORY_MONITORING == 0:  # Every 10 minutes
					state.memory_monitor.check_memory(f"event_display_allday_{int(elapsed//System.SECONDS_PER_MINUTE)}min")

	except Exception as e:
		log_error(f"Event display error: {e}")
		state.memory_monitor.check_memory("single_event_error")

	# Clean up after event display
	gc.collect()
	state.memory_monitor.check_memory("single_event_complete")


def _format_hour_for_forecast(hour):
	"""Format hour for forecast display (helper function to avoid nested def)"""
	if hour == 0:
		return Strings.NOON_12AM
	elif hour < System.HOURS_IN_HALF_DAY:
		return f"{hour}{Strings.AM_SUFFIX}"
	elif hour == System.HOURS_IN_HALF_DAY:
		return Strings.NOON_12PM
	else:
		return f"{hour-System.HOURS_IN_HALF_DAY}{Strings.PM_SUFFIX}"


def show_forecast_display(current_data, forecast_data, display_duration, is_fresh=False, state=None, font=None, display_config=None):
	"""Optimized forecast display with smart precipitation detection"""
	# CRITICAL: Aggressive cleanup
	clear_display(state)
	gc.collect()
	state.memory_monitor.check_memory("forecast_display_start")

	# Check if we have real data
	if not current_data or not forecast_data or len(forecast_data) < 2:
		log_warning(f"Skipping forecast display - insufficient data")
		return False

	# Precipitation analysis - simple sequential logic
	current_has_precip = current_data.get('has_precipitation', False)
	forecast_indices = [0, 1]  # Default

	# Pre-extract precipitation flags (avoid nested access)
	precip_flags = [h.get('has_precipitation', False) for h in forecast_data[:6]]

	if current_has_precip:
		# Currently raining - find when it stops
		for i in range(len(precip_flags)):
			if not precip_flags[i]:
				forecast_indices = [i, min(i + 1, len(forecast_data) - 1)]
				log_debug(f"Rain stops at hour {i+1}")
				break
	else:
		# Not raining - find when it starts
		rain_start = -1
		rain_stop = -1

		for i in range(len(precip_flags)):
			if precip_flags[i] and rain_start == -1:
				rain_start = i
			elif not precip_flags[i] and rain_start != -1 and rain_stop == -1:
				rain_stop = i
				break

		if rain_start != -1:
			if rain_stop != -1:
				forecast_indices = [rain_start, rain_stop]
				log_debug(f"Rain: hour {rain_start+1} to {rain_stop+1}")
			else:
				forecast_indices = [rain_start, min(rain_start + 1, len(forecast_data) - 1)]
				log_debug(f"Rain starts at hour {rain_start+1}")

	# Simple duplicate hour check
	current_hour = state.rtc_instance.datetime.tm_hour
	first_forecast_hour = int(forecast_data[forecast_indices[0]]['datetime'][11:13]) % 24

	if first_forecast_hour == current_hour and forecast_indices[0] == 0 and len(forecast_data) >= 3:
		forecast_indices = [1, 2]
		log_debug(f"Adjusted to skip duplicate hour {current_hour}")

	log_debug(f"Will show hours: {forecast_indices[0]+1} and {forecast_indices[1]+1}")

	clear_display(state)
	gc.collect()

	# LOG what we're about to display
	current_temp = round(current_data["feels_like"])
	next_temps = [round(h["feels_like"]) for h in forecast_data[:2]]
	status = "Fresh" if is_fresh else "Cached"
	log_info(f"Displaying Forecast: Current {current_temp}°C → Next: {next_temps[0]}°C, {next_temps[1]}°C ({display_duration/60:.0f} min) [{status}]")

	# Extract weather data - NO TRY BLOCK to avoid nesting later
	# Column 1 - current temperature with feels-like logic
	temp_col1 = current_data.get('temperature', 0)

	if temp_col1 > Visual.FEELS_LIKE_TEMP_THRESHOLD:
		display_temp_col1 = current_data.get('feels_like', temp_col1)
	else:
		display_temp_col1 = current_data.get('feels_shade', temp_col1)

	col1_temp = f"{round(display_temp_col1)}°"
	col1_icon = f"{current_data.get('weather_icon', 1)}.bmp"

	# Column 2 - temperature with feels-like logic
	temp_col2 = forecast_data[forecast_indices[0]].get('temperature', 0)

	if temp_col2 > Visual.FEELS_LIKE_TEMP_THRESHOLD:
		# Warm: show feels-like
		display_temp_col2 = forecast_data[forecast_indices[0]].get('feels_like', temp_col2)
	else:
		# Cool: show feels-like shade
		display_temp_col2 = forecast_data[forecast_indices[0]].get('feels_shade', temp_col2)

	col2_temp = f"{round(display_temp_col2)}°"

	# Column 3 - temperature with feels-like logic
	temp_col3 = forecast_data[forecast_indices[1]].get('temperature', 0)

	if temp_col3 > Visual.FEELS_LIKE_TEMP_THRESHOLD:
		# Warm: show feels-like
		display_temp_col3 = forecast_data[forecast_indices[1]].get('feels_like', temp_col3)
	else:
		# Cool: show feels-like shade
		display_temp_col3 = forecast_data[forecast_indices[1]].get('feels_shade', temp_col3)

	col3_temp = f"{round(display_temp_col3)}°"

	# Get column icons
	col2_icon = f"{forecast_data[forecast_indices[0]].get('weather_icon', 1)}.bmp"
	col3_icon = f"{forecast_data[forecast_indices[1]].get('weather_icon', 1)}.bmp"

	hour_plus_1 = int(forecast_data[forecast_indices[0]]['datetime'][11:13]) % System.HOURS_IN_DAY
	hour_plus_2 = int(forecast_data[forecast_indices[1]]['datetime'][11:13]) % System.HOURS_IN_DAY

	# Calculate actual hours from datetime strings
	current_hour = state.rtc_instance.datetime.tm_hour
	col2_hour = int(forecast_data[forecast_indices[0]]['datetime'][11:13]) % System.HOURS_IN_DAY
	col3_hour = int(forecast_data[forecast_indices[1]]['datetime'][11:13]) % System.HOURS_IN_DAY

	# Calculate hours ahead from current time (handle midnight wraparound)
	col2_hours_ahead = (col2_hour - current_hour) % System.HOURS_IN_DAY
	col3_hours_ahead = (col3_hour - current_hour) % System.HOURS_IN_DAY

	# Determine colors based on hour gaps
	# Default: both jumped ahead
	col2_color = state.colors["MINT"]
	col3_color = state.colors["MINT"]

	# Override if col2 is immediate
	if col2_hours_ahead <= 1:
		col2_color = state.colors["DIMMEST_WHITE"]
		# Override col3 if also immediate
		if col3_hours_ahead <= 2:
			col3_color = state.colors["DIMMEST_WHITE"]

	# Generate static time labels for columns 2 and 3
	col2_time = _format_hour_for_forecast(hour_plus_1)
	col3_time = _format_hour_for_forecast(hour_plus_2)

	# Column positioning constants
	column_y = Layout.FORECAST_COLUMN_Y
	column_width = Layout.FORECAST_COLUMN_WIDTH
	time_y = Layout.FORECAST_TIME_Y
	temp_y = Layout.FORECAST_TEMP_Y

	# Define column data structure
	columns_data = [
		{"image": col1_icon, "x": Layout.FORECAST_COL1_X, "temp": col1_temp},
		{"image": col2_icon, "x": Layout.FORECAST_COL2_X, "temp": col2_temp},
		{"image": col3_icon, "x": Layout.FORECAST_COL3_X, "temp": col3_temp}
	]

	# Load weather icon columns - NO parent try block to avoid nesting
	for i, col in enumerate(columns_data):
		bitmap = None
		palette = None

		# Try primary weather icon (1-level try - safe!)
		try:
			bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{col['image']}")
		except:
			pass  # Will try fallback

		# Try fallback if primary failed (1-level try - safe!)
		if bitmap is None:
			try:
				bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{i+1}.bmp")
				log_warning(f"Used fallback column image for column {i+1}")
			except:
				pass  # Will skip this column

		# Skip this column if both failed
		if bitmap is None:
			log_warning(f"Failed to load column {i+1} image")
			continue

		# Create and add column (no exception handling needed)
		col_img = displayio.TileGrid(bitmap, pixel_shader=palette)
		col_img.x = col["x"]
		col_img.y = column_y
		state.main_group.append(col_img)

	# Create and display labels - wrap in try block for display errors
	try:
		# Create time labels - only column 1 will be updated
		col1_time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			x=max(center_text("00:00", font, Layout.FORECAST_COL1_X, column_width, state), 1),  # Initial placeholder
			y=time_y
		)

		# Use these colors in the labels
		col2_time_label = bitmap_label.Label(
			font,
			color=col2_color,
			text=col2_time,
			x=max(center_text(col2_time, font, Layout.FORECAST_COL2_X, column_width, state), 1),
			y=time_y
		)

		col3_time_label = bitmap_label.Label(
			font,
			color=col3_color,
			text=col3_time,
			x=max(center_text(col3_time, font, Layout.FORECAST_COL3_X, column_width, state), 1),
			y=time_y
		)

		# Add time labels to display
		state.main_group.append(col1_time_label)
		state.main_group.append(col2_time_label)
		state.main_group.append(col3_time_label)

		# Create temperature labels (all static)
		for col in columns_data:
			centered_x = center_text(col["temp"], font, col["x"], column_width, state) + 1

			temp_label = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=col["temp"],
				x=centered_x,
				y=temp_y
			)
			state.main_group.append(temp_label)

		# Add day indicator if enabled
		if display_config.show_weekday_indicator:
			add_day_indicator(state.main_group, state.rtc_instance, state)


		# Display update loop - update column 1 time only when minute changes
		start_time = time.monotonic()
		loop_count = 0
		last_minute = -1

		while time.monotonic() - start_time < display_duration:
			loop_count += 1

			# Update first column time only when minute changes
			if not state.rtc_instance:
				# Memory check and continue
				if loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:
					state.memory_monitor.check_memory(f"forecast_display_loop_{loop_count}")
				interruptible_sleep(1)
				continue

			# RTC available - check minute change
			current_hour = state.rtc_instance.datetime.tm_hour
			current_minute = state.rtc_instance.datetime.tm_min

			if current_minute != last_minute:
				display_hour = current_hour % System.HOURS_IN_HALF_DAY if current_hour % System.HOURS_IN_HALF_DAY != 0 else System.HOURS_IN_HALF_DAY
				new_time = f"{display_hour}:{current_minute:02d}"

				# Update ONLY the first column time text
				col1_time_label.text = new_time
				# Recenter the text
				col1_time_label.x = max(center_text(new_time, font, Layout.FORECAST_COL1_X, column_width, state), 1)

				last_minute = current_minute

			# Memory monitoring and cleanup
			if loop_count % Timing.MEMORY_CHECK_INTERVAL == 0:
				needs_gc = display_duration > Timing.GC_INTERVAL and loop_count % Timing.GC_INTERVAL == 0
				if needs_gc:
					gc.collect()
					state.memory_monitor.check_memory(f"forecast_display_gc_{loop_count//System.SECONDS_PER_HOUR}")
				else:
					state.memory_monitor.check_memory(f"forecast_display_loop_{loop_count}")

			interruptible_sleep(1)

	except Exception as e:
		log_error(f"Forecast display error: {e}")
		state.memory_monitor.check_memory("forecast_display_error")
		return False

	gc.collect()
	state.memory_monitor.check_memory("forecast_display_complete")
	return True


def show_scheduled_display(rtc, schedule_name, schedule_config, total_duration, current_data=None, state=None, font=None, display_config=None):
	"""
	Display scheduled message for one segment (max 5 minutes)
	Supports multi-segment schedules by tracking overall progress
	"""
	# Calculate how long this segment should display
	elapsed, full_duration, progress = get_schedule_progress(state)

	if elapsed is None:
		# First segment of schedule - initialize session
		state.active_schedule_name = schedule_name
		state.active_schedule_start_time = time.monotonic()
		state.active_schedule_end_time = state.active_schedule_start_time + total_duration
		state.active_schedule_segment_count = 0  # Reset segment counter
		elapsed = 0
		full_duration = total_duration
		progress = 0

		log_info(f"Starting schedule session: {schedule_name} ({total_duration}s total)")

	else:
		log_debug(f"Continuing schedule: {schedule_name} (elapsed: {elapsed:.0f}s / {full_duration:.0f}s)")

	# Increment segment count
	state.active_schedule_segment_count += 1
	log_debug(f"Schedule segment #{state.active_schedule_segment_count}")

	# This segment duration: min(5 minutes, remaining time)
	remaining = full_duration - elapsed
	segment_duration = min(Timing.SCHEDULE_SEGMENT_DURATION, remaining)

	log_debug(f"Segment duration: {segment_duration}s (remaining: {remaining:.0f}s)")

	# Light cleanup before segment (keep session alive for connection reuse)
	gc.collect()
	clear_display(state)

	# Fetch weather data (separate try block for data fetching)
	try:
		# Fetch weather if not provided
		if not current_data:
			# Smart caching: check cache first before fetching
			current_data = get_cached_weather_if_fresh(max_age_seconds=Timing.MAX_CACHE_AGE)

			if current_data:
				log_debug("Using fresh cached weather (< 15 minutes old)")
				is_cached = True
			else:
				# Cache stale or missing - fetch new data
				log_debug("Cache stale or missing - fetching fresh weather")
				current_data = fetch_current_weather_only()
				is_cached = False

		else:
			# current_data was provided as parameter
			is_cached = False

		if not current_data:
			# No weather data available, skip weather section
			log_warning("No weather data - Display schedule + clock only")
			is_cached = False

	except Exception as e:
		log_error(f"Schedule weather fetch error: {e}")
		current_data = None
		is_cached = False

	# === WEATHER SECTION (CONDITIONAL) - No parent try block ===
	if current_data:
		# Extract weather data
		temperature = f"{round(current_data['feels_like'])}°"
		weather_icon = f"{current_data['weather_icon']}.bmp"
		uv_index = current_data['uv_index']

		# Add UV bar if present
		if uv_index > 0:
			uv_length = calculate_uv_bar_length(uv_index)
			for i in range(uv_length):
				if i not in Visual.UV_SPACING_POSITIONS:
					uv_pixel = Line(
						Layout.SCHEDULE_LEFT_MARGIN_X + i,
						Layout.SCHEDULE_UV_Y,
						Layout.SCHEDULE_LEFT_MARGIN_X + i,
						Layout.SCHEDULE_UV_Y,
						state.colors["DIMMEST_WHITE"]
					)
					state.main_group.append(uv_pixel)

		y_offset = Layout.SCHEDULE_X_OFFSET if uv_index > 0 else 0

		# Load weather icon (1-level try - safe!)
		try:
			bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{weather_icon}")
			weather_img = displayio.TileGrid(bitmap, pixel_shader=palette)
			weather_img.x = Layout.SCHEDULE_LEFT_MARGIN_X
			weather_img.y = Layout.SCHEDULE_W_IMAGE_Y + y_offset
			state.main_group.append(weather_img)
		except Exception as e:
			log_error(f"Failed to load weather icon: {e}")

		# Set temperature color based on cache status
		temp_color = state.colors["LILAC"] if is_cached else state.colors["DIMMEST_WHITE"]

		# Temp Labels

		temp_label = bitmap_label.Label(
			font,
			color=temp_color,
			text=temperature,
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.SCHEDULE_TEMP_Y + y_offset
		)
		state.main_group.append(temp_label)

	# === SCHEDULE IMAGE (ALWAYS) - 1-level try (safe!) ===
	try:
		bitmap, palette = load_bmp_image(f"{Paths.SCHEDULE_IMAGES}/{schedule_config['image']}")
		schedule_img = displayio.TileGrid(bitmap, pixel_shader=palette)
		schedule_img.x = Layout.SCHEDULE_IMAGE_X
		schedule_img.y = Layout.SCHEDULE_IMAGE_Y
		state.main_group.append(schedule_img)
	except Exception as e:
		log_error(f"Failed to load schedule image: {e}")
		state.scheduled_display_error_count += 1
		if state.scheduled_display_error_count >= 3:
			display_config.show_scheduled_displays = False
		show_clock_display(rtc, segment_duration)
		return

	state.scheduled_display_error_count = 0

	# === CLOCK LABEL AND DISPLAY LOOP - wrap in try for display errors ===
	try:
		# === CLOCK LABEL (ALWAYS) ===
		time_label = bitmap_label.Label(
			font,
			color=state.colors["DIMMEST_WHITE"],
			x=Layout.SCHEDULE_LEFT_MARGIN_X,
			y=Layout.FORECAST_TIME_Y
		)
		state.main_group.append(time_label)

		# === WEEKDAY INDICATOR (IF ENABLED) ===
		if display_config.show_weekday_indicator:
			add_day_indicator(state.main_group, rtc, state)
			log_verbose("Showing Weekday Color Indicator on Schedule Display")

		# LOG what's being displayed this segment
		segment_num = int(elapsed / Timing.SCHEDULE_SEGMENT_DURATION) + 1
		total_segments = int(full_duration / Timing.SCHEDULE_SEGMENT_DURATION) + (1 if full_duration % Timing.SCHEDULE_SEGMENT_DURATION else 0)

		state.schedule_just_ended = (segment_num >= total_segments)

		if current_data:
			cache_indicator = " [CACHED]" if is_cached else ""
			log_info(f"Displaying Schedule: {schedule_name} - Segment {segment_num}/{total_segments} ({temperature}, {segment_duration/60:.1f} min, progress: {progress*100:.0f}%){cache_indicator}")
		else:
			log_info(f"Displaying Schedule: {schedule_name} - Segment {segment_num}/{total_segments} (Weather Skipped, progress: {progress*100:.0f}%)")

		# Override success tracking
		state.last_successful_weather = time.monotonic()
		state.consecutive_failures = 0

		# === PROGRESS BAR ===
		## Progress bar - based on FULL schedule progress, not segment
		if schedule_config.get("progressbar", True):
			progress_grid, progress_bitmap = create_progress_bar_tilegrid(state)

			# Pre-fill progress bar based on elapsed time using existing function
			if progress > 0:
				update_progress_bar_bitmap(progress_bitmap, elapsed, full_duration)
				log_debug(f"Pre-filled progress bar to {progress*100:.0f}%")

			state.main_group.append(progress_grid)
			show_progress_bar = True
		else:
			progress_grid = None
			progress_bitmap = None
			show_progress_bar = False

		# === DISPLAY LOOP ===
		segment_start = time.monotonic()
		last_minute = -1
		last_displayed_column = -1

		# Adaptive sleep for smooth updates
		sleep_interval = max(Timing.MIN_SLEEP_INTERVAL, min(segment_duration / 60, Timing.MAX_SLEEP_INTERVAL))  # 1-5 seconds

		while time.monotonic() - segment_start < segment_duration:
			current_minute = rtc.datetime.tm_min
			current_time = time.monotonic()

			# Calculate OVERALL progress (from schedule start, not segment start)
			overall_elapsed = elapsed + (current_time - segment_start)
			overall_progress = overall_elapsed / full_duration
			current_column = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * overall_progress)

			# Update progress bar
			if show_progress_bar and current_column != last_displayed_column and current_column < Layout.PROGRESS_BAR_HORIZONTAL_WIDTH:
				update_progress_bar_bitmap(progress_bitmap, overall_elapsed, full_duration)
				last_displayed_column = current_column

			# Update clock
			if current_minute != last_minute:
				hour = rtc.datetime.tm_hour
				display_hour = hour % System.HOURS_IN_HALF_DAY or System.HOURS_IN_HALF_DAY
				time_label.text = f"{display_hour}:{current_minute:02d}"
				last_minute = current_minute

			time.sleep(sleep_interval)

		log_debug(f"Segment complete")

	except Exception as e:
		log_error(f"Scheduled display segment error: {e}")

		# CRITICAL: Add delay to prevent runaway loops on errors

		# Safety: If too many errors in a row, take a break
		if state.consecutive_display_errors >= 5:
			log_error("Too many consecutive errors - safe mode")
			safe_duration = Timing.CLOCK_DISPLAY_DURATION  # 5 minutes
		else:
			# If segment_duration is very small or 0, use minimum 30 seconds
			safe_duration = max(Timing.ERROR_SAFETY_DELAY, segment_duration)

		show_clock_display(rtc, safe_duration)

	finally:
		# Cleanup after segment
		gc.collect()

		# Return segment info
		# return is_last_segment # Boolean - is this last segment of schedule display


def show_color_test_display(duration=Timing.COLOR_TEST, state=None, font=None):
	"""Display color test grid to verify color accuracy"""
	log_debug(f"Displaying Color Test for {duration_message(Timing.COLOR_TEST)}")
	clear_display(state)
	gc.collect()

	try:
		# Get test colors dynamically from COLORS dictionary
		test_color_names = ["MINT", "BUGAMBILIA", "LILAC", "RED", "GREEN", "BLUE",
						   "ORANGE", "YELLOW", "CYAN", "PURPLE", "PINK", "BROWN"]
		texts = ["Aa", "Bb", "Cc", "Dd", "Ee", "Ff", "Gg", "Hh", "Ii", "Jj", "Kk", "Ll"]

		key_text = "Color Key: "

		for i, (color_name, text) in enumerate(zip(test_color_names, texts)):
			color = state.colors[color_name]
			col = i // Visual.COLOR_TEST_GRID_COLS
			row = i % Visual.COLOR_TEST_GRID_COLS

			label = bitmap_label.Label(
				font, color=color, text=text,
				x=Layout.COLOR_TEST_TEXT_X + col * Visual.COLOR_TEST_COL_SPACING, y=Layout.COLOR_TEST_TEXT_Y + row * Visual.COLOR_TEST_ROW_SPACING
			)
			state.main_group.append(label)
			key_text += f"{text}={color_name}(0x{color:06X}) | "

	except Exception as e:
		log_error(f"Color Test display error: {e}")

	log_info(key_text)
	interruptible_sleep(duration)
	gc.collect()
	return True


def show_icon_test_display(icon_numbers=None, duration=Timing.ICON_TEST, state=None, font=None):
	"""
	Test display for weather icon columns

	Args:
		icon_numbers: List of up to 3 icon numbers to display, e.g. [1, 5, 33]
					 If None, cycles through all icons
		duration: How long to display (only used when cycling all icons)
	"""
	if icon_numbers is None:
		# Original behavior - cycle through all icons
		log_info("Starting Icon Test Display - All Icons (Ctrl+C to exit)")

		# AccuWeather icon numbers (skipping 9, 10, 27, 28)
		all_icons = []
		for i in range(1, 45):
			if i not in [9, 10, 27, 28]:
				all_icons.append(i)

		total_icons = len(all_icons)
		icons_per_batch = 3
		num_batches = (total_icons + icons_per_batch - 1) // icons_per_batch

		log_info(f"Testing {total_icons} icons in {num_batches} batches")

		try:
			for batch_num in range(num_batches):
				start_idx = batch_num * icons_per_batch
				end_idx = min(start_idx + icons_per_batch, total_icons)
				batch_icons = all_icons[start_idx:end_idx]

				_display_icon_batch(batch_icons, batch_num + 1, num_batches, False, state, font)

				# Shorter sleep intervals for better interrupt response
				for _ in range(int(duration * 10)):
					time.sleep(0.1)

		except KeyboardInterrupt:
			log_info("Icon test interrupted by user")
			clear_display(state)
			raise
	else:
		# Manual mode - display specific icons indefinitely
		if len(icon_numbers) > 3:
			log_warning(f"Too many icons specified ({len(icon_numbers)}), showing first 3")
			icon_numbers = icon_numbers[:3]

		log_info(f"Displaying icons: {icon_numbers} (Ctrl+C to exit)")
		_display_icon_batch(icon_numbers, None, None, True, state, font)

		# Loop indefinitely until interrupted
		try:
			while True:
				time.sleep(0.1)  # Keep display active, check for interrupt
		except KeyboardInterrupt:
			log_info("Icon test interrupted")
			clear_display(state)
			raise

	log_info("Icon Test Display complete")
	gc.collect()
	return True


def _display_icon_batch(icon_numbers, batch_num=None, total_batches=None, manual_mode=False, state=None, font=None):
	"""Helper function to display a batch of icons"""
	if not manual_mode:
		log_info(f"Batch {batch_num}/{total_batches}: Icons {icon_numbers}")

	clear_display(state)
	gc.collect()

	try:
		# Position icons horizontally (up to 3)
		positions = [
			(Layout.ICON_TEST_COL1_X, Layout.ICON_TEST_ROW1_Y),  # Left
			(Layout.ICON_TEST_COL2_X, Layout.ICON_TEST_ROW1_Y),  # Center
			(Layout.ICON_TEST_COL3_X, Layout.ICON_TEST_ROW1_Y),  # Right
		]

		for i, icon_num in enumerate(icon_numbers):
			if i >= len(positions):
				break

			x, y = positions[i]

			# Load icon image
			try:
				bitmap, palette = state.image_cache.get_image(f"{Paths.COLUMN_IMAGES}/{icon_num}.bmp")
				icon_img = displayio.TileGrid(bitmap, pixel_shader=palette)
				icon_img.x = x
				icon_img.y = y
				state.main_group.append(icon_img)
			except Exception as e:
				log_warning(f"Failed to load icon {icon_num}: {e}")
				# Show error text instead
				error_label = bitmap_label.Label(
					font,
					color=state.colors["RED"],
					text="ERR",
					x=x + 1,
					y=y + 4
				)
				state.main_group.append(error_label)

			# Add icon number below image
			number_label = bitmap_label.Label(
				font,
				color=state.colors["DIMMEST_WHITE"],
				text=str(icon_num),
				x=x + (5 if icon_num < 10 else 3),  # Center single vs double digits
				y=y + Layout.ICON_TEST_NUMBER_Y_OFFSET
			)
			state.main_group.append(number_label)

	except Exception as e:
		log_error(f"Icon display error: {e}")


def create_progress_bar_tilegrid(state=None):
	"""Create a TileGrid-based progress bar with tick marks"""
	# Progress bar dimensions
	bar_width = Layout.PROGRESS_BAR_HORIZONTAL_WIDTH
	bar_height = Layout.PROGRESS_BAR_HORIZONTAL_HEIGHT
	tick_height_above = 2
	tick_height_below = 1
	total_height = tick_height_above + bar_height + tick_height_below  # 5px total

	# Bar position within bitmap
	bar_y_start = tick_height_above  # Bar starts at row 2
	bar_y_end = bar_y_start + bar_height  # Bar ends at row 4

	# Create bitmap
	progress_bitmap = displayio.Bitmap(bar_width, total_height, 4)

	# Create palette
	progress_palette = displayio.Palette(4)
	progress_palette[0] = state.colors["BLACK"]
	progress_palette[1] = state.colors["LILAC"]  # Elapsed
	progress_palette[2] = state.colors["MINT"]   # Remaining
	progress_palette[3] = state.colors["WHITE"]  # Tick marks

	# Initialize with black background
	for y in range(total_height):
		for x in range(bar_width):
			progress_bitmap[x, y] = 0

	# Fill bar area with "remaining" color
	for y in range(bar_y_start, bar_y_end):
		for x in range(bar_width):
			progress_bitmap[x, y] = 2

	# Add tick marks at 0%, 25%, 50%, 75%, 100%
	tick_positions = [0, bar_width // 4, bar_width // 2, 3 * bar_width // 4, bar_width - 1]

	for pos in tick_positions:
		# Major ticks (start, middle, end) get 2px above
		if pos == 0 or pos == bar_width // 2 or pos == bar_width - 1:
			progress_bitmap[pos, 0] = 3
			progress_bitmap[pos, 1] = 3
		else:  # Minor ticks (25%, 75%) get 1px above
			progress_bitmap[pos, 1] = 3

		# All ticks get 1px below
		progress_bitmap[pos, bar_y_end] = 3

	# Create TileGrid
	progress_grid = displayio.TileGrid(
		progress_bitmap,
		pixel_shader=progress_palette,
		x=Layout.PROGRESS_BAR_HORIZONTAL_X,
		y=Layout.PROGRESS_BAR_HORIZONTAL_Y - tick_height_above
	)

	return progress_grid, progress_bitmap


def update_progress_bar_bitmap(progress_bitmap, elapsed_seconds, total_seconds):
	"""Update progress bar bitmap (fills left to right as time elapses)"""
	if total_seconds <= 0:
		return

	# Calculate elapsed pixels
	elapsed_ratio = min(1.0, elapsed_seconds / total_seconds)
	elapsed_width = int(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH * elapsed_ratio)

	# Bar position (rows 2-3 in the 5-row bitmap)
	bar_y_start = 2
	bar_y_end = 4

	# Update only the bar area
	for y in range(bar_y_start, bar_y_end):
		for x in range(Layout.PROGRESS_BAR_HORIZONTAL_WIDTH):
			if x < elapsed_width:
				progress_bitmap[x, y] = 1  # Elapsed (LILAC)
			else:
				progress_bitmap[x, y] = 2  # Remaining (MINT)


def get_schedule_progress(state=None):
	"""
	Calculate progress for active schedule session
	Returns: (elapsed_seconds, total_duration, progress_ratio) or (None, None, None)
	"""

	if not state.active_schedule_name or not state.active_schedule_start_time:
		return None, None, None

	current_time = time.monotonic()

	# Check if schedule has expired
	if state.active_schedule_end_time and current_time >= state.active_schedule_end_time:
		# Schedule is over - clear session
		log_debug(f"Schedule session ended: {state.active_schedule_name}")
		state.active_schedule_name = None
		state.active_schedule_start_time = None
		state.active_schedule_end_time = None
		state.active_schedule_segment_count = 0
		return None, None, None

	elapsed = current_time - state.active_schedule_start_time
	total_duration = state.active_schedule_end_time - state.active_schedule_start_time
	progress_ratio = elapsed / total_duration if total_duration > 0 else 0

	return elapsed, total_duration, progress_ratio
