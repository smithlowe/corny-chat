import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'social_v6_final'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# max_http_buffer_size allows for high-quality photos/voice
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50000000)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    profile_pic = d.Column(db.Text)
    audio_data = db.Column(db.Text)
    time = db.Column(db.String(20))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    # This sends the 'user' name to the HTML
    return render_template('index.html', username=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect(url_for('index'))
    return render_template('login.html')

@socketio.on('message')
def handle_message(data):
    now = datetime.now().strftime("%I:%M %p")
    new_msg = Message(
        username=data['username'],
        message=data.get('message', ''),
        profile_pic=data.get('profile_pic', ''),
        audio_data=data.get('audio', ''),
        time=now
    )
    db.session.add(new_msg)
    db.session.commit()
    
    # Send all info back to the users
    data['time'] = now
    data['id'] = new_msg.id
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)