"""
Test script for IMDB API using the exact curl command parameters
"""
import os
import json
import asyncio
import aiohttp

async def test_direct_curl():
    """Test IMDB API using parameters directly from the curl command"""
    api_key = os.environ.get("IMDB_API_KEY")
    if not api_key:
        print("IMDB_API_KEY environment variable not set")
        return
    
    # Construct the URL manually to match the curl command exactly
    url = 'https://imdb236.p.rapidapi.com/imdb/search?type=movie&genre=Drama&rows=25&sortOrder=ASC&sortField=id'
    
    headers = {
        'x-rapidapi-host': 'imdb236.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }
    
    print(f"Making request to {url}")
    print(f"Headers: {headers}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"Status: {status}")
                print(f"Response: {response_text[:200]}...")  # Print the first 200 chars
                
                if status == 200:
                    try:
                        data = json.loads(response_text)
                        print(f"Success! Found {len(data.get('results', []))} results")
                        
                        # Print the first result for debugging
                        if data.get('results') and len(data.get('results')) > 0:
                            first_result = data['results'][0]
                            print(f"\nFirst result: {json.dumps(first_result, indent=2)[:500]}...")
                    except json.JSONDecodeError:
                        print("Failed to parse response as JSON")
    except Exception as e:
        print(f"Error: {str(e)}")

async def test_without_genres():
    """Test IMDB API without the genres parameter"""
    api_key = os.environ.get("IMDB_API_KEY")
    if not api_key:
        print("IMDB_API_KEY environment variable not set")
        return
    
    url = 'https://imdb236.p.rapidapi.com/imdb/search'
    
    # Only use the genre parameter, not genres
    params = {
        'type': 'movie',
        'genre': 'Drama',
        'rows': '25',
        'sortOrder': 'ASC',
        'sortField': 'id'
    }
    
    headers = {
        'x-rapidapi-host': 'imdb236.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }
    
    print("\n\nTesting without genres parameter:")
    print(f"Making request to {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"Status: {status}")
                print(f"Response: {response_text[:200]}...")  # Print the first 200 chars
                
                if status == 200:
                    try:
                        data = json.loads(response_text)
                        print(f"Success! Found {len(data.get('results', []))} results")
                    except json.JSONDecodeError:
                        print("Failed to parse response as JSON")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_direct_curl())
    asyncio.run(test_without_genres())