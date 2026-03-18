from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
# Ensure cors_allowed_origins is "*" for Render deployment
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

connected_users = 0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global connected_users
    connected_users += 1
    # Broadcast user count to ALL clients
    emit('user_count', {'count': connected_users}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_users
    if connected_users > 0:
        connected_users -= 1
    emit('user_count', {'count': connected_users}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    # This sends the text message to everyone connected
    emit('render_msg', {'type': 'text', 'content': data['content']}, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    # This sends the audio data to everyone connected
    emit('render_msg', {'type': 'voice', 'content': data['audio']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)