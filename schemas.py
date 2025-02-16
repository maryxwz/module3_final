from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    email: str
    username: str

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool


class SubjectBase(BaseModel):
    title: str
    description: str


class SubjectCreate(SubjectBase):
    pass


class SubjectOut(SubjectBase):
    id: int
    teacher_id: int
    access_code: str

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: str
    deadline: datetime

    class Config:
        from_attributes = True


class TaskCreate(TaskBase):
    subject_id: int


class TaskOut(TaskBase):
    id: int
    subject_id: int

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    subject_id: int


class EnrollmentOut(EnrollmentCreate):
    id: int
    student_id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
