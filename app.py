from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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
    emit('message', data, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    # Sends "is typing" status to everyone except the person typing
    emit('display_typing', data, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app)