import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'social_v4_premium'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50000000)

# Track active users for "Last Seen" and "Typing"
active_users = {}

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    profile_pic = db.Column(db.Text)
    audio_data = db.Column(db.Text)
    time = db.Column(db.String(20))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    active_users[username] = "Online"
    emit('status_update', active_users, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    emit('display_typing', data, broadcast=True, include_self=False)

@socketio.on('message')
def handle_message(data):
    if data.get('message') == "/clear_now":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return

    now = datetime.now().strftime("%I:%M %p")
    new_msg = Message(
        username=data.get('username'),
        message=data.get('message'),
        profile_pic=data.get('profile_pic'),
        audio_data=data.get('audio'),
        time=now
    )
    db.session.add(new_msg)
    db.session.commit()
    
    data['time'] = now
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)