import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'corny_memory_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///corny.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# This is the "Memory" structure
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50))
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create the database file
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # When you open the page, it gets the last 50 messages from memory
    history = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
    return render_template('index.html', history=history)

@socketio.on('message')
def handle_message(data):
    # 1. Save to Memory
    new_msg = ChatMessage(user=data['user'], text=data['text'])
    db.session.add(new_msg)
    db.session.commit()
    
    # 2. Shout to everyone
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host='0.0.0.0', port=port)