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
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Convert to expected format with pagination info
                        return {
                            "lifelogs": data.get("data", []),
                            "page": page,
                            "perPage": limit,
                            "totalItems": data.get("meta", {}).get("total", 0),
                            "totalPages": data.get("meta", {}).get("last_page", 1)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Error fetching lifelogs: {response.status} - {error_text}")
                        return {"lifelogs": [], "error": f"API Error: {response.status}"}
        except Exception as e:
            logger.error(f"Exception while fetching lifelogs: {str(e)}")
            return {"lifelogs": [], "error": f"Exception: {str(e)}"}

# Create a singleton instance if API key is available,
# otherwise set to None and initialize later
try:
    limitless = LimitlessAPI()
except ValueError:
    limitless = None
    logger.warning("Limitless API client not initialized - API key not found. Will attempt to initialize later if key is provided.")