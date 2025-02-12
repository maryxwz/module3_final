from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from models import Chat, ChatParticipant, Message, Subject, User
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
import datetime
import asyncio
from fastapi.templating import Jinja2Templates
import json
from security import get_current_user_for_id


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
async def list_of_chats_page(request: Request):
    return templates.TemplateResponse("chats.html", {"request": request})


@router.get("/my_chats/{chat_id}")
async def chat_page(
        request: Request,
        current_user: User = Depends(get_current_user_for_id),
        db: AsyncSession = Depends(get_db),
        chat_id: int = None
):
    subject_query = await db.execute(select(Subject).filter(Subject.chat.has(Chat.id == chat_id)))
    subject = subject_query.scalar_one_or_none()

    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "subject": subject,
            "chat_id": chat_id,
            "user": current_user
        }
    )


@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(chat_id: int, websocket: WebSocket, token=Depends(get_current_user_for_id),
                         db: AsyncSession = Depends(get_db)):
    try:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=400, detail="Token is required")

        user_id = token.id
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

        return [{"chat_id": chat.id, "is_group": chat.is_group, "created_at": chat.created_at, "name": chat.name} for
                chat in chats]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chats: {str(e)}")


@router.post("/chats/")
async def create_chat(
        title: str,
        user_ids: List[int],
        is_group: bool,
        db: AsyncSession = Depends(get_db)
):
    if len(user_ids) < 1:
        raise HTTPException(status_code=400, detail="At least one user is required")

    new_chat = Chat(is_group=is_group, name=title)
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)

    chat_participants = [ChatParticipant(chat_id=new_chat.id, user_id=user_id) for user_id in user_ids]
    db.add_all(chat_participants)
    await db.commit()

    return {"chat_id": new_chat.id, "is_group": new_chat.is_group}


@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: int, db: AsyncSession = Depends(get_db), token=Depends(get_current_user_for_id)):
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        user_id = token.id
        chat_participant = await db.execute(select(ChatParticipant).filter_by(chat_id=chat_id, user_id=user_id))
        chat_participant = chat_participant.scalars().first()

        if not chat_participant:
            raise HTTPException(status_code=400, detail="User is not a participant in this chat")

        result = await db.execute(
            select(Message, User.username)
            .join(User, User.id == Message.sender_id)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        messages = result.all()

        result = await db.execute(
            select(Chat.subject_id).filter_by(id=chat_id)
        )
        subject_id = result.scalar_one_or_none()

        return {
            "user_id": user_id,
            "subject_id": subject_id,
            "messages": [
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "username": username,
                    "content": msg.content,
                    "created_at": msg.created_at,
                }
                for msg, username in messages
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {e}")
