import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from supabase import create_client, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- DATABASE ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

HOSPITAL_CODES = {"Mulago": "MUL789", "Nakasero": "NAK456", "Mukono": "MUK123", "Developer": "LAW2026"}
ACTIVE_DOCTORS = {h: {} for h in HOSPITAL_CODES.keys()}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    h, c = data.get('hospital'), data.get('code')
    return jsonify({"success": HOSPITAL_CODES.get(h) == c})

@socketio.on('join')
def on_join(data):
    name, hospital, role = data.get('name'), data.get('hospital'), data.get('role')
    if not name or not hospital: return
    
    join_room(hospital)
    if role == 'Doctor':
        if ACTIVE_DOCTORS[hospital].get(name) != "busy":
            ACTIVE_DOCTORS[hospital][name] = "available"
    
    # Fetch history if doctor context exists
    doc_name = data.get('doctor_name')
    if doc_name and doc_name != "null":
        try:
            res = supabase.table("messages").select("*").eq("hospital", hospital).eq("doctor_name", doc_name).order("created_at").limit(30).execute()
            emit('load_history', res.data)
        except Exception as e: print(f"DB Error: {e}")
            
    send_updates(hospital)

def send_updates(h):
    avail = [n for n, s in ACTIVE_DOCTORS[h].items() if s == "available"]
    emit('update_doctor_list', avail, room=h)

@socketio.on('accept_patient')
def handle_acc(data):
    h, d, p = data['hospital'], data['doctor'], data['patient']
    ACTIVE_DOCTORS[h][d] = "busy"
    send_updates(h)
    emit('start_session', {'doctor': d, 'patient': p}, room=h)

@socketio.on('send_message')
def handle_msg(data):
    # CRITICAL: Broadcast to the hospital room so both sides hear it
    emit('receive_message', data, room=data['hospital'])
    try:
        supabase.table("messages").insert({
            "sender": data['user'], "hospital": data['hospital'],
            "doctor_name": data.get('doctorName'), "content": data['message']
        }).execute()
    except Exception as e: print(f"Save Error: {e}")

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