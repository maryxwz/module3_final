from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from typing import List
import schemas, models
from sqlalchemy.orm import Session


router = APIRouter(prefix="subjects/task/{task_id}/comments")

@router.get("/", response_model=List[schemas.CommentOut])
async def read_comments(db: Session = Depends(get_db)):
    comments = db.query(models.Comment).all()
    return comments

@router.get("/{comment_id}", response_model=schemas.CommentOut)
async def get_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

@router.post("/", response_model=schemas.CommentOut)
async def create_comment(comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    db_comment = models.Comment(content=comment.content, task_id=comment.task_id)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

