from datetime import datetime
 # Optional: if you want specific Uganda time

@socketio.on('message')
def handle_message(data):
    # Create a nice timestamp (e.g., 06:45 PM)
    now = datetime.now().strftime("%I:%M %p")
    
    # 1. Save to Database (We add the 'time' string here)
    new_msg = ChatMessage(user=data['user'], text=data['text'])
    # Note: If your ChatMessage model doesn't have a time string yet, 
    # we can just pass 'now' to the broadcast for now!
    db.session.add(new_msg)
    db.session.commit()
    
    # 2. Add the time to the data package before shouting it out
    data['time'] = now
    emit('message', data, broadcast=True)