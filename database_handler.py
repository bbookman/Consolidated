from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Bee_Conversation, Bee_Fact, Bee_Todo
import os
import json
from datetime import datetime

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a sessionmaker
Session = sessionmaker(bind=engine)

def parse_date(date_str):
    """Parse date string to datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None

def store_conversations(conversations):
    """
    Store conversations in the database with deduplication.
    
    Args:
        conversations: List of conversation dictionaries from Bee API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        result = {
            "processed": len(conversations),
            "added": 0,
            "skipped": 0
        }
        
        for conv in conversations:
            # Check if this conversation already exists in the database
            conv_id = str(conv.get('id', ''))
            existing = session.query(Bee_Conversation).filter_by(conversation_id=conv_id).first()
            
            if existing:
                result["skipped"] += 1
                continue
            
            # Get location data if it exists
            location = conv.get('primary_location', {})
            address = location.get('address') if location else None
            latitude = location.get('latitude') if location else None
            longitude = location.get('longitude') if location else None
            
            # Create new conversation record
            new_conv = Bee_Conversation(
                conversation_id=conv_id,
                summary=conv.get('summary'),
                created_at=parse_date(conv.get('created_at')),
                address=address,
                latitude=latitude,
                longitude=longitude,
                raw_data=json.dumps(conv)
            )
            
            session.add(new_conv)
            result["added"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def store_facts(facts):
    """
    Store facts in the database with deduplication.
    
    Args:
        facts: List of fact dictionaries from Bee API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        result = {
            "processed": len(facts),
            "added": 0,
            "skipped": 0
        }
        
        for fact in facts:
            fact_text = fact.get('text')
            if not fact_text:
                result["skipped"] += 1
                continue
                
            # Check if this fact already exists in the database
            existing = session.query(Bee_Fact).filter_by(text=fact_text).first()
            
            if existing:
                result["skipped"] += 1
                continue
            
            # Create new fact record
            new_fact = Bee_Fact(
                fact_id=str(fact.get('id', '')),
                text=fact_text,
                created_at=parse_date(fact.get('created_at')),
                raw_data=json.dumps(fact)
            )
            
            session.add(new_fact)
            result["added"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def store_todos(todos):
    """
    Store todos in the database with deduplication.
    
    Args:
        todos: List of todo dictionaries from Bee API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        result = {
            "processed": len(todos),
            "added": 0,
            "skipped": 0
        }
        
        for todo in todos:
            # Check if this todo already exists in the database
            todo_id = str(todo.get('id', ''))
            existing = session.query(Bee_Todo).filter_by(todo_id=todo_id).first()
            
            if existing:
                result["skipped"] += 1
                continue
            
            # Create new todo record
            new_todo = Bee_Todo(
                todo_id=todo_id,
                task=todo.get('text', 'No task description'),
                completed=todo.get('completed', False),
                created_at=parse_date(todo.get('created_at')),
                raw_data=json.dumps(todo)
            )
            
            session.add(new_todo)
            result["added"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_conversations_from_db():
    """Retrieve all conversations from the database."""
    session = Session()
    try:
        return session.query(Bee_Conversation).order_by(Bee_Conversation.created_at.desc()).all()
    finally:
        session.close()

def get_facts_from_db():
    """Retrieve all facts from the database."""
    session = Session()
    try:
        return session.query(Bee_Fact).order_by(Bee_Fact.created_at.desc()).all()
    finally:
        session.close()

def get_todos_from_db():
    """Retrieve all todos from the database."""
    session = Session()
    try:
        return session.query(Bee_Todo).order_by(Bee_Todo.created_at.desc()).all()
    finally:
        session.close()