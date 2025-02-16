# Цей код має функцію віправки смс, connection_manager і шматочок штмл/джс що поєднані з пітоном для показки повідомлення
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException, HTTPException
from pydantic import BaseModel, field_validator, Field
from datetime import datetime
from typing import List


app = FastAPI()


class MessageText(BaseModel): # для класу Сповіщення
    id: int
    time_sent: datetime.now().strftime("%H:%M")


class Message(BaseModel): # клас Сповіщення відповідно завданнячку
    id: int
    person_from: str # тут буде клас юзера
    person_to: str # тут теж буде клас юзера
    text: MessageText
    date_sent: datetime.now()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: Message, websocket: WebSocket):
        await websocket.send_json(message.dict())

    async def broadcast(self, message: Message):
        for connection in self.active_connections:
            await connection.send_json(message.dict())


manager = ConnectionManager()


@app.get('/main')
async def main():
    pass

@app.websocket('/message_sending')
async def message_sending(websocket: WebSocket, message: Message):
    await manager.connect(websocket)
    try:
        while True:
            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# джаваскріпт і шмат html
#     <div id="notification"></div> <!-- Notification element -->
#
#     <script>
#         let ws = new WebSocket("ws://127.0.0.1:8000/message_sending");
#
#         ws.onmessage = function(event) {
#             const message = JSON.parse(event.data);
#
#             // Set the notification text
#             const notificationDiv = document.getElementById('notification');
#             notificationDiv.textContent = `New message from ${message.person_from}: ${message.text.time_sent}`;
#             notificationDiv.style.display = 'block'; // Show the notification
#
#             // Hide the notification after 7 seconds
#             setTimeout(() => {
#                 notificationDiv.style.display = 'none';
#             }, 7000); // 7000 ms = 7 seconds
#         };
#
#         ws.onopen = function() {
#             console.log("WebSocket connection established!");
#         };
#
#         ws.onclose = function() {
#             console.log("WebSocket connection closed!");
#         };
#     </script>
#     <script>
#         let ws = new WebSocket("ws://127.0.0.1:8000/message_sending");
#
#         ws.onmessage = function(event) {
#             const message = JSON.parse(event.data);
#             alert(`New message from ${message.person_from}: ${message.text.time_sent}`);
#         };
#
#         ws.onopen = function() {
#             console.log("WebSocket connection established!");
#         };
#
#         ws.onclose = function() {
#             console.log("WebSocket connection closed!");
#         };
#     </script>
