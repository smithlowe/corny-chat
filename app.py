import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# 1. SETUP FIRST
app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

connected_users = 0

# 2. ROUTES SECOND
@app.route('/')
def index():
    return render_template('index.html')

# 3. SOCKET EVENTS LAST
@socketio.on('connect')
def handle_connect():
    global connected_users
    connected_users += 1
    emit('user_count', {'count': connected_users}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_users
    connected_users = max(0, connected_users - 1)
    emit('user_count', {'count': connected_users}, broadcast=True)

@socketio.on('user_joined')
def handle_join(data):
    emit('render_msg', {
        'type': 'text', 
        'user': 'System', 
        'content': f"{data['name']} hopped into the field! 🌽"
    }, broadcast=True)

@socketio.on('message')
def handle_message(data):
    emit('render_msg', {
        'type': 'text', 
        'user': data['user'], 
        'content': data['content']
    }, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    emit('render_msg', {
        'type': 'voice', 
        'user': data['user'], 
        'content': data['audio']
    }, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)