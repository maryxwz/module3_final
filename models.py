from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, ARRAY, CheckConstraint
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
    meet_link = Column(String, unique=True)
    
    teacher = relationship("User", back_populates="subjects_teaching")
    enrollments = relationship("Enrollment", back_populates="subject")
    tasks = relationship("Task", back_populates="subject")
    chat = relationship("Chat", back_populates="subject", uselist=False)


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    deadline = Column(DateTime)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    max_grade = Column(Integer, default=12)
    
    subject = relationship("Subject", back_populates="tasks")
    comments = relationship("Comment", back_populates="task")
    uploads = relationship("TaskUpload", back_populates="task")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    task_id = Column(Integer, ForeignKey("tasks.id"))
    task_upload_id = Column(Integer, ForeignKey("task_uploads.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Тип комментария: 'public', 'private', 'feedback'
    comment_type = Column(String, nullable=False)
    
    # Отношения
    task = relationship("Task", back_populates="comments")
    task_upload = relationship("TaskUpload", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])
    recipient = relationship("User", foreign_keys=[recipient_id])


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
    name = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    
    subject = relationship("Subject", back_populates="chat", uselist=False)
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


class TaskUpload(Base):
    __tablename__ = "task_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=True)
    files = Column(ARRAY(String), default=list) 
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="uploaded")  
    
    task = relationship("Task", back_populates="uploads")
    student = relationship("User")
    grade = relationship("Grade", back_populates="task_upload", uselist=False)
    comments = relationship("Comment", back_populates="task_upload")


class Grade(Base):
    __tablename__ = "grades"
    
    id = Column(Integer, primary_key=True, index=True)
    task_upload_id = Column(Integer, ForeignKey("task_uploads.id"))
    grade = Column(Integer, CheckConstraint('grade >= 0'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    task_upload = relationship("TaskUpload", back_populates="grade")
