from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import models, schemas
from database import get_db
from security import get_current_user

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("/{access_code}")
async def enroll_in_course(
    access_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = await db.query(models.User).filter(models.User.email == current_user).first()

    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can enroll in courses"
        )

    course = await db.query(models.Course).filter(models.Course.access_code == access_code).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid access code"
        )

    existing_enrollment = await db.query(models.Enrollment).filter(
        models.Enrollment.student_id == user.id,
        models.Enrollment.course_id == course.id
    ).first()
    
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already enrolled in this course"
        )

    enrollment = models.Enrollment(
        student_id=user.id,
        course_id=course.id
    )
    db.add(enrollment)
    await db.commit()
    
    return {"message": f"Successfully enrolled in course: {course.title}"}


@router.get("/my-courses", response_model=List[schemas.CourseOut])
async def get_enrolled_courses(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = await db.query(models.User).filter(models.User.email == current_user).first()
    
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only for students"
        )

    enrollments = await db.query(models.Enrollment).filter(
        models.Enrollment.student_id == user.id
    ).all()
    
    course_ids = [enrollment.course_id for enrollment in enrollments]
    courses = await db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    
    return courses 