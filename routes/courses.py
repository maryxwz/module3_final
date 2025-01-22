from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import models, schemas
from database import get_db
from security import get_current_user
import uuid
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

router = APIRouter(prefix="/courses", tags=["courses"])
templates = Jinja2Templates(directory="templates")


@router.post("/", response_model=schemas.CourseOut)
async def create_course(
    course: schemas.CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = await db.query(models.User).filter(models.User.email == current_user).first()
    if user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create courses"
        )

    access_code = str(uuid.uuid4())[:8]
    db_course = models.Course(
        title=course.title,
        description=course.description,
        access_code=access_code,
        teacher_id=user.id
    )
    db.add(db_course)
    await db.commit()
    await db.refresh(db_course)
    return db_course


@router.get("/", response_model=List[schemas.CourseOut])
async def get_courses(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    user = await db.query(models.User).filter(models.User.email == current_user).first()
    if user.role == "teacher":
        courses = await db.query(models.Course).filter(models.Course.teacher_id == user.id).all()
    else:
        enrollments = await db.query(models.Enrollment).filter(
            models.Enrollment.student_id == user.id
        ).all()
        course_ids = [enrollment.course_id for enrollment in enrollments]
        courses = await db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    return courses


@router.get("/{course_id}", response_model=schemas.CourseOut)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    course = await db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.get("/")
async def index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    query = select(models.User).where(models.User.email == current_user)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user.role == "teacher":
        query = select(models.Course).where(models.Course.teacher_id == user.id)
    else:
        query = select(models.Course).join(
            models.Enrollment,
            models.Course.id == models.Enrollment.course_id
        ).where(models.Enrollment.student_id == user.id)
    
    result = await db.execute(query)
    courses = result.scalars().all()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "courses": courses
        }
    ) 