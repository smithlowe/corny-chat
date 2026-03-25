import eventlet
eventlet.monkey_patch()

import os
import uuid
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from supabase import create_client, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'med_secure_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Supabase Setup
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({"success": False})
    file = request.files['file']
    try:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else "dat"
        unique_name = f"{uuid.uuid4()}.{ext}"
        storage = supabase.storage.from_('medical-files')
        storage.upload(unique_name, file.read())
        return jsonify({"success": True, "url": storage.get_public_url(unique_name)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/verify-code', methods=['POST'])
def verify():
    data = request.json
    passcodes = {"Mulago": "MUL-2026", "Nakasero": "NAK-555", "Mukono": "MUK-888"}
    if data.get('code') == passcodes.get(data.get('hospital')) or data.get('code') == "ADMIN-99":
        return jsonify({"success": True})
    return jsonify({"success": False})

@socketio.on('join')
def on_join(data):
    room = data.get('hospital')
    if room:
        join_room(room)
        # 🔒 PRIVACY: No history fetch here. New joins start with a clean screen.
        print(f"User joined active session: {room}")

@socketio.on('send_message')
def handle_message(data):
    msg, sender, hosp, doc = data.get('message'), data.get('user'), data.get('hospital'), data.get('doctor_name')
    try:
        # Keep record in DB for medical logs, but don't broadcast old ones to new users
        supabase.table("messages").insert({"sender": sender, "content": msg, "hospital": hosp, "doctor_name": doc}).execute()
        emit('receive_message', {'user': sender, 'message': msg}, to=hosp)
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == '__main__':
    socketio.run(app)