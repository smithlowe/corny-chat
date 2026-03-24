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

if __name__ == '__main__':
    # Use eventlet's wsgi server for local testing
    socketio.run(app, debug=True)