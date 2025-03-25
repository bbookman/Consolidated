#!/usr/bin/env python3
"""
Clean Markdown from Bee Conversation Data

This script removes Markdown formatting from the summary, atmosphere, and key_takeaways
fields in the bee_conversations table, ensuring they contain only plain text.
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
    text = re.sub(r'(?i)Atmosphere:.*?(\n\n|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)Key Take ?Aways:.*?(\n\n|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)Key Takeaways:.*?(\n\n|$)', '', text, flags=re.DOTALL)
    
    # Remove Markdown headers (e.g., ## Header)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold formatting (e.g., **bold**)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # Remove italic formatting (e.g., *italic*)
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'\1', text)
    
    # Remove bullet points
    text = re.sub(r'^\s*[\*\-•]\s+', '', text, flags=re.MULTILINE)
    
    # Remove Markdown links [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules
    text = re.sub(r'^\s*[-_*]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # Remove extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text

def clean_bee_conversation_data():
    """Clean Markdown from summary, atmosphere, and key_takeaways in bee_conversations."""
    # Get database connection
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return {"cleaned": 0, "errors": 1}
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get all conversations that have data in summary, atmosphere, or key_takeaways
        cursor.execute("""
            SELECT id, summary, atmosphere, key_takeaways 
            FROM bee_conversations 
            WHERE summary IS NOT NULL OR atmosphere IS NOT NULL OR key_takeaways IS NOT NULL;
        """)
        
        conversations = cursor.fetchall()
        logger.info(f"Found {len(conversations)} conversations with data to clean")
        
        cleaned_count = 0
        error_count = 0
        
        # Process each conversation
        for conv_id, summary, atmosphere, key_takeaways in conversations:
            try:
                # Clean Markdown from each field
                clean_summary = clean_markdown(summary)
                clean_atmosphere = clean_markdown(atmosphere)
                
                # Handle key_takeaways specially since it could be a JSON array
                clean_key_takeaways = None
                if key_takeaways:
                    if isinstance(key_takeaways, str):
                        # Try to parse as JSON if it's stored as a string
                        try:
                            key_takeaways_list = json.loads(key_takeaways)
                            clean_key_takeaways = clean_markdown(key_takeaways_list)
                        except json.JSONDecodeError:
                            # Not valid JSON, treat as regular text
                            clean_key_takeaways = clean_markdown(key_takeaways)
                    else:
                        # Already a Python object (list)
                        clean_key_takeaways = clean_markdown(key_takeaways)
                
                # Update the record
                cursor.execute(
                    """
                    UPDATE bee_conversations 
                    SET summary = %s, atmosphere = %s, key_takeaways = %s 
                    WHERE id = %s
                    """,
                    (clean_summary, clean_atmosphere, Json(clean_key_takeaways) if clean_key_takeaways else None, conv_id)
                )
                
                cleaned_count += 1
                
                # Log progress every 10 conversations
                if cleaned_count % 10 == 0:
                    logger.info(f"Cleaned {cleaned_count} conversations so far")
                    conn.commit()
                
            except Exception as e:
                logger.error(f"Error cleaning conversation {conv_id}: {str(e)}")
                error_count += 1
        
        # Final commit
        conn.commit()
        logger.info(f"Cleaned {cleaned_count} conversations with {error_count} errors")
        
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
    """Main function to run the cleaning process."""
    logger.info("Starting Markdown cleaning process")
    result = clean_bee_conversation_data()
    logger.info(f"Cleaning complete: {result['cleaned']} cleaned, {result['errors']} errors")

if __name__ == "__main__":
    main()