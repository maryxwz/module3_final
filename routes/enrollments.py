from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import models
from database import get_db
from security import get_current_user
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