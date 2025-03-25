"""
Database Migration: Convert Key Takeaways to JSON Lists

This script converts the key_takeaways column data from Text to JSON lists.
Each line in the current text content will become an item in a JSON array.
"""

import json
import logging
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Bee_Conversation

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_key_takeaways_to_json():
    """
    Convert key_takeaways content from text with line breaks to JSON arrays.
    
    This function:
    1. Retrieves all bee_conversations with key_takeaways data
    2. Splits the text content by line breaks into a list
    3. Converts the list to JSON and updates the record
    """
    try:
        # Get database URL from environment variables
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable is not set")
            sys.exit(1)
        
        # Create SQLAlchemy engine and session
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # First modify the column to accept JSON
        logger.info("Modifying key_takeaways column to JSONB type...")
        session.execute(text("ALTER TABLE bee_conversations ALTER COLUMN key_takeaways TYPE JSONB USING COALESCE(key_takeaways::JSONB, 'null'::JSONB)"))
        session.commit()
        
        # Get all conversations with key_takeaways
        logger.info("Retrieving conversations with key_takeaways data...")
        conversations = session.query(Bee_Conversation).filter(Bee_Conversation.key_takeaways.isnot(None)).all()
        
        count = 0
        for conv in conversations:
            if isinstance(conv.key_takeaways, str) and conv.key_takeaways.strip():
                # Split by line breaks and filter out empty lines
                takeaways_list = [line.strip() for line in conv.key_takeaways.split('\n') if line.strip()]
                
                # Update with the JSON array
                conv.key_takeaways = takeaways_list
                count += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Successfully converted {count} conversations to use JSON arrays for key_takeaways")
        
    except Exception as e:
        logger.error(f"Error converting key_takeaways to JSON: {e}")
        if 'session' in locals():
            session.rollback()
        raise
    finally:
        if 'session' in locals():
            session.close()

def main():
    """Main function to run the migration."""
    logger.info("Starting key_takeaways conversion to JSON arrays...")
    convert_key_takeaways_to_json()
    logger.info("Key takeaways conversion completed.")

if __name__ == "__main__":
    main()