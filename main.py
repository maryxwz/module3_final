from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db, recreate_database
from routes import auth, subjects, tasks, enrollments, notifications

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
#comment1

@app.on_event("startup")
async def startup():
    await init_db()

app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(tasks.router)
app.include_router(enrollments.router)
app.include_router(notifications.router)
