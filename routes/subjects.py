from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select
import models, schemas
from database import get_db
from security import get_current_user, get_current_user_optional
import uuid

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
    
    return templates.TemplateResponse(
        "subject_detail.html",
        {
            "request": request,
            "user": user,
            "subject": subject,
            "tasks": tasks
        }
    )


@router.post("/create")
async def create_subject(
    title: str = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    print(f"Creating course with title: {title}") 
    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()

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
    return RedirectResponse(url="/", status_code=303) 


@router.get("/{subject_id}/participants")
async def get_subject_participants(
    subject_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    # current_user: str = Depends(get_current_user)
):
    # if not current_user:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    check_user_in_course = await db.execute(
        select(models.Enrollment).filter(
            # models.Enrollment.student.has(email=current_user), 
            models.Enrollment.subject_id == subject_id
        )
    )
    if not check_user_in_course.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    subject = await db.execute(
        select(models.Subject)
        .options(
            joinedload(models.Subject.teacher),
            joinedload(models.Subject.enrollments).joinedload(models.Enrollment.student)
        )
        .filter(models.Subject.id == subject_id)
    )

    subject_data = subject.scalar_one_or_none()
    if not subject_data:
        raise HTTPException(status_code=404, detail="Subject not found")

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
        ]
    }

    return participants

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
