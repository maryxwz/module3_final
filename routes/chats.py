from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models import Chat, ChatParticipant, Message
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from models import User
from database import get_db
from pydantic import BaseModel
import datetime
import asyncio
from fastapi.templating import Jinja2Templates
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        try:
            await websocket.accept()
            if chat_id not in self.active_connections:
                self.active_connections[chat_id] = []
            self.active_connections[chat_id].append(websocket)
        except Exception as e:
            raise WebSocketDisconnect(f"Error while connecting: {e}")

    def disconnect(self, chat_id: int, websocket: WebSocket):
        try:
            if chat_id in self.active_connections:
                self.active_connections[chat_id].remove(websocket)
                if not self.active_connections[chat_id]:
                    del self.active_connections[chat_id]
        except Exception as e:
            raise WebSocketDisconnect(f"Error while disconnecting: {e}")

    async def broadcast(self, chat_id: int, message: str):
        try:
            if chat_id in self.active_connections:
                for connection in self.active_connections[chat_id]:
                    await connection.send_text(message)
        except Exception as e:
            raise WebSocketDisconnect(f"Error while broadcasting: {e}")


router = APIRouter()
manager = ConnectionManager()
templates = Jinja2Templates(directory="templates")

@router.get("/my_chats")
async def login_page(request: Request):
    return templates.TemplateResponse("chats.html", {"request": request})

@router.get("/my_chats/{chat_id}")
async def login_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.websocket("/ws/chat/{chat_id}/{user_id}")
async def websocket_chat(chat_id: int, user_id: int, websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    try:
        chat_participant = await db.execute(select(ChatParticipant).filter_by(chat_id=chat_id, user_id=user_id))
        chat_participant = chat_participant.scalars().first()

        if not chat_participant:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=400, detail="User is not a participant in this chat")

        await manager.connect(chat_id, websocket)

        user = await db.execute(select(User.username).filter_by(id=user_id))
        user = user.scalars().first()
        print(f"User {user} connected to chat {chat_id}")

        while True:
            try:
                data = await websocket.receive_text()  
                message_data = json.loads(data) 

                message_data['username'] = user
                

                new_message = Message(
                    chat_id=chat_id,
                    sender_id=user_id,
                    content=message_data['content'],
                    created_at=datetime.datetime.utcnow()
                )
                db.add(new_message)
                await db.commit()

                await manager.broadcast(chat_id, json.dumps(message_data)) 

            except asyncio.CancelledError:
                break

    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(f"Unexpected error: {e}")





@router.get("/users/")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.get("/chats/")
async def get_user_chats(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Chat.id, Chat.is_group, Chat.created_at)
            .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
            .filter(ChatParticipant.user_id == user_id)
        )
        chats = result.all()

        return [{"chat_id": chat.id, "is_group": chat.is_group, "created_at": chat.created_at} for chat in chats]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chats: {str(e)}")


@router.post("/chats/")
async def create_chat(user_ids: List[int], db: AsyncSession = Depends(get_db)):
    if len(user_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two users required")
    
    user_ids_sorted = sorted(user_ids)
    
    existing_chats = await db.execute(
        select(Chat).options(selectinload(Chat.participants))
    )
    existing_chats = existing_chats.scalars().all()
    
    for chat in existing_chats:
        participant_ids = sorted([participant.user_id for participant in chat.participants])
        if participant_ids == user_ids_sorted:
            raise HTTPException(status_code=400, detail="A chat with the same participants already exists")
    
    new_chat = Chat(is_group=len(user_ids) > 2)
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    
    chat_participants = [ChatParticipant(chat_id=new_chat.id, user_id=user_id) for user_id in user_ids]
    db.add_all(chat_participants)
    await db.commit()
    
    return {"chat_id": new_chat.id, "is_group": new_chat.is_group}



from sqlalchemy.orm import joinedload

@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Message, User.username)
            .join(User, User.id == Message.sender_id)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        
        messages = result.all()

        return [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "username": username,  
                "content": msg.content,
                "created_at": msg.created_at,
            }
            for msg, username in messages
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {e}")

