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
from network import is_wifi_connected


# ===========================
# HARDWARE INITIALIZATION
# ===========================

def initialize_display():
	"""Initialize RGB matrix display"""
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
	
	log_info(f"Display initialized: {Display.WIDTH}x{Display.HEIGHT} @ {Display.BIT_DEPTH}-bit")
	return state.display


# ===========================
# MATRIX DETECTION & COLORS
# ===========================

def detect_matrix_type():
	"""Auto-detect matrix wiring type (cached for performance)"""
	from code import state
	
	if state.matrix_type_cache is not None:
		return state.matrix_type_cache
	
	uid = microcontroller.cpu.uid
	device_id = "".join([f"{b:02x}" for b in uid[-3:]])
	
	device_mappings = {
		System.DEVICE_TYPE1_ID: "type1",
		System.DEVICE_TYPE2_ID: "type2",
	}
	
	state.matrix_type_cache = device_mappings.get(device_id, "type1")
	log_debug(f"Device ID: {device_id}, Matrix type: {state.matrix_type_cache}")
	return state.matrix_type_cache


def get_matrix_colors():
	"""Get color constants with corrections applied"""
	matrix_type = detect_matrix_type()
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

def get_text_width(text, font):
	"""Get text width using cache"""
	from code import state
	return state.text_cache.get_text_width(text, font)


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

def clear_display():
	"""Clear the display"""
	from code import state
	
	while len(state.main_group) > 0:
		state.main_group.pop()


def right_align_text(text, font, right_edge):
	"""Calculate x position for right-aligned text"""
	return right_edge - get_text_width(text, font)


def center_text(text, font, area_x, area_width):
	"""Calculate x position for centered text"""
	text_width = get_text_width(text, font)
	return area_x + (area_width - text_width) // 2


def get_day_color(rtc):
	"""Get color for current day of week"""
	from code import state
	
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


def add_day_indicator(main_group, rtc):
	"""Add colored day-of-week indicator to display"""
	from code import state
	import displayio
	
	# Day indicator square (top right)
	day_palette = displayio.Palette(2)
	day_palette[0] = state.colors["BLACK"]
	day_palette[1] = get_day_color(rtc)
	
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


def add_indicator_bars(main_group, x_start, uv_index, humidity):
	"""Add UV and humidity indicator bars to display"""
	from code import state
	
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

def get_current_error_state():
	"""Determine current error state based on system status"""
	from code import state

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

def show_clock_display(rtc, duration=Timing.CLOCK_DISPLAY_DURATION):
	"""Display clock as fallback when weather unavailable"""
	from code import state, font, bg_font, display_config

	log_warning(f"Displaying clock for {duration_message(duration)}...")
	clear_display()

	# Determine clock color based on error state
	error_state = get_current_error_state()

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
		add_day_indicator(state.main_group, rtc)
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

def show_weather_display(rtc, duration, weather_data=None):
	"""STUB: Weather display function - needs extraction from code.py"""
	log_error("show_weather_display() not yet implemented - requires extraction from code.py:2551-2708")
	raise NotImplementedError("Display functions require full extraction")


def show_event_display(rtc, duration):
	"""STUB: Event display function - needs extraction from code.py"""
	log_error("show_event_display() not yet implemented - requires extraction from code.py:2777-2956")
	raise NotImplementedError("Display functions require full extraction")


def show_forecast_display(current_data, forecast_data, display_duration, is_fresh=False):
	"""STUB: Forecast display function - needs extraction from code.py"""
	log_error("show_forecast_display() not yet implemented - requires extraction from code.py:3110-3400")
	raise NotImplementedError("Display functions require full extraction")


def show_scheduled_display(rtc, schedule_name, schedule_config, total_duration, current_data=None):
	"""STUB: Scheduled display function - needs extraction from code.py"""
	log_error("show_scheduled_display() not yet implemented - requires extraction from code.py:3522-3759")
	raise NotImplementedError("Display functions require full extraction")


def show_color_test_display(duration=Timing.COLOR_TEST):
	"""Display color test grid to verify color accuracy"""
	from code import state, font

	log_debug(f"Displaying Color Test for {duration_message(Timing.COLOR_TEST)}")
	clear_display()
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


def show_icon_test_display(icon_numbers=None, duration=Timing.ICON_TEST):
	"""
	Test display for weather icon columns

	Args:
		icon_numbers: List of up to 3 icon numbers to display, e.g. [1, 5, 33]
					 If None, cycles through all icons
		duration: How long to display (only used when cycling all icons)
	"""
	from code import state

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

				_display_icon_batch(batch_icons, batch_num + 1, num_batches)

				# Shorter sleep intervals for better interrupt response
				for _ in range(int(duration * 10)):
					time.sleep(0.1)

		except KeyboardInterrupt:
			log_info("Icon test interrupted by user")
			clear_display()
			raise
	else:
		# Manual mode - display specific icons indefinitely
		if len(icon_numbers) > 3:
			log_warning(f"Too many icons specified ({len(icon_numbers)}), showing first 3")
			icon_numbers = icon_numbers[:3]

		log_info(f"Displaying icons: {icon_numbers} (Ctrl+C to exit)")
		_display_icon_batch(icon_numbers, manual_mode=True)

		# Loop indefinitely until interrupted
		try:
			while True:
				time.sleep(0.1)  # Keep display active, check for interrupt
		except KeyboardInterrupt:
			log_info("Icon test interrupted")
			clear_display()
			raise

	log_info("Icon Test Display complete")
	gc.collect()
	return True


def _display_icon_batch(icon_numbers, batch_num=None, total_batches=None, manual_mode=False):
	"""Helper function to display a batch of icons"""
	from code import state, font

	if not manual_mode:
		log_info(f"Batch {batch_num}/{total_batches}: Icons {icon_numbers}")

	clear_display()
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


def create_progress_bar_tilegrid():
	"""Create a TileGrid-based progress bar with tick marks"""
	from code import state

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


def get_schedule_progress():
	"""
	Calculate progress for active schedule session
	Returns: (elapsed_seconds, total_duration, progress_ratio) or (None, None, None)
	"""
	from code import state

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
