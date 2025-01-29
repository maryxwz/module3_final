from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    
    subjects_teaching = relationship("Subject", back_populates="teacher")
    enrollments = relationship("Enrollment", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    access_code = Column(String, unique=True)
    
    teacher = relationship("User", back_populates="subjects_teaching")
    enrollments = relationship("Enrollment", back_populates="subject")
    tasks = relationship("Task", back_populates="subject")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    deadline = Column(DateTime)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    
    subject = relationship("Subject", back_populates="tasks")
    comments = relationship("Comment", back_populates="task")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    task = relationship("Task", back_populates="comments")
    user = relationship("User")


class Enrollment(Base):
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("User", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    is_group = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="chat")
    participants = relationship("ChatParticipant", back_populates="chat")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    chat = relationship("Chat", back_populates="participants")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")