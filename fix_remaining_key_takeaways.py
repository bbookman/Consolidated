"""
Script to fix remaining Key Takeaways in atmosphere field

This script scans the atmosphere column for any content that contains 
"Key Take aways" or "Key Takeaways", extracts that content to the 
key_takeaways column, and removes it from the atmosphere column.
"""

import re
import os
import logging
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Bee_Conversation

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_remaining_key_takeaways_from_atmosphere():
    """
    Extract any remaining key takeaways from atmosphere field if they exist.
    
    This function scans the atmosphere column for "Key Take aways" or "Key Takeaways"
    and moves that content to the key_takeaways column, removing it from atmosphere.
    """
    # Connect to the database
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///life_journal.db')
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Find all conversations with "Key Take aways" or "Key Takeaways" in atmosphere
    conversations = session.query(Bee_Conversation).filter(
        (Bee_Conversation.atmosphere.like('%Key Take aways%')) | 
        (Bee_Conversation.atmosphere.like('%Key Takeaways%'))
    ).all()
    
    logger.info(f"Found {len(conversations)} conversations with Key Takeaways in atmosphere")
    
    updated_count = 0
    
    for conversation in conversations:
        # Parse the atmosphere text to separate atmosphere from key takeaways
        atmosphere_text = conversation.atmosphere if conversation.atmosphere else ""
        
        # Check for the specific patterns we're looking for
        key_takeaways_match = re.search(r'Key Take ?[Aa]ways:?([\s\S]*?)$', atmosphere_text)
        
        if key_takeaways_match:
            # Extract the key takeaways content
            key_takeaways_content = key_takeaways_match.group(1).strip()
            
            # Extract the atmosphere content (everything before Key Takeaways)
            atmosphere_content = atmosphere_text[:key_takeaways_match.start()].strip()
            
            logger.info(f"Conversation {conversation.conversation_id}: Extracting key takeaways")
            logger.info(f"  - Original atmosphere length: {len(atmosphere_text)}")
            logger.info(f"  - New atmosphere length: {len(atmosphere_content)}")
            logger.info(f"  - Key takeaways length: {len(key_takeaways_content)}")
            
            # Update the fields
            conversation.atmosphere = atmosphere_content
            
            # If there's already content in key_takeaways, append to it
            if conversation.key_takeaways and conversation.key_takeaways.strip():
                conversation.key_takeaways += f"\n\n{key_takeaways_content}"
            else:
                conversation.key_takeaways = key_takeaways_content
                
            updated_count += 1
    
    # Commit the changes
    session.commit()
    logger.info(f"Updated {updated_count} conversations")
    session.close()
    
    return updated_count
    
def main():
    """Main function to run the key takeaways extraction process."""
    logger.info("Starting extraction of remaining key takeaways from atmosphere column")
    updated_count = extract_remaining_key_takeaways_from_atmosphere()
    logger.info(f"Extraction complete. Updated {updated_count} conversations")
    
if __name__ == "__main__":
    main()