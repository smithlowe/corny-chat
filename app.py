import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'social_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# User counter
online_users = 0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global online_users
    online_users += 1
    emit('user_count', {'count': online_users}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global online_users
    if online_users > 0:
        online_users -= 1
    emit('user_count', {'count': online_users}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    # This sends the message to everyone connected
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    # host='0.0.0.0' is the key! It tells the app to listen to your phone.
    print("🚀 Server starting... Try connecting your phone to http://192.168.1.213:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)