from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from database import get_db
from typing import List
from subjects import get_all_users_id, users_ids
import schemas, models
from sqlalchemy.orm import Session
from routes.notifications import send_notification
from sqlalchemy.ext.asyncio import AsyncSession
from security import get_current_user, get_current_user_optional, get_current_user_for_id
from sqlalchemy import select


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
async def create_comment(comment: schemas.CommentCreate, db: AsyncSession = Depends(get_db),
                         current_user: str = Depends(get_current_user_for_id)):
    db_comment = models.Comment(content=comment.content, task_id=comment.task_id)
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)

    result = await db.execute(select(models.User))
    all_users = result.scalars().all()

    user_ids = [u.id for u in all_users]

    for user_id in user_ids:
        await send_notification(
            user_id=str(user_id),
            from_user=str(current_user.id),
            message=f'New comment added to task ID {db_comment.task_id}: {db_comment.content}'
        )
    redirect_url = f"/tasks/{db_comment.task_id}?message=Comment successfully created!"
    return RedirectResponse(url=redirect_url, status_code=303)


