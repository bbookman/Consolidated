#!/usr/bin/env python
"""
One-time script to clean duplicate sections from bee conversation data

This script identifies and removes duplicated Summary and Atmosphere sections 
from the database by using more aggressive pattern matching.
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

def remove_duplicate_sections(text):
    """
    Remove duplicate Summary or Atmosphere sections within the content.
    
    Args:
        text: String containing possible duplicate sections
        
    Returns:
        String with duplicate sections removed
    """
    if not text:
        return text
    
    if not isinstance(text, str):
        return text
    
    # Patterns for section headings (both Markdown and plain text)
    section_patterns = {
        "summary": [
            r'## Summary\s*\n',
            r'### Summary\s*\n',
            r'Summary:',
            r'Summary :', 
            r'\*\*Summary\*\*:?',
            r'# Summary'
        ],
        "atmosphere": [
            r'## Atmosphere\s*\n',
            r'### Atmosphere\s*\n',
            r'Atmosphere:',
            r'Atmosphere :',
            r'\*\*Atmosphere\*\*:?',
            r'# Atmosphere'
        ],
        "key_takeaways": [
            r'## Key Takeaways\s*\n',
            r'### Key Takeaways\s*\n',
            r'Key Takeaways:',
            r'Key Takeaways :',
            r'\*\*Key Takeaways\*\*:?',
            r'# Key Takeaways',
            r'## Key Take ?Aways\s*\n',
            r'### Key Take ?Aways\s*\n', 
            r'Key Take ?Aways:',
            r'Key Take ?Aways :',
            r'\*\*Key Take ?Aways\*\*:?',
            r'# Key Take ?Aways'
        ]
    }
    
    # For each section type, check if there are duplicates
    for section_type, patterns in section_patterns.items():
        # Count how many times each pattern appears
        pattern_count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            pattern_count += len(matches)
        
        # If a section appears more than once, we need to clean it
        if pattern_count > 1:
            # Find the first instance of this section and keep only content up to the next section
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    start_pos = match.start()
                    # Find the next section after this one
                    next_section_pos = len(text)
                    all_patterns = []
                    for p_list in section_patterns.values():
                        all_patterns.extend(p_list)
                    
                    for p in all_patterns:
                        next_match = re.search(p, text[start_pos + len(match.group()):], re.IGNORECASE)
                        if next_match:
                            pos = start_pos + len(match.group()) + next_match.start()
                            if pos < next_section_pos:
                                next_section_pos = pos
                    
                    # Extract just the first section's content
                    first_part = text[:start_pos]
                    current_section = text[start_pos:next_section_pos]
                    remaining_text = ""
                    
                    # Check what's left and keep only sections that aren't of the current type
                    if next_section_pos < len(text):
                        remaining_part = text[next_section_pos:]
                        # Remove any sections of the current type from the remaining text
                        for p in patterns:
                            remaining_part = re.sub(p + r'.*?(?=(?:' + '|'.join(all_patterns) + r')|$)', 
                                                    '', remaining_part, flags=re.IGNORECASE | re.DOTALL)
                        remaining_text = remaining_part
                    
                    text = first_part + current_section + remaining_text
                    break
    
    return text

def clean_duplicate_sections():
    """
    Clean duplicate Summary and Atmosphere sections from bee_conversations.
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
        
        cleaned_count = 0
        error_count = 0
        
        # Process each conversation
        for conv_id, summary, atmosphere in conversations:
            try:
                # Clean duplicate sections from each field
                clean_summary = remove_duplicate_sections(summary)
                clean_atmosphere = remove_duplicate_sections(atmosphere)
                
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
                    
                    cleaned_count += 1
                    
                    # Log progress every 10 cleaned conversations
                    if cleaned_count % 10 == 0:
                        logger.info(f"Cleaned {cleaned_count} conversations with duplicate sections so far")
                        conn.commit()
                
            except Exception as e:
                logger.error(f"Error cleaning conversation {conv_id}: {str(e)}")
                error_count += 1
        
        # Final commit
        conn.commit()
        logger.info(f"Removed duplicate sections from {cleaned_count} conversations with {error_count} errors")
        
        return {
            "cleaned": cleaned_count,
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
    logger.info("Starting duplicate section cleaning process")
    result = clean_duplicate_sections()
    logger.info(f"Cleaning complete: {result['cleaned']} cleaned, {result['errors']} errors")

if __name__ == "__main__":
    main()