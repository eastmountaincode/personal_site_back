from flask import Flask, request, jsonify
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    filename = file.filename
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return jsonify({"message": "File successfully uploaded", "filename": filename}), 200

@app.route('/')
def hello_world():
    return 'Hello WORD.'

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large"}), 413

if __name__ == '__main__':
    app.run(debug=True)
