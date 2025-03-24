#!/usr/bin/env python3
"""
One-time script to clean episode indicators from Netflix series titles.
This script identifies series titles with episode information and updates them
to remove the episode indicators, keeping just the base series name.
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

def clean_episode_titles():
    """
    Update episode titles to remove episode indicators, keeping just the base series name.
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
        # Get all titles that look like TV series episodes
        series_titles = session.query(Netflix_History_Item).filter(
            Netflix_History_Item.title.like("%Episode%") | 
            Netflix_History_Item.title.like("%Season%") | 
            Netflix_History_Item.title.like("%Chapter%") |
            Netflix_History_Item.title.like("%Limited Series%")
        ).all()
        
        updated_count = 0
        
        for item in series_titles:
            original_title = item.title
            base_series_name = extract_series_name(original_title)
            
            if base_series_name != original_title:
                logger.info(f"Updating title: '{original_title}' -> '{base_series_name}'")
                
                # Update the Netflix_History_Item title
                item.title = base_series_name
                
                # Update Netflix_Title_Info if it exists
                title_info = session.query(Netflix_Title_Info).filter(
                    Netflix_Title_Info.title == original_title
                ).first()
                
                if title_info:
                    title_info.title = base_series_name
                    logger.info(f"Also updated title info for: '{original_title}'")
                
                updated_count += 1
        
        # Commit the changes
        session.commit()
        logger.info(f"Title cleaning complete: {updated_count} titles updated")
        
    except Exception as e:
        logger.error(f"Error cleaning episode titles: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def main():
    """Main function."""
    logger.info("Starting Netflix episode title cleaning...")
    clean_episode_titles()
    logger.info("Netflix episode title cleaning completed.")

if __name__ == "__main__":
    main()