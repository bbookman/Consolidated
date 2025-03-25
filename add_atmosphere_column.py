#!/usr/bin/env python3
"""
Database Migration: Add Atmosphere Column

This script adds the 'atmosphere' column to the bee_conversations table
to store the atmosphere content separate from the summary.
"""

import os
import json
import sqlalchemy
from sqlalchemy import create_engine, Column, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    exit(1)

# Initialize SQLAlchemy connection
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def add_atmosphere_column():
    """Add atmosphere column to bee_conversations table."""
    try:
        # Check if the column already exists
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='bee_conversations' AND column_name='atmosphere'"
            ))
            if result.fetchone():
                logger.info("Column 'atmosphere' already exists in bee_conversations table")
                return
        
        # Add the atmosphere column
        with engine.connect() as conn:
            logger.info("Adding 'atmosphere' column to bee_conversations table")
            conn.execute(sqlalchemy.text(
                "ALTER TABLE bee_conversations ADD COLUMN atmosphere TEXT"
            ))
            conn.commit()
            logger.info("Column 'atmosphere' added successfully")
    
    except Exception as e:
        logger.error(f"Error adding atmosphere column: {str(e)}")
        raise
        
def extract_atmosphere_from_summaries():
    """
    Extract atmosphere content from existing summaries and 
    update the new atmosphere column.
    """
    session = Session()
    try:
        # Get all conversations with summaries
        conversations = session.execute(sqlalchemy.text(
            "SELECT id, summary FROM bee_conversations WHERE summary IS NOT NULL"
        )).fetchall()
        
        logger.info(f"Found {len(conversations)} conversations with summaries")
        
        # Patterns to match atmosphere section in the summary
        atmosphere_patterns = [
            r'## Atmosphere\s*\n',
            r'### Atmosphere\s*\n', 
            r'## Atmosphere:',
            r'### Atmosphere:',
            r'\*\*Atmosphere\*\*:?',
            r'Atmosphere:'
        ]
        
        updated_count = 0
        for conv_id, full_text in conversations:
            if not full_text:
                continue
                
            # Try to find atmosphere section
            atmosphere_text = ""
            atmosphere_match = None
            for pattern in atmosphere_patterns:
                match = re.search(pattern, full_text)
                if match:
                    atmosphere_match = match
                    break
            
            # Extract text after atmosphere header if found
            if atmosphere_match:
                start_idx = atmosphere_match.end()
                # Find where next section starts (if any)
                next_section_start = len(full_text)
                next_section_patterns = [r'## ', r'### ']
                for pattern in next_section_patterns:
                    match = re.search(pattern, full_text[start_idx:])
                    if match:
                        next_section_start = min(next_section_start, start_idx + match.start())
                
                # Extract atmosphere text
                atmosphere_text = full_text[start_idx:next_section_start].strip()
                
                # Update the database with the extracted atmosphere text
                session.execute(sqlalchemy.text(
                    "UPDATE bee_conversations SET atmosphere = :atmosphere WHERE id = :id"
                ), {"atmosphere": atmosphere_text, "id": conv_id})
                
                updated_count += 1
        
        session.commit()
        logger.info(f"Updated {updated_count} records with atmosphere data")
    
    except Exception as e:
        logger.error(f"Error extracting atmosphere data: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()
        
def clean_summary_column():
    """
    Update the summary column to remove the atmosphere section
    and keep only the actual summary content.
    """
    session = Session()
    try:
        # Get all conversations with summaries
        conversations = session.execute(sqlalchemy.text(
            "SELECT id, summary FROM bee_conversations WHERE summary IS NOT NULL"
        )).fetchall()
        
        logger.info(f"Found {len(conversations)} conversations with summaries to clean")
        
        # Patterns to match summary and atmosphere sections
        summary_patterns = [
            r'## Summary\s*\n',
            r'### Summary\s*\n',
            r'## Summary:',
            r'### Summary:',
            r'\*\*Summary\*\*:?',
            r'Summary:'
        ]
        
        atmosphere_patterns = [
            r'## Atmosphere\s*\n',
            r'### Atmosphere\s*\n', 
            r'## Atmosphere:',
            r'### Atmosphere:',
            r'\*\*Atmosphere\*\*:?',
            r'Atmosphere:'
        ]
        
        updated_count = 0
        for conv_id, full_text in conversations:
            if not full_text:
                continue
                
            # Try to extract Summary section
            summary_match = None
            for pattern in summary_patterns:
                match = re.search(pattern, full_text)
                if match:
                    summary_match = match
                    break
            
            # Extract text after summary header
            if summary_match:
                start_idx = summary_match.end()
                # Find where atmosphere section starts (if it exists)
                atmosphere_start_idx = len(full_text)
                for pattern in atmosphere_patterns:
                    match = re.search(pattern, full_text)
                    if match and match.start() > start_idx:
                        atmosphere_start_idx = min(atmosphere_start_idx, match.start())
                
                # Extract summary text without the atmosphere part
                summary_text = full_text[start_idx:atmosphere_start_idx].strip()
                
                # Update the database with the cleaned summary text
                session.execute(sqlalchemy.text(
                    "UPDATE bee_conversations SET summary = :summary WHERE id = :id"
                ), {"summary": summary_text, "id": conv_id})
                
                updated_count += 1
        
        session.commit()
        logger.info(f"Cleaned {updated_count} summaries to remove atmosphere sections")
    
    except Exception as e:
        logger.error(f"Error cleaning summary data: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def main():
    """Main function to run the migration."""
    logger.info("Starting migration to add atmosphere column")
    add_atmosphere_column()
    extract_atmosphere_from_summaries()
    clean_summary_column()
    logger.info("Migration completed successfully")

if __name__ == "__main__":
    main()