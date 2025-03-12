from flask import Flask, render_template, request, jsonify
import sys
from io import StringIO
import traceback

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute_code():
    code = request.json.get('code', '')
    
    # Capture stdout
    stdout = StringIO()
    stderr = StringIO()
    
    # Store original stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        # Redirect stdout/stderr
        sys.stdout = stdout
        sys.stderr = stderr
        
        # Execute the code
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
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
