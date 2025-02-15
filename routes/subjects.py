from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import select
import models, schemas, security
from database import get_db
from security import get_current_user, get_current_user_optional, get_current_user_for_id
import uuid
from typing import List
from .chats import create_chat

router = APIRouter(prefix="/subjects", tags=["subjects"])
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user_optional)
):
    user = None
    subjects = []
    if current_user:
        result = await db.execute(select(models.User).filter(models.User.email == current_user))
        user = result.scalar_one_or_none()
        
        result = await db.execute(
            select(models.Subject)
            .where(
                (models.Subject.teacher_id == user.id) |
                models.Subject.id.in_(
                    select(models.Enrollment.subject_id)
                    .where(models.Enrollment.student_id == user.id)
                )
            )
        )
        subjects = result.scalars().all()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "subjects": subjects
        }
    )


@router.get("/create")
async def create_subject_page(request: Request):
    return templates.TemplateResponse("subject_create.html", {"request": request})


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

    # Получаем отсортированные задания отдельно
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
    
    return templates.TemplateResponse(
        "subject_detail.html",
        {
            "request": request,
            "subject": subject,
            "tasks": tasks,
            "user": current_user,
            "chat_id": chat_id
        }
    )
  

@router.post("/create")
async def create_subject(
    background_tasks: BackgroundTasks,  
    title: str = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
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

    return RedirectResponse(url="/", status_code=303)




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
    # Получаем все оценки студента по этому предмету
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

    # Вычисляем среднюю оценку
    avg_grade = sum(grade.grade for grade in grades) / len(grades) if grades else 0

    # Get subject data
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
