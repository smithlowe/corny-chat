from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# 🔑 HOSPITAL PASSCODE REGISTRY
# You can add more hospitals here as you grow!
HOSPITAL_CODES = {
    "Mulago": "MUL789",
    "Nakasero": "NAK456",
    "Mukono": "MUK123",
    "Developer": "LAW2026" # Your personal master code
}

@app.route('/')
def index():
    return render_template('index.html')

# New route to verify the code without refreshing the page
@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    hospital = data.get('hospital')
    input_code = data.get('code')
    
    if HOSPITAL_CODES.get(hospital) == input_code:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

# ... keep your existing @socketio.on functions below ...