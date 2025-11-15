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
import adafruit_imageload
from adafruit_display_text import bitmap_label
from adafruit_display_shapes.line import Line

from config import (
    Display, Layout, DayIndicator, Visual, System, Timing, Paths,
    Strings, ColorManager, MONTHS
)
from utils import log_info, log_error, log_warning, log_debug, log_verbose


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
# STUB: DISPLAY FUNCTIONS
# ===========================
# The following functions need to be extracted from code.py:
# - show_weather_display() (lines ~2551-2708)
# - show_clock_display() (lines ~2709-2776)
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


def show_clock_display(rtc, duration=Timing.CLOCK_DISPLAY_DURATION):
	"""STUB: Clock display function - needs extraction from code.py"""
	log_error("show_clock_display() not yet implemented - requires extraction from code.py:2709-2776")
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


# Additional stub functions
def show_color_test_display(duration=Timing.COLOR_TEST):
	"""STUB: Color test display"""
	raise NotImplementedError("Display functions require full extraction")


def show_icon_test_display(icon_numbers=None, duration=Timing.ICON_TEST):
	"""STUB: Icon test display"""
	raise NotImplementedError("Display functions require full extraction")


def create_progress_bar_tilegrid():
	"""STUB: Progress bar creation"""
	raise NotImplementedError("Display functions require full extraction")


def update_progress_bar_bitmap(progress_bitmap, elapsed_seconds, total_seconds):
	"""STUB: Progress bar update"""
	raise NotImplementedError("Display functions require full extraction")


def get_schedule_progress():
	"""STUB: Get schedule progress"""
	raise NotImplementedError("Display functions require full extraction")
