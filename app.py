import os
from flask import Flask, render_template, request, jsonify  # Added request and jsonify
from flask_socketio import SocketIO, emit, join_room      # Added join_room
from supabase import create_client, Client 

app = Flask(__name__)

# --- DATABASE CONNECTION ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app.config['SECRET_KEY'] = 'medical-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# ... rest of your code ...

# 🔑 HOSPITAL PASSCODE REGISTRY
HOSPITAL_CODES = {
    "Mulago": "MUL789",
    "Nakasero": "NAK456",
    "Mukono": "MUK123",
    "Developer": "LAW2026"
}

# 📋 QUEUE & DOCTOR TRACKING
# Stores status: {"Mulago": {"Dr. Law": "available", "Dr. Sarah": "busy"}}
ACTIVE_DOCTORS = {h: {} for h in HOSPITAL_CODES.keys()}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    hospital = data.get('hospital')
    input_code = data.get('code')
    
    # Check if the code matches the hospital registry
    if HOSPITAL_CODES.get(hospital) == input_code:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

# --- SOCKET.IO LOGIC ---

@socketio.on('join')
def on_join(data):
    role = data.get('role')
    hospital = data.get('hospital')
    name = data.get('name')
    
    # Everyone joins the general Hospital Lobby room
    join_room(hospital)
    
    if role == 'Doctor' or role == 'Developer':
        # Mark doctor as available in the global tracker
        ACTIVE_DOCTORS[hospital][name] = "available"
        print(f"👨‍⚕️ Doctor {name} joined the {hospital} lobby.")
    
    # Update the list for all patients in that hospital
    send_doctor_updates(hospital)

def send_doctor_updates(hospital):
    # Only send doctors who are "available" (not busy)
    available_docs = [name for name, status in ACTIVE_DOCTORS[hospital].items() if status == "available"]
    emit('update_doctor_list', available_docs, room=hospital)

@socketio.on('request_consultation')
def handle_request(data):
    # Sends a private alert to the specific hospital lobby
    # We include the patient name and the specific doctor's name
    emit('consultation_request', {
        'patient': data['patient'],
        'doctor': data['doctor']
    }, room=data['hospital'])

@socketio.on('accept_patient')
def handle_accept(data):
    hospital = data['hospital']
    doctor = data['doctor']
    patient = data['patient']
    
    # 🔒 Lock the doctor so they disappear from the "Available" list
    ACTIVE_DOCTORS[hospital][doctor] = "busy"
    send_doctor_updates(hospital)
    
    # Tell both parties to open their chat windows
    emit('start_session', {
        'doctor': doctor, 
        'patient': patient
    }, room=hospital)
@socketio.on('send_message')
def handle_message(data):
    # 1. Save to Supabase (The "Permanent" part)
    try:
        supabase.table("messages").insert({
            "sender": data['user'],
            "hospital": data['hospital'],
            "doctor_name": data.get('doctorName', 'General'), # Safety check
            "content": data['message']
        }).execute()
    except Exception as e:
        print(f"Database Error: {e}")

    # 2. Send live to everyone (The "Chat" part)
    emit('receive_message', data, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    # Optional: Clean up ACTIVE_DOCTORS if a doctor closes their tab
    pass

if __name__ == '__main__':
    socketio.run(app, debug=True)