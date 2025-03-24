"""
One-time script to clean special characters from Netflix titles in the database.
"""

import re
import logging
from sqlalchemy import create_engine, MetaData, Table, select, update
from sqlalchemy.orm import sessionmaker
import os
from models import Netflix_History_Item, Netflix_Title_Info
from database_handler import engine, Session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_title(title):
    """
    Remove special characters from a title.
    
    Args:
        title: Original title string
        
    Returns:
        Cleaned title string
    """
    if not title:
        return title
        
    # Replace colons and other special characters with spaces
    cleaned = re.sub(r'[:\-_]', ' ', title)
    
    # Replace multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Trim leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def update_netflix_history_titles():
    """
    Update all titles in the netflix_history_items table to remove special characters.
    """
    session = Session()
    try:
        # Get all Netflix history items
        items = session.query(Netflix_History_Item).all()
        logger.info(f"Found {len(items)} Netflix history items to update")
        
        updated_count = 0
        for item in items:
            original_title = item.title
            cleaned_title = clean_title(original_title)
            
            if original_title != cleaned_title:
                logger.info(f"Updating title: '{original_title}' -> '{cleaned_title}'")
                item.title = cleaned_title
                updated_count += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Updated {updated_count} Netflix history titles")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating Netflix history titles: {e}")
    finally:
        session.close()

def update_netflix_title_info():
    """
    Update all titles in the netflix_title_info table to remove special characters.
    """
    session = Session()
    try:
        # Get all Netflix title info records
        titles = session.query(Netflix_Title_Info).all()
        logger.info(f"Found {len(titles)} Netflix title info records to update")
        
        updated_count = 0
        for title_info in titles:
            original_title = title_info.title
            cleaned_title = clean_title(original_title)
            
            if original_title != cleaned_title:
                logger.info(f"Updating title info: '{original_title}' -> '{cleaned_title}'")
                title_info.title = cleaned_title
                updated_count += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Updated {updated_count} Netflix title info records")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating Netflix title info records: {e}")
    finally:
        session.close()

def main():
    """Main function to update both tables."""
    logger.info("Starting Netflix titles cleanup process")
    
    # Update both tables
    update_netflix_history_titles()
    update_netflix_title_info()
    
    logger.info("Netflix titles cleanup complete")

if __name__ == "__main__":
    main()