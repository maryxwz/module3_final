from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
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
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        username = data.get('username')
        current_password = data.get('current_password')
        update_data = {}
        
        # Проверяем пароль если меняется username
        if username and username != current_user.username:
            # Проверяем наличие пароля
            if not current_password:
                raise HTTPException(status_code=400, detail="Password required for changing username")
            
            # Проверяем правильность пароля
            if not verify_password(current_password, current_user.hashed_password):
                raise HTTPException(status_code=400, detail="Invalid password")
            
            # Проверяем доступность username
            existing_user = await db.execute(
                select(models.User).filter(models.User.username == username)
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Username already taken")
            
            update_data['username'] = username

        if update_data:
            # Обновляем данные пользователя
            await db.execute(
                update(models.User)
                .where(models.User.id == current_user.id)
                .values(**update_data)
            )
            await db.commit()
            
            # Получаем обновленные данные
            updated_user = await db.execute(
                select(models.User).filter(models.User.id == current_user.id)
            )
            updated_user = updated_user.scalar_one()
            
            return {
                "username": updated_user.username,
                "email": updated_user.email,
                "avatar_url": updated_user.avatar_url
            }
        
        return {
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url
        }
            
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/profile/change-password")
async def change_password(
    password_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        if not verify_password(password_data['current_password'], current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        new_hashed_password = get_password_hash(password_data['new_password'])
        
        await db.execute(
            update(models.User)
            .where(models.User.id == current_user.id)
            .values(hashed_password=new_hashed_password)
        )
        await db.commit()
        
        return {"message": "Password updated successfully"}
            
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}", exc_info=True)
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
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