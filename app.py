import os
from flask import Flask, render_html
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Connects to the Render Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database Table for Messages
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    profile_pic = db.Column(db.Text) # Stores the gallery image string

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(data):
    # Secret command to clear chat
    if data.get('message') == "/clear_all_now":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return

    # Save normal messages
    new_msg = Message(
        username=data['username'], 
        message=data['message'], 
        profile_pic=data.get('profile_pic', '')
    )
    db.session.add(new_msg)
    db.session.commit()
    emit('message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)