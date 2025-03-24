"""
Test script for Netflix enrichment with IMDB data

This script tests the enrichment of Netflix viewing history with IMDB data.
It first imports a sample Netflix viewing history file, then enriches the data using the IMDB API.
"""

import os
import asyncio
import logging
from netflix_importer import import_netflix_history, enrich_netflix_title_data, save_netflix_history_to_json
from database_handler import get_netflix_history_from_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Test Netflix enrichment process"""
    # Step 1: Check if we have a CSV file to import
    csv_file = 'attached_assets/NetflixViewingHistory.csv'
    
    if os.path.exists(csv_file):
        logger.info(f"Found Netflix viewing history CSV at {csv_file}")
        
        # Create a smaller sample file with just 10 titles for testing
        sample_file = 'attached_assets/NetflixViewingHistory_sample.csv'
        with open(csv_file, 'r', encoding='utf-8') as infile:
            with open(sample_file, 'w', encoding='utf-8') as outfile:
                # Copy header and first 10 data rows
                for i, line in enumerate(infile):
                    if i <= 10:  # Header + 10 titles
                        outfile.write(line)
        
        logger.info(f"Created sample file with 10 titles at {sample_file}")
        
        # Import the sample data
        import_result = import_netflix_history(sample_file)
        logger.info(f"Import result: {import_result['processed']} processed, "
                   f"{import_result['added']} added, "
                   f"{import_result['skipped']} skipped")
    else:
        logger.warning(f"Netflix viewing history CSV not found at {csv_file}")
        logger.info("Checking if there's existing Netflix data in the database...")
        
        # Get existing data from the database
        history_items = get_netflix_history_from_db(limit=10)
        if history_items:
            logger.info(f"Found {len(history_items)} existing Netflix history items in the database")
        else:
            logger.error("No Netflix data available. Please import a Netflix viewing history CSV first")
            return
    
    # Step 2: Enrich the data (process max 5 titles to avoid rate limiting)
    logger.info("Starting Netflix title enrichment...")
    enrich_result = await enrich_netflix_title_data(limit=5)
    
    logger.info(f"Enrichment result: {enrich_result['processed']} processed, "
               f"{enrich_result['enriched']} enriched, "
               f"{enrich_result['skipped']} skipped")
    
    # Step 3: Save the enriched data to JSON if debug mode is enabled
    logger.info("Saving enriched Netflix history to JSON (debug mode)...")
    json_path = save_netflix_history_to_json()
    
    if json_path:
        logger.info(f"Saved enriched Netflix history to {json_path}")
    else:
        logger.warning("Failed to save Netflix history to JSON (probably debug mode is disabled)")
    
    # Print a summary of the process
    print("\nNetflix IMDB Enrichment Test Summary:")
    print(f"- Processed: {enrich_result['processed']} titles")
    print(f"- Successfully enriched: {enrich_result['enriched']} titles")
    print(f"- Skipped: {enrich_result['skipped']} titles")
    
    # Get most recent items with content_type populated (indicates IMDB enrichment)
    enriched_items = get_netflix_history_from_db(limit=10)
    if enriched_items:
        print("\nSample of enriched Netflix titles:")
        for i, item in enumerate(enriched_items, 1):
            if item.content_type:  # Show only enriched items
                print(f"{i}. {item.title}")
                print(f"   Type: {item.content_type}, Year: {item.release_year or 'Unknown'}")
                if item.show_name:
                    print(f"   Show: {item.show_name}")
                    if item.season:
                        print(f"   Season: {item.season}")
                    if item.episode_name:
                        print(f"   Episode: {item.episode_name}")
                print()

if __name__ == "__main__":
    asyncio.run(main())