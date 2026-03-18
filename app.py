@socketio.on('user_joined')
def handle_user_joined(data):
    # 1. Properly add user to the active list
    active_users[request.sid] = {
        'name': data.get('name'),
        'role': data.get('role')
    }
    
    name = data.get('name')
    
    # 2. PRIVATE WELCOME: Only the person joining sees this
    emit('render_msg', {
        'user': 'System',
        'content': f'Welcome to Corny-Comm, {name}! Your session is secure and private.',
        'time': ''
    })

    # 3. NOTIFY DOCTORS: Update their sidebars (Patients don't see this list)
    emit_user_update()

    # 4. PUBLIC COUNT: Tell everyone how many are online, but NOT their names
    socketio.emit('user_count', {
        'count': len(active_users)
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        user = active_users.pop(request.sid)
        
        # Update sidebar and count for remaining users
        emit_user_update()
        socketio.emit('user_count', {'count': len(active_users)}, broadcast=True)
        
        # PRIVATE LOGUE: We remove the "X left the clinic" broadcast for total privacy,
        # OR you can keep it as a generic "A user left" if you prefer.
        # Let's keep it silent to maintain full anonymity.