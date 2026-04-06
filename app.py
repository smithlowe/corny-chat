import gevent.monkey
gevent.monkey.patch_all(dns=True, socket=True, thread=True) 

import gevent  # <--- ADD THIS: Needed for gevent.sleep and gevent.spawn
import os
import uuid
from flask import Flask, render_template, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from supabase import create_client

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "med_secure_2026")

# 🏥 Global tracking
active_doctors = {}

# Initialize SocketIO with all stability flags
# Initialize SocketIO with all stability flags
socketio = SocketIO(app, 
    cors_allowed_origins="*", 
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=10,
    manage_session=True,
    allow_upgrades=True,
    logger=True,
    engineio_logger=True
) # <--- THIS BRACKET WAS MISSING

# Supabase Helper
def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = get_supabase()

# --- 🌐 ALL ROUTES GO HERE ---

# --- 🌐 ALL ROUTES GO HERE (ABOVE START BLOCK) ---

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
        # Use the storage bucket 'medical-files'
        storage = supabase.storage.from_('medical-files')
        storage.upload(unique_name, file.read())
        return jsonify({"success": True, "url": storage.get_public_url(unique_name)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/verify-code', methods=['POST'])
def verify():
    data = request.json
    # 🏥 Your Hospital Access Codes
    passcodes = {"Mulago": "MUL-2026", "Nakasero": "NAK-555", "Mukono": "MUK-888"}
    if data.get('code') == passcodes.get(data.get('hospital')) or data.get('code') == "ADMIN-99":
        return jsonify({"success": True})
    return jsonify({"success": False})

# --- 🚀 START SERVER BLOCK (ALWAYS AT THE VERY BOTTOM) ---

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)


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
    print(f"💰 Payment success for session: {session_id}")

    # 1. Update Supabase
    supabase.table("consultations").update({"is_paid": True}).eq("session_id", session_id).execute()

    # 2. Get the Hospital ID from the database
    res = supabase.table("consultations").select("*").eq("session_id", session_id).execute()
    
    if res.data:
        p_data = res.data[0]
        # 🚨 Use the exact ID the doctor uses (e.g., "MUL101")
        hosp_room = p_data.get('hospital_id') 

        if hosp_room:
            # 🏥 Shout to the Doctor's room
            emit('new_patient_waiting', {
                'patient_name': p_data['patient_name'],
                'session_id': session_id
            }, room=hosp_room)
            print(f"📡 Notification sent to Room: {hosp_room}")

# --- 1. THE DOCTOR'S LOBBY ---
@socketio.on('join_lounge')
def handle_lounge_join(data):
    hosp_code = data.get('hospital')
    doc_name = data.get('doctor', 'Unknown Doctor')
    
    print(f"🔍 [DEBUG] Doctor '{doc_name}' trying code: '{hosp_code}'")

    try:
        # 1. Check Supabase for valid code
        result = supabase.table('hospitals').select('*').eq('secret_code', hosp_code).execute()
        
        if result.data:
            hospital_name = result.data[0]['name']
            
            # 2. Join the physical room for notifications
            join_room(hosp_code) 
            
            # 3. Track the SPECIFIC connection (sid)
            active_doctors[request.sid] = {
                "name": doc_name,
                "hospital": hosp_code
            }
            
            # 4. Save to session for reliability
            session['hosp_code'] = hosp_code
            session['is_doctor'] = True
            
            # 5. Send Success Response to the Doctor who joined
            emit('lounge_joined', {
                'status': 'success', 
                'hospital': hospital_name,
                'doctor': doc_name
            })
            
            # 6. Broadcast updated counts to EVERYONE
            emit('update_doctor_counts', {"count": len(active_doctors)}, broadcast=True)
            print(f"✅ {doc_name} is now monitoring {hospital_name}")
            
        else:
            # Code was wrong
            emit('lounge_joined', {'status': 'error', 'message': 'Invalid Access Code'})
            
    except Exception as e:
        # Something went wrong with the Database or Server
        print(f"❌ Supabase/Server Error: {str(e)}")
        emit('lounge_joined', {'status': 'error', 'message': 'Server Error'})

# --- 2. THE PRIVATE CONSULTATION (The New Function) ---
@socketio.on('join')
def on_join(data):
    try:
        username = data.get('user')
        room = data.get('room') # This is the 'cons-xxxx' ID
        role = data.get('role', 'Patient')

        if not room: return

        join_room(room) # Both Doctor and Patient enter this private room
        print(f"👤 {username} ({role}) locked into room: {room}")

        # If a patient joins, let's make sure their status is 'active'
        if role == 'Patient':
             supabase.table("consultations").update({"status": "active"}).eq("session_id", room).execute()

        emit('receive_message', {
            'user': 'System', 
            'message': f'{username} has joined the consultation.'
        }, to=room)

    except Exception as e:
        print(f"❌ Error in on_join: {str(e)}")

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

    # 🏥 The "Lounge" Broadcast - ALIGNED WITH DOCTOR JOIN
    # Instead of f"lounge_{str(h_id).lower()}", use the raw ID
    # because that's what handle_lounge_join uses: join_room(hosp_code)
    
    emit('new_patient_waiting', {
        'patient_name': p_name,
        'session_id': s_id,
        'hospital_id': h_id
    }, to=h_id) # 👈 Just use h_id (e.g., 'MUL101')
    
    print(f"📢 Notification sent to room: {h_id}")


# --- Insid@socketio.on('join')
def on_join(data):
    try:
        username = data.get('user')
        room = data.get('room')
        role = data.get('role', 'Patient')

        if not room:
            return

        join_room(room)
        print(f"👤 {username} ({role}) is joining room: {room}")

        emit('receive_message', {
            'user': 'System', 
            'message': f'{username} has joined.'
        }, to=room)

        if role == 'Patient':
            try:
                # Syncing with your 'status' column in Supabase
                supabase.table("consultations").update({"status": "LIVE"}).eq("session_id", room).execute()
                print(f"✅ Supabase updated: {room} is now LIVE.")
                emit('status_update', {'status': 'LIVE', 'session_id': room}, to=room)
            except Exception as db_e:
                print(f"⚠️ Database Error: {str(db_e)}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR in on_join: {str(e)}")
@socketio.on('doctor_accepted_patient')
def handle_acceptance(data):
    # 1. The Breather
    gevent.sleep(0.1) 
    
    session_id = data.get('session_id')
    hosp = data.get('hospital')
    doc_name = data.get('doctor_name', 'Doctor')

    # 2. THE "SIDEWAYS" UPDATE (Paste it here)
    def update_db():
        try:
            # This runs in the background
            supabase.table("consultations").update({"status": "active"}).eq("session_id", session_id).execute()
            print(f"✅ [DB BACKGROUND] Session {session_id} set to active.")
        except Exception as e:
            print(f"❌ [DB BACKGROUND ERROR]: {e}")

    gevent.spawn(update_db) # This triggers the background task instantly

    # 3. Join the doctor to the private room
    join_room(session_id)
    print(f"👨‍⚕️ {doc_name} joined private session: {session_id}")

    # 4. Notify BOTH the patient and doctor that they are matched
    # This happens immediately because we didn't wait for the DB!
    emit('match_found', {
        'session_id': session_id,
        'doctor_name': doc_name,
        'status': 'connected'
    }, to=session_id)
    # 5. Cleanup: Tell other doctors in the hospital that this patient is taken
    emit('remove_patient_from_list', {'session_id': session_id}, to=hosp, include_self=False)
# ... all your other routes and imports above ...

@socketio.on('send_message')
def handle_message(data):
    # CRITICAL: Use session_id to ensure private chat, not the hospital room
    room = data.get('session_id') 
    if not room:
        return
    
    # Broadcast ONLY to the private session room
    emit('receive_message', data, to=room)

    try:
        supabase.table("messages").insert({
            "session_id": room, # Match this to your Supabase column
            "sender": data.get('user', 'Unknown'), 
            "content": data.get('message', ''), 
            "doctor_name": data.get('doctor_name', '')
        }).execute()
    except Exception as e:
        print(f"⚠️ Database Log Error: {e}")

if __name__ == '__main__':
    # Render assigns a dynamic port; we must capture it
    port = int(os.environ.get("PORT", 10000))
    # host='0.0.0.0' allows external traffic to reach the app
    socketio.run(app, host='0.0.0.0', port=port)