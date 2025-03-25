"""
One-time script to clean Markdown formatting from summary and atmosphere fields in the database.

This script identifies and removes Markdown syntax (like *, **, #, -, etc.) from the summary and
atmosphere fields in the bee_conversations table, while preserving the actual content.
Key takeaways fields are left unchanged as specified by the user.
"""

import re
import sys
from datetime import datetime
from models import Bee_Conversation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Get database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def clean_markdown(text):
    """
    Clean Markdown formatting from text while preserving content.
    
    Args:
        text: String containing Markdown formatting
        
    Returns:
        String with Markdown formatting removed
    """
    if not text:
        return text
    
    # Replace markdown headers (# Header) with just the text
    text = re.sub(r'^#+\s*(.*?)$', r'\1', text, flags=re.MULTILINE)
    
    # Replace bold (**text**) with just the text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # Replace italic (*text*) with just the text
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'\1', text)
    
    # Replace markdown bullet points with plain text
    text = re.sub(r'^\s*\*\s*(.*?)$', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*-\s*(.*?)$', r'\1', text, flags=re.MULTILINE)
    
    # Remove any stray markdown characters
    text = re.sub(r'^\s*#\s*$', '', text, flags=re.MULTILINE)
    
    # Trim extra whitespace
    text = re.sub(r'\n\n+', '\n\n', text)
    text = text.strip()
    
    return text

def clean_markdown_in_database():
    """
    Clean Markdown formatting from summary and atmosphere fields in the bee_conversations table.
    """
    try:
        # Get all conversations that might have Markdown
        conversations = session.query(Bee_Conversation).filter(
            (Bee_Conversation.summary.like('%*%')) | 
            (Bee_Conversation.summary.like('%#%')) | 
            (Bee_Conversation.summary.like('%-%')) |
            (Bee_Conversation.atmosphere.like('%*%')) | 
            (Bee_Conversation.atmosphere.like('%#%')) | 
            (Bee_Conversation.atmosphere.like('%-%'))
        ).all()
        
        print(f"Found {len(conversations)} conversations with potential Markdown formatting.")
        
        updated_count = 0
        for conv in conversations:
            original_summary = conv.summary
            original_atmosphere = conv.atmosphere
            
            # Clean Markdown from summary
            if conv.summary:
                cleaned_summary = clean_markdown(conv.summary)
                if cleaned_summary != original_summary:
                    conv.summary = cleaned_summary
                    print(f"Cleaned summary for conversation ID {conv.id}")
                    updated_count += 1
            
            # Clean Markdown from atmosphere
            if conv.atmosphere:
                cleaned_atmosphere = clean_markdown(conv.atmosphere)
                if cleaned_atmosphere != original_atmosphere:
                    conv.atmosphere = cleaned_atmosphere
                    print(f"Cleaned atmosphere for conversation ID {conv.id}")
                    updated_count += 1
        
        if updated_count > 0:
            session.commit()
            print(f"Successfully updated {updated_count} fields.")
        else:
            print("No fields needed updating.")
            
        return updated_count
            
    except Exception as e:
        session.rollback()
        print(f"Error: {str(e)}")
        return 0
    finally:
        session.close()

def main():
    """Main function to run the Markdown cleaning process."""
    print("Starting Markdown cleaning process...")
    start_time = datetime.now()
    
    updated_count = clean_markdown_in_database()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"Markdown cleaning completed in {duration:.2f} seconds.")
    print(f"Total fields updated: {updated_count}")

if __name__ == "__main__":
    main()