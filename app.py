from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from supabase import create_client
import os

app = Flask(__name__)

# Fixed: Removed the 's' at the end of this line
socketio = SocketIO(app, cors_allowed_origins="*")

# --- SUPABASE SETUP ---
HOSPITAL_CODES = {
    "Mulago": "MUL-2026",
    "Nsambya": "NSB-77",
    "CityMedical": "CITY-DOC"
}
# Ensure your environment variables are set in Render
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# --- SOCKET EVENTS ---
# --- THE HOME PAGE (Crucial or the site won't load!) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify():
    data = request.json
    hospital = data.get('hospital')
    code_entered = data.get('code')

    if HOSPITAL_CODES.get(hospital) == code_entered:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Invalid Doctor Code!"})

# --- SOCKET EVENTS ---
@socketio.on('join')
def on_join(data):
    username = data.get('user')
    room_id = data.get('room')
    join_room(room_id)
    print(f"🏥 CLINIC ONLINE: {username} has entered Private Room: {room_id}")
    emit('receive_message', {
        'user': 'SYSTEM',
        'message': f'{username} has joined the consultation.',
        'room': room_id
    }, to=room_id)

@socketio.on('send_message')
def handle_message(data):
    """Sends message ONLY to the people in the specified room and saves to DB"""
    # 1. Get the data from the incoming message
    user = data.get('user')
    message = data.get('message')
    room_id = data.get('room') # Use 'room' to match your JavaScript

    # 2. Privacy: Send ONLY to that specific room
    emit('receive_message', {
        'user': user,
        'message': message,
        'room': room_id
    }, to=room_id)
    
    # 3. 💾 SAVE TO SUPABASE (Optional, but good for history)
    if supabase and room_id:
        try:
            supabase.table("messages").insert({
                "user_name": user, 
                "content": message, 
                "room_id": room_id # Changed 'hospital' to 'room_id' for your new setup
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