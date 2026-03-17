import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Buffer set to 50MB to ensure high-quality voice/images go through
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50000000)

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
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['user'], pfp=session.get('pfp', ''))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        session['pfp'] = request.form.get('pfp_data')
        return redirect(url_for('index'))
    return render_template('login.html')

@socketio.on('typing')
def handle_typing(data):
    # Sends "User is typing..." to everyone except the person typing
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
        username=data['username'],
        message=data.get('message', ''),
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