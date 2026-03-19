const express = require('express');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);

app.use(express.static('public')); 

io.on('connection', (socket) => {
    socket.on('join', (data) => {
        // 1. Create a unique, case-insensitive room name
        const consultationRoom = `${data.hospital}_${data.doctorName}`.toLowerCase();
        
        // 2. Join the room
        socket.join(consultationRoom);

        // 3. Send a private "Welcome" only to the user who joined
        socket.emit('receive_message', {
            user: "System",
            message: `Welcome to ${data.hospital}. A medical professional will be with you shortly.`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
        
        // 4. Store user data on the socket for security
        socket.userName = data.name;
        socket.role = data.role;
        socket.hospital = data.hospital;
        socket.doctorName = data.doctorName;
        socket.room = consultationRoom;

        console.log(`${data.name} (${data.role}) joined ${consultationRoom}`);
    });

    socket.on('send_message', (data) => {
        // Use socket.userName (server-side) for better security
        const secureData = {
            user: socket.userName,
            message: data.message,
            timestamp: data.timestamp
        };
        io.in(socket.room).emit('receive_message', secureData);
    });

    socket.on('typing', (data) => {
        // Broadcast typing status only to the other person
        socket.to(socket.room).emit('display_typing', data);
    });

    socket.on('disconnect', () => {
        if (socket.userName) {
            console.log(`ALERT: ${socket.userName} has left.`);
            
            // Inform the remaining user in the room
            socket.to(socket.room).emit('receive_message', {
                user: "System",
                message: `${socket.userName} has left the consultation.`,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            });
        }
    });
});

const PORT = process.env.PORT || 3000;
http.listen(PORT, () => {
    console.log(`Corny-Comm Medical running on port ${PORT}`);
});