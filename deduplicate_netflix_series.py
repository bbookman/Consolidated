#!/usr/bin/env python3
"""
One-time script to deduplicate Netflix series in the database.
This script will identify series with multiple episodes and keep only the first episode,
removing all other episodes of the same series.
"""

import re
import logging
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from models import Netflix_History_Item, Netflix_Title_Info, Base
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_series_name(title):
    """
    Extract the base series name from a title with episode information.
    
    Args:
        title: Original Netflix title with episode information
        
    Returns:
        Base series name without episode/season information
    """
    # Remove episode indicators
    base_title = title
    
    # Try to extract series name before episode indicators
    episode_keywords = [" Episode ", " Season ", " Chapter ", " Part "]
    for keyword in episode_keywords:
        if keyword.lower() in base_title.lower():
            base_title = base_title.split(keyword, 1)[0]
            break
    
    # Also handle format like "Series_Name: Season X: Episode Y"
    if ":" in base_title:
        base_title = base_title.split(":", 1)[0]
    
    # Handle "Limited Series" indicator
    if "Limited Series" in base_title:
        base_title = base_title.replace("Limited Series", "").strip()
    
    return base_title.strip()

def deduplicate_netflix_series():
    """
    Identify series with multiple episodes and keep only one episode per series.
    """
    # Get database URL from environment variables
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Create SQLAlchemy engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # First, get all titles that look like TV series episodes
        series_pattern = "%Episode% OR title LIKE %Season% OR title LIKE %Chapter%"
        series_titles = session.query(Netflix_History_Item.title).filter(
            Netflix_History_Item.title.like("%Episode%") | 
            Netflix_History_Item.title.like("%Season%") | 
            Netflix_History_Item.title.like("%Chapter%")
        ).all()
        
        # Extract unique series names
        series_map = {}
        for title_tuple in series_titles:
            title = title_tuple[0]
            series_name = extract_series_name(title)
            
            if series_name not in series_map:
                series_map[series_name] = []
            
            series_map[series_name].append(title)
        
        # For each series, keep only the oldest episode and delete the rest
        deleted_count = 0
        kept_count = 0
        
        for series_name, episodes in series_map.items():
            if len(episodes) <= 1:
                # Only one episode, nothing to deduplicate
                logger.info(f"Series '{series_name}' has only one episode, skipping.")
                kept_count += 1
                continue
            
            # Get all episodes with their watch dates
            episode_data = session.query(
                Netflix_History_Item.id, 
                Netflix_History_Item.title,
                Netflix_History_Item.watch_date
            ).filter(
                Netflix_History_Item.title.in_(episodes)
            ).order_by(
                Netflix_History_Item.watch_date
            ).all()
            
            # Keep the oldest episode (first watched)
            if not episode_data:
                logger.warning(f"No episodes found for series '{series_name}'")
                continue
            
            # Keep the first (oldest) episode
            to_keep = episode_data[0]
            kept_count += 1
            logger.info(f"Keeping episode: {to_keep.title} (watched on {to_keep.watch_date})")
            
            # Delete all other episodes
            for episode in episode_data[1:]:
                logger.info(f"Deleting episode: {episode.title} (watched on {episode.watch_date})")
                session.query(Netflix_History_Item).filter(
                    Netflix_History_Item.id == episode.id
                ).delete()
                deleted_count += 1
                
                # Also delete from Netflix_Title_Info if it exists
                title_info = session.query(Netflix_Title_Info).filter(
                    Netflix_Title_Info.title == episode.title
                ).first()
                
                if title_info:
                    session.delete(title_info)
                    logger.info(f"Deleted title info for: {episode.title}")
        
        # Commit the changes
        session.commit()
        logger.info(f"Deduplication complete: {kept_count} episodes kept, {deleted_count} episodes deleted")
        
    except Exception as e:
        logger.error(f"Error deduplicating Netflix series: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def main():
    """Main function."""
    logger.info("Starting Netflix series deduplication...")
    deduplicate_netflix_series()
    logger.info("Netflix series deduplication completed.")

if __name__ == "__main__":
    main()