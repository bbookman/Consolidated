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
    3. Updates the database to use JSON format
    4. Updates each record with JSON array data
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
        
        # Get all conversations with key_takeaways before changing column type
        logger.info("Retrieving conversations with key_takeaways data...")
        conversations = session.query(Bee_Conversation).filter(Bee_Conversation.key_takeaways.isnot(None)).all()
        
        # Store the text data temporarily
        logger.info(f"Found {len(conversations)} conversations with key_takeaways")
        temp_data = {}
        for conv in conversations:
            if isinstance(conv.key_takeaways, str) and conv.key_takeaways.strip():
                # Split by line breaks and filter out empty lines
                takeaways_list = [line.strip() for line in conv.key_takeaways.split('\n') if line.strip()]
                temp_data[conv.id] = takeaways_list
        
        # Now modify the column to JSON/JSONB type by first setting to NULL
        logger.info(f"Temporarily setting key_takeaways to NULL for {len(temp_data)} records...")
        session.execute(text("UPDATE bee_conversations SET key_takeaways = NULL WHERE key_takeaways IS NOT NULL"))
        session.commit()
        
        # Change column type to JSONB
        logger.info("Altering key_takeaways column to JSONB type...")
        session.execute(text("ALTER TABLE bee_conversations ALTER COLUMN key_takeaways TYPE JSONB USING NULL"))
        session.commit()
        
        # Now update each record with its JSON data
        logger.info(f"Updating {len(temp_data)} records with JSON array data...")
        count = 0
        for conv_id, takeaways_list in temp_data.items():
            if takeaways_list:
                # Convert Python list to JSON string
                json_data = json.dumps(takeaways_list)
                # Update the record using a different approach with parameter binding
                session.execute(
                    text("UPDATE bee_conversations SET key_takeaways = cast(:json_data AS jsonb) WHERE id = :conv_id"),
                    {"json_data": json_data, "conv_id": conv_id}
                )
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