from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# This line creates 'socketio' - it MUST come before the @socketio.on lines
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(data):
    emit('render_msg', data, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    emit('render_msg', {'type': 'voice', 'content': data['audio']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)