from pydantic import BaseModel


#CREATE SCHEMAS
class SubjectCreate(BaseModel):
    title: str
    description: str
    subject_type: str


# class TaskCreate(BaseModel):
#     title: str
#     description: str


class CommentCreate(BaseModel):
    content: str


#OUT SCHEMAS
class SubjectOut(SubjectCreate):
    id: int


# class TaskOut(TaskCreate):
#     id: int
#     comments: list[CommentCreate] = []

class CommentOut(CommentCreate):
    id: int
