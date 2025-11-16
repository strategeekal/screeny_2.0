
### Option 1: Minimal Modularization (3 Files - Recommended)

Split into 3 files to minimize memory impact while improving maintainability.

#### File Structure
```
screeny_2.0/
├── config.py          # ~800 lines - Configuration & constants
├── network.py         # ~600 lines - Network & API operations
├── code.py            # ~2700 lines - Display & main loop
└── ...
```

#### config.py (~800 lines)
**Contains:** Static configuration data loaded once at startup

```python
# All constant classes (Display, Layout, Timing, API, etc.)
# DisplayConfig class
# ColorManager class
# ImageCache and TextWidthCache classes
# MemoryMonitor class
# validate_configuration()
```

**Rationale:**
- Mostly static data (minimal memory overhead)
- No circular dependencies
- Can be easily swapped for test configurations
- Clear separation of configuration from logic

#### network.py (~600 lines)
**Contains:** All network, WiFi, session, and API operations

```python
# Imports from config
from config import API, Recovery, Memory, Strings, Timing, System

# Functions:
# - setup_rtc()
# - setup_wifi_with_recovery()
# - check_and_recover_wifi()
# - is_wifi_connected()
# - get_timezone_offset()
# - sync_time_with_timezone()
# - cleanup_sockets()
# - get_requests_session()
# - cleanup_global_session()
# - fetch_weather_with_retries()
# - fetch_current_and_forecast_weather()
# - get_cached_weather_if_fresh()
# - fetch_current_weather_only()
# - get_api_key()
```

**Rationale:**
- Isolates network issues (easier debugging)
- Socket management in one place
- Can be tested independently
- Clear API boundary

#### code.py (~2700 lines)
**Contains:** State, display functions, data loading, main loop

```python
# Import modules
from config import *
from network import *

# State management (WeatherDisplayState)
# Logging functions
# Data loading (CSV, GitHub)
# Display functions (weather, forecast, events, schedules)
# Main loop orchestration
# System initialization
```

**Rationale:**
- Main orchestration logic stays together
- Display functions are cohesive (hard to split further)
- State management accessible to all functions

#### Estimated Memory Impact
- **Import overhead:** +50-100KB
- **Post-split usage:** 15-25% (still within safe range)
- **Risk level:** Low (plenty of headroom)

---

### Option 2: Proper Modularization (5-6 Files)

Split into more focused modules for maximum maintainability.

#### File Structure
```
screeny_2.0/
├── config.py          # ~500 lines - Constants only
├── state.py           # ~200 lines - State management
├── network.py         # ~400 lines - WiFi & sessions
├── api.py             # ~300 lines - AccuWeather API
├── data.py            # ~400 lines - CSV & GitHub
├── display.py         # ~1200 lines - Display functions
├── code.py            # ~1100 lines - Main loop
└── ...
```

#### config.py (~500 lines)
Pure constants only - no classes with methods (except simple getters/setters)

#### state.py (~200 lines)
```python
from config import Paths, Timing

class ImageCache:
	"""Image caching with LRU eviction"""

class TextWidthCache:
	"""Text width caching for performance"""

class MemoryMonitor:
	"""Memory usage tracking and reporting"""

class WeatherDisplayState:
	"""Global state management"""
	def __init__(self):
		self.image_cache = ImageCache(max_size=12)
		self.text_cache = TextWidthCache()
		self.memory_monitor = MemoryMonitor()
		# ... all state variables

# Global instance
state = WeatherDisplayState()
```

**Rationale:**
- State is lightweight (just data structures)
- Accessed by many modules
- No circular dependencies (only imports config)

#### network.py (~400 lines)
Low-level network operations only (WiFi, sockets, sessions, timezone)
- Does NOT include API calls
- Provides session management for other modules

#### api.py (~300 lines)
```python
from config import API, Recovery
from state import state
from network import get_requests_session, cleanup_global_session

# fetch_weather_with_retries()
# fetch_current_and_forecast_weather()
# get_cached_weather_if_fresh()
# fetch_current_weather_only()
# get_api_key()
```

**Rationale:**
- API-specific logic isolated
- Easy to add new APIs (stocks, sports)
- Clear dependency: uses network, not vice versa

#### data.py (~400 lines)
```python
from config import Paths, Strings
from state import state
from network import get_requests_session

# load_events_from_csv()
# fetch_ephemeral_events()
# load_all_events()
# parse_events_csv_content()
# parse_schedule_csv_content()
# fetch_github_data()
# load_schedules_from_csv()

class ScheduledDisplay:
	"""Schedule management"""
```

**Rationale:**
- Data management separate from display
- Can test CSV parsing independently
- Clear responsibility

#### display.py (~1200 lines)
All display rendering functions
- Loads fonts once (shared across all functions)
- All visual rendering logic

#### code.py (~1100 lines)
```python
# Import all modules
from config import *
from state import state
from network import *
from api import *
from data import *
from display import *

# Logging functions
# Main loop
# System initialization
# Entry point
```

**Rationale:**
- Main orchestrator
- Thin layer coordinating other modules

#### Estimated Memory Impact
- **Import overhead:** +100-200KB
- **Post-split usage:** 20-30%
- **Risk level:** Medium (test thoroughly)

---

### Import Dependency Graph

**Option 1 (3 files):**
```
config.py (no dependencies)
	↓
network.py (imports config, uses state from code.py)
	↓
code.py (imports config, network; defines state)
```

**Option 2 (5-6 files):**
```
config.py (no dependencies)
	↓
state.py (imports config)
	↓
network.py (imports config, state)
	↓
api.py (imports config, state, network)
	↓
data.py (imports config, state, network)
	↓
display.py (imports config, state)
	↓
code.py (imports all)
```

---

### Testing Memory Impact

Before implementing either option, test import overhead:

```python
# Add to beginning of code.py (before any imports)
import gc

# Baseline
gc.collect()
baseline = gc.mem_free()
print(f"Baseline free memory: {baseline} bytes")

# After imports
from config import *
from network import *
# ... etc

gc.collect()
after_imports = gc.mem_free()
overhead = baseline - after_imports
print(f"After imports: {after_imports} bytes")
print(f"Import overhead: {overhead} bytes ({overhead/1024:.1f} KB)")
```

**Decision Criteria:**
- Overhead < 100KB → **Option 2** (proper modularization)
- Overhead 100-200KB → **Option 1** (minimal split)
- Overhead > 200KB → **Keep monolith** (improve organization only)

---

### Circular Dependency Prevention

**Problem:** `network.py` needs `state`, but `state.py` defines state

**Solution (Option 1):**
- Keep state in `code.py`
- Pass state as parameter to network functions
- Or import state at runtime (not at module level)

**Solution (Option 2):**
- `state.py` only imports `config` (no other modules)
- All other modules can safely import `state`
- Linear dependency chain (no cycles)

---

### Implementation Recommendation

**Recommended Approach: Start with Option 1**

1. **Lowest Risk**
   - Minimal imports (2 new modules)
   - Easiest to revert if issues arise
   - Smaller surface area for bugs

2. **Biggest Wins**
   - Reduces main file by 34% (4117 → 2700 lines)
   - Separates configuration (easier testing)
   - Isolates network issues (easier debugging)

3. **Path Forward**
   - Test Option 1 for stability (24-48 hours)
   - If memory/stability good → consider Option 2
   - If issues arise → stay with Option 1 or revert

### Implementation Steps (Option 1)

1. **Create config.py**
   - Copy lines 1-550 (constants)
   - Add cache classes
   - Add memory monitor
   - Test import in isolation

2. **Create network.py**
   - Copy lines 1014-1576 (network functions)
   - Add necessary imports
   - Handle state dependencies
   - Test WiFi/API functions

3. **Update code.py**
   - Add imports: `from config import *` and `from network import *`
   - Remove copied sections
   - Test full functionality

4. **Validation**
   - Measure memory at startup (before/after)
   - Run normal cycle (2-4 hours)
   - Run schedule display (2+ hours)
   - Verify 24-hour stability

5. **Monitor**
   - Memory usage trends
   - API call patterns
   - Socket exhaustion issues
   - Any new errors

---

### When NOT to Modularize

Keep monolithic structure if:
- Memory testing shows >200KB import overhead
- Any stability issues during testing
- Performance degradation observed
- Team prefers simpler deployment

**Alternative:** Improve monolith organization:
- Better section markers (you already have some)
- Table of contents at top of file
- Consistent naming conventions
- Enhanced comments/documentation
- Type hints (CircuitPython 9+ supports them)

---

### Modularization Status

**Current:** Monolithic (4117 lines in code.py)
**Planned:** Option 1 (3 files) - pending memory testing
**Future:** Option 2 (5-6 files) - if Option 1 successful

See "Future Enhancements" section for implementation timeline.