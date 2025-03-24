#!/usr/bin/env python3
"""
One-time script to remove duplicate Netflix series entries from the database.

This script identifies all series in the Netflix viewing history database and ensures
that only the earliest-watched episode of each series is kept, removing any duplicates.
This is useful for cleaning up existing databases where series may have been imported
across multiple import operations.
"""

import os
import sys
import logging
import json
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session

from models import Netflix_History_Item, Base
from netflix_importer import extract_series_name, is_series_episode

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def remove_duplicate_netflix_series():
    """
    Identify all series in the database and remove duplicate episodes,
    keeping only the earliest-watched episode of each series.
    
    Returns:
        Dictionary with counts of total series found, entries removed, and entries kept
    """
    # Create database session
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        return {"error": "DATABASE_URL not set"}
    
    engine = create_engine(DATABASE_URL)
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    
    result = {
        "total_series": 0,
        "total_entries": 0,
        "entries_kept": 0,
        "entries_removed": 0
    }
    
    try:
        # Get all Netflix history items
        all_items = session.query(Netflix_History_Item).all()
        result["total_entries"] = len(all_items)
        
        # Group items by series name
        series_groups = {}
        for item in all_items:
            if is_series_episode(item.title):
                series_name = extract_series_name(item.title)
                if series_name not in series_groups:
                    series_groups[series_name] = []
                series_groups[series_name].append(item)
        
        result["total_series"] = len(series_groups)
        logger.info(f"Found {len(series_groups)} unique series with a total of {len(all_items)} entries")
        
        # Process each series group
        for series_name, episodes in series_groups.items():
            if len(episodes) <= 1:
                # Only one episode for this series, nothing to deduplicate
                result["entries_kept"] += 1
                continue
            
            # Sort by watch date (oldest first)
            episodes.sort(key=lambda x: x.watch_date if x.watch_date else datetime.max)
            
            # Keep the first (earliest) episode
            keep_episode = episodes[0]
            result["entries_kept"] += 1
            
            # Remove all other episodes
            for episode in episodes[1:]:
                logger.info(f"Removing duplicate series episode: {episode.title} (watch_date: {episode.watch_date})")
                session.delete(episode)
                result["entries_removed"] += 1
        
        # Commit changes
        if result["entries_removed"] > 0:
            session.commit()
            logger.info(f"Successfully removed {result['entries_removed']} duplicate series episodes")
        else:
            logger.info("No duplicate series episodes found")
            
        return result
    
    except Exception as e:
        logger.error(f"Error removing duplicate Netflix series: {str(e)}")
        session.rollback()
        return {"error": str(e)}
    
    finally:
        session.close()

def main():
    """Main function."""
    print("Removing duplicate Netflix series entries from the database...")
    result = remove_duplicate_netflix_series()
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    
    print(f"\nResults:")
    print(f"- Found {result['total_series']} unique series with {result['total_entries']} total entries")
    print(f"- Kept {result['entries_kept']} entries (one per series)")
    print(f"- Removed {result['entries_removed']} duplicate entries")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())