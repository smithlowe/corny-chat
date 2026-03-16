import os
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    # NEW: Stores the time the message was sent
    timestamp = db.Column(db.String(10), default=lambda: datetime.now().strftime("%H:%M"))

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
    
    messages = Message.query.all()
    for msg in messages:
        emit('message', {'username': msg.username, 'message': msg.content, 'time': msg.timestamp})

@socketio.on('message')
def handle_message(data):
    # ADMIN COMMAND: Type "/clear" to wipe the database
    if data['message'] == "/clear":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return

    new_msg = Message(username=data['username'], content=data['message'])
    db.session.add(new_msg)
    db.session.commit()
    
    # Send message with the current time
    data['time'] = datetime.now().strftime("%H:%M")
    emit('message', data, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    emit('display_typing', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_users
    connected_users = max(0, connected_users - 1)
    emit('user_count', {'count': connected_users}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)