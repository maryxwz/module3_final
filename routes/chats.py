from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from models import Chat, ChatParticipant, Message, Subject, User, PrivateChat, PrivateMessage, Enrollment
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from database import get_db
import datetime
import asyncio
from fastapi.templating import Jinja2Templates
import json
from security import get_current_user_for_id, get_current_user_ws
import logging
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


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


"""PAGES"""
@router.get("/my_chats")
async def list_of_chats_page(request: Request, current_user: User = Depends(get_current_user_for_id)):
    return templates.TemplateResponse("chats.html", {"request": request, "user": current_user})

@router.get("/user/chat/{username}")
async def list_of_chats_page(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_for_id), username: str = None):
    return templates.TemplateResponse("private_chat.html", {"request": request, "user": current_user, "username": username})

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




"""WEBSOCKETS"""
# FOR GROUP
@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat(chat_id: int, websocket: WebSocket, token = Depends(get_current_user_for_id), db: AsyncSession = Depends(get_db)):
    try:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=400, detail="Token is required")

        user_id = token.id
        
        chat_query = await db.execute(
            select(Chat).filter_by(id=chat_id)
        )
        chat = chat_query.scalar_one_or_none()
        
        if not chat:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        subject_query = await db.execute(
            select(Subject).filter_by(id=chat.subject_id)
        )
        subject = subject_query.scalar_one_or_none()
        
        is_teacher = subject and subject.teacher_id == user_id
        
        if not is_teacher:
            enrollment_query = await db.execute(
                select(Enrollment).filter_by(
                    student_id=user_id,
                    subject_id=chat.subject_id
                )
            )
            is_student = enrollment_query.scalar_one_or_none() is not None
            
            if not is_student:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

        await manager.connect(chat_id, websocket)

        user = await db.execute(select(User.username, User.avatar_url).filter_by(id=user_id))
        user = user.first()

        while True:
            try:
                data = await websocket.receive_text()  
                message_data = json.loads(data) 

                message_data['username'] = user.username
                message_data['avatar_url'] = user.avatar_url

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


@router.websocket("/ws/user/chat/{username}")
async def websocket_private_chat(username: str, websocket: WebSocket, token=Depends(get_current_user_for_id), db: AsyncSession = Depends(get_db)):
    chat_id = None 
    try:
        if not token:
            logger.warning(f"User token not found, closing websocket connection.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return  

        current_user_id = token.id
        logger.info(f"User {token.username} attempting to connect to private chat with {username}.")

        recipient_query = await db.execute(select(User.id).filter_by(username=username))
        recipient_ids = recipient_query.scalars().all()

        if len(recipient_ids) != 1:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=400, detail="Username must be unique")
        recipient_id = recipient_ids[0]

        if not recipient_id:
            logger.warning(f"Recipient user {username} not found, closing websocket connection.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return  

        logger.info(f"Recipient user {username} found, checking existing chats.")

        chat_query = await db.execute(
            select(PrivateChat)
            .filter(
                ((PrivateChat.user1_id == current_user_id) & (PrivateChat.user2_id == recipient_id)) |
                ((PrivateChat.user1_id == recipient_id) & (PrivateChat.user2_id == current_user_id))
            )
        )
        private_chat = chat_query.scalar_one_or_none()

        if not private_chat:
            logger.info(f"No existing chat found, creating a new private chat.")
            private_chat = PrivateChat(user1_id=current_user_id, user2_id=recipient_id)
            db.add(private_chat)
            await db.commit()
            await db.refresh(private_chat)

        chat_id = private_chat.id
        logger.info(f"User {token.username} connected to private chat with {username} (Chat ID: {chat_id}).")
        
        await manager.connect(chat_id, websocket)

        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"Received message from {token.username}: {data}")
                message_data = json.loads(data)

                new_message = PrivateMessage(
                    chat_id=chat_id,
                    sender_id=current_user_id,
                    content=message_data['content'],
                    created_at=datetime.datetime.utcnow()
                )
                db.add(new_message)
                await db.commit()

                message_data["username"] = token.username
                message_data["sender_id"] = current_user_id 
                message_data["avatar_url"] = token.avatar_url

                await manager.broadcast(chat_id, json.dumps(message_data))
            except asyncio.CancelledError:
                break

    except WebSocketDisconnect:
        if chat_id is not None:
            logger.info(f"WebSocket disconnected, removing user {token.username} from chat (Chat ID: {chat_id}).")
            manager.disconnect(chat_id, websocket)
    except Exception as e:
        logger.error(f"Error during WebSocket connection: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)

    
@router.get("/chats/")
async def get_user_chats(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Chat.id, Chat.is_group, Chat.created_at)
            .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
            .filter(ChatParticipant.user_id == user_id)
        )
        chats = result.all()

        return [{"chat_id": chat.id, "is_group": chat.is_group, "created_at": chat.created_at, "name": chat.name} for chat in chats]

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
async def get_chat_messages(chat_id: int, db: AsyncSession = Depends(get_db), token = Depends(get_current_user_for_id)):
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        user_id = token.id
        
        # Получаем чат и предмет
        chat_query = await db.execute(
            select(Chat).filter_by(id=chat_id)
        )
        chat = chat_query.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
            
        subject_query = await db.execute(
            select(Subject).filter_by(id=chat.subject_id)
        )
        subject = subject_query.scalar_one_or_none()
        
        is_teacher = subject and subject.teacher_id == user_id
        
        if not is_teacher:
            enrollment_query = await db.execute(
                select(Enrollment).filter_by(
                    student_id=user_id,
                    subject_id=chat.subject_id
                )
            )
            is_student = enrollment_query.scalar_one_or_none() is not None
            
            if not is_student:
                raise HTTPException(status_code=403, detail="Access denied")

        result = await db.execute(
            select(Message, User.username, User.avatar_url)
            .join(User, User.id == Message.sender_id)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        messages = result.all()

        return {
            "user_id": user_id,
            "subject_id": chat.subject_id,
            "messages": [
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "username": username,
                    "avatar_url": avatar_url,
                    "content": msg.content,
                    "created_at": msg.created_at,
                }
                for msg, username, avatar_url in messages
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {e}")


@router.get("/user/chat/{username}/messages")
async def get_private_chat_messages(
    username: str,
    db: AsyncSession = Depends(get_db),
    token=Depends(get_current_user_for_id)
):
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    current_user_id = token.id

    recipient_query = await db.execute(select(User).filter_by(username=username))
    recipient = recipient_query.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        print(f"Recipient found: {recipient.username}")


    chat_query = await db.execute(
    select(PrivateChat)
    .filter(
        ((PrivateChat.user1_id == current_user_id) & (PrivateChat.user2_id == recipient.id)) |
        ((PrivateChat.user1_id == recipient.id) & (PrivateChat.user2_id == current_user_id))
    )
)
    private_chat = chat_query.scalar_one_or_none()

    if not private_chat:
        private_chat = PrivateChat(user1_id=current_user_id, user2_id=recipient.id)
        db.add(private_chat)
        await db.commit()  
        await db.refresh(private_chat)
        print(f"New chat created: {private_chat.id}")

    messages_query = await db.execute(
        select(PrivateMessage, User.username)
        .join(User, User.id == PrivateMessage.sender_id)
        .filter(PrivateMessage.chat_id == private_chat.id)
        .order_by(PrivateMessage.created_at)
    )
    messages = messages_query.all()

    return {
        "user_id": current_user_id,
        "chat_id": private_chat.id,
        "current_username": token.username,
        "messages": [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "username": sender_username, 
                "content": msg.content,
                "created_at": msg.created_at,
                "avatar_url": (await db.execute(
                    select(User.avatar_url).where(User.id == msg.sender_id)
                )).scalar_one_or_none()
            }
            for msg, sender_username in messages
        ]
    }
