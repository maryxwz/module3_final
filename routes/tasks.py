from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import models, schemas
from database import get_db
from security import get_current_user
from fastapi.responses import RedirectResponse
from datetime import datetime

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/create", response_model=schemas.TaskOut)
async def create_task(
    title: str = Form(...),
    description: str = Form(...),
    deadline: datetime = Form(...),
    subject_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()
    
    result = await db.execute(select(models.Subject).filter(models.Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    if subject.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Only the teacher can create tasks")
    
    db_task = models.Task(
        title=title,
        description=description,
        deadline=deadline,
        subject_id=subject_id
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return RedirectResponse(url=f"/subjects/{subject_id}", status_code=303)


@router.get("/subject/{subject_id}", response_model=List[schemas.TaskOut])
async def get_subject_tasks(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()
    
    result = await db.execute(select(models.Subject).filter(models.Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    if subject.teacher_id != user.id:
        result = await db.execute(
            select(models.Enrollment).filter(
                models.Enrollment.student_id == user.id,
                models.Enrollment.subject_id == subject_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(select(models.Task).filter(models.Task.subject_id == subject_id))
    tasks = result.scalars().all()
    return tasks
