from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*")

# Counter for active users
connected_users = 0

@app.route('/')
def index():
    return render_template('index.html')

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

@socketio.on('message')
def handle_message(data):
    emit('render_msg', data, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    emit('render_msg', {'type': 'voice', 'content': data['audio']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)