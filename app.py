from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*")

user_count = 0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('user_joined')
def handle_user_joined(data):
    global user_count
    user_count += 1
    emit('render_msg', {'user': 'System', 'content': f"🌽 {data['name']} joined the field!"}, broadcast=True)
    emit('user_count', {'count': user_count}, broadcast=True)

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
    # This sends the audio data to everyone
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
    global user_count
    if user_count > 0:
        user_count -= 1
    emit('user_count', {'count': user_count}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)