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

# HD Buffer for Gallery Images
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10000000)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(10), default=lambda: datetime.now().strftime("%H:%M"))
    is_audio = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

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
        is_audio=data.get('is_audio', False),
        profile_pic=data.get('profile_pic')
    )
    db.session.add(new_msg)
    db.session.commit()
    
    data['time'] = datetime.now().strftime("%H:%M")
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)