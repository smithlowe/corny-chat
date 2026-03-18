@socketio.on('user_joined')
def handle_join(data):
    # Optional: Broadcast a message that someone joined
    emit('render_msg', {'type': 'text', 'user': 'System', 'content': f"{data['name']} hopped into the field! 🌽"}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    # Use the name sent from the frontend
    emit('render_msg', {'type': 'text', 'user': data['user'], 'content': data['content']}, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    emit('render_msg', {'type': 'voice', 'user': data['user'], 'content': data['audio']}, broadcast=True)