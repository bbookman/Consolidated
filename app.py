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

        # Manual pagination since the API doesn't support it directly
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_data = {
            'conversations': conversations.get('conversations', [])[start_idx:end_idx],
            'total': len(conversations.get('conversations', [])),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(conversations.get('conversations', [])) + per_page - 1) // per_page
        }

        # Store the data in a text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('data', exist_ok=True)
        with open(f'data/conversations_{timestamp}.txt', 'w') as f:
            json.dump(conversations, f, indent=2)

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

        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_data = {
            'facts': facts.get('facts', [])[start_idx:end_idx],
            'total': len(facts.get('facts', [])),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(facts.get('facts', [])) + per_page - 1) // per_page
        }

        # Store the data in a text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('data', exist_ok=True)
        with open(f'data/facts_{timestamp}.txt', 'w') as f:
            json.dump(facts, f, indent=2)

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

        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_data = {
            'todos': todos.get('todos', [])[start_idx:end_idx],
            'total': len(todos.get('todos', [])),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(todos.get('todos', [])) + per_page - 1) // per_page
        }

        # Store the data in a text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('data', exist_ok=True)
        with open(f'data/todos_{timestamp}.txt', 'w') as f:
            json.dump(todos, f, indent=2)

        return paginated_data

    except Exception as e:
        app.logger.error(f"Error in get_todos: {str(e)}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)