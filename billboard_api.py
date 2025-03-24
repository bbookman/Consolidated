"""
Billboard Charts API Client

This module provides a client for interacting with the Billboard Charts API to retrieve
chart data for various Billboard charts, including Hot 100, Billboard 200, etc.
"""

import os
import json
import logging
import aiohttp
import asyncio
import traceback
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class BillboardAPI:
    """
    Client for interacting with the Billboard Charts API via RapidAPI
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the Billboard API client
        
        Args:
            api_key: API key for Billboard Charts API on RapidAPI. 
                    If None, will look for BILLBOARD_API_KEY env var
        """
        self.api_key = api_key or os.environ.get('BILLBOARD_API_KEY')
        if not self.api_key:
            logger.warning("No Billboard API key provided or found in environment variables")
            
        self.base_url = "https://billboard-charts-api.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Host": "billboard-charts-api.p.rapidapi.com",
            "X-RapidAPI-Key": self.api_key
        }
        
    async def get_chart(self, chart_name="hot-100", date=None, max_retries=3, retry_delay=2):
        """
        Get Billboard chart data with retry mechanism
        
        Args:
            chart_name: Name of the chart to retrieve (hot-100, billboard-200, etc.)
            date: Optional date string in format YYYY-MM-DD to get historical chart
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Seconds to wait between retries (default: 2)
            
        Returns:
            Dictionary containing chart data or error message
        """
        if not self.api_key:
            return {"error": "Billboard API key not set"}
            
        # Construct the URL
        url = f"{self.base_url}/{chart_name}.php"
        
        # Add date parameter if provided
        params = {}
        if date:
            params["date"] = date
            
        logger.info(f"Fetching chart data (attempt 1/{max_retries+1}): {url} for chart {chart_name}")
        
        # Attempt the request with retries
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, params=params, timeout=30) as response:
                        # Check for successful response
                        if response.status == 200:
                            # Parse the response as JSON
                            data = await response.json()
                            logger.info(f"Billboard API response data type: {type(data)}")
                            
                            # Log a snippet of the response for debugging
                            if isinstance(data, dict):
                                logger.info(f"Response keys: {list(data.keys())}")
                                raw_snippet = str(data)[:500] + "..." if len(str(data)) > 500 else str(data)
                                logger.info(f"Raw response snippet: {raw_snippet}")
                                
                            logger.info(f"Successfully retrieved chart data for {chart_name}")
                            
                            # Format the response to match our expected structure
                            # Response typically has: title, info, week, songs
                            
                            # Parse the date from the week string if possible
                            date = None
                            if 'week' in data:
                                week_str = data.get('week', '')
                                if week_str.startswith('Week of '):
                                    date_part = week_str[8:].strip()
                                    try:
                                        # Convert "March 22, 2025" to "2025-03-22"
                                        parsed_date = datetime.strptime(date_part, '%B %d, %Y')
                                        date = parsed_date.strftime('%Y-%m-%d')
                                    except:
                                        date = datetime.utcnow().strftime('%Y-%m-%d')
                            
                            # Default to current date if parsing failed
                            if not date:
                                date = datetime.utcnow().strftime('%Y-%m-%d')
                                
                            # Format songs to match our expected entries structure
                            entries = []
                            if 'songs' in data and isinstance(data['songs'], list):
                                for song in data['songs']:
                                    entry = {
                                        'rank': song.get('position'),
                                        'title': song.get('name', 'Unknown Title'),
                                        'artist': song.get('artist', 'Unknown Artist'),
                                        'image': song.get('image'),
                                        'last_week': song.get('last_week_position'),
                                        'peak_position': song.get('peak_position'),
                                        'weeks_on_chart': song.get('weeks_on_chart')
                                    }
                                    entries.append(entry)
                            
                            # Add timestamp for when this data was retrieved
                            result = {
                                "chart": {
                                    "name": chart_name,
                                    "date": date,
                                    "title": data.get('title', f'Billboard {chart_name.upper()}'),
                                    "info": data.get('info', ''),
                                    "entries": entries
                                },
                                "timestamp": datetime.utcnow().isoformat(),
                                "chart_name": chart_name
                            }
                            
                            return result
                        else:
                            # Handle error responses
                            error_text = await response.text()
                            logger.warning(f"Error response from Billboard API: {response.status}, {error_text}")
                            
                            if attempt < max_retries:
                                logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+2}/{max_retries+1})")
                                await asyncio.sleep(retry_delay)
                            else:
                                return {
                                    "error": f"Failed to fetch data after {max_retries+1} attempts. Status: {response.status}",
                                    "status_code": response.status,
                                    "response": error_text
                                }
                                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout error on attempt {attempt+1}/{max_retries+1}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds")
                    await asyncio.sleep(retry_delay)
                else:
                    return {"error": "Timeout error after multiple retries"}
                    
            except Exception as e:
                logger.error(f"Error fetching chart data: {str(e)}")
                logger.error(traceback.format_exc())
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt+2}/{max_retries+1})")
                    await asyncio.sleep(retry_delay)
                else:
                    return {"error": f"Error fetching chart data: {str(e)}"}
                    
    async def get_hot_100(self, date=None):
        """
        Get Billboard Hot 100 chart data
        
        Args:
            date: Optional date string in format YYYY-MM-DD
            
        Returns:
            Dictionary containing Hot 100 chart data
        """
        return await self.get_chart("hot-100", date)
        
# Note: Billboard 200 chart endpoint is not available from this API provider