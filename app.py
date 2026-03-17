import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'social_secret_777'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Massive 50MB buffer to handle high-quality voice notes and large images
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50000000)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    profile_pic = db.Column(db.Text)
    audio_data = db.Column(db.Text)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(data):
    if data.get('message') == "/clear_now":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return

    new_msg = Message(
        username=data.get('username'),
        message=data.get('message'),
        profile_pic=data.get('profile_pic'),
        audio_data=data.get('audio')
    )
    db.session.add(new_msg)
    db.session.commit()
    # Broadcast everything (including the audio key)
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)