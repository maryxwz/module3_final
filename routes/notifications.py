from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory="templates")

class MessageText(BaseModel):
    id: int
    time_sent: str = datetime.now().strftime("%H:%M")


class Message(BaseModel):
    id: int
    person_from: str
    person_to: str
    text: MessageText
    date_sent: datetime = datetime.now()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_message(self, message: Message):
        if message.person_to in self.active_connections:
            for connection in self.active_connections[message.person_to]:
                await connection.send_json(message.dict())


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


async def send_notification(user_id: str, from_user: str, message: str):
    msg = Message(
        id=len(manager.active_connections),
        person_from=from_user,
        person_to=user_id,
        text=MessageText(
            id=len(manager.active_connections),
            time_sent=datetime.now().strftime("%H:%M")
        )
    )
    await manager.send_message(msg)

    return templates.TemplateResponse("subject_create.html", {
        "request": Request,
        "message": message
    })
# INFO:     127.0.0.1:61299 - "POST /subjects/create HTTP/1.1" 200 OK