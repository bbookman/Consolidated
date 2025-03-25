#!/usr/bin/env python3
"""
Update Bee Conversation Columns

This script updates the summary, atmosphere, and key_takeaways columns in the bee_conversations
table by extracting values from the raw_data JSON.
"""

import json
import re
import logging
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from models import Bee_Conversation

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create database connection
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    logger.error("DATABASE_URL not found in environment variables")
    exit(1)

engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

def extract_section(full_text, section_patterns):
    """
    Extract a section of text based on patterns.
    
    Args:
        full_text: The full text to search
        section_patterns: List of regex patterns to match the section header
        
    Returns:
        Extracted section text or empty string if not found
    """
    if not full_text:
        return ""
        
    section_text = ""
    
    # Try to find the section header
    section_match = None
    for pattern in section_patterns:
        match = re.search(pattern, full_text)
        if match:
            section_match = match
            break
            
    # Extract text after section header
    if section_match:
        start_idx = section_match.end()
        # Find where next section starts (if any)
        next_section_start = len(full_text)
        next_section_patterns = [r'## ', r'### ']
        for pattern in next_section_patterns:
            match = re.search(pattern, full_text[start_idx:])
            if match:
                next_section_start = min(next_section_start, start_idx + match.start())
        
        # Extract section text
        section_text = full_text[start_idx:next_section_start].strip()
    
    return section_text

def update_conversation_columns():
    """
    Update summary, atmosphere, and key_takeaways columns for all conversations.
    """
    session = Session()
    try:
        # Get all conversations
        conversations = session.query(Bee_Conversation).all()
        logger.info(f"Updating {len(conversations)} conversations")
        
        updated_count = 0
        error_count = 0
        
        # Summary section patterns
        summary_patterns = [
            r'## Summary\s*\n',
            r'### Summary\s*\n',
            r'## Summary:',
            r'### Summary:',
            r'\*\*Summary\*\*:?',
            r'Summary:'
        ]
        
        # Atmosphere section patterns
        atmosphere_patterns = [
            r'## Atmosphere\s*\n',
            r'### Atmosphere\s*\n', 
            r'## Atmosphere:',
            r'### Atmosphere:',
            r'\*\*Atmosphere\*\*:?',
            r'Atmosphere:'
        ]
        
        # Key Takeaways section patterns
        key_takeaways_patterns = [
            r'## Key Take[aA]ways\s*\n',
            r'### Key Take[aA]ways\s*\n',
            r'## Key Take[aA]ways:',
            r'### Key Take[aA]ways:',
            r'\*\*Key Take[aA]ways\*\*:?',
            r'Key Take[aA]ways:',
            r'## Key Takeaways\s*\n',
            r'### Key Takeaways\s*\n',
            r'## Key Takeaways:',
            r'### Key Takeaways:',
            r'\*\*Key Takeaways\*\*:?',
            r'Key Takeaways:'
        ]
        
        for conv in conversations:
            try:
                raw_data = {}
                try:
                    if conv.raw_data:
                        raw_data = json.loads(conv.raw_data)
                except json.JSONDecodeError:
                    logger.error(f"Error parsing raw_data JSON for conversation {conv.id}")
                    error_count += 1
                    continue
                
                # Extract summary from raw_data
                summary_text = ""
                if raw_data.get("summary"):
                    full_text = raw_data.get("summary")
                    summary_text = extract_section(full_text, summary_patterns)
                    if not summary_text and full_text:
                        # If no summary section found, use the whole text
                        summary_text = full_text.strip()
                
                # Extract atmosphere from raw_data
                atmosphere_text = ""
                if raw_data.get("summary"):
                    full_text = raw_data.get("summary")
                    atmosphere_text = extract_section(full_text, atmosphere_patterns)
                
                # Extract key takeaways from raw_data
                key_takeaways_text = ""
                if raw_data.get("summary"):
                    full_text = raw_data.get("summary")
                    key_takeaways_text = extract_section(full_text, key_takeaways_patterns)
                
                # Convert key takeaways text to list if it exists
                key_takeaways_list = None
                if key_takeaways_text:
                    # Split by newlines and handle bullet points
                    key_takeaways_items = key_takeaways_text.strip().split('\n')
                    key_takeaways_list = []
                    for item in key_takeaways_items:
                        # Remove bullet points or dashes if they exist
                        cleaned_item = re.sub(r'^[\*\-•]+\s*', '', item.strip())
                        if cleaned_item:  # Only add non-empty items
                            key_takeaways_list.append(cleaned_item)
                
                # Update the conversation record
                conv.summary = summary_text
                conv.atmosphere = atmosphere_text
                conv.key_takeaways = key_takeaways_list
                
                updated_count += 1
                
                # Log progress every 10 conversations
                if updated_count % 10 == 0:
                    logger.info(f"Updated {updated_count} conversations so far")
            
            except Exception as e:
                logger.error(f"Error updating conversation {conv.id}: {str(e)}")
                error_count += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Updated {updated_count} conversations with {error_count} errors")
        
        return {
            "updated": updated_count,
            "errors": error_count
        }
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error in update_conversation_columns: {str(e)}")
        return {
            "updated": 0,
            "errors": 1
        }
    finally:
        session.close()

def main():
    """Main function to run the update process."""
    logger.info("Starting conversation columns update")
    result = update_conversation_columns()
    logger.info(f"Update complete: {result['updated']} updated, {result['errors']} errors")

if __name__ == "__main__":
    main()