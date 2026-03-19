from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'medical-secret!'
# Allow connections from your Render URL
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    # Flask looks inside the /templates folder for this
    return render_template('index.html')

@socketio.on('join')
def on_join(data):
    username = data.get('name')
    hospital = data.get('hospital')
    doctor = data.get('doctorName')
    
    # Create a unique room ID (e.g., mulago_dr-lawrence)
    room = f"{hospital}_{doctor}".lower().replace(" ", "_")
    
    join_room(room)
    print(f"✅ {username} joined medical room: {room}")
    
    # Send a welcome message to just that user
    emit('receive_message', {
        'user': 'System',
        'message': f'Connected to {hospital} secure line. Private room: {room}',
        'timestamp': 'System'
    })

@socketio.on('send_message')
def handle_message(data):
    # In a real app, we'd store the room on the session. 
    # For this version, we broadcast to the specific room the user is in.
    room = f"{data.get('hospital')}_{data.get('doctorName')}".lower().replace(" ", "_")
    emit('receive_message', data, room=room)

@socketio.on('typing')
def handle_typing(data):
    room = f"{data.get('hospital')}_{data.get('doctorName')}".lower().replace(" ", "_")
    emit('display_typing', data, room=room, include_self=False)

if __name__ == '__main__':
    socketio.run(app)