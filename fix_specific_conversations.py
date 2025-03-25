#!/usr/bin/env python
"""
Fix Specific Conversations with Duplicate Sections

This script fixes specifically identified conversations on March 14, 2025
where duplicate sections are still appearing.
"""
import os
import re
import json
import logging
import psycopg2
from psycopg2.extras import Json
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_conversation_details(cursor, date_str, hour):
    """
    Get details for a specific conversation by date and hour.
    
    Args:
        cursor: Database cursor
        date_str: Date string in format YYYY-MM-DD
        hour: Hour of the day (0-23)
        
    Returns:
        Tuple of (id, summary, atmosphere, key_takeaways) if found, None otherwise
    """
    # Create datetime objects for the start and end of the hour
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    hour_start = date_obj.replace(hour=hour, minute=0, second=0, microsecond=0)
    hour_end = date_obj.replace(hour=hour, minute=59, second=59, microsecond=999999)
    
    # Query the database
    cursor.execute("""
        SELECT id, summary, atmosphere, key_takeaways, raw_data, created_at
        FROM bee_conversations
        WHERE created_at BETWEEN %s AND %s
    """, (hour_start, hour_end))
    
    conversations = cursor.fetchall()
    if conversations:
        return conversations
    return None

def clean_text(text):
    """
    Thoroughly clean text to remove duplicate sections and Markdown.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return text
    
    # Remove Markdown formatting
    # Headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Bold and italic
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*\n]+)\*', r'\1', text)
    
    # Bullet points
    text = re.sub(r'^\s*[\*\-•]\s+', '', text, flags=re.MULTILINE)
    
    # Remove section headers that should be in separate fields
    text = re.sub(r'(?i)^Summary:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^Atmosphere:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^Key\s*Take\s*aways:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^Key\s*Takeaways:\s*', '', text, flags=re.MULTILINE)
    
    # Remove duplicate paragraphs
    unique_paragraphs = []
    paragraphs = re.split(r'\n\n+', text)
    
    for p in paragraphs:
        cleaned_p = p.strip()
        if cleaned_p and cleaned_p not in unique_paragraphs:
            unique_paragraphs.append(cleaned_p)
    
    return '\n\n'.join(unique_paragraphs)

def extract_conversation_parts_from_raw_data(raw_data_str):
    """
    Extract conversation parts from raw_data.
    
    Args:
        raw_data_str: Raw data JSON string
        
    Returns:
        Dictionary with summary, atmosphere, and key_takeaways
    """
    try:
        # Parse raw data
        if isinstance(raw_data_str, str):
            raw_data = json.loads(raw_data_str)
        else:
            raw_data = raw_data_str
        
        # Find content in known paths
        content = None
        if isinstance(raw_data, dict):
            if 'data' in raw_data and 'content' in raw_data['data']:
                content = raw_data['data']['content']
            elif 'content' in raw_data:
                content = raw_data['content']
            elif 'summary' in raw_data:
                content = raw_data['summary']
        
        if not content:
            return None
        
        # Extract sections
        summary = ""
        atmosphere = ""
        key_takeaways = []
        
        # Patterns to find sections
        summary_pattern = r'(?i)(?:#+\s*)?Summary:?\s*(.*?)(?=(?:#+\s*)?(?:Atmosphere|Key\s*Take\s*aways|Key\s*Takeaways):|$)'
        atmosphere_pattern = r'(?i)(?:#+\s*)?Atmosphere:?\s*(.*?)(?=(?:#+\s*)?(?:Summary|Key\s*Take\s*aways|Key\s*Takeaways):|$)'
        key_takeaways_pattern = r'(?i)(?:#+\s*)?Key\s*Take\s*aways:?\s*(.*?)(?=(?:#+\s*)?(?:Summary|Atmosphere):|$)'
        if not re.search(key_takeaways_pattern, content, re.DOTALL):
            key_takeaways_pattern = r'(?i)(?:#+\s*)?Key\s*Takeaways:?\s*(.*?)(?=(?:#+\s*)?(?:Summary|Atmosphere):|$)'
        
        # Extract summary
        summary_match = re.search(summary_pattern, content, re.DOTALL)
        if summary_match:
            summary = clean_text(summary_match.group(1).strip())
        
        # Extract atmosphere
        atmosphere_match = re.search(atmosphere_pattern, content, re.DOTALL)
        if atmosphere_match:
            atmosphere = clean_text(atmosphere_match.group(1).strip())
        
        # Extract key takeaways
        key_takeaways_match = re.search(key_takeaways_pattern, content, re.DOTALL)
        if key_takeaways_match:
            takeaways_text = key_takeaways_match.group(1).strip()
            # Split into individual points
            points = re.split(r'\n+', takeaways_text)
            for point in points:
                clean_point = re.sub(r'^\s*[\*\-•]\s+', '', point).strip()
                if clean_point:
                    key_takeaways.append(clean_point)
        
        return {
            "summary": summary,
            "atmosphere": atmosphere,
            "key_takeaways": key_takeaways
        }
    
    except Exception as e:
        logger.error(f"Error extracting conversation parts: {str(e)}")
        return None

def fix_specific_conversations():
    """
    Fix specific conversations identified as problematic.
    """
    # Get database connection
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Fix March 14, 2025 conversations at 2 PM and 5 PM
        date_str = "2025-03-14"
        for hour in [14, 17]:  # 2 PM and 5 PM
            conversations = get_conversation_details(cursor, date_str, hour)
            
            if not conversations:
                logger.info(f"No conversation found on {date_str} at {hour}:00")
                continue
            
            for conv_id, summary, atmosphere, key_takeaways, raw_data, created_at in conversations:
                logger.info(f"Processing conversation {conv_id} from {created_at}")
                
                # Get clean parts from raw data
                parts = extract_conversation_parts_from_raw_data(raw_data)
                
                if parts:
                    # Update the conversation
                    cursor.execute("""
                        UPDATE bee_conversations
                        SET summary = %s, atmosphere = %s, key_takeaways = %s
                        WHERE id = %s
                    """, (parts["summary"], parts["atmosphere"], 
                          Json(parts["key_takeaways"]) if parts["key_takeaways"] else None, 
                          conv_id))
                    
                    logger.info(f"Updated conversation {conv_id}")
                else:
                    # If we couldn't extract from raw data, just clean the existing text
                    new_summary = clean_text(summary)
                    new_atmosphere = clean_text(atmosphere)
                    
                    # Clean key_takeaways
                    new_key_takeaways = None
                    if key_takeaways:
                        if isinstance(key_takeaways, list):
                            # Remove duplicates
                            seen = set()
                            new_key_takeaways = []
                            for item in key_takeaways:
                                if item and item not in seen:
                                    seen.add(item)
                                    new_key_takeaways.append(item)
                        else:
                            # Try to parse as JSON
                            try:
                                items = json.loads(key_takeaways)
                                if isinstance(items, list):
                                    # Remove duplicates
                                    seen = set()
                                    new_key_takeaways = []
                                    for item in items:
                                        if item and item not in seen:
                                            seen.add(item)
                                            new_key_takeaways.append(item)
                            except:
                                # Just clean the text
                                new_key_takeaways = clean_text(key_takeaways)
                    
                    # Update the conversation
                    cursor.execute("""
                        UPDATE bee_conversations
                        SET summary = %s, atmosphere = %s, key_takeaways = %s
                        WHERE id = %s
                    """, (new_summary, new_atmosphere, 
                          Json(new_key_takeaways) if new_key_takeaways else None, 
                          conv_id))
                    
                    logger.info(f"Updated conversation {conv_id} with cleaned text")
        
        # Commit changes
        conn.commit()
        logger.info("Successfully fixed specific conversations")
    
    except Exception as e:
        logger.error(f"Error fixing conversations: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_specific_conversations()