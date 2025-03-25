"""
Script to extract remaining Key Take Aways from atmosphere field

This script scans the atmosphere column of all bee_conversations for any content
that starts with "Key Take Aways" or similar variations, and moves that content
to the key_takeaways column.
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

def extract_key_takeaways_from_atmosphere():
    """
    Extract key takeaways from atmosphere field if they exist.
    
    This function scans the atmosphere column for content after a 
    "Key Take Aways:" or "Key Takeaways:" heading and moves that content
    to the key_takeaways column.
    """
    try:
        # Get all conversations that might have key takeaways in atmosphere
        patterns = [
            '%Key Take Aways%', 
            '%Key Takeaways%', 
            '%Key takeaways%', 
            '%Key take aways%'
        ]
        
        condition = Bee_Conversation.atmosphere.like(patterns[0])
        for pattern in patterns[1:]:
            condition = condition | Bee_Conversation.atmosphere.like(pattern)
            
        conversations = session.query(Bee_Conversation).filter(condition).all()
        
        print(f"Found {len(conversations)} conversations with potential key takeaways in atmosphere field.")
        
        updated_count = 0
        for conv in conversations:
            # Skip if no atmosphere content
            if not conv.atmosphere:
                continue
                
            # Define regex pattern to match key takeaways section
            patterns = [
                r'Key Take Aways:?\s*([\s\S]*?)(?:\Z)',
                r'Key Takeaways:?\s*([\s\S]*?)(?:\Z)',
                r'Key takeaways:?\s*([\s\S]*?)(?:\Z)',
                r'Key take aways:?\s*([\s\S]*?)(?:\Z)'
            ]
            
            takeaways_content = None
            clean_atmosphere = conv.atmosphere
            
            # Try each pattern until we find a match
            for pattern in patterns:
                match = re.search(pattern, conv.atmosphere)
                if match:
                    takeaways_content = match.group(1).strip()
                    # Remove the key takeaways section from atmosphere
                    clean_atmosphere = re.sub(pattern, '', conv.atmosphere).strip()
                    break
            
            if takeaways_content:
                print(f"Found key takeaways in conversation ID {conv.id}")
                
                # Update key_takeaways column
                if conv.key_takeaways:
                    # If key_takeaways already has content, append the new content
                    print(f"Appending to existing key_takeaways for conversation ID {conv.id}")
                    conv.key_takeaways = f"{conv.key_takeaways}\n\n{takeaways_content}"
                else:
                    # Otherwise, just set the new content
                    conv.key_takeaways = takeaways_content
                
                # Update atmosphere to remove key takeaways section
                conv.atmosphere = clean_atmosphere
                
                updated_count += 1
        
        if updated_count > 0:
            session.commit()
            print(f"Successfully updated {updated_count} conversations.")
        else:
            print("No conversations needed updating.")
            
        return updated_count
            
    except Exception as e:
        session.rollback()
        print(f"Error: {str(e)}")
        return 0
    finally:
        session.close()

def main():
    """Main function to run the key takeaways extraction process."""
    print("Starting key takeaways extraction process...")
    start_time = datetime.now()
    
    updated_count = extract_key_takeaways_from_atmosphere()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"Key takeaways extraction completed in {duration:.2f} seconds.")
    print(f"Total conversations updated: {updated_count}")

if __name__ == "__main__":
    main()