from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
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
    return RedirectResponse(url="/", status_code=303)

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
        raise HTTPException(status_code=403, detail="Only the teacher can update the access code")

    new_code = str(uuid.uuid4())[:8]
    subject.access_code = new_code
    await db.commit()
    await db.refresh(subject)

    return {"message": "Access code updated successfully", "new_access_code": new_code}


@router.post("/join/{access_code}")
async def join_subject(
        access_code: str,
        db: AsyncSession = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()

    result = await db.execute(select(models.Subject).filter(models.Subject.access_code == access_code))
    subject = result.scalar_one_or_none()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    result = await db.execute(
        select(models.Enrollment).filter(
            models.Enrollment.student_id == user.id,
            models.Enrollment.subject_id == subject.id
        )
    )
    enrollment = result.scalar_one_or_none()

    if enrollment:
        return {"message": "You are already enrolled in this course"}

    db_enrollment = models.Enrollment(student_id=user.id, subject_id=subject.id)
    db.add(db_enrollment)
    await db.commit()

    return {"message": f"Successfully joined the course: {subject.title}"}
