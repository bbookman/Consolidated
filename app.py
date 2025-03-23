from flask import Flask, render_template, request, jsonify
import sys
from io import StringIO
import traceback
import asyncio
import os
from beeai import Bee
import json
from datetime import datetime
from functools import wraps
import database_handler as db
from limitless_api import limitless, LimitlessAPI

app = Flask(__name__)
bee = Bee(os.environ.get('BEE_API_KEY'))

# Initialize Limitless API if it wasn't initialized in the module
if limitless is None and os.environ.get('LIMITLESS_API_KEY'):
    try:
        limitless = LimitlessAPI(os.environ.get('LIMITLESS_API_KEY'))
        app.logger.info("Limitless API client initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize Limitless API client: {str(e)}")

def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

def format_conversation(conv):
    # Clean up the summary by removing duplicate headers
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
    
    return {
        "Summary": summary,
        "Created At": conv.get("created_at", "Unknown"),
        "Address": address
    }

def format_fact(fact):
    # Handle None values
    text = fact.get("text")
    if text is None:
        text = "No text available"
    
    return {
        "Text": text,
        "Created At": fact.get("created_at", "Unknown")
    }

def format_todo(todo):
    # Handle None values
    task = todo.get("text")
    if task is None:
        task = "No task description"
        
    return {
        "Task": task,
        "Completed": "Yes" if todo.get("completed") else "No",
        "Created At": todo.get("created_at", "Unknown")
    }

def format_lifelog(log):
    # Handle None values
    title = log.get("title")
    if title is None:
        title = "No title available"
        
    description = log.get("description")
    if description is None:
        description = "No description available"
    
    # Format tags if they exist
    tags = log.get("tags", [])
    tags_str = ", ".join(tags) if tags else "No tags"
    
    return {
        "Title": title,
        "Description": description,
        "Type": log.get("type", "Unknown type"),
        "Tags": tags_str,
        "Created At": log.get("created_at", "Unknown"),
        "Updated At": log.get("updated_at", "Unknown")
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
    app.logger.info(f"Fetching all pages for {fetch_func.__name__} and user {user_id}")
    all_items = []
    
    try:
        # Get the first page
        first_response = await fetch_func(user_id)
        app.logger.info(f"First response type: {type(first_response)}")
        
        # Determine the response structure
        if not isinstance(first_response, dict):
            app.logger.warning(f"Unexpected response format: {type(first_response)}")
            return first_response
        
        # Find the data key (conversations, facts, todos, lifelogs)
        items_key = None
        for key in ['conversations', 'facts', 'todos', 'lifelogs']:
            if key in first_response:
                items_key = key
                break
                
        if not items_key:
            app.logger.warning(f"Could not determine items key in: {first_response.keys()}")
            # Special case for Limitless API which might return data differently
            if 'data' in first_response:
                app.logger.info("Found 'data' key in response, using it for Limitless API")
                all_items.extend(first_response['data'])
                
                # Handle pagination differently for Limitless API
                if 'meta' in first_response and 'last_page' in first_response['meta']:
                    total_pages = first_response['meta']['last_page']
                    app.logger.info(f"Found {total_pages} total pages in Limitless API response")
                    
                    # Fetch remaining pages
                    for page in range(2, total_pages + 1):
                        try:
                            app.logger.info(f"Fetching page {page} of {total_pages}")
                            response = await fetch_func(page=page)
                            if 'data' in response:
                                all_items.extend(response['data'])
                        except Exception as e:
                            app.logger.error(f"Error fetching page {page}: {str(e)}")
                            break
                
                return all_items
            
            return []
            
        # Get items from first page
        if items_key in first_response and first_response[items_key]:
            all_items.extend(first_response[items_key])
            
        # Get total pages
        total_pages = first_response.get('totalPages', 1)
        app.logger.info(f"Found {total_pages} total pages")
        
        # Fetch remaining pages
        for page in range(2, total_pages + 1):
            try:
                app.logger.info(f"Fetching page {page} of {total_pages}")
                response = await fetch_func(user_id, page=page)
                if items_key in response and response[items_key]:
                    all_items.extend(response[items_key])
            except Exception as e:
                app.logger.error(f"Error fetching page {page}: {str(e)}")
                break
    except Exception as e:
        app.logger.error(f"Error in fetch_all_pages: {str(e)}")
        app.logger.error(traceback.format_exc())
        
    app.logger.info(f"Fetched {len(all_items)} items in total")
    return all_items

def save_to_file(data, data_type, original_data):
    """
    Save data to JSON files in the appropriate API-specific directory
    
    Args:
        data: List of formatted data items (not used - kept for backward compatibility)
        data_type: Type of data (conversations, facts, todos, lifelogs)
        original_data: Raw data from API
    """
    try:
        # Get absolute path for data directory
        current_dir = os.getcwd()
        data_dir = os.path.join(current_dir, 'data')
        
        # Ensure all directories exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Create consolidated_summaries directory
        consolidated_dir = os.path.join(data_dir, 'consolidated_summaries')
        os.makedirs(consolidated_dir, exist_ok=True)
        
        # Determine which API subdirectory to use
        if data_type == 'lifelogs':
            api_subdir = 'limitless'
        else:
            api_subdir = 'bee'
            
        # Create API-specific directory
        api_dir = os.path.join(data_dir, api_subdir)
        os.makedirs(api_dir, exist_ok=True)
        
        app.logger.info(f"Using API directory: {api_dir}")
        
        # Check for existing files of this data type
        existing_files = [f for f in os.listdir(api_dir) if f.startswith(data_type) and f.endswith('.json')]
        
        # Extract the actual data from the response dict
        key_map = {
            'conversations': 'conversations',
            'facts': 'facts',
            'todos': 'todos',
            'lifelogs': 'lifelogs'
        }
        data_key = key_map.get(data_type)
        
        if not data_key or data_key not in original_data:
            # If we can't find the key in the response or it's missing, use the whole response
            current_data = original_data
        else:
            current_data = original_data[data_key]
        
        # Check if we need to save new data
        new_data_to_save = True
        latest_data = None
        
        # If we have existing files, check if the data is different
        if existing_files:
            # Sort by timestamp to get the latest file
            latest_file = sorted(existing_files)[-1]
            latest_file_path = os.path.join(api_dir, latest_file)
            
            try:
                with open(latest_file_path, 'r') as f:
                    latest_data = json.load(f)
                
                # Compare data considering potential structure differences
                if data_key in latest_data and data_key in original_data:
                    if json.dumps(sorted(latest_data[data_key], key=lambda x: json.dumps(x, sort_keys=True))) == \
                       json.dumps(sorted(original_data[data_key], key=lambda x: json.dumps(x, sort_keys=True))):
                        new_data_to_save = False
                        app.logger.info(f"Data for {data_type} is identical to the latest file, not saving")
                        return True
                elif json.dumps(latest_data, sort_keys=True) == json.dumps(original_data, sort_keys=True):
                    new_data_to_save = False
                    app.logger.info(f"Data for {data_type} is identical to the latest file, not saving")
                    return True
            except Exception as e:
                app.logger.warning(f"Error checking existing data, will save new file: {str(e)}")
                new_data_to_save = True
        
        # Only save if there's new data
        if new_data_to_save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = os.path.join(api_dir, f"{data_type}_{timestamp}.json")
            app.logger.info(f"Saving new JSON data to {json_file}")
            
            with open(json_file, 'w') as f:
                json.dump(original_data, f, indent=2)
                
            app.logger.info(f"Successfully wrote JSON file to {json_file}")
        
        return True
        
    except Exception as e:
        app.logger.error(f"Error saving data to file: {str(e)}")
        app.logger.error(traceback.format_exc())
        return False

@app.route('/')
@async_route
async def index():
    """
    Main route that automatically loads data when the page is loaded.
    Fetches all conversations, facts, and todos from the Bee API
    and saves them to the database and files.
    """
    app.logger.info("Homepage accessed - automatically fetching data")
    try:
        # Fetch all data types from the API
        conversations_data = await fetch_all_pages(bee.get_conversations, "me")
        facts_data = await fetch_all_pages(bee.get_facts, "me")
        todos_data = await fetch_all_pages(bee.get_todos, "me")
        
        # Format the data for display
        # Handle both list and dictionary return types
        if isinstance(conversations_data, dict):
            conversations_list = conversations_data.get('conversations', [])
        else:
            conversations_list = conversations_data
            
        if isinstance(facts_data, dict):
            facts_list = facts_data.get('facts', [])
        else:
            facts_list = facts_data
            
        if isinstance(todos_data, dict):
            todos_list = todos_data.get('todos', [])
        else:
            todos_list = todos_data
        
        formatted_conversations = [format_conversation(conv) for conv in conversations_list]
        formatted_facts = [format_fact(fact) for fact in facts_list]
        formatted_todos = [format_todo(todo) for todo in todos_list]
        
        # Save to files
        save_to_file(formatted_conversations, 'conversations', conversations_data)
        save_to_file(formatted_facts, 'facts', facts_data)
        save_to_file(formatted_todos, 'todos', todos_data)
        
        # Store in database with deduplication
        db_conversations_result = db.store_conversations(conversations_list)
        db_facts_result = db.store_facts(facts_list)
        db_todos_result = db.store_todos(todos_list)
        
        # Prepare data for initial render
        initial_data = {
            'conversations': formatted_conversations,
            'facts': formatted_facts,
            'todos': formatted_todos,
            'db_stats': {
                'conversations': db_conversations_result,
                'facts': db_facts_result,
                'todos': db_todos_result
            }
        }
        
        # Pass data to template for initial render
        return render_template('index.html', initial_data=json.dumps(initial_data), datetime=datetime)
    except Exception as e:
        app.logger.error(f"Error in automatic data fetching: {str(e)}")
        # Return template without data in case of error
        return render_template('index.html', initial_data=json.dumps({
            'error': str(e)
        }), datetime=datetime)

@app.route('/execute', methods=['POST'])
def execute_code():
    code = request.json.get('code', '')

    stdout = StringIO()
    stderr = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.stdout = stdout
        sys.stderr = stderr

        exec(code, {})

        output = stdout.getvalue()
        error = stderr.getvalue()

        return jsonify({
            'success': True,
            'output': output,
            'error': error
        })

    except Exception as e:
        error_msg = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        })

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

@app.route('/api/conversations', methods=['GET'])
@async_route
async def get_conversations():
    try:
        page = int(request.args.get('page', 1))

        # Debug the API key
        api_key = os.environ.get('BEE_API_KEY')
        if not api_key:
            app.logger.error("BEE_API_KEY is not set in environment variables")
            return {'error': 'API key is not configured'}, 500
        
        app.logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:]} (length: {len(api_key)})")
        
        # Try to get conversations with direct debug
        try:
            app.logger.info("Attempting to fetch conversations directly")
            conversations_response = await bee.get_conversations("me", page=page)
            app.logger.info(f"Direct API response type: {type(conversations_response)}")
            app.logger.info(f"Direct API response content: {conversations_response}")
        except Exception as direct_err:
            app.logger.error(f"Direct API call error: {str(direct_err)}")
            return {'error': f'Direct API error: {str(direct_err)}'}, 500

        # Fetch all pages for saving
        all_conversations = await fetch_all_pages(bee.get_conversations, "me")
        app.logger.info(f"All conversations count: {len(all_conversations)}")
        formatted_all_conversations = [format_conversation(conv) for conv in all_conversations]

        # Save complete dataset to file
        save_to_file(formatted_all_conversations, 'conversations', {'conversations': all_conversations})
        
        # Store conversations in database with deduplication
        db_result = db.store_conversations(all_conversations)
        app.logger.info(f"Database storage result: {db_result}")

        # Get current page data for display
        conversations = await bee.get_conversations("me", page=page)
        formatted_conversations = [format_conversation(conv) for conv in conversations.get('conversations', [])]

        paginated_data = {
            'conversations': formatted_conversations,
            'total': conversations.get('totalCount', 0),
            'page': page,
            'per_page': len(formatted_conversations),
            'total_pages': conversations.get('totalPages', 1)
        }

        return paginated_data

    except Exception as e:
        app.logger.error(f"Error in get_conversations: {str(e)}")
        app.logger.error(f"Error details: {traceback.format_exc()}")
        return {'error': str(e)}, 500

@app.route('/api/facts', methods=['GET'])
@async_route
async def get_facts():
    try:
        # Fetch all facts
        all_facts = await fetch_all_pages(bee.get_facts, "me")
        formatted_facts = [format_fact(fact) for fact in all_facts]

        # Save complete dataset to file
        save_to_file(formatted_facts, 'facts', {'facts': all_facts})
        
        # Store facts in database with deduplication
        db_result = db.store_facts(all_facts)
        app.logger.info(f"Database facts storage result: {db_result}")

        return {'facts': formatted_facts}

    except Exception as e:
        app.logger.error(f"Error in get_facts: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/todos', methods=['GET'])
@async_route
async def get_todos():
    try:
        page = int(request.args.get('page', 1))

        # Fetch all pages for saving
        all_todos = await fetch_all_pages(bee.get_todos, "me")
        formatted_all_todos = [format_todo(todo) for todo in all_todos]

        # Save complete dataset to file
        save_to_file(formatted_all_todos, 'todos', {'todos': all_todos})
        
        # Store todos in database with deduplication
        db_result = db.store_todos(all_todos)
        app.logger.info(f"Database todos storage result: {db_result}")

        # Get current page data for display
        todos = await bee.get_todos("me", page=page)
        formatted_todos = [format_todo(todo) for todo in todos.get('todos', [])]

        paginated_data = {
            'todos': formatted_todos,
            'total': todos.get('totalCount', 0),
            'page': page,
            'per_page': len(formatted_todos),
            'total_pages': todos.get('totalPages', 1)
        }

        return paginated_data

    except Exception as e:
        app.logger.error(f"Error in get_todos: {str(e)}")
        return {'error': str(e)}, 500

# Database-specific API endpoints
@app.route('/api/db/conversations', methods=['GET'])
def get_db_conversations():
    try:
        # Retrieve conversations from database
        conversations = db.get_conversations_from_db()
        app.logger.info(f"Retrieved {len(conversations)} conversations from database")
        
        # Format for display
        formatted_conversations = []
        raw_data = []
        
        for conv in conversations:
            # Convert from SQLAlchemy object to dictionary
            formatted_conv = {
                "Summary": conv.summary if conv.summary else "No summary available",
                "Created At": conv.created_at.isoformat() if conv.created_at else "Unknown",
                "Address": conv.address if conv.address else "No address"
            }
            formatted_conversations.append(formatted_conv)
            
            # Get raw data for file saving
            if conv.raw_data:
                try:
                    raw_data.append(json.loads(conv.raw_data))
                except:
                    app.logger.warning(f"Could not parse raw_data for conversation {conv.id}")
        
        # Save database data to files
        if formatted_conversations:
            saved = save_to_file(
                formatted_conversations, 
                'db_conversations', 
                {'conversations': raw_data}
            )
            if saved:
                app.logger.info("Successfully saved database conversations to files")
            else:
                app.logger.warning("Failed to save database conversations to files")
            
        return {'conversations': formatted_conversations, 'count': len(formatted_conversations)}
        
    except Exception as e:
        app.logger.error(f"Error getting conversations from DB: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/db/facts', methods=['GET'])
def get_db_facts():
    try:
        # Retrieve facts from database
        facts = db.get_facts_from_db()
        app.logger.info(f"Retrieved {len(facts)} facts from database")
        
        # Format for display
        formatted_facts = []
        raw_data = []
        
        for fact in facts:
            # Convert from SQLAlchemy object to dictionary
            formatted_fact = {
                "Text": fact.text,
                "Created At": fact.created_at.isoformat() if fact.created_at else "Unknown"
            }
            formatted_facts.append(formatted_fact)
            
            # Get raw data for file saving
            if fact.raw_data:
                try:
                    raw_data.append(json.loads(fact.raw_data))
                except:
                    app.logger.warning(f"Could not parse raw_data for fact {fact.id}")
        
        # Save database data to files
        if formatted_facts:
            saved = save_to_file(
                formatted_facts, 
                'db_facts', 
                {'facts': raw_data}
            )
            if saved:
                app.logger.info("Successfully saved database facts to files")
            else:
                app.logger.warning("Failed to save database facts to files")
            
        return {'facts': formatted_facts, 'count': len(formatted_facts)}
        
    except Exception as e:
        app.logger.error(f"Error getting facts from DB: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/db/todos', methods=['GET'])
def get_db_todos():
    try:
        # Retrieve todos from database
        todos = db.get_todos_from_db()
        app.logger.info(f"Retrieved {len(todos)} todos from database")
        
        # Format for display
        formatted_todos = []
        raw_data = []
        
        for todo in todos:
            # Convert from SQLAlchemy object to dictionary
            formatted_todo = {
                "Task": todo.task,
                "Completed": "Yes" if todo.completed else "No",
                "Created At": todo.created_at.isoformat() if todo.created_at else "Unknown"
            }
            formatted_todos.append(formatted_todo)
            
            # Get raw data for file saving
            if todo.raw_data:
                try:
                    raw_data.append(json.loads(todo.raw_data))
                except:
                    app.logger.warning(f"Could not parse raw_data for todo {todo.id}")
        
        # Save database data to files
        if formatted_todos:
            saved = save_to_file(
                formatted_todos, 
                'db_todos', 
                {'todos': raw_data}
            )
            if saved:
                app.logger.info("Successfully saved database todos to files")
            else:
                app.logger.warning("Failed to save database todos to files")
            
        return {'todos': formatted_todos, 'count': len(formatted_todos)}
        
    except Exception as e:
        app.logger.error(f"Error getting todos from DB: {str(e)}")
        return {'error': str(e)}, 500

def run_cli():
    """
    CLI entry point for the application. Fetches data from API, stores in database,
    and then saves database content to JSON files to avoid duplicates.
    """
    print("Starting Bee AI Data Collector CLI")
    try:
        # Step 1: Fetch data from API and store in database
        loop = asyncio.get_event_loop()
        
        print("Fetching conversations from API...")
        conversations = loop.run_until_complete(fetch_all_pages(bee.get_conversations, "me"))
        if isinstance(conversations, dict):
            conversations_list = conversations.get('conversations', [])
        else:
            conversations_list = conversations
        print(f"Fetched {len(conversations_list)} conversations")
        
        print("Fetching facts from API...")
        facts = loop.run_until_complete(fetch_all_pages(bee.get_facts, "me"))
        if isinstance(facts, dict):
            facts_list = facts.get('facts', [])
        else:
            facts_list = facts
        print(f"Fetched {len(facts_list)} facts")
        
        print("Fetching todos from API...")
        todos = loop.run_until_complete(fetch_all_pages(bee.get_todos, "me"))
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
                
                lifelogs = loop.run_until_complete(fetch_all_pages(get_lifelogs_wrapper, "dummy"))
                print(f"Debug - lifelogs type: {type(lifelogs)}")
                
                # Fix case where lifelogs_list is a list with a string like ['lifelogs']
                if isinstance(lifelogs, list) and len(lifelogs) == 1 and isinstance(lifelogs[0], str) and lifelogs[0] == 'lifelogs':
                    print("Detected invalid lifelog list format, replacing with empty list")
                    lifelogs_list = []
                # Normal processing for dictionary response with 'lifelogs' key
                elif isinstance(lifelogs, dict):
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

if __name__ == '__main__':
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Run in CLI mode
        run_cli()
    else:
        # Run as web server
        app.run(host='0.0.0.0', port=5000, debug=True)