"""
IMDB API Client

This module provides a client for interacting with the IMDB API via RapidAPI to retrieve
movie and TV show data based on search criteria.
"""

import os
import json
import logging
import aiohttp
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IMDBAPI:
    """
    Client for interacting with the IMDB API via RapidAPI
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the IMDB API client
        
        Args:
            api_key: API key for IMDB API on RapidAPI. 
                    If None, will look for IMDB_API_KEY env var
        """
        self.api_key = api_key or os.environ.get("IMDB_API_KEY")
        self.api_host = "imdb236.p.rapidapi.com"
        self.base_url = "https://imdb236.p.rapidapi.com/imdb"
        
        if not self.api_key:
            logger.warning("No IMDB API key provided. Set IMDB_API_KEY environment variable.")
        else:
            logger.info("IMDB API client initialized with key.")
    
    async def search_movies(self, genre=None, rows=25, sort_order="ASC", sort_field="id", max_retries=3, retry_delay=2):
        """
        Search for movies in the IMDB database with retry mechanism
        
        Args:
            genre: Optional genre to filter by (e.g., "Drama", "Comedy", etc.)
            rows: Number of results to return (default: 25)
            sort_order: Sort order (ASC or DESC)
            sort_field: Field to sort by (e.g., "id", "title", etc.)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Seconds to wait between retries (default: 2)
            
        Returns:
            Dictionary containing search results or error message
        """
        if not self.api_key:
            return {"error": "No API key provided. Set IMDB_API_KEY environment variable."}
        
        headers = {
            "x-rapidapi-host": self.api_host,
            "x-rapidapi-key": self.api_key
        }
        
        # Build query parameters
        params = {
            "type": "movie",
            "rows": rows,
            "sortOrder": sort_order,
            "sortField": sort_field
        }
        
        # Add genre if provided
        if genre:
            params["genre"] = genre
            # Don't add 'genres' parameter as it causes issues with this API
        
        url = f"{self.base_url}/search"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching IMDB data (attempt {attempt+1}/{max_retries+1}): {url} with params {params}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"Successfully retrieved IMDB data")
                            return data
                        else:
                            error_text = await response.text()
                            logger.error(f"Error fetching IMDB data: HTTP {response.status}, {error_text}")
                            return {"error": f"API error: {response.status}", "details": error_text}
            
            except Exception as e:
                logger.error(f"Exception while fetching IMDB data: {str(e)}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Max retries exceeded")
                    return {"error": f"Failed to fetch IMDB data after {max_retries+1} attempts", "details": str(e)}
        
        return {"error": "Failed to fetch IMDB data (unknown error)"}

async def main():
    """Simple test function to verify the IMDB API client"""
    api = IMDBAPI()
    results = await api.search_movies(genre="Drama")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())