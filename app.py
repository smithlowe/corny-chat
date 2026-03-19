import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from supabase import create_client, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-2026'
# Use eventlet for better performance on Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- DATABASE ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

HOSPITAL_CODES = {
    "Mulago": "MUL789", "Nakasero": "NAK456", "Mukono": "MUK123", "Developer": "LAW2026"
}

# Shared memory for available doctors
ACTIVE_DOCTORS = {h: {} for h in HOSPITAL_CODES.keys()}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    if HOSPITAL_CODES.get(data.get('hospital')) == data.get('code'):
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@socketio.on('join')
def on_join(data):
    name = data.get('name')
    hospital = data.get('hospital')
    role = data.get('role')
    
    if not name or not hospital: return
    join_room(hospital)
    
    if role == 'Doctor':
        # Keep them 'busy' if they are mid-consultation, else make available
        if ACTIVE_DOCTORS[hospital].get(name) != "busy":
            ACTIVE_DOCTORS[hospital][name] = "available"
    
    # Push history if re-joining a specific doctor's chat
    doc_context = data.get('doctor_name')
    if doc_context and doc_context != "null":
        try:
            history = supabase.table("messages").select("*")\
                .eq("hospital", hospital).eq("doctor_name", doc_context)\
                .order("created_at", desc=False).limit(30).execute()
            emit('load_history', history.data)
        except: pass
        
    send_updates(hospital)

def send_updates(h):
    docs = [n for n, s in ACTIVE_DOCTORS[h].items() if s == "available"]
    emit('update_doctor_list', docs, room=h)

@socketio.on('request_consultation')
def handle_req(data):
    emit('consultation_request', data, room=data['hospital'])

@socketio.on('accept_patient')
def handle_acc(data):
    h, d, p = data['hospital'], data['doctor'], data['patient']
    ACTIVE_DOCTORS[h][d] = "busy"
    send_updates(h)
    emit('start_session', {'doctor': d, 'patient': p}, room=h)

@socketio.on('send_message')
def handle_msg(data):
    # Save to Supabase
    try:
        supabase.table("messages").insert({
            "sender": data['user'], "hospital": data['hospital'],
            "doctor_name": data.get('doctorName'), "content": data['message']
        }).execute()
    except: pass
    # Broadcast to everyone in the hospital room
    emit('receive_message', data, room=data['hospital'])

@socketio.on('end_session_global')
def handle_end(data):
    h, d = data['hospital'], data['doctor']
    if h in ACTIVE_DOCTORS: ACTIVE_DOCTORS[h][d] = "available"
    emit('force_exit_session', {'doctor': d}, room=h)
    send_updates(h)

@socketio.on('doctor_logout')
def handle_logout(data):
    h, n = data['hospital'], data['name']
    if h in ACTIVE_DOCTORS: ACTIVE_DOCTORS[h].pop(n, None)
    send_updates(h)

if __name__ == '__main__':
    socketio.run(app, debug=True)