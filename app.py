import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_stable_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///corny.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Switch to gevent for better stability on Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50))
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# Track online users
online_users = 0

@app.route('/')
def index():
    history = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
    return render_template('index.html', history=history)

@socketio.on('connect')
def handle_connect():
    global online_users
    online_users += 1
    emit('user_count', {'count': online_users}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global online_users
    if online_users > 0:
        online_users -= 1
    emit('user_count', {'count': online_users}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    # Format time for Uganda (EAT)
    eat = pytz.timezone('Africa/Kampala')
    now = datetime.now(eat).strftime("%I:%M %p")
    
    new_msg = ChatMessage(user=data['user'], text=data['text'])
    db.session.add(new_msg)
    db.session.commit()
    
    data['time'] = now
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)