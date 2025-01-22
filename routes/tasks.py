from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import models, schemas
from database import get_db
from security import get_current_user
from datetime import datetime

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=schemas.TaskOut)
async def create_task(
    task: schemas.TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = await db.query(models.User).filter(models.User.email == current_user).first()
    course = await db.query(models.Course).filter(models.Course.id == task.course_id).first()
    
    if not course or course.teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create tasks for your own courses"
        )
    
    db_task = models.Task(
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        course_id=task.course_id
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/course/{course_id}", response_model=List[schemas.TaskOut])
async def get_course_tasks(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = await db.query(models.User).filter(models.User.email == current_user).first()
    course = await db.query(models.Course).filter(models.Course.id == course_id).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if user.role == "student":
        enrollment = await db.query(models.Enrollment).filter(
            models.Enrollment.student_id == user.id,
            models.Enrollment.course_id == course_id
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this course"
            )
    
    tasks = await db.query(models.Task).filter(models.Task.course_id == course_id).all()
    return tasks 