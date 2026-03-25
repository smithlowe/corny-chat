from flask_socketio import join_room, leave_room, emit

# ... (keep your Supabase and App setup at the top)

@socketio.on('join')
def on_join(data):
    """Triggered when a user enters a private room"""
    username = data.get('user')
    room_id = data.get('room')  # This will be the Patient's unique name or ID
    
    join_room(room_id)
    print(f"🏥 CLINIC ONLINE: {username} has entered Private Room: {room_id}")
    
    # Optional: Notify the room that someone arrived
    emit('receive_message', {
        'user': 'SYSTEM',
        'message': f'{username} has joined the consultation.',
        'room': room_id
    }, to=room_id)

@socketio.on('send_message')
def handle_message(data):
    """Sends message ONLY to the people in the specified room"""
    room_id = data.get('room')
    
    # 'to=room_id' is the secret sauce for privacy!
    emit('receive_message', data, to=room_id)
    
    # 💾 SAVE TO SUPABASE
    if supabase:
        try:
            supabase.table("messages").insert({
                "user_name": user, 
                "content": message, 
                "hospital": hosp
            }).execute()
        except Exception as e:
            print(f"Supabase Error: {e}")

    # 📢 BROADCAST REAL-TIME
    emit('receive_message', {
        'user': user,
        'message': message,
        'hospital': hosp
    }, to=hosp)
    from flask import request, jsonify
import uuid  # This helps give every file a unique name

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file selected"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Empty filename"}), 400

    try:
        # 1. Create a unique name (e.g., "7a2b-patient-xray.jpg")
        file_ext = file.filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        
        # 2. Read the file bytes
        file_data = file.read()
        
        # 3. Upload to Supabase 'medical-files' bucket
        storage_path = f"uploads/{unique_name}"
        supabase.storage.from_('medical-files').upload(storage_path, file_data)
        
        # 4. Get the Public URL
        file_url = supabase.storage.from_('medical-files').get_public_url(storage_path)
        
        return jsonify({"success": True, "url": file_url})
    
    except Exception as e:
        print(f"Upload Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Use eventlet's wsgi server for local testing
    socketio.run(app, debug=True)