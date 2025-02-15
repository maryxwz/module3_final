from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import models, schemas, security
from database import get_db
from security import get_current_user_optional
from routes.notifications import send_notification

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def authenticate_user(email: str, password: str, db: AsyncSession):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    user = result.scalar_one_or_none()
    if not user or not security.verify_password(password, user.hashed_password):
        return None
    return user


@router.get("/")
async def index(
    request: Request, 
    db: AsyncSession = Depends(get_db), 
    current_user: str = Depends(get_current_user_optional)
):
    user = None
    subjects = []
    
    if current_user:
        result = await db.execute(select(models.User).filter(models.User.email == current_user))
        user = result.scalar_one_or_none()
        
        if user: 
            result = await db.execute(
                select(models.Subject).where(
                    (models.Subject.teacher_id == user.id) |
                    models.Subject.id.in_(
                        select(models.Enrollment.subject_id)
                        .where(models.Enrollment.student_id == user.id)
                    )
                )
            )
            subjects = result.scalars().all()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "subjects": subjects
        }
    )


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register(
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = security.get_password_hash(password)
    db_user = models.User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    await db.commit()
    result = await db.execute(select(models.User).filter(models.User == True))
    all = result.scalars().all()
    for admin in all:
        await send_notification(
            user_id=str(admin.id),
            from_user=str(db_user.id),
            message=f'New user registered: {db_user.username} ({db_user.email})'
        )

    return RedirectResponse(url="/login?message=Registration successful! Please log in.", status_code=303)


@router.post("/login")
async def login(
        email: str = Form(...),
        password: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(email, password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = security.create_access_token(data={"sub": email})
    response = RedirectResponse(url="/?message=Login successful!", status_code=303)

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,
        expires=1800,
        samesite="lax"
    )

    result = await db.execute(select(models.User).filter(models.User == True))
    all_admins = result.scalars().all()

    for admin in all_admins:
        await send_notification(
            user_id=str(admin.id),
            from_user=str(user.id),
            message=f'User {user.username} has logged in.'
        )

    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response 