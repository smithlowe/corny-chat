import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room # 👈 Added leave_room
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
    
    # ... Supabase update code ...

    res = supabase.table("consultations").select("*").eq("session_id", session_id).execute()
    if res.data:
        p_data = res.data[0]
        
        # 🚨 THE FIX: Use the raw hosp_code (e.g., "MUL101") 
        # matches the join_room(hosp_code) in your join_lounge function
        hosp_room = p_data['hospital_id'] 

        # 🏥 ALERT DOCTORS
        emit('new_patient_waiting', {
            'patient_name': p_data['patient_name'],
            'session_id': session_id
        }, room=hosp_room) # 👈 Send to "MUL101" instead of "lounge_mul101"
        
        print(f"📡 Broadcast sent to Hospital Room: {hosp_room}")

@socketio.on('join_lounge')
def handle_lounge_join(data):
    hosp_code = data.get('hospital') # e.g., "MUL101"
    doc_name = data.get('doctor')

    # 1. Verify code in Supabase
    result = supabase.table('hospitals').select('*').eq('secret_code', hosp_code).execute()
    
    if result.data:
        hospital_name = result.data[0]['name']
        join_room(hosp_code)
        
        # 2. Update tracking
        session['hosp_code'] = hosp_code
        active_doctors[hosp_code] = active_doctors.get(hosp_code, 0) + 1
        
        # 3. SUCCESS RESPONSE (Crucial for the Frontend to transition)
        emit('lounge_joined', {
            'status': 'success', 
            'hospital': hospital_name,
            'doctor': doc_name
        })

        # 4. BROADCAST UPDATED COUNTS
        emit('update_doctor_counts', active_doctors, broadcast=True)
        
        print(f"👨‍⚕️ {doc_name} is now ONLINE in {hospital_name} ({hosp_code})")
    else:
        # FAILURE
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
    # 🚨 FIX: Match the 'hospital_id' key from your JS
    h_id = data.get('hospital_id', 'unknown') 
    s_id = data.get('session_id')
    
    # 🚨 FIX: Match the 'amount_paid' key from your JS
    actual_fee = data.get('amount_paid', 5000)

    try:
        # Save to Supabase
        supabase.table("consultations").insert({
            "session_id": s_id,
            "patient_name": p_name,
            "hospital_id": str(h_id),
            "is_paid": True, 
            "status": "waiting",
            "amount_paid": actual_fee,
            "platform_fee": 1000 
        }).execute()
        print(f"✅ Supabase updated: {s_id} (Fee: {actual_fee}) is now LIVE.")
    except Exception as e:
        print(f"❌ Supabase Error: {e}")

    # 🏥 The "Lounge" Broadcast
    # We send the alert to the specific hospital lounge
    lounge_room = f"lounge_{str(h_id).lower()}"
    emit('new_patient_waiting', {
        'patient_name': p_name,
        'session_id': s_id,
        'hospital_id': h_id
    }, room=lounge_room)

@socketio.on('join')
def on_join(data):
    room = data.get('hospital') 
    role = data.get('role')
    user = data.get('user')

    # 1. Security check for Doctors entering a PRIVATE Consultation
    if room.startswith('cons-') and role == 'Doctor':
        res = supabase.table("consultations").select("*").eq("session_id", room).execute()
        if not res.data:
            print(f"⚠️ Access Denied: {room} not in DB.")
            emit('error', {'msg': '🛑 Session not found.'})
            return 

    # 2. Add this Print so you can see what's happening in your terminal
    print(f"👤 {user} ({role}) is joining room: {room}")

    # 3. Actually join the room (This works for both 'cons-' and 'lounge_')
    join_room(room)
    
    # 4. Tell the room someone joined
    emit('receive_message', {'user': 'System', 'message': f'{user} has joined.'}, to=room)
# --- Inside app.py ---
@socketio.on('doctor_accepted_patient')
def handle_acceptance(data):
    session_id = data.get('session_id')
    hosp = data.get('hospital', 'unknown')
    doc_name = data.get('doctor_name', 'Doctor')
    lounge_room = f"lounge_{str(hosp).lower()}"

    # 1. Update Supabase so no other doctor can take this session
    try:
        supabase.table("consultations").update({"status": "active"}).eq("session_id", session_id).execute()
    except Exception as e:
        print(f"❌ Supabase Update Error: {e}")

    # 2. THE MOVE: Doctor leaves the general lounge and joins the private chat
    leave_room(lounge_room) # 🚪 Stop hearing other patient alerts
    join_room(session_id)   # 🤝 Join the private session with the patient
    print(f"👨‍⚕️ {doc_name} joined private session: {session_id}")

    # 3. Tell the Patient their doctor has arrived
    emit('match_found', {
        'session_id': session_id, 
        'doctor': doc_name
    }, room=session_id)

    # 4. Cleanup the Lounge: Tell OTHER doctors to remove this patient from their list
    # 'include_self=False' is key so the current doctor's UI stays clean
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