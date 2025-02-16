from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import bcrypt
from typing import Optional
import aiofiles
import os
from datetime import datetime
from models import models
from database import get_db
from security import verify_password, get_password_hash, get_current_user

router = APIRouter()

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/api/profile/update")
async def update_profile(
    avatar: Optional[UploadFile] = File(None),
    email: str = Form(...),
    username: str = Form(...),
    current_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Проверяем пароль
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")
    
    # Проверяем уникальность email и username
    if email != current_user.email:
        existing_user = await db.execute(select(models.User).filter(models.User.email == email))
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
    
    if username != current_user.username:
        existing_user = await db.execute(select(models.User).filter(models.User.username == username))
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Обрабатываем аватар если он загружен
    avatar_url = current_user.avatar_url
    if avatar:
        content = await avatar.read()
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        file_extension = os.path.splitext(avatar.filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Генерируем уникальное имя файла
        new_filename = f"{current_user.id}_{datetime.now().timestamp()}{file_extension}"
        file_path = os.path.join("avatars", new_filename)
        
        # Сохраняем файл
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(content)
            
        avatar_url = f"/avatars/{new_filename}"
        
        # Удаляем старый аватар если он существует
        if current_user.avatar_url:
            old_avatar_path = os.path.join(".", current_user.avatar_url.lstrip('/'))
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
    
    # Обновляем профиль в базе данных
    query = update(models.User).where(models.User.id == current_user.id).values(
        email=email,
        username=username,
        avatar_url=avatar_url
    )
    await db.execute(query)
    await db.commit()
    
    return {
        "email": email,
        "username": username,
        "avatar_url": avatar_url
    }

@router.post("/api/profile/change-password")
async def change_password(
    password_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Проверяем текущий пароль
    if not verify_password(password_data["current_password"], current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")
    
    # Проверяем совпадение нового пароля
    if password_data["new_password"] != password_data["confirm_password"]:
        raise HTTPException(status_code=400, detail="New passwords don't match")
    
    # Хешируем новый пароль
    hashed_password = get_password_hash(password_data["new_password"])
    
    # Обновляем пароль в базе данных
    query = update(models.User).where(models.User.id == current_user.id).values(
        hashed_password=hashed_password
    )
    await db.execute(query)
    await db.commit()
    
    return {"message": "Password updated successfully"} 