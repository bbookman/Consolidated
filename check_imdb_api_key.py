"""
Check IMDB API Key

Simple script to verify if the IMDB API key is configured and working correctly.
"""

import asyncio
import json
import os
from imdb_api import IMDBAPI

async def main():
    """Check if IMDB API key is configured and working."""
    print("Checking IMDB API key...")
    
    # Check if environment variable is set
    api_key = os.environ.get("IMDB_API_KEY")
    if not api_key:
        print("❌ IMDB_API_KEY environment variable is not set.")
        print("Please set the IMDB_API_KEY environment variable with your RapidAPI key.")
        return
    
    print(f"✓ Found IMDB_API_KEY in environment variables")
    
    # Try making a simple API call
    try:
        imdb_api = IMDBAPI(api_key)
        results = await imdb_api.search_movies(genre="Drama", rows=3)
        
        if "error" in results:
            print(f"❌ API call failed: {results['error']}")
            if "details" in results:
                print(f"Details: {results['details']}")
            return
        
        # Check if we got valid response
        if results and isinstance(results, dict) and "results" in results:
            print("✓ Successfully connected to IMDB API")
            print(f"✓ Retrieved {len(results['results'])} results")
            
            # Print first result as example
            if results["results"]:
                first_movie = results["results"][0]
                print("\nExample movie data:")
                print(f"Title: {first_movie.get('primaryTitle', 'N/A')}")
                print(f"ID: {first_movie.get('id', 'N/A')}")
                print(f"Type: {first_movie.get('type', 'N/A')}")
                print(f"Description: {first_movie.get('description', 'N/A')[:100]}...")
        else:
            print("❌ Unexpected API response format")
            print(f"Response: {json.dumps(results, indent=2)}")
    
    except Exception as e:
        print(f"❌ Error testing IMDB API: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())