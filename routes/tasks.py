from datetime import datetime
from typing import List
import os
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, HTTPException, Form, Request, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
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

UPLOAD_DIR = Path("uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


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
        select(models.Task)
        .options(selectinload(models.Task.subject))
        .where(models.Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the teacher can edit tasks")

    return templates.TemplateResponse("edit_task.html", {"request": request, "task": task})


@router.post("/edit/{task_id}")
async def update_task(
    task_id: int,
    title: str = Form(...),
    description: str = Form(...),
    deadline: datetime = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    try:
        stmt = (
            select(models.Task)
            .options(selectinload(models.Task.subject))
            .where(models.Task.id == task_id)
        )
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.subject.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to edit this task")

        task.title = title
        task.description = description
        task.deadline = deadline

        db.add(task)
        await db.commit()

        return RedirectResponse(url=f"/subjects/{task.subject_id}", status_code=303)

    except Exception as e:
        await db.rollback()
        print(f"Error updating task: {str(e)}")
        return RedirectResponse(
            url=f"/tasks/edit/{task_id}",
            status_code=303
        )


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


@router.get("/task/{task_id}")
async def task_detail(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    stmt = (
        select(models.Task)
        .options(
            selectinload(models.Task.subject),
            selectinload(models.Task.uploads).selectinload(models.TaskUpload.student)
        )
        .where(models.Task.id == task_id)
    )
    
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.subject.teacher_id != current_user.id:
        enrollment_stmt = select(models.Enrollment).where(
            models.Enrollment.subject_id == task.subject_id,
            models.Enrollment.student_id == current_user.id
        )
        result = await db.execute(enrollment_stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    upload = None
    if current_user.id != task.subject.teacher_id:
        upload_stmt = select(models.TaskUpload).where(
            models.TaskUpload.task_id == task_id,
            models.TaskUpload.student_id == current_user.id
        )
        result = await db.execute(upload_stmt)
        upload = result.scalar_one_or_none()

    status = None
    if upload:
        if upload.uploaded_at <= task.deadline:
            status = "uploaded"
        else:
            status = "late"
    elif datetime.utcnow() > task.deadline:
        status = "overdue"
    else:
        status = "assigned"

    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "task": task,
            "user": current_user,
            "upload": upload,
            "status": status
        }
    )


@router.post("/task/{task_id}/upload")
async def upload_task(
    task_id: int,
    content: str = Form(None),
    files: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = await db.execute(
        select(models.TaskUpload)
        .filter(
            models.TaskUpload.task_id == task_id,
            models.TaskUpload.student_id == current_user.id
        )
    )
    upload = result.scalar_one_or_none()
    
    saved_files = []
    if files:
        for file in files:
            file_path = f"{task_id}_{current_user.id}_{file.filename}"
            with open(UPLOAD_DIR / file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file_path)  
    
    status = "uploaded"
    if task.deadline < datetime.utcnow():
        status = "late"
    
    if upload:
        upload.content = content
        upload.files = saved_files if files else upload.files
        upload.updated_at = datetime.utcnow()
        upload.status = status
    else:
        upload = models.TaskUpload(
            task_id=task_id,
            student_id=current_user.id,
            content=content,
            files=saved_files,
            status=status
        )
        db.add(upload)
    
    await db.commit()
    return RedirectResponse(url=f"/tasks/task/{task_id}", status_code=303)


@router.get("/uploads/{file_path:path}")
async def get_upload(file_path: str):
    return FileResponse(f"{UPLOAD_DIR}/{file_path}")