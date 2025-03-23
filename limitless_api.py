import os
import aiohttp
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class LimitlessAPI:
    """
    Client for interacting with the Limitless.ai API
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the Limitless API client
        
        Args:
            api_key: API key for Limitless.ai. If None, will look for LIMITLESS_API_KEY env var
        """
        self.api_key = api_key or os.environ.get('LIMITLESS_API_KEY')
        if not self.api_key:
            raise ValueError("Limitless API key is not provided and LIMITLESS_API_KEY environment variable is not set")
            
        self.base_url = "https://api.limitless.ai/v1"
        self.headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }
        
    async def get_lifelogs(self, page=1, limit=100, max_retries=3, retry_delay=2):
        """
        Get lifelogs from the Limitless API with retry mechanism
        
        Args:
            page: Page number to retrieve
            limit: Number of items per page
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Seconds to wait between retries (default: 2)
            
        Returns:
            Dictionary containing lifelogs and pagination info
        """
        url = f"{self.base_url}/lifelogs"
        params = {
            "page": page,
            "limit": limit
        }
        
        # Initialize empty result
        result = {"lifelogs": [], "page": page, "perPage": limit, "totalItems": 0, "totalPages": 1}
        
        # Initialize retries counter
        retries = 0
        
        while retries <= max_retries:
            try:
                # Use a longer timeout to handle slow API responses
                timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"Fetching lifelogs (attempt {retries+1}/{max_retries+1}): {url} with params {params}")
                    
                    async with session.get(url, headers=self.headers, params=params) as response:
                        # Check if response is successful
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Error fetching lifelogs: {response.status} - {error_text}")
                            
                            # Check if this is a retryable error (e.g., 429, 500, 502, 503, 504)
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
                            text_response = await response.text()
                            logger.error(f"Raw response: {text_response[:500]}...")
                            if retries < max_retries:
                                retries += 1
                                logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay = min(retry_delay * 2, 10)
                                continue
                            else:
                                result["error"] = f"Failed to parse JSON: {str(json_error)}"
                                return result
                        
                        logger.info(f"Limitless API response data type: {type(data)}")
                        
                        # Log response structure for debugging
                        if isinstance(data, dict):
                            logger.info(f"Response keys: {list(data.keys())}")
                            logger.info(f"Raw response snippet: {str(data)[:300]}...")
                        
                        # Extract lifelogs from response
                        lifelogs = []
                        
                        # Handle different response formats
                        if isinstance(data, dict) and "data" in data:
                            data_field = data["data"]
                            
                            # Format 1: data.data.lifelogs array
                            if isinstance(data_field, dict) and "lifelogs" in data_field and isinstance(data_field["lifelogs"], list):
                                lifelogs = data_field["lifelogs"]
                                logger.info(f"Found {len(lifelogs)} lifelogs in data.data.lifelogs format")
                            
                            # Format 2: data.data is a list of lifelogs
                            elif isinstance(data_field, list):
                                lifelogs = data_field
                                logger.info(f"Found {len(lifelogs)} lifelogs in data.data list format")
                            
                            # Format 3: data.data is a single lifelog object
                            elif isinstance(data_field, dict) and "contents" in data_field:
                                lifelogs = [data_field]
                                logger.info("Found single lifelog object")
                        # Format 4: Direct array of lifelogs
                        elif isinstance(data, list):
                            lifelogs = data
                            logger.info(f"Found {len(lifelogs)} lifelogs in direct list format")
                        
                        # Log sample data if available
                        if lifelogs and len(lifelogs) > 0:
                            if isinstance(lifelogs[0], dict):
                                logger.info(f"Sample lifelog: {str(lifelogs[0])[:200]}...")
                        
                        # Update result with found lifelogs
                        if lifelogs:
                            result["lifelogs"] = lifelogs
                            result["totalItems"] = data.get("meta", {}).get("total", len(lifelogs)) if isinstance(data, dict) else len(lifelogs)
                            result["totalPages"] = data.get("meta", {}).get("last_page", 1) if isinstance(data, dict) else 1
                        else:
                            logger.warning(f"No lifelogs found in response: {str(data)[:200]}")
                            result["error"] = "No lifelogs found in response"
                        
                        # Successfully retrieved and processed data
                        return result
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching lifelogs (attempt {retries+1}/{max_retries+1})")
                if retries < max_retries:
                    retries += 1
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 10)
                else:
                    result["error"] = "Timeout error after multiple retries"
                    return result
                    
            except Exception as e:
                logger.error(f"Exception while fetching lifelogs: {str(e)}")
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
    limitless = LimitlessAPI()
except ValueError:
    limitless = None
    logger.warning("Limitless API client not initialized - API key not found. Will attempt to initialize later if key is provided.")