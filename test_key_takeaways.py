"""
Test script to add sample key takeaways to verify JSON implementation
"""

import json
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Bee_Conversation

def add_sample_key_takeaways():
    """Add sample key takeaways to a few conversations to test JSON storage"""
    try:
        # Get database URL from environment variables
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            print("DATABASE_URL environment variable is not set")
            sys.exit(1)
        
        # Create SQLAlchemy engine and session
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get first 3 conversations
        conversations = session.query(Bee_Conversation).order_by(Bee_Conversation.id).limit(3).all()
        
        for i, conv in enumerate(conversations):
            # Create different sample key takeaways for each conversation
            if i == 0:
                key_takeaways = ["First important point about this conversation", 
                                "Second observation from the discussion", 
                                "Final conclusion reached"]
            elif i == 1:
                key_takeaways = ["Identified critical issue in project", 
                                "Discussed potential solutions", 
                                "Agreed on next steps", 
                                "Set timeline for implementation"]
            else:
                key_takeaways = ["Reviewed recent performance metrics", 
                                "Notable improvement in customer satisfaction", 
                                "Areas needing attention: response time", 
                                "Action item: schedule follow-up meeting"]
            
            # Update the conversation with JSON array
            conv.key_takeaways = key_takeaways
            print(f"Added {len(key_takeaways)} key takeaways to conversation {conv.id}")
        
        # Commit changes
        session.commit()
        print("Successfully added sample key takeaways to test conversations")
        
    except Exception as e:
        print(f"Error adding sample key takeaways: {e}")
        if 'session' in locals():
            session.rollback()
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    add_sample_key_takeaways()