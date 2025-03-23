"""
OpenWeatherMap API Client

This module provides a client for interacting with the OpenWeatherMap API to retrieve
weather data based on latitude and longitude coordinates.
"""

import os
import aiohttp
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenWeatherAPI:
    """
    Client for interacting with the OpenWeatherMap API
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the OpenWeatherMap API client
        
        Args:
            api_key: API key for OpenWeatherMap. If None, will look for OPENWEATHER_API_KEY env var
        """
        # Use provided API key or get from environment
        self.api_key = api_key or os.environ.get('OPENWEATHER_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is required. Set OPENWEATHER_API_KEY environment variable or pass api_key to constructor.")
        
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.headers = {
            "Accept": "application/json"
        }
    
    async def get_current_weather(self, latitude, longitude, units="metric", max_retries=3, retry_delay=2):
        """
        Get current weather data from OpenWeatherMap API with retry mechanism
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            units: Units of measurement (metric, imperial, or standard)
            max_retries: Maximum number of retry attempts
            retry_delay: Seconds to wait between retries
            
        Returns:
            Dictionary containing weather data
        """
        url = f"{self.base_url}/weather"
        params = {
            "lat": latitude,
            "lon": longitude,
            "units": units,
            "appid": self.api_key
        }
        
        # Initialize empty result
        result = {"weather": None, "error": None}
        
        # Initialize retries counter
        retries = 0
        
        while retries <= max_retries:
            try:
                # Use a longer timeout to handle slow API responses
                timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"Fetching weather data (attempt {retries+1}/{max_retries+1}): {url} for lat={latitude}, lon={longitude}")
                    
                    async with session.get(url, headers=self.headers, params=params) as response:
                        # Check if response is successful
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Error fetching weather data: {response.status} - {error_text}")
                            
                            # Check if this is a retryable error
                            if response.status in [429, 500, 502, 503, 504] and retries < max_retries:
                                retries += 1
                                logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                # Increase delay for next retry (exponential backoff)
                                retry_delay = min(retry_delay * 2, 10)  # Cap at 10 seconds
                                continue
                            else:
                                # Non-retryable error or max retries reached
                                result["error"] = f"API Error: {response.status}"
                                return result
                        
                        # Parse JSON response
                        try:
                            data = await response.json()
                        except Exception as json_error:
                            logger.error(f"Failed to parse JSON response: {str(json_error)}")
                            if retries < max_retries:
                                retries += 1
                                logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay = min(retry_delay * 2, 10)
                                continue
                            else:
                                result["error"] = f"Failed to parse JSON: {str(json_error)}"
                                return result
                        
                        logger.info(f"Weather API response data type: {type(data)}")
                        
                        # Log response structure for debugging
                        if isinstance(data, dict):
                            logger.info(f"Response keys: {list(data.keys())}")
                            logger.info(f"Raw response snippet: {str(data)[:300]}...")
                        
                        # Successfully retrieved and processed data
                        result["weather"] = data
                        logger.info(f"Successfully retrieved weather data for lat={latitude}, lon={longitude}")
                        return result
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching weather data (attempt {retries+1}/{max_retries+1})")
                if retries < max_retries:
                    retries += 1
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 10)
                else:
                    result["error"] = "Timeout error after multiple retries"
                    return result
                    
            except Exception as e:
                logger.error(f"Exception while fetching weather data: {str(e)}")
                if retries < max_retries:
                    retries += 1
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 10)
                else:
                    result["error"] = f"Exception: {str(e)}"
                    return result

# Create a singleton instance if API key is available,
# otherwise set to None and initialize later
try:
    openweather = OpenWeatherAPI()
    logger.info("OpenWeatherMap API client initialized successfully")
except ValueError:
    openweather = None
    logger.warning("OpenWeatherMap API client not initialized - API key not found. Will attempt to initialize later if key is provided.")