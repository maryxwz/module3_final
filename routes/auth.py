from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import models, schemas, security
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def authenticate_user(email: str, password: str, db: AsyncSession):
    query = select(models.User).where(models.User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(password, user.hashed_password):
        return None
    return user


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    query = select(models.User).where(models.User.email == email)
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = security.get_password_hash(password)
    db_user = models.User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        role=role
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return RedirectResponse(url="/auth/login", status_code=303)


@router.post("/token")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    redirect = RedirectResponse(url="/index", status_code=303)

    redirect.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,
        expires=1800,
        samesite="lax"
    )
    
    return redirect 