import os
import uuid
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask import session
from supabase import create_client, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'med_secure_2026'

# Fixed: Removed the double async_mode and set it to gevent
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Supabase Setup (Remains exactly as you had it)
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


@socketio.on('request_consultation')
def handle_request(data):
    # ...
    # Fetch the fee from the hospitals table first
    res = supabase.table("hospitals").select("consultation_fee").eq("secret_code", hospital).single().execute()
    hosp_fee = res.data.get('consultation_fee', 5000) if res.data else 5000

    emit('payment_prompt', {
        'session_id': session_id,
        'fee': hosp_fee, # ✅ Matches Supabase
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
active_doctors = {} # Put this at the very top of app.py

@socketio.on('join_lounge')
def handle_lounge_join(data):
    # 1. Get the code from the doctor
    hosp_code = data.get('hospital') # Matches your frontend hospSelect.value
    doc_name = data.get('doctor')

    # 2. SECURITY CHECK: Verify this code exists in Supabase
    result = supabase.table('hospitals').select('*').eq('secret_code', hosp_code).execute()
    
    if result.data:
        # SUCCESS: Code is valid
        hospital_name = result.data[0]['name']
        join_room(hosp_code)

        # 3. TRACKING: Store in session for the disconnect event
        session['hosp_code'] = hosp_code
        session['is_doctor'] = True

        # 4. COUNTER: Increment the active doctor count
        active_doctors[hosp_code] = active_doctors.get(hosp_code, 0) + 1
        
        # 5. RESPONSE: Tell the doctor they are in
        emit('lounge_joined', {
            'status': 'success', 
            'hospital': hospital_name,
            'doctor': doc_name
        })

        # 6. BROADCAST: Tell everyone (patients + doctors) the new counts
        emit('update_doctor_counts', active_doctors, broadcast=True)
        print(f"👨‍⚕️ {doc_name} joined {hospital_name}. Total online: {active_doctors[hosp_code]}")
    
    else:
        # FAILURE: Code doesn't exist in your database
        emit('lounge_joined', {'status': 'error', 'message': 'Invalid Access Code'})

@socketio.on('disconnect')
def handle_disconnect():
    hosp_code = session.get('hosp_code')
    is_doc = session.get('is_doctor')

    if is_doc and hosp_code in active_doctors:
        active_doctors[hosp_code] = max(0, active_doctors[hosp_code] - 1)
        emit('update_doctor_counts', active_doctors, broadcast=True)
        print(f"📡 Connection lost. {hosp_code} doctor count: {active_doctors[hosp_code]}")

@socketio.on('patient_paid_and_waiting')
def handle_patient_waiting(data):
    p_name = data.get('patient_name')
    h_id = data.get('hospital', 'unknown')
    s_id = data.get('session_id')
    
    # 💰 NEW: Pull the specific fee sent from the frontend 
    # If for some reason it's missing, it defaults to 5000
    actual_fee = data.get('fee', 5000)

    try:
        # Match your SQL structure exactly
        supabase.table("consultations").insert({
            "session_id": s_id,
            "patient_name": p_name,
            "hospital_id": h_id,
            "is_paid": True, 
            "status": "waiting",
            "amount_paid": actual_fee,  # ✅ Now matches the hospital's price
            "platform_fee": 1000        # Your fixed commission
        }).execute()
        print(f"✅ Supabase updated: {s_id} (Fee: {actual_fee}) is now LIVE.")
    except Exception as e:
        print(f"❌ Supabase Error: {e}")

    # Notify doctors in the specific hospital lounge
    lounge_room = f"lounge_{str(h_id).lower()}"
    emit('new_patient_waiting', {
        'patient_name': p_name,
        'session_id': s_id
    }, room=lounge_room)

@socketio.on('join')
def on_join(data):
    room = data.get('hospital') 
    role = data.get('role')
    user = data.get('user')

    # Security check for Doctors
    if room.startswith('cons-') and role == 'Doctor':
        res = supabase.table("consultations").select("*").eq("session_id", room).execute()
        if not res.data:
            print(f"⚠️ Access Denied: {room} not in DB.")
            emit('error', {'msg': '🛑 Session not found.'})
            return 

    join_room(room)
    emit('receive_message', {'user': 'System', 'message': f'{user} has joined.'}, to=room)
# --- Inside app.py ---
@socketio.on('doctor_accepted_patient')
def handle_acceptance(data):
    session_id = data.get('session_id')
    hosp = data.get('hospital', 'unknown')
    lounge_room = f"lounge_{str(hosp).lower()}"

    # 1. Update Supabase status to 'active' or 'taken'
    supabase.table("consultations").update({"status": "active"}).eq("session_id", session_id).execute()

    # 2. Tell the Patient they are matched (Same as before)
    emit('match_found', {'session_id': session_id, 'doctor': data.get('doctor_name')}, room=session_id)

    # 3. THE FIX: Tell all other doctors in the lounge to remove this patient
    # 'include_self=False' ensures the current doctor's UI doesn't break
    emit('remove_patient_from_list', {'session_id': session_id}, room=lounge_room, include_self=False)
# ... all your other routes and imports above ...

@socketio.on('send_message')
def handle_message(data):
    hosp = data.get('hospital')
    if not hosp:
        return
    
    # Broadcast to everyone in the hospital room
    emit('receive_message', data, to=hosp)

    try:
        supabase.table("messages").insert({
            "sender": data.get('user', 'Unknown'), 
            "content": data.get('message', ''), 
            "hospital": hosp, 
            "doctor_name": data.get('doctor_name', '')
        }).execute()
    except Exception as e:
        print(f"⚠️ Database Log Error: {e}")

# THIS MUST BE THE ABSOLUTE LAST TWO LINES
if __name__ == '__main__':
    socketio.run(app)