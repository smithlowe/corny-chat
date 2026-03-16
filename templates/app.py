import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'global_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# Memory to store who is online
users_online = []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def on_join(data):
    username = data['username']
    if username not in users_online:
        users_online.append(username)
    
    # Notify everyone
    emit('status', {'msg': f'🌍 {username} joined from the world!'}, broadcast=True)
    emit('user_list', users_online, broadcast=True)

@socketio.on('message')
def on_message(data):
    emit('chat', {'user': data['user'], 'msg': data['msg']}, broadcast=True)

if __name__ == '__main__':
    # Using 5001 to avoid common Windows port blocks
    print("🚀 App starting at http://127.0.0.1:5001")
    socketio.run(app, host='127.0.0.1', port=5001, debug=True)