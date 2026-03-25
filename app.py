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
@socketio.on('join')
def on_join(data):
    room = data.get('room')
    join_room(room)
    emit('receive_message', {'user': 'SYSTEM', 'message': f'{data.get("user")} joined the room.'}, to=room)

@socketio.on('send_message')
def handle_message(data):
    room = data.get('room_id')
    emit('receive_message', {
        'user': data.get('user'),
        'message': data.get('message')
    }, to=room)

# 6. SERVER START (Always at the absolute bottom)
if __name__ == '__main__':
    socketio.run(app)