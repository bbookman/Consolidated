"""
Update Lifelog Timestamps

This script updates the timestamps for existing Limitless lifelogs in the database
by extracting startTime and endTime from the contents.
"""

import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Limitless_Lifelog
from database_handler import parse_date
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a sessionmaker
Session = sessionmaker(bind=engine)

def update_lifelog_timestamps():
    """
    Update timestamps for existing Limitless lifelogs in the database.
    Extracts startTime and endTime from contents.
    """
    session = Session()
    try:
        # Get all lifelogs
        lifelogs = session.query(Limitless_Lifelog).all()
        logger.info(f"Found {len(lifelogs)} Limitless lifelogs in the database")
        
        updated_count = 0
        skipped_count = 0
        
        for log in lifelogs:
            try:
                # Skip if already has timestamps
                if log.created_at is not None and log.updated_at is not None:
                    logger.info(f"Lifelog {log.log_id} already has timestamps, skipping")
                    skipped_count += 1
                    continue
                
                # Parse raw_data
                raw_data = json.loads(log.raw_data)
                
                # Extract timestamps from contents
                created_at = None
                updated_at = None
                
                # Look for startTime and endTime in contents
                if 'contents' in raw_data and isinstance(raw_data['contents'], list):
                    # Find the earliest startTime and latest endTime
                    for item in raw_data['contents']:
                        start_time = item.get('startTime')
                        parsed_start = parse_date(start_time) if start_time else None
                        
                        if parsed_start:
                            if created_at is None:
                                created_at = parsed_start
                            elif parsed_start < created_at:
                                created_at = parsed_start
                            
                        end_time = item.get('endTime')
                        parsed_end = parse_date(end_time) if end_time else None
                        
                        if parsed_end:
                            if updated_at is None:
                                updated_at = parsed_end
                            elif parsed_end > updated_at:
                                updated_at = parsed_end
                
                # Update the lifelog if we found valid timestamps
                if created_at:
                    log.created_at = created_at
                    if updated_at:
                        log.updated_at = updated_at
                    updated_count += 1
                    logger.info(f"Updated timestamps for lifelog {log.log_id}")
                else:
                    logger.warning(f"No valid timestamps found for lifelog {log.log_id}")
                    skipped_count += 1
            
            except Exception as e:
                logger.error(f"Error updating lifelog {log.log_id}: {str(e)}")
                skipped_count += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Updated {updated_count} lifelogs, skipped {skipped_count}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating lifelog timestamps: {str(e)}")
    finally:
        session.close()

def main():
    """Main function."""
    logger.info("Starting timestamp update")
    update_lifelog_timestamps()
    logger.info("Completed timestamp update")

if __name__ == "__main__":
    main()