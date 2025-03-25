#!/usr/bin/env python
"""
Fix Summary and Atmosphere from Raw Data

This script extracts clean summary and atmosphere content from the raw_data JSON field
and updates the corresponding fields in the database. This bypasses any previous
processing issues that might have resulted in duplicate sections or Markdown artifacts.
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

def clean_markdown(text):
    """
    Remove Markdown formatting from text.
    
    Args:
        text: String containing Markdown formatting
        
    Returns:
        String with Markdown formatting removed
    """
    if not text:
        return text
        
    # Handle different types
    if isinstance(text, list):
        return [clean_markdown(item) for item in text]
    if not isinstance(text, str):
        return text
        
    # Remove section headings that should be in separate fields
    text = re.sub(r'(?i)^Summary:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(?i)Atmosphere:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(?i)Key Take ?Aways:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(?i)Key Takeaways:.*?(\n\n|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # Remove section heading variations more thoroughly
    text = re.sub(r'(?i)^#+\s*Summary:?.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^#+\s*Atmosphere:?.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^#+\s*Key Take ?Aways:?.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^#+\s*Key Takeaways:?.*?\n', '', text, flags=re.MULTILINE)
    
    # Remove Markdown headers (e.g., ## Header)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Enhanced Markdown cleanup - Run multiple times to catch nested formatting
    # Remove bold formatting (e.g., **bold**)
    for _ in range(3):  # Run multiple passes to catch nested formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # Remove italic formatting (e.g., *italic*)
    for _ in range(3):
        text = re.sub(r'\*([^\*\n]+)\*', r'\1', text)
    
    # Remove remaining single asterisks that might be part of incomplete formatting
    text = re.sub(r'(?<!\*)\*(?!\*)', '', text)
    
    # Remove bullet points with different symbols and spacing patterns
    text = re.sub(r'^\s*[\*\-•]\s+', '', text, flags=re.MULTILINE)
    
    # Remove Markdown links [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove code blocks with any language specifier
    text = re.sub(r'```[\w]*\n.*?```', '', text, flags=re.DOTALL)
    
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules
    text = re.sub(r'^\s*[-_*]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # Remove HTML tags that might be present
    text = re.sub(r'<[^>]+>', '', text)
    
    # Fix common markdown artifacts
    text = text.replace('**', '').replace('__', '')
    
    # Remove extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text

def extract_section(text, section_patterns):
    """
    Extract a section from text based on the provided section patterns.
    
    Args:
        text: The full text to search in
        section_patterns: List of regex patterns to identify the section
        
    Returns:
        Extracted section content with formatting removed, or empty string if not found
    """
    if not text:
        return ""
    
    # Try each pattern until we find a match
    for pattern in section_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Find where this section ends (next section starts or end of text)
            start_pos = match.end()
            # Look for the next section heading
            next_section = re.search(r'(?i)(?:^|\n)(?:#+\s*)?(?:summary|atmosphere|key\s*takeaways|key\s*take\s*aways)\s*[:\n]', text[start_pos:], re.MULTILINE)
            
            if next_section:
                section_content = text[start_pos:start_pos + next_section.start()].strip()
            else:
                section_content = text[start_pos:].strip()
            
            # Clean any Markdown formatting from the content
            return clean_markdown(section_content)
    
    return ""

def parse_raw_json(raw_data):
    """
    Parse the raw_data field to extract properly formatted sections.
    
    Args:
        raw_data: Raw JSON string from the database
        
    Returns:
        Dictionary with extracted and cleaned sections
    """
    try:
        # Parse the raw JSON
        if isinstance(raw_data, str):
            data = json.loads(raw_data)
        else:
            data = raw_data
        
        # Get the full content to search for sections
        full_content = ""
        if isinstance(data, dict):
            # Check common paths where the content might be
            if 'content' in data:
                full_content = data['content']
            elif 'data' in data and isinstance(data['data'], dict) and 'content' in data['data']:
                full_content = data['data']['content']
            elif 'summary' in data:
                full_content = data['summary']
        
        if not full_content and isinstance(data, str):
            full_content = data
        
        # If we couldn't find structured content, return empty results
        if not full_content:
            return {"summary": "", "atmosphere": "", "key_takeaways": []}
        
        # Define patterns to extract sections
        summary_patterns = [
            r'(?i)##\s*Summary\s*[\n:]',
            r'(?i)#\s*Summary\s*[\n:]',
            r'(?i)Summary\s*:',
            r'(?i)\*\*Summary\*\*\s*:?'
        ]
        
        atmosphere_patterns = [
            r'(?i)##\s*Atmosphere\s*[\n:]',
            r'(?i)#\s*Atmosphere\s*[\n:]',
            r'(?i)Atmosphere\s*:',
            r'(?i)\*\*Atmosphere\*\*\s*:?'
        ]
        
        key_takeaways_patterns = [
            r'(?i)##\s*Key\s*Takeaways\s*[\n:]',
            r'(?i)#\s*Key\s*Takeaways\s*[\n:]',
            r'(?i)Key\s*Takeaways\s*:',
            r'(?i)\*\*Key\s*Takeaways\*\*\s*:?',
            r'(?i)##\s*Key\s*Take\s*Aways\s*[\n:]',
            r'(?i)#\s*Key\s*Take\s*Aways\s*[\n:]',
            r'(?i)Key\s*Take\s*Aways\s*:',
            r'(?i)\*\*Key\s*Take\s*Aways\*\*\s*:?'
        ]
        
        # Extract each section
        summary = extract_section(full_content, summary_patterns)
        atmosphere = extract_section(full_content, atmosphere_patterns)
        key_takeaways_text = extract_section(full_content, key_takeaways_patterns)
        
        # Convert key takeaways text to an array of points
        key_takeaways = []
        if key_takeaways_text:
            # Split by bullet points or newlines and clean
            lines = re.split(r'\n+', key_takeaways_text)
            for line in lines:
                # Remove bullet points and leading/trailing spaces
                clean_line = re.sub(r'^\s*[\*\-•]\s*', '', line).strip()
                if clean_line:
                    key_takeaways.append(clean_line)
        
        return {
            "summary": summary,
            "atmosphere": atmosphere,
            "key_takeaways": key_takeaways
        }
    
    except Exception as e:
        logger.error(f"Error parsing raw JSON: {str(e)}")
        return {"summary": "", "atmosphere": "", "key_takeaways": []}

def fix_from_raw_data():
    """
    Fix summary and atmosphere by extracting clean data from the raw_data field.
    """
    # Get database connection
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return {"fixed": 0, "errors": 1}
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get all conversations with raw_data
        cursor.execute("""
            SELECT id, raw_data 
            FROM bee_conversations 
            WHERE raw_data IS NOT NULL;
        """)
        
        conversations = cursor.fetchall()
        logger.info(f"Found {len(conversations)} conversations with raw_data to process")
        
        fixed_count = 0
        error_count = 0
        
        # Process each conversation
        for conv_id, raw_data in conversations:
            try:
                # Extract clean sections from raw_data
                sections = parse_raw_json(raw_data)
                
                # Update the record with extracted sections
                cursor.execute(
                    """
                    UPDATE bee_conversations 
                    SET summary = %s, atmosphere = %s, key_takeaways = %s
                    WHERE id = %s
                    """,
                    (sections["summary"], sections["atmosphere"], 
                     Json(sections["key_takeaways"]) if sections["key_takeaways"] else None, 
                     conv_id)
                )
                
                fixed_count += 1
                
                # Log progress every 10 fixed conversations
                if fixed_count % 10 == 0:
                    logger.info(f"Fixed {fixed_count} conversations from raw_data so far")
                    conn.commit()
            
            except Exception as e:
                logger.error(f"Error fixing conversation {conv_id}: {str(e)}")
                error_count += 1
        
        # Final commit
        conn.commit()
        logger.info(f"Fixed {fixed_count} conversations from raw_data with {error_count} errors")
        
        return {
            "fixed": fixed_count,
            "errors": error_count
        }
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {
            "fixed": 0,
            "errors": 1
        }
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function to run the fix process."""
    logger.info("Starting fix from raw_data process")
    result = fix_from_raw_data()
    logger.info(f"Fix complete: {result['fixed']} fixed, {result['errors']} errors")

if __name__ == "__main__":
    main()