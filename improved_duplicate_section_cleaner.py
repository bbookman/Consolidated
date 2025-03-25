#!/usr/bin/env python
"""
One-time script to clean duplicate sections from bee conversation data

This script uses a more direct approach to identify and remove duplicated 
Summary and Atmosphere sections in the bee_conversations table.
"""
import os
import re
import json
import logging
import psycopg2
from psycopg2.extras import Json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_duplicate_sections(text):
    """
    Clean duplicate sections by extracting content between section markers.
    This implementation just keeps the first occurrence of each section type.
    
    Args:
        text: String containing possible duplicate sections
        
    Returns:
        String with duplicate sections removed
    """
    if not text or not isinstance(text, str):
        return text
    
    # Define regex patterns for section detection
    section_markers = {
        'summary': r'(?i)(?:^|\n)(?:#+\s*)?(?:summary|summary\s*:)',
        'atmosphere': r'(?i)(?:^|\n)(?:#+\s*)?(?:atmosphere|atmosphere\s*:)',
        'key_takeaways': r'(?i)(?:^|\n)(?:#+\s*)?(?:key\s*takeaways|key\s*takeaways\s*:|key\s*take\s*aways|key\s*take\s*aways\s*:)'
    }
    
    # Find all section markers in the text
    sections = {}
    for section_name, pattern in section_markers.items():
        matches = list(re.finditer(pattern, text))
        if matches:
            for match in matches:
                start_pos = match.start()
                if match.group().startswith('\n'):
                    start_pos += 1  # Adjust for newline prefix
                sections[start_pos] = section_name
    
    if not sections:
        return text  # No sections found
    
    # Sort sections by position
    sorted_positions = sorted(sections.keys())
    
    # Identify duplicates (same section type appearing multiple times)
    seen_sections = {}
    duplicate_markers = []
    
    for pos in sorted_positions:
        section_type = sections[pos]
        if section_type in seen_sections:
            duplicate_markers.append(pos)
        else:
            seen_sections[section_type] = pos
    
    if not duplicate_markers:
        return text  # No duplicates found
    
    # Remove duplicate sections
    # We'll build a new text excluding the duplicate sections
    result = text
    
    # Process duplicates in reverse order to avoid position changes
    duplicate_markers.sort(reverse=True)
    
    for dup_pos in duplicate_markers:
        section_type = sections[dup_pos]
        
        # Find the end of this duplicate section
        section_end = len(text)
        for pos in sorted_positions:
            if pos > dup_pos:
                section_end = pos
                break
        
        # Remove this duplicate section
        duplicate_content = text[dup_pos:section_end]
        result = result.replace(duplicate_content, '', 1)
    
    # Check for empty lines and normalize spacing
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()
    
    return result

def process_conversations():
    """
    Process all bee_conversations to remove duplicate sections.
    """
    # Get database connection
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return {"cleaned": 0, "errors": 1}
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get all conversations that have data in summary or atmosphere
        cursor.execute("""
            SELECT id, summary, atmosphere 
            FROM bee_conversations 
            WHERE summary IS NOT NULL OR atmosphere IS NOT NULL;
        """)
        
        conversations = cursor.fetchall()
        logger.info(f"Found {len(conversations)} conversations to check for duplicate sections")
        
        updated_count = 0
        error_count = 0
        
        # Process each conversation
        for conv_id, summary, atmosphere in conversations:
            try:
                # Clean duplicate sections from each field
                clean_summary = clean_duplicate_sections(summary)
                clean_atmosphere = clean_duplicate_sections(atmosphere)
                
                # Check if anything changed
                if clean_summary != summary or clean_atmosphere != atmosphere:
                    # Update the record
                    cursor.execute(
                        """
                        UPDATE bee_conversations 
                        SET summary = %s, atmosphere = %s
                        WHERE id = %s
                        """,
                        (clean_summary, clean_atmosphere, conv_id)
                    )
                    
                    updated_count += 1
                    
                    # Log progress every 10 cleaned conversations
                    if updated_count % 10 == 0:
                        logger.info(f"Cleaned {updated_count} conversations with duplicate sections so far")
                        conn.commit()
                
            except Exception as e:
                logger.error(f"Error cleaning conversation {conv_id}: {str(e)}")
                error_count += 1
        
        # Final commit
        conn.commit()
        logger.info(f"Removed duplicate sections from {updated_count} conversations with {error_count} errors")
        
        return {
            "cleaned": updated_count,
            "errors": error_count
        }
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {
            "cleaned": 0,
            "errors": 1
        }
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function to run the duplicate section cleaning process."""
    logger.info("Starting improved duplicate section cleaning process")
    result = process_conversations()
    logger.info(f"Cleaning complete: {result['cleaned']} cleaned, {result['errors']} errors")

if __name__ == "__main__":
    main()