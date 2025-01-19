from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from typing import List
import schemas, models
from sqlalchemy.orm import Session


router = APIRouter()


@router.get("/subjects/", response_model=List[schemas.SubjectOut])
async def read_subjects(db: Session = Depends(get_db)):
    subjects = db.query(models.Subject).all()
    return subjects

@router.get("/subjects/{subject_id}", response_model=schemas.SubjectOut)
async def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.post("/subjects/", response_model=schemas.SubjectOut)
async def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_subject = models.Subject(title=subject.title, description=subject.description, subject_type=subject.subject_type)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject






