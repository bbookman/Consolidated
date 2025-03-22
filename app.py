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

app = Flask(__name__)
bee = Bee(os.environ.get('BEE_API_KEY'))

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

async def fetch_all_pages(fetch_func, user_id):
    all_items = []
    first_response = await fetch_func(user_id)

    # Get total pages from first response
    total_pages = first_response.get('totalPages', 1)

    # Add items from first page
    items_key = None
    for key in ['conversations', 'facts', 'todos']:
        if key in first_response:
            items_key = key
            break

    if items_key:
        all_items.extend(first_response[items_key])

    # Fetch remaining pages
    for page in range(2, total_pages + 1):
        try:
            response = await fetch_func(user_id, page=page)
            if items_key in response and response[items_key]:
                all_items.extend(response[items_key])
        except Exception as e:
            app.logger.error(f"Error fetching page {page}: {str(e)}")
            break

    return all_items

def save_to_file(data, data_type, original_data):
    """
    Save data to files in data/text and data/json directories
    
    Args:
        data: List of formatted data items
        data_type: Type of data (conversations, facts, todos)
        original_data: Raw data from API
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    app.logger.info(f"Saving {data_type} to file with timestamp {timestamp}")
    
    try:
        # Get absolute path for data directory
        current_dir = os.getcwd()
        data_dir = os.path.join(current_dir, 'data')
        text_dir = os.path.join(data_dir, 'text')
        json_dir = os.path.join(data_dir, 'json')
        
        # Create main data directory and subfolders
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        
        app.logger.info(f"Created directories at {data_dir}")
        
        # Save formatted data as text
        formatted_file = os.path.join(text_dir, f"{data_type}_{timestamp}.txt")
        app.logger.info(f"Saving formatted data to {formatted_file}")
        
        with open(formatted_file, 'w') as f:
            f.write(f"=== {data_type.upper()} ===\n")
            f.write(f"Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total items: {len(data)}\n\n")
            
            for idx, item in enumerate(data, 1):
                f.write(f"--- Item {idx} ---\n")
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
                
        app.logger.info(f"Successfully wrote text file to {formatted_file}")
        
        # Save raw JSON for reference
        json_file = os.path.join(json_dir, f"{data_type}_{timestamp}.json")
        app.logger.info(f"Saving JSON data to {json_file}")
        
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
        conversations_data = await fetch_all_pages(bee.conversations, "user")
        facts_data = await fetch_all_pages(bee.facts, "user")
        todos_data = await fetch_all_pages(bee.todos, "user")
        
        # Format the data for display
        conversations_list = conversations_data.get('conversations', [])
        facts_list = facts_data.get('facts', [])
        todos_list = todos_data.get('todos', [])
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)