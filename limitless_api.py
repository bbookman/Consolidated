import os
import aiohttp
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
        
    async def get_lifelogs(self, page=1, limit=100):
        """
        Get lifelogs from the Limitless API
        
        Args:
            page: Page number to retrieve
            limit: Number of items per page
            
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
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    # Check if response is successful
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error fetching lifelogs: {response.status} - {error_text}")
                        result["error"] = f"API Error: {response.status}"
                        return result
                    
                    # Parse JSON response
                    data = await response.json()
                    logger.info(f"Limitless API response data type: {type(data)}")
                    
                    # Log response structure for debugging
                    if isinstance(data, dict):
                        logger.info(f"Response keys: {data.keys()}")
                        logger.info(f"Raw response snippet: {json.dumps(data)[:300]}...")
                    
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
                    
                    # Log sample data if available
                    if lifelogs and len(lifelogs) > 0:
                        if isinstance(lifelogs[0], dict):
                            logger.info(f"Sample lifelog: {json.dumps(lifelogs[0])[:200]}...")
                    
                    # Update result with found lifelogs
                    if lifelogs:
                        result["lifelogs"] = lifelogs
                        result["totalItems"] = data.get("meta", {}).get("total", len(lifelogs))
                        result["totalPages"] = data.get("meta", {}).get("last_page", 1)
                    else:
                        logger.warning(f"No lifelogs found in response: {str(data)[:200]}")
                        result["error"] = "No lifelogs found in response"
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Exception while fetching lifelogs: {str(e)}")
            result["error"] = f"Exception: {str(e)}"
            return result

# Create a singleton instance if API key is available,
# otherwise set to None and initialize later
try:
    limitless = LimitlessAPI()
except ValueError:
    limitless = None
    logger.warning("Limitless API client not initialized - API key not found. Will attempt to initialize later if key is provided.")