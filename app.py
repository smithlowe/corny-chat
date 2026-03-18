@socketio.on('message')
def handle_message(data):
    # data format: {'type': 'text', 'content': 'hello'}
    emit('render_msg', data, broadcast=True)

@socketio.on('voice_note')
def handle_voice(data):
    # data format: {'audio': 'base64_string'}
    emit('render_msg', {'type': 'voice', 'content': data['audio']}, broadcast=True)