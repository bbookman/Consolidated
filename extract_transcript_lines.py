#!/usr/bin/env python3
"""
Extract Transcript Lines Script

This script extracts transcript lines (blockquote content) from existing lifelog entries
and populates the limitless_transcript_lines table, associating each line with the appropriate
subsummary based on their positions in the original content array.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models import Limitless_Lifelog, Limitless_Lifelog_SubSummary, Limitless_Transcript_Line

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def clean_text(text):
    """
    Remove Markdown formatting and special characters from text.
    
    Args:
        text: String containing possible Markdown formatting
        
    Returns:
        Cleaned string with Markdown and special formatting removed
    """
    if not text:
        return ""
    
    # Remove Markdown formatting
    cleaned = text.replace('*', '')
    cleaned = cleaned.replace('_', '')
    cleaned = cleaned.replace('#', '')
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def extract_speaker_from_text(text):
    """
    Extract speaker name from transcript line text if available.
    
    Many transcript lines start with a speaker name followed by a colon.
    This function attempts to extract that name.
    
    Args:
        text: Transcript line text that may include a speaker prefix
        
    Returns:
        Tuple of (speaker_name, cleaned_text) or (None, original_text) if no speaker found
    """
    if not text:
        return None, ""
    
    # Common pattern: "Speaker: Text of what they said"
    speaker_match = re.match(r'^([A-Za-z\s\.]+):\s*(.*)', text)
    if speaker_match:
        speaker = speaker_match.group(1).strip()
        content = speaker_match.group(2).strip()
        return speaker, content
    
    return None, text

def extract_transcript_lines():
    """
    Extract transcript lines (blockquote content) from all existing lifelog entries
    and store them in the limitless_transcript_lines table with appropriate relationships.
    """
    session = Session()
    
    try:
        # Find all lifelogs with subsummaries but no transcript lines
        lifelogs_with_subsummaries = session.query(Limitless_Lifelog)\
            .join(Limitless_Lifelog_SubSummary)\
            .filter(~Limitless_Lifelog_SubSummary.transcript_lines.any())\
            .distinct().all()
        
        if not lifelogs_with_subsummaries:
            logger.info("No lifelogs with subsummaries found that need transcript line extraction")
            return
        
        logger.info(f"Found {len(lifelogs_with_subsummaries)} lifelogs with subsummaries but no transcript lines")
        
        processed_count = 0
        added_lines_count = 0
        
        for lifelog in lifelogs_with_subsummaries:
            # Parse raw data to get the original contents array
            if not lifelog.raw_data:
                logger.warning(f"Lifelog {lifelog.log_id} has no raw_data, skipping")
                continue
            
            try:
                raw_data = json.loads(lifelog.raw_data)
                if not raw_data or 'contents' not in raw_data:
                    logger.warning(f"Lifelog {lifelog.log_id} has invalid raw_data format, skipping")
                    continue
                
                contents = raw_data.get('contents', [])
                
                # Get all subsummaries for this lifelog
                subsummaries = session.query(Limitless_Lifelog_SubSummary)\
                    .filter(Limitless_Lifelog_SubSummary.lifelog_id == lifelog.log_id)\
                    .order_by(Limitless_Lifelog_SubSummary.position)\
                    .all()
                
                # Extract the blockquote contents and associate with subsummaries
                heading2_positions = [i for i, item in enumerate(contents) 
                                      if item.get('type') == 'heading2']
                
                # Process each subsummary
                for i, subsummary in enumerate(subsummaries):
                    # Find the corresponding position in the contents array
                    if i >= len(heading2_positions):
                        logger.warning(f"Subsummary index {i} out of range for heading2_positions")
                        continue
                    
                    start_pos = heading2_positions[i] + 1
                    end_pos = heading2_positions[i+1] if i+1 < len(heading2_positions) else len(contents)
                    
                    # Collect all blockquote items between this heading2 and the next
                    transcript_position = 0
                    for pos in range(start_pos, end_pos):
                        if pos >= len(contents):
                            break
                            
                        content_item = contents[pos]
                        if content_item.get('type') != 'blockquote':
                            continue
                        
                        text = content_item.get('content', '')
                        if not text.strip():
                            continue
                        
                        # Extract speaker and clean text
                        speaker, cleaned_text = extract_speaker_from_text(text)
                        
                        # Create transcript line entry
                        transcript_line = Limitless_Transcript_Line(
                            subsummary_id=subsummary.id,
                            speaker=speaker,
                            text=cleaned_text,
                            start_time=content_item.get('startTime'),
                            end_time=content_item.get('endTime'),
                            position=transcript_position
                        )
                        
                        session.add(transcript_line)
                        transcript_position += 1
                        added_lines_count += 1
                
                processed_count += 1
                if processed_count % 5 == 0:
                    logger.info(f"Processed {processed_count}/{len(lifelogs_with_subsummaries)} lifelogs, added {added_lines_count} transcript lines")
                    session.commit()
            
            except Exception as e:
                logger.error(f"Error processing lifelog {lifelog.log_id}: {str(e)}")
                continue
        
        # Final commit
        session.commit()
        logger.info(f"Completed processing {processed_count} lifelogs, added {added_lines_count} transcript lines")
    
    except Exception as e:
        logger.error(f"Error extracting transcript lines: {str(e)}")
        session.rollback()
    
    finally:
        session.close()

def main():
    """Main function to run the extraction process."""
    try:
        extract_transcript_lines()
        logger.info("Transcript line extraction completed successfully")
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())