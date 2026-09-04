import os
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "track": "PS05"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)
