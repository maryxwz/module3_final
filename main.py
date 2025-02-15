from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db, recreate_database
from routes import auth, subjects, tasks, enrollments, notifications, chats, calendar_page
from calendar_page import *


app = FastAPI(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(tasks.router)
app.include_router(enrollments.router)
app.include_router(notifications.router)
app.include_router(chats.router)
app.include_router(calendar_page.router)


if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", reload=True)