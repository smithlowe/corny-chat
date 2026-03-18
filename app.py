import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'med_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*")

# This stores everyone currently in the clinic
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

# --- THE CLINIC SWITCHBOARD HELPER ---
def emit_user_update():
    """Updates the Doctor's sidebar with the current patient list"""
    users_list = []
    for sid, info in active_users.items():
        users_list.append({
            'name': info.get('name'),
            'role': info.get('role'),
            'sid': sid
        })
    
    # Sends the list to all connected clients
    socketio.emit('user_count', {
        'count': len(active_users),
        'users_list': users_list
    })

# --- EVENT HANDLERS ---

@socketio.on('user_joined')
def handle_user_joined(data):
    # Register the user
    active_users[request.sid] = {
        'name': data['name'],
        'role': data['role']
    }
    
    # Update the Doctor's sidebar immediately
    emit_user_update()
    
    # System announcement
    emit('render_msg', {
        'user': 'System',
        'content': f"🏥 {data['name']} ({data['role']}) joined the session.",
        'time': ''
    }, broadcast=True)

@socketio.on('message')
def handle_message(data):
    sender_sid = request.sid
    sender_info = active_users.get(sender_sid, {})
    sender_role = sender_info.get('role', 'Patient')
    
    target_sid = data.get('target') # This is the SID from the Sidebar click

    message_packet = {
        'user': data['user'],
        'content': data['content'],
        'time': data['time'],
        'sender_role': sender_role
    }

    if sender_role == 'Doctor':
        if target_sid and target_sid in active_users:
            # PRIVATE: Send only to that patient and the doctor
            emit('render_msg', message_packet, room=target_sid)
            emit('render_msg', message_packet, room=sender_sid)
        else:
            # PUBLIC: Dr. making a general announcement
            emit('render_msg', message_packet, broadcast=True)
    else:
        # PATIENT: Messages only go to Doctors and themselves
        for sid, info in active_users.items():
            if info.get('role') == 'Doctor' or sid == sender_sid:
                emit('render_msg', message_packet, room=sid)

@socketio.on('voice_note')
def handle_voice(data):
    # Same privacy logic for voice notes
    target_sid = data.get('target')
    sender_sid = request.sid
    sender_role = active_users.get(sender_sid, {}).get('role', 'Patient')
    
    packet = {
        'user': data['user'],
        'content': data['audio'],
        'time': data['time'],
        'type': 'voice',
        'sender_role': sender_role
    }
    
    if sender_role == 'Doctor' and target_sid:
        emit('render_msg', packet, room=target_sid)
        emit('render_msg', packet, room=sender_sid)
    elif sender_role == 'Patient':
        for sid, info in active_users.items():
            if info.get('role') == 'Doctor' or sid == sender_sid:
                emit('render_msg', packet, room=sid)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        user = active_users.pop(request.sid)
        # Update sidebar to remove them
        emit_user_update()
        
        emit('render_msg', {
            'user': 'System',
            'content': f"{user['name']} left the clinic.",
            'time': ''
        }, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)