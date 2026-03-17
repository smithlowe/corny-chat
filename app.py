import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_123'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    # Corny-chat usually starts straight at the chat interface
    return render_template('index.html')

@socketio.on('message')
def handle_message(data):
    # Sends the message, username, and pfp to everyone
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    # Use the port Render expects
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)