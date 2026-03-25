import os
import uuid
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from supabase import create_client, Client

# 1. INITIALIZATION
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Supabase Setup (Ensure these are in your Render Environment Variables)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 2. MAIN PAGE ROUTE
@app.route('/')
def index():
    return render_template('index.html')

# 3. FILE UPLOAD ROUTE (Must be its own block!)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"})

    try:
        # Create unique filename
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else "dat"
        unique_name = f"{uuid.uuid4()}.{ext}"
        
        file_data = file.read()
        
        # Upload to Supabase
        storage = supabase.storage.from_('medical-files')
        storage.upload(unique_name, file_data)
        
        # Get URL
        file_url = storage.get_public_url(unique_name)
        
        return jsonify({"success": True, "url": file_url, "filename": file.filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# 4. PASSCODE VERIFICATION ROUTE
@app.route('/verify-code', methods=['POST'])
def verify():
    data = request.json
    hospital = data.get('hospital')
    code_entered = data.get('code')
    
    # 🏥 Hospital Secret Codes (You can change these to anything!)
    # Mulinda, update these codes to your preferred passwords:
    passcodes = {
        "Mulago": "MUL-2026",
        "Nakasero": "NAK-555",
        "Mukono": "MUK-888"
    }

    # Check if the code matches the selected hospital
    if hospital in passcodes and code_entered == passcodes[hospital]:
        return jsonify({"success": True})
    
    # If it's a Developer/Admin role (Optional extra)
    if code_entered == "ADMIN-99":
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Incorrect passcode for " + str(hospital)})

# 5. SOCKET.IO EVENTS (Handling Real-time Chat)
# 5. SOCKET.IO EVENTS (Handling Real-time Chat + Database)
# 5. SOCKET.IO EVENTS (Updated for your 6-column Medical Table)
@socketio.on('join')
def on_join(data):
    # Use 'hospital' as the room ID since that is your column name
    room = data.get('hospital') or data.get('room_id') or "default_room"
    user = data.get('user', 'Unknown')
    join_room(room)
    
    try:
        # Fetch history where hospital matches the room
        response = supabase.table("messages") \
            .select("*") \
            .eq("hospital", room) \
            .order("created_at", desc=False) \
            .execute()
        
        for m in response.data:
            emit('receive_message', {'user': m.get('sender'), 'message': m.get('content')})
    except Exception as e:
        print(f"Fetch Error: {e}")

@socketio.on('send_message')
def handle_message(data):
    print(f"DEBUG - Data Received: {data}") # Check your VS Code terminal for this!
    
    # We must use the exact keys your JavaScript is sending
    room = data.get('hospital') or data.get('room_id')
    user = data.get('user')
    msg = data.get('message')
    doc = data.get('doctor_name', 'No Doctor Assigned')

    try:
        # Save to your 6-column table
        supabase.table("messages").insert({
            "sender": user,
            "content": msg,
            "hospital": room,
            "doctor_name": doc
        }).execute()
        
        # ONLY emit if the save was successful
        emit('receive_message', {'user': user, 'message': msg}, to=room)
    except Exception as e:
        print(f"Database Save Error: {e}")
# 6. SERVER START (Always at the absolute bottom)
if __name__ == '__main__':
    socketio.run(app)