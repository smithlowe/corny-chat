import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey123'

# Uses a local file. No external database needed!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database Structure
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    profile_pic = db.Column(db.Text)

# Create the database file automatically
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(data):
    # Admin clear command
    if data.get('message') == "/clear_now":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return

    # Save and broadcast message
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