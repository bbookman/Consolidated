"""
One-time script to clean atmosphere data from summary field in the database.

This script identifies conversations where the summary text contains the atmosphere content
and removes that content from the summary, since it's already available in the separate
atmosphere field.
"""

import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import re
import sys

# Import models and database connection
sys.path.append('.')
from models import Base, Bee_Conversation

def clean_summary_field():
    """
    Update the summary field to remove the atmosphere section
    that's already stored in the atmosphere field.
    """
    try:
        # Create database connection
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            print("Error: DATABASE_URL environment variable not set")
            return
            
        engine = create_engine(DATABASE_URL)
        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()
        
        try:
            # Get all conversations that might have atmosphere text in summary
            conversations = session.query(Bee_Conversation).filter(
                Bee_Conversation.summary.like('%Atmosphere%')
            ).all()
            
            if not conversations:
                print("No conversations found with potential atmosphere duplication.")
                return
                
            print(f"Found {len(conversations)} conversations with potential atmosphere text in summary.")
            
            updated_count = 0
            
            for conv in conversations:
                if not conv.summary or not conv.atmosphere:
                    continue
                    
                # Get the atmosphere content without any markdown/formatting
                atmosphere_content = conv.atmosphere.strip()
                
                # Define pattern to detect atmosphere section in summary
                # This will match:
                # 1. Lines starting with "Atmosphere" (with optional formatting)
                # 2. Followed by the atmosphere content
                patterns = [
                    # Look for "Atmosphere" heading followed by content
                    r'(?:^|\n)\s*(?:#+\s*)?Atmosphere(?::|\s*)?\s*\n([\s\S]*?)(?=\n\s*(?:#+\s*)?(?:Key|Summary|$)|\Z)',
                    
                    # Look for "Atmosphere" in bold (with optional colon) followed by content
                    r'(?:^|\n)\s*\*\*Atmosphere(?::)?\*\*\s*\n([\s\S]*?)(?=\n\s*(?:#+\s*)?(?:Key|Summary|$)|\Z)',
                    
                    # Simple text "Atmosphere" with optional colon
                    r'(?:^|\n)\s*Atmosphere(?::|\s*)?\s*\n([\s\S]*?)(?=\n\s*(?:#+\s*)?(?:Key|Summary|$)|\Z)'
                ]
                
                original_summary = conv.summary
                modified_summary = original_summary
                
                for pattern in patterns:
                    matches = re.finditer(pattern, modified_summary, re.MULTILINE)
                    for match in matches:
                        # Get the entire matched section including the "Atmosphere" heading
                        full_match = match.group(0)
                        # Remove the matched section from the summary
                        modified_summary = modified_summary.replace(full_match, '')
                
                # Clean up any double newlines left behind
                modified_summary = re.sub(r'\n{3,}', '\n\n', modified_summary)
                modified_summary = modified_summary.strip()
                
                if modified_summary != original_summary:
                    # Update the summary in the database
                    conv.summary = modified_summary
                    updated_count += 1
            
            if updated_count > 0:
                print(f"Updated {updated_count} conversation summaries to remove atmosphere duplication.")
                session.commit()
                print("Changes committed to database.")
            else:
                print("No changes needed.")
                
        except Exception as e:
            session.rollback()
            print(f"Error cleaning summary field: {str(e)}")
        finally:
            session.close()
            
    except Exception as e:
        print(f"Database connection error: {str(e)}")

def main():
    """Main function to run the summary cleaning process."""
    print("Starting summary cleaning process...")
    clean_summary_field()
    print("Process complete!")

if __name__ == "__main__":
    main()