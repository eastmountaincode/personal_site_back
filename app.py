import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, send_from_directory
import os
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
import threading
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins=[
    "https://celadon-strudel-b171cf.netlify.app",
    "https://andrew-boylan.com",
    "http://andrew-boylan.com"
    ])

# Configuration
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 300 MB limit

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def ensure_minimum_delay(start_time, delay):
    elapsed_time = time.time() - start_time
    if elapsed_time < delay:
        eventlet.sleep(delay - elapsed_time)

def emit_with_delay(event, data, start_time, delay=1.8):
    ensure_minimum_delay(start_time, delay)
    socketio.emit(event, data)
    return time.time()  # Return the new start time

@app.route('/upload', methods=['POST'])
def upload_file():
    app.logger.info('top of upload file')
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(file_path)
        app.logger.info(f"File saved to {file_path}")

        return jsonify({"message": "File successfully uploaded", 
                        "filename": filename}), 200
    except Exception as e:
        # If an error occurs, delete the file
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": str(e)}), 500

# SocketIO event for starting file processing
@socketio.on('start_processing')
def handle_start_processing(data):
    socketio.emit('initiating_depolarization')
    start_time = time.time()

    app.logger.info('top of handle start processing in app.py')
    filename = data['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    app.logger.info(f"Processing file at {file_path}")


    # Ensure the file exists
    if not os.path.exists(file_path):
        socketio.emit('processing_error', {'error': 'File not found on server'})
        return

    try:
        start_time = emit_with_delay('reading_file', None, start_time)

        with open(file_path, 'rb') as file:
            binary_data = file.read()

        # Get the first 5 bytes in binary format
        first_5_bytes_binary = ''.join(format(byte, '08b') for byte in binary_data[:5])

        logging.info("Before emitting the head for binary")

        start_time = emit_with_delay('first_5_binary', {'data': first_5_bytes_binary}, start_time)

        start_time = emit_with_delay('flipping_bits_status', None, start_time)

        flipped_data = bytes(~byte & 0xFF for byte in binary_data)

        first_5_bytes_binary = ''.join(format(byte, '08b') for byte in flipped_data[:5])

        start_time = emit_with_delay('first_5_binary', {'data': first_5_bytes_binary}, start_time)

        start_time = emit_with_delay('flipping_bits_status', None, start_time)

        depolarized_data = bytes(~byte & 0xFF for byte in flipped_data)

        first_5_bytes_binary = ''.join(format(byte, '08b') for byte in depolarized_data[:5])

        start_time = emit_with_delay('first_5_binary', {'data': first_5_bytes_binary}, start_time)

        app.logger.info("Before constructing new file name")

         # Construct new filename
        file_name, file_extension = os.path.splitext(filename)
        depolarized_file_name = f"{file_name}_depolarized{file_extension}"
        depolarized_file_path = os.path.join(app.config['UPLOAD_FOLDER'], depolarized_file_name)

        # Save the depolarized data to a new file
        with open(depolarized_file_path, 'wb') as depolarized_file:
            depolarized_file.write(depolarized_data)

        # Schedule the file for deletion after 60 seconds
        delete_file_later(depolarized_file_path, delay=60)

        app.logger.info(f"After creating depolarized file at {depolarized_file_path}")

        # Emit event with download URL
        download_url = f"http://{request.host}/download/{depolarized_file_name}"

        start_time = emit_with_delay('complete_message', None, start_time)

        start_time = emit_with_delay('file_ready', {'download_url': download_url}, start_time)

        app.logger.info(f"After emitting file_ready for download_url: {download_url}")

        # Optionally delete the original file
        os.remove(file_path)

        app.logger.info(f"after removing file at {file_path}")


    except Exception as e:
        socketio.emit('processing_error', {'error': str(e)})


def delete_file_later(file_path, delay):
    """Delete a file after a specified delay (in seconds)."""
    def delayed_delete():
        time.sleep(delay)
        if os.path.exists(file_path):
            os.remove(file_path)
            app.logger.info(f"File at {file_path} removed")

    thread = threading.Thread(target=delayed_delete)
    thread.start()

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found or has expired"}), 404

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def hello_world():
    return 'Hello WORD.'

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large (max size 300 MB)"}), 413

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001)
