from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db, recreate_database
from routes import auth, subjects, tasks, enrollments, notifications, chats
<<<<<<< HEAD

app = FastAPI()
=======
from pathlib import Path


app = FastAPI(debug=True)
>>>>>>> c519b27fae364bba17c7d6c6c4bd7316af27f5d2
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


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

<<<<<<< HEAD
=======

if __name__ == "__main__":
    uvicorn.run(f"{__name__}:app", reload=True)
>>>>>>> c519b27fae364bba17c7d6c6c4bd7316af27f5d2
