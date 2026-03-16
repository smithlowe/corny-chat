from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy # This handles the database
import os

app = Flask(__name__)
# Set up the database file
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# This creates the "Message" table in our database
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    content = db.Column(db.String(500))

# Create the database file if it doesn't exist
with app.app_context():
    db.create_all()

connected_users = 0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global connected_users
    connected_users += 1
    emit('user_count', {'count': connected_users}, broadcast=True)
    
    # NEW: When someone connects, send them ALL old messages from the database
    old_messages = Message.query.all()
    for msg in old_messages:
        emit('message', {'username': msg.username, 'message': msg.content})

@socketio.on('message')
def handle_message(data):
    # SAVE the message to the database notebook
    new_msg = Message(username=data['username'], content=data['message'])
    db.session.add(new_msg)
    db.session.commit()
    
    emit('message', data, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    emit('display_typing', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_users
    connected_users = max(0, connected_users - 1)
    emit('user_count', {'count': connected_users}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)