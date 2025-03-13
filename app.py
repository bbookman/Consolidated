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
        per_page = int(request.args.get('per_page', 10))

        conversations = await bee.get_conversations("me")
        formatted_conversations = [format_conversation(conv) for conv in conversations.get('conversations', [])]

        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_data = {
            'conversations': formatted_conversations[start_idx:end_idx],
            'total': len(formatted_conversations),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(formatted_conversations) + per_page - 1) // per_page
        }

        # Save both formatted and raw data
        save_to_file(formatted_conversations, 'conversations', conversations)

        return paginated_data

    except Exception as e:
        app.logger.error(f"Error in get_conversations: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/facts', methods=['GET'])
@async_route
async def get_facts():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        facts = await bee.get_facts("me")
        formatted_facts = [format_fact(fact) for fact in facts.get('facts', [])]

        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_data = {
            'facts': formatted_facts[start_idx:end_idx],
            'total': len(formatted_facts),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(formatted_facts) + per_page - 1) // per_page
        }

        # Save both formatted and raw data
        save_to_file(formatted_facts, 'facts', facts)

        return paginated_data

    except Exception as e:
        app.logger.error(f"Error in get_facts: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/todos', methods=['GET'])
@async_route
async def get_todos():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        todos = await bee.get_todos("me")
        formatted_todos = [format_todo(todo) for todo in todos.get('todos', [])]

        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_data = {
            'todos': formatted_todos[start_idx:end_idx],
            'total': len(formatted_todos),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(formatted_todos) + per_page - 1) // per_page
        }

        # Save both formatted and raw data
        save_to_file(formatted_todos, 'todos', todos)

        return paginated_data

    except Exception as e:
        app.logger.error(f"Error in get_todos: {str(e)}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)