#!/usr/bin/env python3
"""
Extract Lifelog Sub-Summaries Script

This script extracts subsummaries (heading2 content) from existing lifelog entries
and populates the limitless_lifelog_subsummaries table.
"""

import json
import logging
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models import Limitless_Lifelog, Limitless_Lifelog_SubSummary, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def extract_subsummaries():
    """
    Extract subsummaries (heading2 content) from all existing lifelog entries
    and store them in the limitless_lifelog_subsummaries table.
    """
    # Get database URL from environment variables
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Create SQLAlchemy engine and session
    engine = create_engine(DATABASE_URL)
    
    # Ensure the table exists
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Get all lifelogs that have not yet had subsummaries extracted
        lifelogs = session.execute(
            select(Limitless_Lifelog)
            .outerjoin(Limitless_Lifelog_SubSummary)
            .where(Limitless_Lifelog_SubSummary.id == None)
        ).scalars().all()
        
        logger.info(f"Found {len(lifelogs)} lifelogs without subsummaries")
        
        processed_count = 0
        subsummaries_added = 0
        
        for lifelog in lifelogs:
            processed_count += 1
            
            # Parse raw_data JSON
            try:
                raw_data = json.loads(lifelog.raw_data)
                contents = raw_data.get('contents', [])
                
                # Find all heading2 items
                heading2_items = []
                for i, item in enumerate(contents):
                    if item.get('type') == 'heading2':
                        heading2_items.append({
                            'content': item.get('content', ''),
                            'position': i
                        })
                
                # Add subsummaries to database
                for idx, h2 in enumerate(heading2_items):
                    subsummary = Limitless_Lifelog_SubSummary(
                        lifelog_id=lifelog.log_id,
                        content=h2['content'],
                        position=idx,
                        created_at=datetime.utcnow()
                    )
                    session.add(subsummary)
                    subsummaries_added += 1
                
                # Commit after each lifelog to avoid losing data if an error occurs
                session.commit()
                
                if processed_count % 10 == 0 or processed_count == len(lifelogs):
                    logger.info(f"Processed {processed_count}/{len(lifelogs)} lifelogs, added {subsummaries_added} subsummaries")
                
            except Exception as e:
                logger.error(f"Error processing lifelog {lifelog.id} ({lifelog.log_id}): {str(e)}")
                session.rollback()
                continue
    
    logger.info(f"Processing complete. Processed {processed_count} lifelogs, added {subsummaries_added} subsummaries")
    return {
        "processed": processed_count,
        "added": subsummaries_added
    }

def main():
    """Main function to run the extraction process."""
    try:
        results = extract_subsummaries()
        logger.info(f"Extraction complete. Processed {results['processed']} lifelogs, added {results['added']} subsummaries")
        return 0
    except Exception as e:
        logger.error(f"Error extracting subsummaries: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())