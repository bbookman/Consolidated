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
    
    # Extract show name without episode info (split by colon)
    base_title = title.split(':')[0] if ':' in title else title
    
    # Remove anything after "Episode" or "Season" keywords
    episode_keywords = [" Episode ", " Season ", " Chapter ", " Part "]
    for keyword in episode_keywords:
        if keyword.lower() in base_title.lower():
            base_title = base_title.split(keyword, 1)[0]
    
    # Also handle episode indicators with numbers like "- E01" or "S01E01"
    base_title = re.sub(r'\s+-\s+[Ee]\d+.*$', '', base_title)  # Remove "- E01" pattern
    base_title = re.sub(r'\s+[Ss]\d+[Ee]\d+.*$', '', base_title)  # Remove "S01E01" pattern
    
    # Handle special cases before removing all special characters
    # Convert possessive form to regular form (Queen's → Queens)
    base_title = base_title.replace("'s", "s")
    
    # Remove special characters, keeping only alphanumeric and spaces
    cleaned = re.sub(r'[^\w\s]', '', base_title)
    
    # Remove extra spaces and trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Remove "Limited Series" and similar suffixes
    suffixes_to_remove = ["Limited Series", "The Complete Series", "The Series"]
    for suffix in suffixes_to_remove:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-(len(suffix))].strip()
    
    return cleaned

async def test_netflix_imdb_autocomplete():
    """Test the IMDB API autocomplete search with Netflix titles"""
    # Initialize API client
    api = IMDBAPI()
    
    # Read titles from the Netflix viewing history CSV
    netflix_titles = []
    
    # Add some mainstream titles that should be in IMDB
    test_titles = [
        "Stranger Things: Season 4: Chapter One",
        "Breaking Bad: Season 1: Episode 1",
        "The Queen's Gambit: Limited Series: Episode 1",
        "Better Call Saul: Season 6: Episode 13",
        "Better Than Us: Episode 7"
    ]
    
    for test_title in test_titles:
        netflix_titles.append({
            'full_title': test_title,
            'search_term': clean_title(test_title)
        })
        
    # If you want to read from the actual CSV, uncomment below
    # with open('attached_assets/NetflixViewingHistory.csv', 'r', encoding='utf-8') as file:
    #     reader = csv.DictReader(file)
    #     for i, row in enumerate(reader):
    #         if i >= 5:  # Get just the first 5 titles
    #             break
    #         title = row.get('Title', '')
    #         netflix_titles.append({
    #             'full_title': title[1:-1] if title.startswith('"') and title.endswith('"') else title,
    #             'search_term': clean_title(title)
    #         })
    
    print(f"Testing IMDB autocomplete search with {len(netflix_titles)} Netflix titles")
    
    # Test autocomplete search with each title
    for i, title_info in enumerate(netflix_titles, 1):
        search_term = title_info['search_term']
        print(f"\n{i}. Netflix title: {title_info['full_title']}")
        print(f"   Cleaned search term: {search_term}")
        
        # Try autocomplete search first with original cleaned term
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
            
            # Try some variations if the original search failed
            variations = []
            
            # Try without "The" prefix if it exists
            if search_term.startswith("The "):
                variations.append(search_term[4:])
            
            # Try with "The" prefix if it doesn't exist and isn't too long
            if not search_term.startswith("The ") and len(search_term.split()) <= 3:
                variations.append("The " + search_term)
                
            # Try with apostrophe for possessive nouns (Queens → Queen's)
            if "s " in search_term:
                variation = search_term.replace("s ", "'s ")
                variations.append(variation)
                
            # Try with different spacing/punctuation for titles that might have it
            for word in ["and", "&"]:
                if f" {word} " in search_term.lower():
                    variation = search_term.lower().replace(f" {word} ", " ")
                    variations.append(variation.title())
            
            found_match = False
            
            # Try each variation
            for var_idx, variation in enumerate(variations):
                print(f"   Trying variation {var_idx+1}/{len(variations)}: '{variation}'")
                var_results = await api.autocomplete_search(variation, max_results=3)
                
                if "results" in var_results and var_results["results"]:
                    print(f"   ✓ Found {len(var_results['results'])} matching titles in IMDB with variation")
                    
                    # Print the first few results
                    for j, movie in enumerate(var_results["results"][:3], 1):
                        print(f"     {j}. {movie.get('primaryTitle', 'N/A')} ({movie.get('type', 'N/A')}) - {movie.get('id', 'N/A')}")
                    
                    found_match = True
                    break
            
            if not found_match:
                print(f"   ❌ No IMDB matches found for: '{search_term}' or its variations")

if __name__ == "__main__":
    asyncio.run(test_netflix_imdb_autocomplete())