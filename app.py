import os
import eventlet
# CRITICAL: This must be the very first thing in the file for Render
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-key-for-local-testing')

# Supabase Setup (Ensure these are set in Render Environment Variables)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase only if keys exist
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# SocketIO Setup with Eventlet for Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    return render_template('index.html')

# Doctor Verification Route
@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    code = data.get('code')
    hospital = data.get('hospital')
    
    # Simple logic for now: Check if code is 'DOC123'
    # In the future, you can query Supabase here
    if code == "DOC123":
        return jsonify({"success": True})
    return jsonify({"success": False})

# --- SOCKET EVENTS ---

@socketio.on('join')
def handle_join(data):
    name = data.get('name')
    hosp = data.get('hospital')
    
    if name and hosp:
        join_room(hosp)
        print(f"User {name} joined hospital room: {hosp}")
        # Send a status message to everyone in that hospital
        emit('status', {'msg': f'🏥 {name} is now online in {hosp}'}, to=hosp)

@socketio.on('send_message')
def handle_message(data):
    user = data.get('user')
    message = data.get('message')
    hosp = data.get('hospital')
    
    # 💾 SAVE TO SUPABASE
    if supabase:
        try:
            supabase.table("messages").insert({
                "user_name": user, 
                "content": message, 
                "hospital": hosp
            }).execute()
        except Exception as e:
            print(f"Supabase Error: {e}")

    # 📢 BROADCAST REAL-TIME
    emit('receive_message', {
        'user': user,
        'message': message,
        'hospital': hosp
    }, to=hosp)
    from flask import request, jsonify
import uuid  # This helps give every file a unique name

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file selected"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Empty filename"}), 400

    try:
        # 1. Create a unique name (e.g., "7a2b-patient-xray.jpg")
        file_ext = file.filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        
        # 2. Read the file bytes
        file_data = file.read()
        
        # 3. Upload to Supabase 'medical-files' bucket
        storage_path = f"uploads/{unique_name}"
        supabase.storage.from_('medical-files').upload(storage_path, file_data)
        
        # 4. Get the Public URL
        file_url = supabase.storage.from_('medical-files').get_public_url(storage_path)
        
        return jsonify({"success": True, "url": file_url})
    
    except Exception as e:
        print(f"Upload Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Use eventlet's wsgi server for local testing
    socketio.run(app, debug=True)