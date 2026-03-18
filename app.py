from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
# CORS fix for Render deployment
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
    # Pass the message AND the timestamp to everyone
    emit('render_msg', {
        'user': data['user'], 
        'content': data['content'], 
        'time': data['time'],
        'type': 'text'
    }, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    # Sends "User is typing" to everyone EXCEPT the person typing
    emit('display_typing', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    global user_count
    if user_count > 0:
        user_count -= 1
    emit('user_count', {'count': user_count}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)