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
        conversations = await bee.get_conversations("me")

        # Store the data in a text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('data', exist_ok=True)
        with open(f'data/conversations_{timestamp}.txt', 'w') as f:
            json.dump(conversations, f, indent=2)

        return conversations

    except Exception as e:
        app.logger.error(f"Error in get_conversations: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/facts', methods=['GET'])
@async_route
async def get_facts():
    try:
        facts = await bee.get_facts("me")

        # Store the data in a text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('data', exist_ok=True)
        with open(f'data/facts_{timestamp}.txt', 'w') as f:
            json.dump(facts, f, indent=2)

        return facts

    except Exception as e:
        app.logger.error(f"Error in get_facts: {str(e)}")
        return {'error': str(e)}, 500

@app.route('/api/todos', methods=['GET'])
@async_route
async def get_todos():
    try:
        todos = await bee.get_todos("me")

        # Store the data in a text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('data', exist_ok=True)
        with open(f'data/todos_{timestamp}.txt', 'w') as f:
            json.dump(todos, f, indent=2)

        return todos

    except Exception as e:
        app.logger.error(f"Error in get_todos: {str(e)}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)