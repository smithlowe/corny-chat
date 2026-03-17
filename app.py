import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.config['SECRET_KEY'] = 'social_ultra_v5'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth Setup (Replace with your keys from Google Console)
app.config['GOOGLE_CLIENT_ID'] = "YOUR_CLIENT_ID"
app.config['GOOGLE_CLIENT_SECRET'] = "YOUR_CLIENT_SECRET"

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50000000)
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    profile_pic = db.Column(db.Text)
    audio_data = db.Column(db.Text)
    time = db.Column(db.String(20))
    is_read = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user' not in session:
        return render_template('login.html')
    return render_template('index.html', user=session['user'])

@app.route('/login-google')
def login_google():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user_info = google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
    session['user'] = {
        'name': user_info['name'],
        'picture': user_info['picture']
    }
    return redirect('/')

@socketio.on('message')
def handle_message(data):
    now = datetime.now().strftime("%I:%M %p")
    msg_id = datetime.now().timestamp() # Unique ID for read receipts
    
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
    data['id'] = new_msg.id
    emit('message', data, broadcast=True)

# READ RECEIPT LOGIC
@socketio.on('mark_read')
def mark_read(data):
    msg = Message.query.get(data['msg_id'])
    if msg:
        msg.is_read = True
        db.session.commit()
        emit('message_read', {'msg_id': data['msg_id']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)