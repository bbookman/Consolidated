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

app = Flask(__name__)
bee = Bee(os.environ.get('BEE_API_KEY'))

def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

def format_conversation(conv):
    return {
        "Title": conv.get("title", "Untitled Conversation"),
        "Summary": conv.get("summary", "No summary available"),
        "Created At": conv.get("created_at", "Unknown"),
        "ID": conv.get("id", "Unknown")
    }

def format_fact(fact):
    return {
        "Text": fact.get("text", "No text available"),
        "Confirmed": "Yes" if fact.get("confirmed") else "No",
        "Created At": fact.get("created_at", "Unknown"),
        "ID": fact.get("id", "Unknown")
    }

def format_todo(todo):
    return {
        "Task": todo.get("text", "No task description"),
        "Completed": "Yes" if todo.get("completed") else "No",
        "Created At": todo.get("created_at", "Unknown"),
        "ID": todo.get("id", "Unknown")
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
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Create main data directory and subfolders
    os.makedirs('data/text', exist_ok=True)
    os.makedirs('data/json', exist_ok=True)

    # Save formatted data as text
    formatted_file = f'data/text/{data_type}_{timestamp}.txt'
    with open(formatted_file, 'w') as f:
        f.write(f"=== {data_type.upper()} ===\n")
        f.write(f"Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total items: {len(data)}\n\n")

        for idx, item in enumerate(data, 1):
            f.write(f"--- Item {idx} ---\n")
            for key, value in item.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")

    # Save raw JSON for reference
    json_file = f'data/json/{data_type}_{timestamp}.json'
    with open(json_file, 'w') as f:
        json.dump(original_data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

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

        # Fetch all pages for saving
        all_conversations = await fetch_all_pages(bee.get_conversations, "me")
        formatted_all_conversations = [format_conversation(conv) for conv in all_conversations]

        # Save complete dataset
        save_to_file(formatted_all_conversations, 'conversations', {'conversations': all_conversations})

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
        return {'error': str(e)}, 500

@app.route('/api/facts', methods=['GET'])
@async_route
async def get_facts():
    try:
        page = int(request.args.get('page', 1))

        # Fetch all pages for saving
        all_facts = await fetch_all_pages(bee.get_facts, "me")
        formatted_all_facts = [format_fact(fact) for fact in all_facts]

        # Save complete dataset
        save_to_file(formatted_all_facts, 'facts', {'facts': all_facts})

        # Get current page data for display
        facts = await bee.get_facts("me", page=page)
        formatted_facts = [format_fact(fact) for fact in facts.get('facts', [])]

        paginated_data = {
            'facts': formatted_facts,
            'total': facts.get('totalCount', 0),
            'page': page,
            'per_page': len(formatted_facts),
            'total_pages': facts.get('totalPages', 1)
        }

        return paginated_data

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

        # Save complete dataset
        save_to_file(formatted_all_todos, 'todos', {'todos': all_todos})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)