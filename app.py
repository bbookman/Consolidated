#!/usr/bin/env python3
"""
Multi-API Data Collection CLI

This script provides a command-line interface for collecting and storing data from 
multiple APIs (Bee AI and Limitless) into a database and JSON files.
"""

import sys
import os
import json
import traceback
import logging
import asyncio
from datetime import datetime
from beeai import Bee
import pytz

from limitless_api import LimitlessAPI
import database_handler as db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize API clients
bee = None
limitless = None

def initialize_apis():
    """Initialize API clients with keys from environment variables"""
    global bee, limitless
    
    # Initialize Bee API
    bee_api_key = os.environ.get('BEE_API_KEY')
    if bee_api_key:
        bee = Bee(api_key=bee_api_key)
        logger.info("Bee API client initialized successfully")
    else:
        logger.warning("BEE_API_KEY not found in environment variables")

    # Initialize Limitless API
    limitless_api_key = os.environ.get('LIMITLESS_API_KEY')
    if limitless_api_key:
        limitless = LimitlessAPI(api_key=limitless_api_key)
        logger.info("Limitless API client initialized successfully")
    else:
        logger.warning("LIMITLESS_API_KEY not found in environment variables")

def format_conversation(conv):
    """Format a conversation object from the Bee API for display/storage"""
    # Clean up the summary
    summary = conv.get("summary", "No summary available")
    
    # Handle None summary value
    if summary is None:
        summary = "No summary available"
    # Normal processing if summary exists
    else:
        if summary.startswith("## Summary\n"):
            summary = summary[len("## Summary\n"):]
        if summary.startswith("Summary: "):
            summary = summary[len("Summary: "):]
        if summary.startswith("Summary\n"):
            summary = summary[len("Summary\n"):]
    
    # Get address from primary_location if it exists
    address = "No address"
    if conv.get("primary_location") and conv["primary_location"].get("address"):
        address = conv["primary_location"]["address"]
    
    latitude = None
    longitude = None
    if conv.get("primary_location") and conv["primary_location"].get("latitude") and conv["primary_location"].get("longitude"):
        latitude = conv["primary_location"]["latitude"]
        longitude = conv["primary_location"]["longitude"]
    
    # Extract start and end times
    start_time = None
    end_time = None
    created_at = None
    
    if conv.get("start_time"):
        start_time = conv["start_time"]
    if conv.get("end_time"):
        end_time = conv["end_time"]
    if conv.get("created_at"):
        created_at = conv["created_at"]
    
    return {
        "Title": f"Conversation on {created_at[:10] if created_at else 'Unknown Date'}",
        "Summary": summary,
        "Address": address,
        "Start Time": start_time,
        "End Time": end_time,
        "Created At": created_at,
        "Latitude": latitude,
        "Longitude": longitude
    }

def format_fact(fact):
    """Format a fact object from the Bee API for display/storage"""
    return {
        "Text": fact.get("text", "No text available"),
        "Created At": fact.get("created_at", "Unknown date")
    }

def format_todo(todo):
    """Format a todo object from the Bee API for display/storage"""
    return {
        "Task": todo.get("task", "No task description"),
        "Completed": "Yes" if todo.get("completed", False) else "No",
        "Created At": todo.get("created_at", "Unknown date")
    }

def format_lifelog(log):
    """Format a lifelog object from the Limitless API for display/storage"""
    title = "No title available"
    description = "No description available"
    tags = "No tags"
    log_type = "Unknown type"
    created_at = "Unknown date"
    updated_at = None
    
    # Extract title from contents if possible
    contents = log.get("contents", [])
    if contents and isinstance(contents, list):
        for item in contents:
            if isinstance(item, dict) and item.get("type") == "heading1" and item.get("content"):
                title = item.get("content")
                break
    
    # Use metadata or fallback to contents for description
    if log.get("metadata") and log.get("metadata").get("description"):
        description = log.get("metadata").get("description")
    elif contents and len(contents) > 1:
        for item in contents:
            if isinstance(item, dict) and item.get("type") == "heading2" and item.get("content"):
                description = item.get("content")
                break
    
    # Get tags if available
    if log.get("tags") and isinstance(log.get("tags"), list):
        tags = ", ".join(log.get("tags"))
    
    # Get type if available
    if log.get("type"):
        log_type = log.get("type")
    
    # Get timestamps
    if log.get("createdAt"):
        created_at = log.get("createdAt")
    if log.get("updatedAt"):
        updated_at = log.get("updatedAt")
    
    return {
        "Title": title,
        "Description": description,
        "Tags": tags,
        "Type": log_type,
        "Created At": created_at,
        "Updated At": updated_at
    }

async def fetch_all_pages(fetch_func, user_id):
    """
    Fetch all pages of data from a paginated API endpoint
    
    Args:
        fetch_func: The API function to call (e.g., bee.get_conversations)
        user_id: The user ID to fetch data for (typically "me")
        
    Returns:
        A list of all items fetched across all pages
    """
    logger.info(f"Fetching all pages for {fetch_func.__name__} and user {user_id}")
    
    try:
        # Get the first page to determine total pages
        response = await fetch_func(user_id, page=1)
        logger.info(f"First response type: {type(response)}")
        
        # Handle different response formats
        all_items = []
        
        if isinstance(response, dict):
            # Add items from first page
            if 'data' in response and isinstance(response['data'], dict) and 'lifelogs' in response['data']:
                # New API format with data.lifelogs structure
                all_items.extend(response['data']['lifelogs'])
                total_pages = response.get('meta', {}).get('pages', 1)
            else:
                # Standard API format
                item_key = next((key for key in ['conversations', 'facts', 'todos', 'lifelogs'] if key in response), None)
                if item_key:
                    all_items.extend(response[item_key])
                    total_pages = response.get('totalPages', 1)
                else:
                    # Unknown format, just return the response
                    return response
            
            logger.info(f"Found {total_pages} total pages")
            
            # Fetch remaining pages
            for page in range(2, total_pages + 1):
                logger.info(f"Fetching page {page} of {total_pages}")
                page_response = await fetch_func(user_id, page=page)
                
                # Add items from this page
                if 'data' in page_response and isinstance(page_response['data'], dict) and 'lifelogs' in page_response['data']:
                    all_items.extend(page_response['data']['lifelogs'])
                else:
                    item_key = next((key for key in ['conversations', 'facts', 'todos', 'lifelogs'] if key in page_response), None)
                    if item_key:
                        all_items.extend(page_response[item_key])
        
        elif isinstance(response, list):
            # Direct list response
            all_items = response
        
        logger.info(f"Fetched {len(all_items)} items in total")
        return all_items
        
    except Exception as e:
        logger.error(f"Error fetching all pages: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def save_to_file(data, data_type, original_data):
    """
    Save data to JSON files in the appropriate API-specific directory
    
    Args:
        data: List of formatted data items (not used - kept for backward compatibility)
        data_type: Type of data (conversations, facts, todos, lifelogs)
        original_data: Raw data from API
    """
    # Check if there's any data to save
    if not original_data or (isinstance(original_data, dict) and 
                            all(not original_data.get(k) for k in original_data)):
        logger.info(f"No data to save for {data_type}, skipping file creation")
        return True
        
    try:
        # Determine which API the data is from
        api_name = "bee"
        if data_type == "lifelogs" or data_type.startswith("db_lifelogs"):
            api_name = "limitless"
        
        # Create directories if they don't exist (only if we have data to save)
        data_dir = os.path.join("data", api_name)
        os.makedirs(data_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_type}_{timestamp}.json"
        filepath = os.path.join(data_dir, filename)
        
        logger.info(f"Using API directory: {os.path.abspath(data_dir)}")
        
        # Check if we should skip saving if the data is the same as the latest file
        last_file = find_latest_file(data_dir, data_type)
        if last_file:
            with open(last_file, 'r') as f:
                try:
                    existing_data = json.load(f)
                    if existing_data == original_data:
                        logger.info(f"Data for {data_type} is identical to the latest file, not saving")
                        return True
                except json.JSONDecodeError:
                    # If there's an error parsing the previous file, we'll save a new one
                    pass
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(original_data, f, indent=2)
            
        logger.info(f"Saved {data_type} data to {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving {data_type} to file: {str(e)}")
        return False

def find_latest_file(directory, prefix):
    """Find the most recent file with the given prefix in the directory"""
    try:
        files = [os.path.join(directory, f) for f in os.listdir(directory) 
                if f.startswith(prefix) and f.endswith('.json')]
        if not files:
            return None
        return max(files, key=os.path.getmtime)
    except Exception as e:
        logger.error(f"Error finding latest file: {str(e)}")
        return None

async def run_cli_async():
    """
    CLI entry point for the application (async version). Fetches data from API, stores in database,
    and then saves database content to JSON files to avoid duplicates.
    """
    try:
        # Step 1: Fetch data from API and store in database
        print("Fetching conversations from API...")
        conversations = await fetch_all_pages(bee.get_conversations, "me")
        if isinstance(conversations, dict):
            conversations_list = conversations.get('conversations', [])
        else:
            conversations_list = conversations
        print(f"Fetched {len(conversations_list)} conversations")
        
        print("Fetching facts from API...")
        facts = await fetch_all_pages(bee.get_facts, "me")
        if isinstance(facts, dict):
            facts_list = facts.get('facts', [])
        else:
            facts_list = facts
        print(f"Fetched {len(facts_list)} facts")
        
        print("Fetching todos from API...")
        todos = await fetch_all_pages(bee.get_todos, "me")
        if isinstance(todos, dict):
            todos_list = todos.get('todos', [])
        else:
            todos_list = todos
        print(f"Fetched {len(todos_list)} todos")
        
        # Fetch lifelogs from Limitless API if available
        lifelogs_list = []
        if limitless:
            print("Fetching lifelogs from Limitless API...")
            try:
                # Create a wrapper function that doesn't require user_id parameter
                async def get_lifelogs_wrapper(dummy=None, page=1):
                    return await limitless.get_lifelogs(page=page)
                
                lifelogs = await fetch_all_pages(get_lifelogs_wrapper, "dummy")
                print(f"Debug - lifelogs type: {type(lifelogs)}")
                
                # Fix case where lifelogs_list is a list with a string like ['lifelogs']
                if isinstance(lifelogs, list) and len(lifelogs) == 1 and isinstance(lifelogs[0], str) and lifelogs[0] == 'lifelogs':
                    print("Detected invalid lifelog list format, replacing with empty list")
                    lifelogs_list = []
                # Normal processing for dictionary response with 'lifelogs' key
                elif isinstance(lifelogs, dict):
                    if 'data' in lifelogs and isinstance(lifelogs['data'], dict) and 'lifelogs' in lifelogs['data']:
                        # New API format
                        lifelogs_list = lifelogs['data']['lifelogs']
                    else:
                        # Standard format
                        lifelogs_list = lifelogs.get('lifelogs', [])
                    print(f"Debug - lifelogs_list type: {type(lifelogs_list)}")
                    print(f"Debug - lifelogs_list content sample: {str(lifelogs_list)[:100]}")
                # Fallback for direct list
                else:
                    # Only use direct list if it contains dictionaries/objects, not strings
                    if isinstance(lifelogs, list) and (not lifelogs or isinstance(lifelogs[0], dict)):
                        lifelogs_list = lifelogs
                    else:
                        lifelogs_list = []
                        print("Unexpected lifelogs format, using empty list")
                    print(f"Debug - lifelogs_list (direct) type: {type(lifelogs_list)}")
                    print(f"Debug - lifelogs_list (direct) content sample: {str(lifelogs_list)[:100]}")
                print(f"Fetched {len(lifelogs_list)} lifelogs")
            except Exception as e:
                print(f"Error fetching lifelogs: {str(e)}")
                print(traceback.format_exc())
        else:
            print("Limitless API client not initialized - skipping lifelogs")
        
        # Step 2: Store in database with deduplication
        print("Storing in database...")
        db_conversations_result = db.store_conversations(conversations_list)
        db_facts_result = db.store_facts(facts_list)
        db_todos_result = db.store_todos(todos_list)
        
        # Store lifelogs if available
        db_lifelogs_result = {"processed": 0, "added": 0, "skipped": 0}
        if lifelogs_list:
            db_lifelogs_result = db.store_lifelogs(lifelogs_list)
        
        # Print database results
        print(f"\nDatabase Results:")
        print(f"Conversations: {db_conversations_result['processed']} processed, {db_conversations_result['added']} added, {db_conversations_result['skipped']} skipped")
        print(f"Facts: {db_facts_result['processed']} processed, {db_facts_result['added']} added, {db_facts_result['skipped']} skipped")
        print(f"Todos: {db_todos_result['processed']} processed, {db_todos_result['added']} added, {db_todos_result['skipped']} skipped")
        print(f"Lifelogs: {db_lifelogs_result['processed']} processed, {db_lifelogs_result['added']} added, {db_lifelogs_result['skipped']} skipped")
        
        # Step 3: Retrieve from database and save to JSON files
        print("\nRetrieving from database and saving to JSON files...")
        
        # Get conversations from database
        print("Processing conversations from database...")
        db_conversations = db.get_conversations_from_db()
        print(f"Retrieved {len(db_conversations)} conversations from database")
        
        # Format data for saving
        formatted_conversations = []
        conversation_raw_data = []
        
        for conv in db_conversations:
            # Convert from SQLAlchemy object to dictionary
            formatted_conv = {
                "Summary": conv.summary if conv.summary else "No summary available",
                "Created At": conv.created_at.isoformat() if conv.created_at else "Unknown",
                "Address": conv.address if conv.address else "No address"
            }
            formatted_conversations.append(formatted_conv)
            
            # Get raw data if available
            if conv.raw_data:
                try:
                    conversation_raw_data.append(json.loads(conv.raw_data))
                except:
                    print(f"Warning: Could not parse raw_data for conversation {conv.id}")
        
        # Save conversations to file
        saved_conv = save_to_file(
            formatted_conversations, 
            'conversations', 
            {'conversations': conversation_raw_data}
        )
        if saved_conv:
            print("Successfully processed conversations to JSON")
        
        # Get facts from database
        print("Processing facts from database...")
        db_facts = db.get_facts_from_db()
        print(f"Retrieved {len(db_facts)} facts from database")
        
        # Format data for saving
        formatted_facts = []
        fact_raw_data = []
        
        for fact in db_facts:
            # Convert from SQLAlchemy object to dictionary
            formatted_fact = {
                "Text": fact.text,
                "Created At": fact.created_at.isoformat() if fact.created_at else "Unknown"
            }
            formatted_facts.append(formatted_fact)
            
            # Get raw data if available
            if fact.raw_data:
                try:
                    fact_raw_data.append(json.loads(fact.raw_data))
                except:
                    print(f"Warning: Could not parse raw_data for fact {fact.id}")
        
        # Save facts to file
        saved_facts = save_to_file(
            formatted_facts, 
            'facts', 
            {'facts': fact_raw_data}
        )
        if saved_facts:
            print("Successfully processed facts to JSON")
        
        # Get todos from database
        print("Processing todos from database...")
        db_todos = db.get_todos_from_db()
        print(f"Retrieved {len(db_todos)} todos from database")
        
        # Format data for saving
        formatted_todos = []
        todo_raw_data = []
        
        for todo in db_todos:
            # Convert from SQLAlchemy object to dictionary
            formatted_todo = {
                "Task": todo.task,
                "Completed": "Yes" if todo.completed else "No",
                "Created At": todo.created_at.isoformat() if todo.created_at else "Unknown"
            }
            formatted_todos.append(formatted_todo)
            
            # Get raw data if available
            if todo.raw_data:
                try:
                    todo_raw_data.append(json.loads(todo.raw_data))
                except:
                    print(f"Warning: Could not parse raw_data for todo {todo.id}")
        
        # Save todos to file
        saved_todos = save_to_file(
            formatted_todos, 
            'todos', 
            {'todos': todo_raw_data}
        )
        if saved_todos:
            print("Successfully processed todos to JSON")
        
        # Get lifelogs from database if available
        if limitless:
            print("Processing lifelogs from database...")
            db_lifelogs = db.get_lifelogs_from_db()
            print(f"Retrieved {len(db_lifelogs)} lifelogs from database")
            
            # Format data for saving
            formatted_lifelogs = []
            lifelog_raw_data = []
            
            for lifelog in db_lifelogs:
                # Convert from SQLAlchemy object to dictionary
                formatted_lifelog = {
                    "Title": lifelog.title if lifelog.title else "No title available",
                    "Description": lifelog.description if lifelog.description else "No description available",
                    "Type": lifelog.log_type if lifelog.log_type else "Unknown type",
                    "Tags": lifelog.tags if lifelog.tags else "No tags",
                    "Created At": lifelog.created_at.isoformat() if lifelog.created_at else "Unknown",
                    "Updated At": lifelog.updated_at.isoformat() if lifelog.updated_at else "Unknown"
                }
                formatted_lifelogs.append(formatted_lifelog)
                
                # Get raw data if available
                if lifelog.raw_data:
                    try:
                        lifelog_raw_data.append(json.loads(lifelog.raw_data))
                    except:
                        print(f"Warning: Could not parse raw_data for lifelog {lifelog.id}")
            
            # Save lifelogs to file
            saved_lifelogs = save_to_file(
                formatted_lifelogs, 
                'lifelogs', 
                {'lifelogs': lifelog_raw_data}
            )
            if saved_lifelogs:
                print("Successfully processed lifelogs to JSON")
        
        print("\nData collection complete!")
        
    except Exception as e:
        print(f"Error in CLI data collection: {str(e)}")
        print(traceback.format_exc())

def run_cli():
    """
    CLI entry point for the application. Fetches data from API, stores in database,
    and then saves database content to JSON files to avoid duplicates.
    """
    print("Starting Multi-API Data Collector CLI")
    
    # Delete the data directory if it exists
    data_dir = os.path.join("data")
    if os.path.exists(data_dir):
        print(f"Removing old data directory: {os.path.abspath(data_dir)}")
        import shutil
        try:
            shutil.rmtree(data_dir)
            print("Old data directory removed successfully")
        except Exception as e:
            print(f"Error removing data directory: {str(e)}")
    
    initialize_apis()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cli_async())

if __name__ == '__main__':
    run_cli()