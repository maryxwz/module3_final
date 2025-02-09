from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from security import get_current_user_for_id
import models
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/subjects/{subject_id}/statistics", name="get_statistics")
async def get_statistics(
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

@router.post("/grade_upload/{upload_id}")
async def save_grade(
    upload_id: int,
    grade: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_for_id)
):
    # Изменяем запрос, чтобы загрузить все необходимые связанные данные
    result = await db.execute(
        select(models.TaskUpload)
        .options(
            selectinload(models.TaskUpload.task)
            .selectinload(models.Task.subject)
        )
        .where(models.TaskUpload.id == upload_id)
    )
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Проверяем, является ли текущий пользователь учителем этого предмета
    if upload.task.subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only teacher can grade uploads")

    if grade < 0 or grade > upload.task.max_grade:
        raise HTTPException(
            status_code=400, 
            detail=f"Grade must be between 0 and {upload.task.max_grade}"
        )

    # Проверяем существование оценки
    result = await db.execute(
        select(models.Grade).where(models.Grade.task_upload_id == upload_id)
    )
    existing_grade = result.scalar_one_or_none()

    if existing_grade:
        # Обновляем существующую оценку
        existing_grade.grade = grade
    else:
        # Создаем новую оценку
        new_grade = models.Grade(
            task_upload_id=upload_id,
            grade=grade
        )
        db.add(new_grade)

    await db.commit()

    return RedirectResponse(url=f"/tasks/task/{upload.task_id}", status_code=303) 