from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import selectinload

import models
import schemas
from database import get_db
from security import get_current_user, get_current_user_for_id

router = APIRouter(prefix="/tasks", tags=["tasks"])
templates = Jinja2Templates(directory="templates")


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


@router.get("/homeworks")
async def homework_page(request: Request, db: AsyncSession = Depends(get_db),
                        current_user: models.User = Depends(get_current_user_for_id)):
    stmt = select(models.Enrollment).where(models.Enrollment.student_id == current_user.id)
    result = await db.execute(stmt)
    enrollments = result.scalars().all()

    enrolled_subject_ids = [enrollment.subject_id for enrollment in enrollments]

    current_time = datetime.now()

    stmt = select(models.Task).join(models.Subject).where(
        models.Task.subject_id.in_(enrolled_subject_ids),
        models.Task.deadline >= current_time
    ).order_by(models.Task.deadline)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return templates.TemplateResponse("homeworks.html", {"request": request, "tasks": tasks})


@router.get("/edit/{task_id}")
async def edit_task_form(
        request: Request,
        task_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.subject)).where(models.Task.id == task_id))
    task = result.scalar_one_or_none()

    await db.refresh(task)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the teacher can edit tasks")

    return templates.TemplateResponse("edit_task.html", {"request": request, "task": task})


@router.post("/task_edit/{task_id}")
async def update_task(task_id: int,
                      title: str = Form(...),
                      description: str = Form(...),
                      deadline: str = Form(...),
                      db: AsyncSession = Depends(get_db),
                      ):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.subject)).filter(models.Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    task.title = title
    task.description = description
    task.deadline = datetime.fromisoformat(deadline)

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return RedirectResponse(url=f"/subjects/{task.subject_id}", status_code=303)


@router.post("/delete/{task_id}")
async def subject_delete(
        task_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.subject)).filter(models.Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if not task.subject or task.subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the teacher can delete tasks")

    await db.delete(task)
    await db.commit()

    return RedirectResponse(url=f"/subjects/{task.subject_id}", status_code=303)
