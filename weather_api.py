"""
Pantallita 3.0 - Weather API Module
Fetch current weather from AccuWeather with inline parsing
"""

import time

import config
import state
import logger

# ============================================================================
# WEATHER FETCHING
# ============================================================================

def fetch_current():
    """
    Fetch current weather from AccuWeather.
    Uses cache if recent data available.
    Returns: {temp, feels_like, feels_shade, uv, humidity, icon, condition}
    """

    # Check cache first
    if state.last_weather_data and state.last_weather_time > 0:
        age = time.monotonic() - state.last_weather_time
        if age < config.Timing.WEATHER_CACHE_MAX_AGE:
            logger.log(f"Using cached weather data (age: {int(age)}s)", config.LogLevel.DEBUG)
            return state.last_weather_data

    # Check if we have API credentials
    if not config.Env.ACCUWEATHER_KEY or not config.Env.ACCUWEATHER_LOCATION:
        logger.log("AccuWeather credentials not configured", config.LogLevel.ERROR)
        return None

    if not state.session:
        logger.log("No network session available", config.LogLevel.ERROR)
        return None

    logger.log("Fetching weather from AccuWeather...")

    response = None
    try:
        # Build API URL
        endpoint = config.API.ACCUWEATHER_CURRENT.format(
            location=config.Env.ACCUWEATHER_LOCATION
        )
        url = config.API.ACCUWEATHER_BASE + endpoint

        # Determine temperature unit (Metric or Imperial)
        if config.Env.TEMPERATURE_UNIT == "C":
            temp_unit = "Metric"
        else:
            temp_unit = "Imperial"

        # Add API key to URL
        url += f"&apikey={config.Env.ACCUWEATHER_KEY}"

        logger.log(f"Fetching from: {url[:60]}...", config.LogLevel.DEBUG)

        # Fetch weather data
        response = state.session.get(url, timeout=10)

        if response.status_code != 200:
            logger.log(f"AccuWeather API returned {response.status_code}", config.LogLevel.ERROR)
            state.weather_fetch_errors += 1
            return state.last_weather_data  # Return cached data if available

        # Parse JSON response (inline - no helper function)
        data = response.json()

        # AccuWeather returns array with single element
        if not data or len(data) == 0:
            logger.log("Empty response from AccuWeather", config.LogLevel.ERROR)
            state.weather_fetch_errors += 1
            return state.last_weather_data

        weather = data[0]

        # Extract temperature in correct unit (inline parsing)
        temp = weather.get("Temperature", {}).get(temp_unit, {}).get("Value")
        if temp is None:
            logger.log("Temperature not found in response", config.LogLevel.ERROR)
            state.weather_fetch_errors += 1
            return state.last_weather_data

        # Extract feels like temperature
        feels_like = weather.get("RealFeelTemperature", {}).get(temp_unit, {}).get("Value")
        if feels_like is None:
            feels_like = temp  # Fallback to actual temp

        # Extract feels like shade temperature
        feels_shade = weather.get("RealFeelTemperatureShade", {}).get(temp_unit, {}).get("Value")
        if feels_shade is None:
            feels_shade = feels_like  # Fallback to feels like

        # Extract UV index (0-11+)
        uv_index = weather.get("UVIndex", 0)

        # Extract humidity (0-100)
        humidity = weather.get("RelativeHumidity", 0)

        # Extract weather icon number (1-44)
        icon = weather.get("WeatherIcon", 1)

        # Extract condition text
        condition = weather.get("WeatherText", "")

        # Convert to integers (inline - no helper)
        temp = int(temp)
        feels_like = int(feels_like)
        feels_shade = int(feels_shade)
        uv_index = int(uv_index)
        humidity = int(humidity)
        icon = int(icon)
        condition = str(condition)

        # Build weather data dictionary
        weather_data = {
            "temp": temp,
            "feels_like": feels_like,
            "feels_shade": feels_shade,
            "uv": uv_index,
            "humidity": humidity,
            "icon": icon,
            "condition": condition
        }

        logger.log_weather(condition, temp, unit)

        # Update cache
        state.last_weather_data = weather_data
        state.last_weather_time = time.monotonic()
        state.weather_fetch_count += 1

        return weather_data

    except Exception as e:
        logger.log(f"Weather fetch failed: {e}", config.LogLevel.ERROR)
        state.weather_fetch_errors += 1
        return state.last_weather_data  # Return cached data if available

    finally:
        # CRITICAL: Always close response to prevent socket exhaustion
        if response:
            try:
                response.close()
            except:
                pass

# ============================================================================
# NOTES
# ============================================================================
"""
AccuWeather Current Conditions API Response Structure:

[
    {
        "LocalObservationDateTime": "2025-12-12T10:15:00-06:00",
        "EpochTime": 1734019500,
        "WeatherText": "Mostly cloudy",
        "WeatherIcon": 6,
        "HasPrecipitation": false,
        "Temperature": {
            "Metric": {"Value": 25.0, "Unit": "C"},
            "Imperial": {"Value": 77.0, "Unit": "F"}
        },
        "RealFeelTemperature": {
            "Metric": {"Value": 28.3, "Unit": "C"},
            "Imperial": {"Value": 83.0, "Unit": "F"}
        },
        "RealFeelTemperatureShade": {
            "Metric": {"Value": 25.6, "Unit": "C"},
            "Imperial": {"Value": 78.0, "Unit": "F"}
        },
        "RelativeHumidity": 65,
        "UVIndex": 7,
        "Visibility": {
            "Metric": {"Value": 16.1, "Unit": "km"},
            "Imperial": {"Value": 10.0, "Unit": "mi"}
        },
        "CloudCover": 75,
        ...
    }
]

Temperature Unit Selection:
- config.Env.TEMPERATURE_UNIT = "C" → Use "Metric"
- config.Env.TEMPERATURE_UNIT = "F" → Use "Imperial"

This way we fetch temperature in the correct unit directly from API,
no conversion needed!

Cache Strategy:
- Cache max age: 15 minutes (900 seconds)
- On API failure: Return cached data if available
- On first run: Cache will be None, display clock fallback

Stack Depth:
Level 0: main() in code.py
Level 1: run_test_cycle() in code.py
Level 2: fetch_current() in this module [WE ARE HERE]
Level 3: None - everything inline!

Total: 2 levels
"""
