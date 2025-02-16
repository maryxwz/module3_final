from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import select, text
import models, schemas, security
from database import get_db
from security import get_current_user, get_current_user_optional, get_current_user_for_id
import uuid
from typing import List
from .chats import create_chat
import logging

from routes.notifications import send_notification

router = APIRouter(prefix="/subjects", tags=["subjects"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

users_ids = []
async def get_all_users_id(db: AsyncSession = Depends(get_db)):
    async with db.stream(select(models.User.id)) as result:
        async for row in result:
            users_ids.append(row)
    return users_ids


async def get_user_courses(db: AsyncSession, user_id: int):
    teacher_result = await db.execute(
        select(models.Subject)
        .filter(models.Subject.teacher_id == user_id)
        .order_by(models.Subject.title)
    )
    teacher_courses = teacher_result.scalars().all()

    student_result = await db.execute(
        select(models.Subject)
        .join(models.Enrollment, models.Subject.id == models.Enrollment.subject_id)
        .filter(models.Enrollment.student_id == user_id)
        .order_by(models.Subject.title)
    )
    student_courses = student_result.scalars().all()

    return teacher_courses, student_courses

@router.get("/")
async def home(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_optional)
):
    if current_user:
        teacher_result = await db.execute(
            select(models.Subject)
            .filter(models.Subject.teacher_id == current_user.id)
            .order_by(models.Subject.title)
        )
        teacher_courses = teacher_result.scalars().all()

        student_result = await db.execute(
            select(models.Subject)
            .join(models.Enrollment, models.Subject.id == models.Enrollment.subject_id)
            .filter(models.Enrollment.student_id == current_user.id)
            .order_by(models.Subject.title)
        )
        student_courses = student_result.scalars().all()
    else:
        teacher_courses = []
        student_courses = []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
            "teacher_courses": teacher_courses,
            "student_courses": student_courses
        }
    )


@router.get("/create")
async def create_subject_page(request: Request, message: str = None):
    return templates.TemplateResponse("subject_create.html", {
        "request": request,
        "message": message if message else ""
    })


@router.get("/{subject_id}")
async def get_subject(
    subject_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(
        select(models.Subject)
        .options(
            selectinload(models.Subject.tasks),
            selectinload(models.Subject.teacher),
            selectinload(models.Subject.enrollments)
        )
        .filter(models.Subject.id == subject_id)
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    result = await db.execute(
        select(models.Task)
        .filter(models.Task.subject_id == subject_id)
        .order_by(models.Task.id.desc())
    )
    tasks = result.scalars().all()
    
    result = await db.execute(
        select(models.Chat)
        .filter(models.Chat.subject_id == subject_id)
    )
    chat = result.scalar_one_or_none()
    chat_id = chat.id if chat else None
    
    teacher_courses, student_courses = await get_user_courses(db, current_user.id)
    
    return templates.TemplateResponse(
        "subject_detail.html",
        {
            "request": request,
            "subject": subject,
            "tasks": tasks,
            "user": current_user,
            "chat_id": chat_id,
            "teacher_courses": teacher_courses,
            "student_courses": student_courses,
            "current_subject": subject
        }
    )
  

@router.post("/create")
async def create_subject(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    print(f"Creating course with title: {title}")

    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_subject = models.Subject(
        title=title,
        description=description,
        teacher_id=user.id,
        access_code=str(uuid.uuid4())[:8]
    )
    db.add(db_subject)
    await db.commit()
    await db.refresh(db_subject)
    print(f"Created course with id: {db_subject.id}")

    # Створення чату
    default_chat = models.Chat(
        is_group=True,
        name=f"{db_subject.title} Chat",
        subject_id=db_subject.id  
    )
    db.add(default_chat)
    await db.commit()
    await db.refresh(default_chat)
    print(f"Created default chat with id: {default_chat.id} for course id: {db_subject.id}")

    chat_participant = models.ChatParticipant(chat_id=default_chat.id, user_id=user.id)
    db.add(chat_participant)
    await db.commit()
    print(f"Added user {user.id} as a participant of chat {default_chat.id}")

    result = await db.execute(select(models.User))
    all_users = result.scalars().all()

    user_ids = [u.id for u in all_users]

    for user_id in user_ids:
        await send_notification(user_id=str(user_id), from_user=str(user.id),
                                message=f'Created a new course: {db_subject.title}')

    redirect_url = f"/subjects/create?message=Subject successfully created!"
    return RedirectResponse(url=redirect_url, status_code=303)




@router.get("/{subject_id}/participants")
async def get_subject_participants(
    subject_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user_for_id)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    enrollment_query = await db.execute(
        select(models.Enrollment)
        .filter_by(student_id=current_user.id, subject_id=subject_id)
    )
    enrollment = enrollment_query.scalar_one_or_none()

    teacher_query = await db.execute(
        select(models.Subject)
        .filter_by(teacher_id=current_user.id, id=subject_id)
    )
    teacher = teacher_query.scalar_one_or_none()

    if not enrollment and not teacher:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(models.Subject)
        .options(
            joinedload(models.Subject.teacher),
            joinedload(models.Subject.enrollments).joinedload(models.Enrollment.student)
        )
        .filter_by(id=subject_id)
    )
    subject_data = result.scalars().first()
    
    if not subject_data:
        raise HTTPException(status_code=404, detail="Subject not found")

    chat_query = await db.execute(select(models.Chat).filter_by(subject_id=subject_id))
    chat = chat_query.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    participants = {
        "teacher": {
            "id": subject_data.teacher.id,
            "username": subject_data.teacher.username,
            "email": subject_data.teacher.email
        },
        "students": [
            {
                "id": enrollment.student.id,
                "username": enrollment.student.username,
                "email": enrollment.student.email
            }
            for enrollment in subject_data.enrollments  
        ],
    }

    return templates.TemplateResponse(
        "participants.html",
        {"request": request, "subject": subject_data, "participants": participants, "user": current_user, "chat_id": chat.id}
    )



@router.get("/subjects/{subject_id}/statistics")
async def get_subject_statistics(
    subject_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(
        select(models.Grade)
        .join(models.TaskUpload)
        .join(models.Task)
        .options(
            selectinload(models.Grade.task_upload)
            .selectinload(models.TaskUpload.task)
        )
        .where(
            models.Task.subject_id == subject_id,
            models.TaskUpload.student_id == current_user.id
        )
    )
    grades = result.scalars().all()
    
    avg_grade = sum(grade.grade for grade in grades) / len(grades) if grades else 0

    subject = await db.execute(select(models.Subject).filter(models.Subject.id == subject_id))
    subject = subject.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    return templates.TemplateResponse(
        "statistic.html",
        {
            "request": request,
            "grades": grades,
            "avg_grade": round(avg_grade, 2),
            "subject_title": subject.title,
            "user": current_user
        }
    )


@router.put("/{subject_id}/update-access-code")
async def update_access_code(
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
        raise HTTPException(status_code=403, detail="Only the teacher can update access code")
    
    new_access_code = str(uuid.uuid4())[:8]
    subject.access_code = new_access_code
    await db.commit()
    
    return {"new_access_code": new_access_code}


@router.put("/{subject_id}/disable-access-code")
async def disable_access_code(
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
        raise HTTPException(status_code=403, detail="Only the teacher can disable access code")
    
    subject.access_code = None
    await db.commit()
    
    return {"message": "Access code disabled"}

@router.post("/{subject_id}/update")
async def update_course(
    subject_id: int,
    title: str = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(
        select(models.Subject).filter(models.Subject.id == subject_id)
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    if subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the teacher can update the course")
    
    subject.title = title
    subject.description = description
    
    await db.commit()
    
    return RedirectResponse(
        url=f"/subjects/{subject_id}", 
        status_code=303
    )

@router.post("/{subject_id}/delete")
async def delete_course(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    result = await db.execute(
        select(models.Subject).filter(models.Subject.id == subject_id)
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    if subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the teacher can delete the course")
    
    await db.execute(
        text("DELETE FROM tasks WHERE subject_id = :subject_id"),
        {"subject_id": subject_id}
    )
    
    chat_result = await db.execute(
        select(models.Chat).filter(models.Chat.subject_id == subject_id)
    )
    chat = chat_result.scalar_one_or_none()
    if chat:
        await db.execute(
            text("DELETE FROM messages WHERE chat_id = :chat_id"),
            {"chat_id": chat.id}
        )
        await db.execute(
            text("DELETE FROM chat_participants WHERE chat_id = :chat_id"),
            {"chat_id": chat.id}
        )
        await db.execute(
            text("DELETE FROM chats WHERE subject_id = :subject_id"),
            {"subject_id": subject_id}
        )
    
    await db.execute(
        text("DELETE FROM enrollments WHERE subject_id = :subject_id"),
        {"subject_id": subject_id}
    )
    
    await db.execute(
        text("DELETE FROM subjects WHERE id = :subject_id"),
        {"subject_id": subject_id}
    )
    
    await db.commit()
    
    return RedirectResponse(
        url="/", 
        status_code=303
    )
