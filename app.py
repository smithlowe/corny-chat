from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# 🔑 HOSPITAL PASSCODE REGISTRY
HOSPITAL_CODES = {
    "Mulago": "MUL789",
    "Nakasero": "NAK456",
    "Mukono": "MUK123",
    "Developer": "LAW2026" 
}

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

# --- SOCKET LOGIC ---

@socketio.on('join')
def on_join(data):
    username = data.get('name')
    hospital = data.get('hospital')
    doctor = data.get('doctorName')
    
    # Creates unique private room
    room = f"{hospital}_{doctor}".lower().replace(" ", "_")
    
    join_room(room)
    print(f"✅ {username} joined: {room}")
    
    emit('receive_message', {
        'user': 'System',
        'message': f'Secure connection established with {hospital}.',
        'timestamp': 'System'
    })

@socketio.on('send_message')
def handle_message(data):
    # Ensures message only goes to the specific Doctor/Patient room
    room = f"{data.get('hospital')}_{data.get('doctorName')}".lower().replace(" ", "_")
    emit('receive_message', data, room=room)

if __name__ == '__main__':
    socketio.run(app)