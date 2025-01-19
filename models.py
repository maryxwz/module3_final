from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    subject_type = Column(String)

    # tasks = relationship("Task", back_populates="subject")


# class Task(Base):
#     __tablename__ = "tasks"

#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String, index=True)
#     description = Column(Text)
#     subject_id = Column(Integer, ForeignKey("subjects.id"))

#     subject = relationship("Subject", back_populates="tasks")
#     comments = relationship("Comment", back_populates="comments")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    task_id = Column(Integer, ForeignKey("tasks.id"))

#     task = relationship("Task", back_populates="comments")