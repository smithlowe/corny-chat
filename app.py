import eventlet
eventlet.monkey_patch() # Must be at the very top for Render

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-123'
# Note: On Render, 'filesystem' sessions might need a 'flask_session' extension.
# For now, we will stick to standard signed cookies (default).

socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage
hospitals = {
    "Mulago": {"doctors": set(), "codes": ["MUL123"]},
    "Nakasero": {"doctors": set(), "codes": ["NAK456"]},
    "Mukono": {"doctors": set(), "codes": ["MUK789"]}
}
chat_histories = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    hosp = data.get('hospital')
    code = data.get('code')
    name = data.get('name')
    
    if hosp in hospitals and code in hospitals[hosp]['codes']:
        session['user_name'] = name
        session['hospital'] = hosp
        session['role'] = 'Doctor'
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/logout', methods=['POST'])
def logout_route():
    session.clear() 
    return jsonify({"success": True}) # Fixed missing parenthesis here

# --- Socket Events ---

@socketio.on('join')
def handle_join(data):
    # Use session data if available, fallback to provided data
    name = session.get('user_name') or data.get('name')
    hosp = session.get('hospital') or data.get('hospital')
    role = session.get('role') or data.get('role')
    
    if not name or not hosp:
        return False # Reject join if no identity found

    if role == 'Doctor':
        hospitals[hosp]['doctors'].add(name)
    
    join_room(hosp)
    emit('status', {'msg': f'{name} has entered the room.'}, to=hosp)
    emit('update_doctor_list', list(hospitals[hosp]['doctors']), to=hosp)

@socketio.on('accept_patient')
def handle_accept(data):
    room_id = str(uuid.uuid4())[:8]
    data['room_id'] = room_id
    emit('start_private_session', data, to=data['hospital'])

@socketio.on('join_private')
def handle_private_join(data):
    room = data['room_id']
    join_room(room)
    if room in chat_histories:
        emit('load_history', chat_histories[room])

@socketio.on('send_message')
def handle_message(data):
    room = data.get('room_id')
    msg_obj = {
        "user": data['user'],
        "message": data['message'],
        "doctorName": data.get('doctorName')
    }
    
    if room not in chat_histories:
        chat_histories[room] = []
    chat_histories[room].append({"sender": data['user'], "content": data['message']})
    
    emit('receive_message', msg_obj, to=room)

@socketio.on('end_session_global')
def handle_end(data):
    room = data.get('room_id')
    emit('force_exit_session', data, to=room)
    if room in chat_histories:
        del chat_histories[room]
    leave_room(room)

@socketio.on('doctor_logout')
def handle_logout(data):
    hosp = data.get('hospital')
    name = data.get('name')
    if hosp in hospitals and name in hospitals[hosp]['doctors']:
        hospitals[hosp]['doctors'].remove(name)
    emit('update_doctor_list', list(hospitals[hosp]['doctors']), to=hosp)

if __name__ == '__main__':
    # Use the port Render provides, or 5000 locally
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)