import os
import sqlite3
from datetime import datetime
import re
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
# Use a secure secret key from environment or fallback to a default for development
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'aayan-portfolio-secret-key-129031')

# Configure CORS so local file testing can still interact with the APIs
CORS(app, supports_credentials=True)

DB_FILE = 'portfolio.db'
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    # Enable WAL mode for concurrent reads and writes
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the messages table if it doesn't exist."""
    conn = get_db()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                read_status INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
    finally:
        conn.close()

# Initialize database on startup
init_db()

# Serve Frontend Static Pages
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def serve_admin():
    return send_from_directory('.', 'admin.html')

# API Endpoints
@app.route('/api/contact', methods=['POST'])
def contact_submit():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()

        # Input Validation
        if not name or not email or not subject or not message:
            return jsonify({'success': False, 'message': 'All fields are required.'}), 400

        if len(name) > 100 or len(subject) > 200 or len(message) > 5000:
            return jsonify({'success': False, 'message': 'Input length exceeded limits.'}), 400

        # Simple email regex validation
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            return jsonify({'success': False, 'message': 'Please provide a valid email address.'}), 400

        # Insert message into database
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO messages (name, email, subject, message, timestamp) VALUES (?, ?, ?, ?, ?)',
                (name, email, subject, message, timestamp)
            )
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True, 'message': 'Your message has been sent successfully!'}), 201

    except Exception as e:
        app.logger.error(f"Error in contact submission: {str(e)}")
        return jsonify({'success': False, 'message': 'An internal server error occurred.'}), 500

# Admin Authentication Endpoints
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No login credentials provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'message': 'Logged in successfully'}), 200
    
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@app.route('/api/admin/check-auth', methods=['GET'])
def check_auth():
    if session.get('admin_logged_in'):
        return jsonify({'authenticated': True}), 200
    return jsonify({'authenticated': False}), 401

# Admin Messages API
@app.route('/api/admin/messages', methods=['GET'])
def get_messages():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401

    conn = get_db()
    try:
        cursor = conn.execute('SELECT * FROM messages ORDER BY timestamp DESC')
        messages = [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

    return jsonify({'success': True, 'messages': messages}), 200

@app.route('/api/admin/messages/<int:msg_id>/read', methods=['PUT'])
def toggle_read(msg_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401

    data = request.get_json()
    read_status = int(data.get('read', 0))

    conn = get_db()
    try:
        conn.execute('UPDATE messages SET read_status = ? WHERE id = ?', (read_status, msg_id))
        conn.commit()
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Message status updated'}), 200

@app.route('/api/admin/messages/<int:msg_id>', methods=['DELETE'])
def delete_message(msg_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401

    conn = get_db()
    try:
        conn.execute('DELETE FROM messages WHERE id = ?', (msg_id,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Message deleted successfully'}), 200

if __name__ == '__main__':
    print(f"Starting Aayan Madnas Portfolio Backend server...")
    print(f"Admin URL: http://localhost:5000/admin")
    print(f"Default Admin Credentials: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    app.run(host='0.0.0.0', port=5000, debug=True)
