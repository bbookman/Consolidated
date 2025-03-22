from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Bee_Conversation, Bee_Fact, Bee_Todo, Limitless_Lifelog
import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def store_lifelogs(lifelogs):
    """
    Store lifelogs in the database with deduplication.
    
    Args:
        lifelogs: List of lifelog dictionaries from Limitless API
    
    Returns:
        Dict with counts of items processed, added, and skipped
    """
    session = Session()
    try:
        # Initialize result with 0 processed in case we have an empty list or error
        result = {
            "processed": 0,
            "added": 0,
            "skipped": 0
        }
        
        # Skip processing if we get an empty list or a list with a single string 'lifelogs'
        if not lifelogs or (isinstance(lifelogs, list) and len(lifelogs) == 1 and isinstance(lifelogs[0], str) and lifelogs[0] == 'lifelogs'):
            logger.warning("Received empty or invalid lifelogs list, skipping")
            return result
            
        # Update processed count for valid list
        result["processed"] = len(lifelogs)
        
        for log in lifelogs:
            # Skip if it's a string that's just "lifelogs"
            if isinstance(log, str) and log == "lifelogs":
                logger.warning("Skipping string entry 'lifelogs'")
                result["skipped"] += 1
                continue
                
            # Handle both string and dictionary format for actual lifelog data
            if isinstance(log, str) and log != "lifelogs":
                # Try to parse the string as JSON
                try:
                    log_data = json.loads(log)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse lifelog string as JSON: {log[:30]}...")
                    result["skipped"] += 1
                    continue
            else:
                log_data = log
                
            # Skip if log_data is not a dictionary (e.g., it might be None or another type)
            if not isinstance(log_data, dict):
                logger.warning(f"Skipping non-dictionary lifelog data: {type(log_data)}")
                result["skipped"] += 1
                continue
                
            # Check if this lifelog already exists in the database
            log_id = str(log_data.get('id', ''))
            if not log_id:
                logger.warning("Skipping lifelog with no ID")
                result["skipped"] += 1
                continue
                
            existing = session.query(Limitless_Lifelog).filter_by(log_id=log_id).first()
            
            if existing:
                logger.info(f"Lifelog ID {log_id} already exists, skipping")
                result["skipped"] += 1
                continue
            
            try:
                # Extract tags if they exist
                tags = log_data.get('tags')
                if tags and isinstance(tags, list):
                    tags_json = json.dumps(tags)
                else:
                    tags_json = None
                
                # Create new lifelog record
                new_log = Limitless_Lifelog(
                    log_id=log_id,
                    title=log_data.get('title'),
                    description=log_data.get('description'),
                    created_at=parse_date(log_data.get('created_at')),
                    updated_at=parse_date(log_data.get('updated_at')),
                    log_type=log_data.get('type'),
                    tags=tags_json,
                    raw_data=json.dumps(log_data)
                )
                
                session.add(new_log)
                result["added"] += 1
                logger.info(f"Added lifelog with ID {log_id}")
            except Exception as e:
                logger.error(f"Error adding lifelog {log_id}: {str(e)}")
                result["skipped"] += 1
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in store_lifelogs: {str(e)}")
        # Return empty result if exception happens before result is initialized
        return {
            "processed": 0,
            "added": 0,
            "skipped": 0
        }
    finally:
        session.close()

def get_lifelogs_from_db():
    """Retrieve all lifelogs from the database."""
    session = Session()
    try:
        return session.query(Limitless_Lifelog).order_by(Limitless_Lifelog.created_at.desc()).all()
    finally:
        session.close()