import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from supabase import create_client, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- DATABASE CONNECTION ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 🔑 HOSPITAL PASSCODE REGISTRY
HOSPITAL_CODES = {
    "Mulago": "MUL789",
    "Nakasero": "NAK456",
    "Mukono": "MUK123",
    "Developer": "LAW2026"
}

# 📋 QUEUE & DOCTOR TRACKING
ACTIVE_DOCTORS = {h: {} for h in HOSPITAL_CODES.keys()}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    hospital = data.get('hospital')
    input_code = data.get('code')
    if HOSPITAL_CODES.get(hospital) == input_code:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

# --- SOCKET.IO LOGIC ---

@socketio.on('join')
def on_join(data):
    name = data.get('name')
    hospital = data.get('hospital')
    role = data.get('role')
    doctor_name = data.get('doctor_name') 
    
    join_room(hospital)
    
    if role in ['Doctor', 'Developer']:
        # Keep status as "busy" if they are re-joining a session, else "available"
        if ACTIVE_DOCTORS[hospital].get(name) != "busy":
            ACTIVE_DOCTORS[hospital][name] = "available"
    
    # 📥 PULL HISTORY
    if doctor_name and doctor_name != "undefined" and doctor_name != "null":
        try:
            history = supabase.table("messages") \
                .select("*") \
                .eq("hospital", hospital) \
                .eq("doctor_name", doctor_name) \
                .order("created_at", desc=False) \
                .limit(40) \
                .execute()
            emit('load_history', history.data)
        except Exception as e:
            print(f"History Load Error: {e}")
    
    send_doctor_updates(hospital)

def send_doctor_updates(hospital):
    available_docs = [name for name, status in ACTIVE_DOCTORS[hospital].items() if status == "available"]
    emit('update_doctor_list', available_docs, room=hospital)

@socketio.on('request_consultation')
def handle_request(data):
    emit('consultation_request', {
        'patient': data['patient'],
        'doctor': data['doctor']
    }, room=data['hospital'])

@socketio.on('accept_patient')
def handle_accept(data):
    hospital = data['hospital']
    doctor = data['doctor']
    patient = data['patient']
    
    ACTIVE_DOCTORS[hospital][doctor] = "busy"
    send_doctor_updates(hospital)
    
    emit('start_session', {'doctor': doctor, 'patient': patient}, room=hospital)

@socketio.on('send_message')
def handle_message(data):
    try:
        supabase.table("messages").insert({
            "sender": data['user'],
            "hospital": data['hospital'],
            "doctor_name": data.get('doctorName', 'General'),
            "content": data['message']
        }).execute()
    except Exception as e:
        print(f"DB Error: {e}")
    emit('receive_message', data, broadcast=True)

@socketio.on('end_session_global')
def handle_end_session(data):
    hospital = data.get('hospital')
    doctor = data.get('doctor')
    if hospital in ACTIVE_DOCTORS and doctor in ACTIVE_DOCTORS[hospital]:
        ACTIVE_DOCTORS[hospital][doctor] = "available"
    emit('force_exit_session', {'doctor': doctor}, room=hospital)
    send_doctor_updates(hospital)

@socketio.on('doctor_logout')
def handle_logout(data):
    hospital = data.get('hospital')
    name = data.get('name')
    if hospital in ACTIVE_DOCTORS and name in ACTIVE_DOCTORS[hospital]:
        del ACTIVE_DOCTORS[hospital][name]
    send_doctor_updates(hospital)

if __name__ == '__main__':
    socketio.run(app, debug=True)