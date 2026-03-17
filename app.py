@socketio.on('message')
def handle_message(data):
    if data.get('message') == "/clear_now":
        Message.query.delete()
        db.session.commit()
        emit('reload', broadcast=True)
        return

    now = datetime.now().strftime("%I:%M %p")
    
    # Save to Database
    new_msg = Message(
        username=data['username'],
        message=data.get('message', ''),
        profile_pic=data.get('profile_pic'),
        audio_data=data.get('audio'),
        time=now
    )
    db.session.add(new_msg)
    db.session.commit()
    
    # Send back to everyone with all required fields
    output = {
        'id': new_msg.id,
        'username': data['username'],
        'message': data.get('message', ''),
        'profile_pic': data.get('profile_pic'),
        'audio': data.get('audio'),
        'time': now
    }
    emit('message', output, broadcast=True)