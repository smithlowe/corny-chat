from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users in a dictionary { socket_id: username }
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # Connection established; we wait for joined or resync to count them
    pass

@socketio.on('user_joined')
def handle_user_joined(data):
    # We now save a 'dictionary' of info for each user
    active_users[request.sid] = {
        'name': data['name'],
        'role': data.get('role', 'Patient') # Defaults to Patient if not sent
    }
    
    # Custom announcement based on role
    user_name = data['name']
    if data.get('role') == 'Doctor':
        msg = f"👨‍⚕️ Dr. {user_name} has entered the clinic."
    else:
        msg = f"🏥 Patient {user_name} is requesting a consultation."

    emit('render_msg', {'user': 'System', 'content': msg}, broadcast=True)
    emit('user_count', {'count': len(active_users)}, broadcast=True)

@socketio.on('resync_user')
def handle_resync(data):
    # This keeps them logged in when they refresh
    active_users[request.sid] = {
        'name': data['name'],
        'role': data.get('role', 'Patient')
    }
    emit('user_count', {'count': len(active_users)}, broadcast=True)
    
    # Broadcast join message to everyone
    emit('render_msg', {'user': 'System', 'content': f"🌽 {data['name']} joined the field!"}, broadcast=True)
    
    # Send the NEW total count to everyone
    emit('user_count', {'count': len(active_users)}, broadcast=True)

@socketio.on('resync_user')
def handle_resync(data):
    # Add them to the active list SILENTLY (no "Joined" message)
    active_users[request.sid] = data['name']
    # Update the count for everyone so it doesn't stay at 0
    emit('user_count', {'count': len(active_users)}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    emit('render_msg', {
        'user': data['user'], 
        'content': data['content'], 
        'time': data['time'],
        'type': 'text'
    }, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    emit('render_msg', {
        'user': data['user'], 
        'content': data['audio'], 
        'time': data['time'],
        'type': 'voice'
    }, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    emit('display_typing', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    # Remove the user from our tracker when they leave or close the tab
    if request.sid in active_users:
        del active_users[request.sid]
    
    # Update everyone else with the new lower count
    emit('user_count', {'count': len(active_users)}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)