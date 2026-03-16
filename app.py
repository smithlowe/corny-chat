import os
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# SocketIO setup with 10MB limit for high-quality audio
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10000000)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(code=db.Text, nullable=False)
    timestamp = db.Column(db.String(10), default=lambda: datetime.now().strftime("%H:%M"))
    is_audio = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

connected_users = 0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global connected_users
    connected_users += 1
    emit('user_count', {'count': connected_users}, broadcast=True)
    messages = Message.query.order_by(Message.id.asc()).all()
    for msg in messages:
        emit('message', {
            'username': msg.username, 
            'message': msg.content, 
            'time': msg.timestamp, 
            'is_audio': msg.is_audio
        })

@socketio.on('message')
def handle_message(data):
    if data.get('message') == "/clear":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return
    
    new_msg = Message(
        username=data['username'], 
        content=data['message'], 
        is_audio=data.get('is_audio', False)
    )
    db.session.add(new_msg)
    db.session.commit()
    data['time'] = datetime.now().strftime("%H:%M")
    emit('message', data, broadcast=True)

@socketio.on('vibe_change')
def handle_vibe(data):
    emit('vibe_update', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_users
    connected_users = max(0, connected_users - 1)
    emit('user_count', {'count': connected_users}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)