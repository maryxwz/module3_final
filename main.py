from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from routes import auth, courses, tasks, enrollments, notifications
from database import engine, get_db
from security import get_current_user
import models

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(enrollments.router, tags=["enrollments"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/index")
async def index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    query = select(models.User).where(models.User.email == current_user)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user
        }
    )
