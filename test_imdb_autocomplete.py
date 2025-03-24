"""
Test script for IMDB API autocomplete search functionality
"""

import asyncio
import json
from imdb_api import IMDBAPI

async def test_autocomplete_search():
    """Test the IMDB API autocomplete search functionality"""
    print("Testing IMDB API autocomplete search...")
    
    # Initialize API client
    api = IMDBAPI()
    
    # Test with a query that should return results
    query = "Incept"
    print(f"Searching for titles that match: '{query}'")
    
    results = await api.autocomplete_search(query, max_results=5)
    
    if "error" in results:
        print(f"❌ Error performing autocomplete search: {results['error']}")
        if "details" in results:
            print(f"Details: {results['details']}")
        return
    
    if "results" in results and results["results"]:
        print(f"✓ Autocomplete search successful")
        print(f"✓ Found {len(results['results'])} matching titles")
        
        # Print the first few results
        print("\nTop matches:")
        for i, movie in enumerate(results["results"][:5], 1):
            print(f"{i}. {movie.get('primaryTitle', 'N/A')} ({movie.get('type', 'N/A')}) - {movie.get('id', 'N/A')}")
            print(f"   Description: {movie.get('description', 'N/A')[:100]}..." if movie.get('description') else "   No description available")
            print()
    else:
        print(f"❌ No results found for query: '{query}'")
        print(f"Response: {json.dumps(results, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_autocomplete_search())