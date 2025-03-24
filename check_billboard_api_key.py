"""
Check Billboard API Key

Simple script to verify if the Billboard API key is configured and working correctly.
"""

import asyncio
import os
import sys
from billboard_api import BillboardAPI

async def main():
    """Check if Billboard API key is configured and working."""
    api_key = os.environ.get('BILLBOARD_API_KEY')
    
    if not api_key:
        print("ERROR: Billboard API key not found in environment variables")
        print("Please set the BILLBOARD_API_KEY environment variable")
        sys.exit(1)
        
    # Test with a simple API call
    print(f"Testing Billboard API key: {api_key[:5]}...{api_key[-5:]}")
    
    billboard_api = BillboardAPI(api_key)
    result = await billboard_api.get_hot_100()
    
    if "error" in result:
        print(f"ERROR: API key test failed - {result['error']}")
        sys.exit(1)
    else:
        print("SUCCESS: Billboard API key is valid and working correctly")
        
        # Show first few chart items
        chart_data = result.get("chart", {})
        entries = chart_data.get("entries", [])
        
        if entries and len(entries) > 0:
            print("\nHot 100 Chart (Top 3):")
            for i, entry in enumerate(entries[:3]):
                print(f"{i+1}. {entry.get('title', 'Unknown')} - {entry.get('artist', 'Unknown')}")
        
if __name__ == "__main__":
    asyncio.run(main())