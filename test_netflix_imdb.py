"""
Test script for importing a few Netflix titles and testing IMDB autocomplete search with them
"""

import asyncio
import csv
import json
import re
from imdb_api import IMDBAPI

def clean_title(title):
    """Remove special characters and normalize the title for better search results"""
    # First, remove quotes if they exist
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1]
    
    # Extract show name without episode info
    base_title = title.split(':')[0] if ':' in title else title
    
    # Remove special characters, keeping only alphanumeric and spaces
    cleaned = re.sub(r'[^\w\s]', '', base_title)
    
    # Remove extra spaces and trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

async def test_netflix_imdb_autocomplete():
    """Test the IMDB API autocomplete search with Netflix titles"""
    # Initialize API client
    api = IMDBAPI()
    
    # Read a few titles from the Netflix viewing history CSV
    netflix_titles = []
    with open('attached_assets/NetflixViewingHistory.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        # Skip the first 10 titles to get different ones
        for i, row in enumerate(reader):
            if i < 10:  # Skip the first 10
                continue
            if len(netflix_titles) >= 5:  # Get just 5 titles
                break
            title = row.get('Title', '')
            
            netflix_titles.append({
                'full_title': title[1:-1] if title.startswith('"') and title.endswith('"') else title,
                'search_term': clean_title(title)
            })
    
    print(f"Testing IMDB autocomplete search with {len(netflix_titles)} Netflix titles")
    
    # Test autocomplete search with each title
    for i, title_info in enumerate(netflix_titles, 1):
        search_term = title_info['search_term']
        print(f"\n{i}. Netflix title: {title_info['full_title']}")
        print(f"   Cleaned search term: {search_term}")
        
        # Try autocomplete search first
        results = await api.autocomplete_search(search_term, max_results=3)
        
        if "error" in results:
            print(f"   ❌ Error performing autocomplete search: {results['error']}")
            continue
        
        if "results" in results and results["results"]:
            print(f"   ✓ Found {len(results['results'])} matching titles in IMDB via autocomplete")
            
            # Print the first few results
            for j, movie in enumerate(results["results"][:3], 1):
                print(f"     {j}. {movie.get('primaryTitle', 'N/A')} ({movie.get('type', 'N/A')}) - {movie.get('id', 'N/A')}")
        else:
            print(f"   ℹ️ No autocomplete matches found for: '{search_term}'")
            print(f"   Trying direct title search instead...")
            
            # If autocomplete fails, try direct title search
            direct_results = await api.search_movies(title=search_term, rows=3)
            
            if "error" in direct_results:
                print(f"   ❌ Error performing direct title search: {direct_results['error']}")
            elif "results" in direct_results and direct_results["results"]:
                print(f"   ✓ Found {len(direct_results['results'])} matching titles in IMDB via direct search")
                
                # Print the first few results
                for j, movie in enumerate(direct_results["results"][:3], 1):
                    print(f"     {j}. {movie.get('primaryTitle', 'N/A')} ({movie.get('type', 'N/A')}) - {movie.get('id', 'N/A')}")
            else:
                print(f"   ❌ No IMDB matches found for: '{search_term}' using either search method")

if __name__ == "__main__":
    asyncio.run(test_netflix_imdb_autocomplete())