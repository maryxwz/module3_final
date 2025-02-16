from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db, recreate_database
from calendar_page import *
from routes import auth, subjects, tasks, enrollments, notifications, chats, grades_statistic, users, calendar_page
from pathlib import Path
from database import init_db

import asyncio


app = FastAPI(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/avatars", StaticFiles(directory="avatars"), name="avatars")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(tasks.router)
app.include_router(enrollments.router)
app.include_router(notifications.router)
app.include_router(chats.router)
app.include_router(calendar_page.router)
app.include_router(grades_statistic.router)


if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", reload=True)

