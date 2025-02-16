from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import bcrypt
from typing import Optional, Dict
import aiofiles
import os
from datetime import datetime
import models
from database import get_db
from security import verify_password, get_password_hash, get_current_user_for_id
import logging
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/api/profile/update")
async def update_profile(
    request: Request,
    current_user: models.User = Depends(get_current_user_for_id),
    db: AsyncSession = Depends(get_db)
):
    try:
        form = await request.form()
        data = dict(form)
        
        # Обработка аватара
        if 'avatar' in data and isinstance(data['avatar'], UploadFile):
            avatar = data['avatar']
            if avatar.filename:
                # Проверяем расширение файла
                file_ext = os.path.splitext(avatar.filename)[1].lower()
                if file_ext not in ALLOWED_EXTENSIONS:
                    raise HTTPException(status_code=400, detail="Invalid file type")
                
                # Создаем директорию, если её нет
                os.makedirs("avatars", exist_ok=True)
                
                # Генерируем уникальное имя файла с timestamp
                timestamp = int(datetime.now().timestamp())
                filename = f"{current_user.id}_{timestamp}{file_ext}"
                file_location = f"avatars/{filename}"
                
                # Сохраняем файл
                try:
                    content = await avatar.read()
                    if len(content) > MAX_FILE_SIZE:
                        raise HTTPException(status_code=400, detail="File too large")
                        
                    async with aiofiles.open(file_location, 'wb') as out_file:
                        await out_file.write(content)
                    
                    print(f"File saved to: {file_location}")  # Отладочный вывод
                    
                    # Обновляем путь к аватару в БД
                    avatar_url = f"/avatars/{filename}"
                    await db.execute(
                        update(models.User)
                        .where(models.User.id == current_user.id)
                        .values(avatar_url=avatar_url)
                    )
                    await db.commit()
                    
                    # Получаем обновленные данные
                    result = await db.execute(
                        select(models.User).filter(models.User.id == current_user.id)
                    )
                    updated_user = result.scalar_one()
                    
                    return {
                        "username": updated_user.username,
                        "email": updated_user.email,
                        "avatar_url": updated_user.avatar_url,
                        "user_id": current_user.id
                    }
                except Exception as e:
                    logger.error(f"Error saving avatar: {str(e)}")
                    raise HTTPException(status_code=500, detail="Error saving avatar")

        return {
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
            "user_id": current_user.id
        }
            
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/profile/change-password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        # Проверяем текущий пароль
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Хешируем новый пароль
        new_hashed_password = get_password_hash(new_password)
        
        # Обновляем пароль в БД
        await db.execute(
            update(models.User)
            .where(models.User.id == current_user.id)
            .values(hashed_password=new_hashed_password)
        )
        
        await db.commit()
        
        logger.info(f"Password updated successfully for user {current_user.username}")
        
        # Перенаправляем на главную страницу
        return RedirectResponse(url="/", status_code=303)
            
    except HTTPException as he:
        await db.rollback()
        logger.error(f"HTTP error while updating password: {str(he)}")
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating password: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/profile/update-username")
async def update_username(
    username: str = Form(...),
    current_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        # Проверяем пароль
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Проверяем доступность username
        existing_user = await db.execute(
            select(models.User).filter(
                models.User.username == username,
                models.User.id != current_user.id
            )
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")
        
        old_username = current_user.username
        
        # Обновляем только username в таблице users
        await db.execute(
            update(models.User)
            .where(models.User.id == current_user.id)
            .values(username=username)
        )
        
        await db.commit()
        
        logger.info(f"Username updated successfully from {old_username} to {username}")
        
        # Перенаправляем на главную страницу
        return RedirectResponse(url="/", status_code=303)
    
    except HTTPException as he:
        await db.rollback()
        logger.error(f"HTTP error while updating username: {str(he)}")
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating username: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/profile/update-email")
async def update_email(
    email: str = Form(...),
    current_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        # Проверяем пароль
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        old_email = current_user.email
        
        # Обновляем email в таблице users
        await db.execute(
            update(models.User)
            .where(models.User.id == current_user.id)
            .values(email=email)
        )
        
        await db.commit()
        
        logger.info(f"Email updated successfully from {old_email} to {email}")
        
        # Перенаправляем на главную страницу
        return RedirectResponse(url="/", status_code=303)
    
    except HTTPException as he:
        await db.rollback()
        logger.error(f"HTTP error while updating email: {str(he)}")
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/profile/update-avatar")
async def update_avatar(
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        if avatar.filename:
            # Проверяем расширение файла
            file_ext = os.path.splitext(avatar.filename)[1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail="Invalid file type")
            
            # Создаем директорию, если её нет
            os.makedirs("avatars", exist_ok=True)
            
            # Генерируем уникальное имя файла с timestamp
            timestamp = int(datetime.now().timestamp())
            filename = f"{current_user.id}_{timestamp}{file_ext}"
            file_location = f"avatars/{filename}"
            
            # Сохраняем файл
            content = await avatar.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")
                
            async with aiofiles.open(file_location, 'wb') as out_file:
                await out_file.write(content)
            
            # Обновляем путь к аватару в БД
            avatar_url = f"/avatars/{filename}"
            await db.execute(
                update(models.User)
                .where(models.User.id == current_user.id)
                .values(avatar_url=avatar_url)
            )
            await db.commit()
            
            # Получаем обновленные данные
            result = await db.execute(
                select(models.User).filter(models.User.id == current_user.id)
            )
            updated_user = result.scalar_one()
            
            return {
                "success": True,
                "avatar_url": updated_user.avatar_url,
                "user_id": current_user.id
            }
            
    except Exception as e:
        logger.error(f"Error updating avatar: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 