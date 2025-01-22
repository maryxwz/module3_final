from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: str


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    title: str
    description: str


class CourseCreate(CourseBase):
    pass


class CourseOut(CourseBase):
    id: int
    access_code: str
    teacher_id: int

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: str
    deadline: datetime


class TaskCreate(TaskBase):
    course_id: int


class TaskOut(TaskBase):
    id: int
    course_id: int

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    task_id: int


class CommentOut(CommentBase):
    id: int
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
