from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import models
from database import get_db
from routes.tasks import templates
from security import get_current_user, get_current_user_for_id
from fastapi.responses import RedirectResponse
from typing import List
import schemas


router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("/join")
async def enroll_in_subject(
        access_code: str = Form(...),
        db: AsyncSession = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
    if result.scalar_one_or_none():
        return RedirectResponse(url="/", status_code=303)

    db_enrollment = models.Enrollment(student_id=user.id, subject_id=subject.id)
    db.add(db_enrollment)

    result = await db.execute(select(models.Chat).filter(models.Chat.subject_id == subject.id))
    chat = result.scalar_one_or_none()

    if chat:
        result = await db.execute(
            select(models.ChatParticipant).filter(
                models.ChatParticipant.chat_id == chat.id,
                models.ChatParticipant.user_id == user.id
            )
        )
        if not result.scalar_one_or_none():
            chat_participant = models.ChatParticipant(chat_id=chat.id, user_id=user.id)
            db.add(chat_participant)

    await db.commit()

    return RedirectResponse(url="/", status_code=303)



@router.get("/my-subjects", response_model=List[schemas.SubjectOut])
async def get_enrolled_subjects(
        db: AsyncSession = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    result = await db.execute(select(models.User).filter(models.User.email == current_user))
    user = result.scalar_one_or_none()

    result = await db.execute(
        select(models.Subject)
        .join(models.Enrollment)
        .filter(models.Enrollment.student_id == user.id)
    )
    subjects = result.scalars().all()
    return subjects


@router.get("/search_courses")
async def search_courses(request: Request, query: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Subject).filter(models.Subject.title.ilike(f"%{query}%"))
    )
    courses = result.scalars().all()

    if not courses:
        raise HTTPException(status_code=404, detail="No courses found")

    return templates.TemplateResponse("search_courses.html", {"request": request, "courses": courses, "query": query})


@router.get("/course_settings/{subject_id}", name="settings_for_course")
async def settings_for_course(
    subject_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_for_id),
):
    result = await db.execute(select(models.Subject).filter(models.Subject.id == subject_id))
    subject = result.scalars().first()

    if not subject or subject.teacher_id != current_user.id:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "settings_course.html",
        {"request": request, "subject": subject, "current_user": current_user}
    )


@router.post("/meet_link/{subject_id}")
async def save_meet_link(subject_id: int, meet_link: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Subject).filter(models.Subject.id == subject_id))
    subject = result.scalars().first()

    subject.meet_link = meet_link
    await db.commit()
    return RedirectResponse(url=f"/subjects/{subject_id}", status_code=303)
