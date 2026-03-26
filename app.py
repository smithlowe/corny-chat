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
    user_role = data.get('role') # We pass 'Doctor' or 'Patient'
    
    # If a Doctor tries to join a private consultation room
    if user_role == 'Doctor' and room.startswith('cons-'):
        # Check Supabase if this specific session is PAID
        check = supabase.table("consultations").select("status").eq("session_id", room).single().execute()
        
        if check.data and check.data['status'] == 'paid':
            join_room(room)
            emit('system_msg', {'msg': 'Doctor has entered the verified session.'}, to=room)
        else:
            emit('error', {'msg': 'Access Denied: Payment not verified for this session.'})
    else:
        # Patients can always join their own requested rooms
        join_room(room) 
@socketio.on('request_consultation')
def handle_request(data):
    patient = data.get('user')
    hospital = data.get('hospital_id')
    lat = data.get('lat')
    lon = data.get('lon')
    
    session_id = f"cons-{uuid.uuid4().hex[:8]}" 
    
    # 💰 Record the 5,000 UGX fee and your 1,000 UGX commission
    supabase.table("consultations").insert({
        "session_id": session_id,
        "patient_name": patient,
        "hospital_id": hospital,
        "amount_paid": 5000,
        "platform_fee": 1000, 
        "is_paid": False, # 🔒 Locked
        "patient_lat": lat,
        "patient_lon": lon
    }).execute()
    
    emit('payment_prompt', {
        'session_id': session_id,
        'fee': 5000,
        'hospital': hospital
    })
@socketio.on('test_payment_success')
def handle_payment_master(data):
    session_id = data.get('session_id')
    
    # 1. UNLOCK: Update Supabase so the Doctor can eventually enter
    supabase.table("consultations").update({"is_paid": True}).eq("session_id", session_id).execute()
    
    # 2. GET DATA: Fetch the patient's name and hospital ID
    res = supabase.table("consultations").select("*").eq("session_id", session_id).single().execute()
    patient_data = res.data
    
    if patient_data:
        # 3. ALERT PATIENT: Tell the patient's browser to show the "Waiting" screen
        emit('match_found', {'session_id': session_id}, room=request.sid)

        # 4. PING DOCTORS: Notify all doctors in that specific hospital's lounge
        hospital_lounge = f"lounge_{patient_data['hospital_id']}"
        emit('new_patient_waiting', {
            'patient_name': patient_data['patient_name'],
            'session_id': session_id,
            'hospital': patient_data['hospital_id']
        }, room=hospital_lounge)
        
        print(f"✅ Payment verified for {patient_data['patient_name']}. Doctors in {hospital_lounge} notified.")
@socketio.on('patient_paid_and_waiting')
def handle_patient_waiting(data):
    patient_name = data.get('patient_name')
    hosp_id = data.get('hospital') 
    
    # Create the Unique Session ID
    import uuid
    session_id = str(uuid.uuid4())[:8]

    # Save to Supabase (Record the 5k transaction)
    supabase.table("consultations").insert({
        "session_id": session_id,
        "patient_name": patient_name,
        "hospital_id": hosp_id,
        "status": "waiting"
    }).execute()

    # Ping ONLY the doctors in that hospital's lounge
    lounge_room = f"lounge_{hosp_id}"
    emit('new_patient_waiting', {
        'patient_name': patient_name,
        'session_id': session_id
    }, room=lounge_room)
    
    print(f"✅ {patient_name} is waiting for a doctor in {lounge_room}")
@socketio.on('doctor_accepted_patient')
def handle_acceptance(data):
    session_id = data.get('session_id')
    doc_name = data.get('doctor_name')
    
    # Get hospital_id for this session to tell the right lounge
    res = supabase.table("consultations").select("hospital_id").eq("session_id", session_id).single().execute()
    hosp_id = res.data['hospital_id']
    
    # Update Supabase to record which doctor took the case
    supabase.table("consultations").update({"doctor_name": doc_name}).eq("session_id", session_id).execute()

    # Broadcast to all OTHER doctors in that hospital lounge to remove the button
    lounge_room = f"lounge_{hosp_id}"
    emit('remove_patient_from_list', {'session_id': session_id}, room=lounge_room)
    
    print(f"✅ Doctor {doc_name} accepted session {session_id}. Removed from {lounge_room} queue.")
@socketio.on('join')
def on_join(data):
    room = data.get('hospital')
    role = data.get('role')

    if room.startswith('cons-') and role == 'Doctor':
        # 🛡️ THE LOCK: Check if is_paid is True in Supabase
        check = supabase.table("consultations").select("is_paid").eq("session_id", room).single().execute()
        if not check.data or not check.data.get('is_paid'):
            emit('error', {'msg': '🛑 Access Denied: Payment not verified for this session.'})
            return 

    join_room(room)
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