"""
Test script for importing a few Netflix titles and testing IMDB autocomplete search with them
"""

import asyncio
import csv
import json
from imdb_api import IMDBAPI

async def test_netflix_imdb_autocomplete():
    """Test the IMDB API autocomplete search with Netflix titles"""
    # Initialize API client
    api = IMDBAPI()
    
    # Read a few titles from the Netflix viewing history CSV
    netflix_titles = []
    with open('attached_assets/NetflixViewingHistory.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            if i >= 5:  # Get just the first 5 titles
                break
            title = row.get('Title', '')
            # Remove quotes if they exist
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            
            # Extract show name without episode info
            show_name = title.split(':')[0] if ':' in title else title
            netflix_titles.append({
                'full_title': title,
                'search_term': show_name.strip()
            })
    
    print(f"Testing IMDB autocomplete search with {len(netflix_titles)} Netflix titles")
    
    # Test autocomplete search with each title
    for i, title_info in enumerate(netflix_titles, 1):
        search_term = title_info['search_term']
        print(f"\n{i}. Netflix title: {title_info['full_title']}")
        print(f"   Search term: {search_term}")
        
        results = await api.autocomplete_search(search_term, max_results=3)
        
        if "error" in results:
            print(f"   ❌ Error performing autocomplete search: {results['error']}")
            continue
        
        if "results" in results and results["results"]:
            print(f"   ✓ Found {len(results['results'])} matching titles in IMDB")
            
            # Print the first few results
            for j, movie in enumerate(results["results"][:3], 1):
                print(f"     {j}. {movie.get('primaryTitle', 'N/A')} ({movie.get('type', 'N/A')}) - {movie.get('id', 'N/A')}")
        else:
            print(f"   ❌ No IMDB matches found for: '{search_term}'")

if __name__ == "__main__":
    asyncio.run(test_netflix_imdb_autocomplete())