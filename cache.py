"""
Cache module for Pantallita 2.0
Contains ImageCache and TextWidthCache for performance optimization
"""

from adafruit_display_text import bitmap_label
from config import Memory


class ImageCache:
	"""
	Cache for BMP images to avoid redundant filesystem reads.
	Uses FIFO eviction when cache is full.
	"""
	DEFAULT_MAX_SIZE = 12  # Named constant for default cache size

	def __init__(self, max_size=None):
		self.cache = {}  # filepath -> (bitmap, palette)
		self.max_size = max_size or self.DEFAULT_MAX_SIZE
		self.hit_count = 0
		self.miss_count = 0

	def get_image(self, filepath):
		"""
		Get image from cache or load from filesystem.

		Args:
			filepath (str): Path to BMP image file

		Returns:
			tuple: (bitmap, palette) or (None, None) if load fails
		"""
		from utils import log_verbose, log_error
		from display import load_bmp_image

		if filepath in self.cache:
			self.hit_count += 1
			return self.cache[filepath]

		# Cache miss - load the image
		try:
			bitmap, palette = load_bmp_image(filepath)
			self.miss_count += 1

			# Check if cache is full
			if len(self.cache) >= self.max_size:
				# Remove oldest entry (simple FIFO)
				oldest_key = next(iter(self.cache))
				del self.cache[oldest_key]
				log_verbose(f"Image cache full, removed: {oldest_key}")

			self.cache[filepath] = (bitmap, palette)
			log_verbose(f"Cached image: {filepath}")
			return bitmap, palette

		except Exception as e:
			log_error(f"Failed to load image {filepath}: {e}")
			return None, None

	def clear_cache(self):
		"""Clear all cached images"""
		from utils import log_verbose

		self.cache.clear()
		log_verbose("Image cache cleared")

	def get_stats(self):
		"""
		Get cache statistics.

		Returns:
			str: Human-readable cache statistics
		"""
		total = self.hit_count + self.miss_count
		hit_rate = (self.hit_count / total * 100) if total > 0 else 0
		return f"Cache: {len(self.cache)} items, {hit_rate:.1f}% hit rate"


class TextWidthCache:
	"""
	Cache for text width calculations to avoid redundant bounding box computations.
	Uses FIFO eviction when cache is full.
	"""
	DEFAULT_MAX_SIZE = 50  # Named constant for default cache size

	def __init__(self, max_size=None):
		self.cache = {}  # (text, font_id) -> width
		self.max_size = max_size or self.DEFAULT_MAX_SIZE
		self.hit_count = 0
		self.miss_count = 0

	def get_text_width(self, text, font):
		"""
		Get text width from cache or calculate.

		Args:
			text (str): Text to measure
			font: Bitmap font object

		Returns:
			int: Width of text in pixels
		"""
		if not text:
			return 0

		cache_key = (text, id(font))

		if cache_key in self.cache:
			self.hit_count += 1
			return self.cache[cache_key]

		# Cache miss - calculate width
		temp_label = bitmap_label.Label(font, text=text)
		bbox = temp_label.bounding_box
		width = bbox[2] if bbox else 0

		self.miss_count += 1

		# Evict oldest if cache full
		if len(self.cache) >= self.max_size:
			oldest_key = next(iter(self.cache))
			del self.cache[oldest_key]

		self.cache[cache_key] = width
		return width

	def get_stats(self):
		"""
		Get cache statistics.

		Returns:
			str: Human-readable cache statistics
		"""
		total = self.hit_count + self.miss_count
		hit_rate = (self.hit_count / total * 100) if total > 0 else 0
		return f"Text cache: {len(self.cache)} items, {hit_rate:.1f}% hit rate"
