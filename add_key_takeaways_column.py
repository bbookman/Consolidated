"""
Database Migration: Add Key Takeaways Column

This script adds the 'key_takeaways' column to the bee_conversations table
to store the key takeaways content separate from the summary.
"""

import re
import os
import sys
from sqlalchemy import create_engine, Column, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from models import Bee_Conversation

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def add_key_takeaways_column():
    """Add key_takeaways column to bee_conversations table."""
    try:
        # Check if the column already exists
        with engine.connect() as conn:
            conn.execute(text("SELECT key_takeaways FROM bee_conversations LIMIT 1"))
        print("key_takeaways column already exists, skipping creation")
    except Exception:
        print("Creating key_takeaways column...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE bee_conversations ADD COLUMN key_takeaways TEXT"))
            conn.commit()
        print("key_takeaways column created successfully")


def extract_key_takeaways_from_summaries():
    """
    Extract key takeaways content from existing summaries and 
    update the new key_takeaways column.
    """
    conversations = session.query(Bee_Conversation).all()
    updated_count = 0
    
    for conv in conversations:
        if not conv.summary:
            continue
            
        # Try different patterns for extracting key takeaways
        key_takeaways = None
        
        # Pattern 1: ## Key Take Aways: or ## Key Takeaways:
        pattern1 = r'(?:^|\n)(?:##?\s*Key\s+Take(?:\s*|-)Aways?:?)(.*?)(?:\n\s*##|\n\s*$|\Z)'
        match = re.search(pattern1, conv.summary, re.DOTALL | re.IGNORECASE)
        if match:
            key_takeaways = match.group(1).strip()
        
        # Pattern 2: Key Take Aways: or Key Takeaways: at the beginning of a line
        if not key_takeaways:
            pattern2 = r'(?:^|\n)(?:Key\s+Take(?:\s*|-)Aways?:?)(.*?)(?:\n\s*##|\n\s*$|\Z)'
            match = re.search(pattern2, conv.summary, re.DOTALL | re.IGNORECASE)
            if match:
                key_takeaways = match.group(1).strip()
        
        # Pattern 3: Look for bullet points section at the end
        if not key_takeaways:
            pattern3 = r'(?:^|\n)(\*\s+.*?)(?:\n\s*##|\n\s*$|\Z)'
            match = re.search(pattern3, conv.summary, re.DOTALL)
            if match:
                key_takeaways = match.group(1).strip()
        
        # Update the database if key takeaways were found
        if key_takeaways:
            conv.key_takeaways = key_takeaways
            updated_count += 1
    
    session.commit()
    print(f"Extracted key takeaways from {updated_count} conversations")


def clean_summary_column():
    """
    Update the summary column to remove the key takeaways section
    and keep only the actual summary content.
    """
    conversations = session.query(Bee_Conversation).all()
    updated_count = 0
    
    for conv in conversations:
        if not conv.summary or not conv.key_takeaways:
            continue
            
        # Try different patterns for removing key takeaways from summary
        original_summary = conv.summary
        new_summary = None
        
        # Pattern 1: ## Key Take Aways: or ## Key Takeaways:
        pattern1 = r'(?:\n##?\s*Key\s+Take(?:\s*|-)Aways?:?)(.*?)(?:\n\s*##|\n\s*$|\Z)'
        new_summary = re.sub(pattern1, '', original_summary, flags=re.DOTALL | re.IGNORECASE)
        
        # Pattern 2: Key Take Aways: or Key Takeaways: at the beginning of a line
        pattern2 = r'(?:\nKey\s+Take(?:\s*|-)Aways?:?)(.*?)(?:\n\s*##|\n\s*$|\Z)'
        new_summary = re.sub(pattern2, '', new_summary, flags=re.DOTALL | re.IGNORECASE)
        
        # Pattern 3: Remove bullet points if they match the key_takeaways content
        if conv.key_takeaways and conv.key_takeaways.strip().startswith('*'):
            escaped_takeaways = re.escape(conv.key_takeaways.strip())
            pattern3 = f'(?:\n|\s){escaped_takeaways}(?:\n|$)'
            new_summary = re.sub(pattern3, '', new_summary, flags=re.DOTALL)
        
        # Remove trailing whitespace and multiple newlines
        new_summary = re.sub(r'\n{3,}', '\n\n', new_summary).strip()
        
        # Update the database if the summary changed
        if new_summary != original_summary:
            conv.summary = new_summary
            updated_count += 1
    
    session.commit()
    print(f"Cleaned summary column for {updated_count} conversations")


def main():
    """Main function to run the migration."""
    try:
        add_key_takeaways_column()
        extract_key_takeaways_from_summaries()
        clean_summary_column()
        print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()