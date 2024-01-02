from flask import Flask, request, jsonify
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 500 MB limit

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
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(file_path)

        with open(file_path, 'rb') as file:
            binary_data = file.read()

        # Using hexadecimal ensures that the data is
        # represented using only printable characters.
            
        # Get hex data for first 20 bytes
        hex_data_20 = binary_data[:5].hex()

        # Flip the bits
        flipped_data = bytes(~byte & 0xFF for byte in binary_data)

        # Get hex of flipped data for first 20 bytes
        hex_flipped_data_20 = flipped_data[:5].hex()

        return jsonify({"message": "File successfully uploaded", 
                        "filename": filename, 
                        "data_head": hex_data_20,
                        "data_head_flipped": hex_flipped_data_20}), 200
    except Exception as e:
        # If an error occurs, delete the file
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": str(e)}), 500


@app.route('/')
def hello_world():
    return 'Hello WORD.'

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large"}), 413

if __name__ == '__main__':
    app.run(port=5001)
