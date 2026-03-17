import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_secret_key'
# Use eventlet for better performance on Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    # Direct access to the chat
    return render_template('index.html')

@socketio.on('message')
def handle_message(data):
    # This takes whatever the user sends and 'shouts' it to everyone
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    # Render provides a PORT environment variable we must use
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)