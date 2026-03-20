from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
from flask import session

@socketio.on('join')
def on_join(data):
    username = data.get('username')
    # If the username is missing from the request and the session
    if not username and 'username' not in session:
        return False # This rejects the connection/event
    
    room = data.get('room')
    join_room(room)
    emit('status', {'msg': f'{username} has entered the room.'}, room=room)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-123'
# Ensure sessions work across restarts during development
app.config['SESSION_TYPE'] = 'filesystem' 
socketio = SocketIO(app, cors_allowed_origins="*")
# In-memory storage (Use a DB like SQLite/Postgres for production)
hospitals = {
    "Mulago": {"doctors": set(), "codes": ["MUL123"]},
    "Nakasero": {"doctors": set(), "codes": ["NAK456"]},
    "Mukono": {"doctors": set(), "codes": ["MUK789"]}
}
chat_histories = {} # room_id: [messages]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    hosp = data.get('hospital')
    code = data.get('code')
    name = data.get('name') # Get the name from the request
    
    if hosp in hospitals and code in hospitals[hosp]['codes']:
        # STORE IN SESSION
        session['user_name'] = name
        session['hospital'] = hosp
        session['role'] = 'Doctor'
        return jsonify({"success": True})
    return jsonify({"success": False})
    
    @app.route('/logout', methods=['POST'])
def logout_route():
    session.clear() # Wipes the server-side session
    return jsonify({"success": True}

# --- Socket Events ---

@socketio.on('join')
def handle_join(data):
    name = data['name']
    hosp = data['hospital']
    role = data['role']
    
    # Logic for Doctors
    if role == 'Doctor':
        hospitals[hosp]['doctors'].add(name)
    
    # Join the hospital-wide lobby room
    join_room(hosp)
    
    # Update only the patients in that specific hospital lobby
    emit('update_doctor_list', list(hospitals[hosp]['doctors']), to=hosp)

@socketio.on('accept_patient')
def handle_accept(data):
    # Create a unique private room ID
    room_id = str(uuid.uuid4())[:8]
    data['room_id'] = room_id
    
    # Notify both patient and doctor in the hospital lobby to move to private
    emit('start_private_session', data, to=data['hospital'])

@socketio.on('join_private')
def handle_private_join(data):
    room = data['room_id']
    join_room(room)
    # If history exists, send it to the user joining
    if room in chat_histories:
        emit('load_history', chat_histories[room])

@socketio.on('send_message')
def handle_message(data):
    room = data.get('room_id')
    msg_obj = {
        "user": data['user'],
        "message": data['message'],
        "doctorName": data['doctorName']
    }
    
    # Store history
    if room not in chat_histories:
        chat_histories[room] = []
    chat_histories[room].append({"sender": data['user'], "content": data['message']})
    
    # Send only to the private room
    emit('receive_message', msg_obj, to=room)

@socketio.on('end_session_global')
def handle_end(data):
    room = data.get('room_id')
    # Signal both parties to exit the chat UI
    emit('force_exit_session', data, to=room)
    # Clear history and leave room
    if room in chat_histories:
        del chat_histories[room]
    leave_room(room)

@socketio.on('doctor_logout')
def handle_logout(data):
    hosp = data['hospital']
    name = data['name']
    if name in hospitals[hosp]['doctors']:
        hospitals[hosp]['doctors'].remove(name)
    emit('update_doctor_list', list(hospitals[hosp]['doctors']), to=hosp)

if __name__ == '__main__':
    socketio.run(app, debug=True)