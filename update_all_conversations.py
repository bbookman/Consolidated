#!/usr/bin/env python3
"""
Update All Bee Conversations with Direct SQL

This script updates all conversations in the bee_conversations table using direct SQL queries
to extract summary, atmosphere, and key_takeaways from the raw_data JSON.
"""

import json
import re
import logging
import os
import psycopg2
from psycopg2.extras import Json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def update_all_conversations():
    """Update all conversations in the database using direct SQL."""
    # Get database connection
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return {"updated": 0, "errors": 1}
    
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
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get all conversations
        cursor.execute("SELECT id, raw_data FROM bee_conversations;")
        conversations = cursor.fetchall()
        logger.info(f"Updating {len(conversations)} conversations")
        
        updated_count = 0
        error_count = 0
        
        for conv_id, raw_data_str in conversations:
            try:
                if not raw_data_str:
                    logger.warning(f"No raw_data for conversation {conv_id}")
                    error_count += 1
                    continue
                    
                raw_data = json.loads(raw_data_str)
                
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
                
                # Update the conversation record with direct SQL
                cursor.execute(
                    "UPDATE bee_conversations SET summary = %s, atmosphere = %s, key_takeaways = %s WHERE id = %s",
                    (summary_text, atmosphere_text, Json(key_takeaways_list) if key_takeaways_list else None, conv_id)
                )
                
                updated_count += 1
                
                # Log progress every 10 conversations
                if updated_count % 10 == 0:
                    logger.info(f"Updated {updated_count} conversations so far")
                    # Commit every 10 records to avoid long transactions
                    conn.commit()
            
            except Exception as e:
                logger.error(f"Error updating conversation {conv_id}: {str(e)}")
                error_count += 1
        
        # Final commit
        conn.commit()
        logger.info(f"Updated {updated_count} conversations with {error_count} errors")
        
        return {
            "updated": updated_count,
            "errors": error_count
        }
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {
            "updated": 0,
            "errors": 1
        }
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function to run the update process."""
    logger.info("Starting conversation columns update with direct SQL")
    result = update_all_conversations()
    logger.info(f"Update complete: {result['updated']} updated, {result['errors']} errors")

if __name__ == "__main__":
    main()