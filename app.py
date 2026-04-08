import gevent.monkey
gevent.monkey.patch_all(dns=True, socket=True, thread=True) 

import gevent
import os
import uuid
from flask import Flask, render_template, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from supabase import create_client

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "med_secure_2026")

# 🏥 Global tracking for UI counts
active_doctors = {}

# Initialize SocketIO
socketio = SocketIO(app, 
    cors_allowed_origins="*", 
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=10,
    manage_session=True,
    allow_upgrades=True
)

# Supabase Helper
def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = get_supabase()

# --- 🌐 HTTP ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return "OK", 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: 
        return jsonify({"success": False, "error": "No file"})
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

# --- 🛰️ SOCKET.IO LOGIC ---

# 1. THE DOCTOR'S LOBBY
@socketio.on('join_lounge')
def handle_lounge_join(data):
    hosp_code = data.get('hospital')
    doc_name = data.get('doctor', 'Unknown Doctor')
    
    try:
        result = supabase.table('hospitals').select('*').eq('secret_code', hosp_code).execute()
        if result.data:
            hospital_name = result.data[0]['name']
            join_room(hosp_code) # Join the hospital room to hear patient requests
            
            active_doctors[request.sid] = {"name": doc_name, "hospital": hosp_code}
            session['hosp_code'] = hosp_code
            session['is_doctor'] = True
            
            emit('lounge_joined', {
                'status': 'success', 
                'hospital': hospital_name,
                'doctor': doc_name
            })
            emit('update_doctor_counts', {"count": len(active_doctors)}, broadcast=True)
        else:
            emit('lounge_joined', {'status': 'error', 'message': 'Invalid Access Code'})
    except Exception as e:
        emit('lounge_joined', {'status': 'error', 'message': 'Server Error'})

# 2. PATIENT REQUEST FLOW
@socketio.on('patient_paid_and_waiting')
def handle_patient_waiting(data):
    p_name = data.get('patient_name')
    h_id = data.get('hospital_id', 'unknown') 
    s_id = data.get('session_id')
    actual_fee = data.get('amount_paid', 5000)

    try:
        supabase.table("consultations").insert({
            "session_id": s_id,
            "patient_name": p_name,
            "hospital_id": str(h_id),
            "is_paid": True, 
            "status": "waiting",
            "amount_paid": actual_fee
        }).execute()
    except Exception as e:
        print(f"Supabase Error: {e}")

    # Notify all doctors in that specific hospital room
    emit('new_patient_waiting', {
        'patient_name': p_name,
        'session_id': s_id,
        'hospital_id': h_id
    }, to=h_id)

# 3. ACCEPTANCE & ROOM JOINING
@socketio.on('doctor_accepted_patient')
def handle_acceptance(data):
    session_id = data.get('session_id')
    hosp = data.get('hospital')
    doc_name = data.get('doctor_name', 'Doctor')

    join_room(session_id)
    
    # Update DB in background
    gevent.spawn(lambda: supabase.table("consultations").update({"status": "active"}).eq("session_id", session_id).execute())

    # Alert both parties to switch to the chat UI
    emit('match_found', {
        'session_id': session_id,
        'doctor': doc_name, 
        'doctor_name': doc_name,
        'status': 'connected'
    }, to=session_id)
    
    # Remove from other doctors' waiting lists
    emit('remove_patient_from_list', {'session_id': session_id}, to=hosp, include_self=False)

@socketio.on('join')
def on_join(data):
    username = data.get('user')
    room = data.get('room')
    role = data.get('role', 'Patient')

    if room:
        join_room(room)
        emit('receive_message', {
            'user': 'System', 
            'message': f'{username} has joined the consultation.'
        }, to=room)

# 4. MESSAGING
@socketio.on('send_message')
def handle_message(data):
    room = data.get('session_id') 
    if not room: return
    
    emit('receive_message', data, to=room)

    # Log to Supabase for medical records
    try:
        supabase.table("messages").insert({
            "session_id": room,
            "sender": data.get('user', 'Unknown'), 
            "content": data.get('message', ''), 
            "media_url": data.get('media_url'),
            "media_type": data.get('media_type')
        }).execute()
    except Exception as e:
        print(f"Log Error: {e}")

# 5. DISCONNECTS
@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_doctors:
        del active_doctors[request.sid]
        emit('update_doctor_counts', {"count": len(active_doctors)}, broadcast=True)

# --- 🚀 START SERVER ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)