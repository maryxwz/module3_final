from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
import sqlite3
import uuid
import hashlib
import aiosmtplib
from email.message import EmailMessage
import ssl

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
DATABASE = 'test.db'


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str


class CourseCreate(BaseModel):
    course_name: str


def get_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    return conn, c


def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.post("/register/")
async def register_user(user: UserCreate):
    conn, c = get_db()
    c.execute("SELECT * FROM users WHERE username = ? OR email = ?", (user.username, user.email))
    if c.fetchone():
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    hashed_password = get_password_hash(user.password)
    activation_code = str(uuid.uuid4())
    c.execute("INSERT INTO users (username, email, password, role, is_active) VALUES (?, ?, ?, ?, ?)",
              (user.username, user.email, hashed_password, user.role, False))
    conn.commit()
    conn.close()

    message = f"Please confirm your email by clicking on this link: http://127.0.0.1:8000/confirm/{activation_code}"
    try:
        await send_email(user.email, "Email Confirmation", message)
    except aiosmtplib.errors.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="Incorrect email or password for email sending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    return {"message": "Registration successful! Please confirm your email."}


async def send_email(to: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = "your-email@gmail.com"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    await aiosmtplib.send(message, hostname="smtp.gmail.com", port=587, username="your-email@gmail.com",
                          password="your-app-password", start_tls=True, tls_context=context)


@app.get("/confirm/{activation_code}")
async def confirm_email(activation_code: str):
    conn, c = get_db()
    c.execute("UPDATE users SET is_active = True WHERE id = ?", (activation_code,))
    if c.rowcount == 0:
        raise HTTPException(status_code=404, detail="Activation code not found")
    conn.commit()
    conn.close()
    return {"message": "Email confirmed successfully!"}


@app.post("/create-course/")
async def create_course(course: CourseCreate, token: str = Depends(oauth2_scheme)):
    conn, c = get_db()
    access_code = str(uuid.uuid4())
    c.execute("INSERT INTO courses (course_name, access_code) VALUES (?, ?)", (course.course_name, access_code))
    conn.commit()
    conn.close()
    return {"course_name": course.course_name, "access_code": access_code}


@app.post("/enroll/")
async def enroll(course_id: int, access_code: str, token: str = Depends(oauth2_scheme)):
    conn, c = get_db()
    c.execute("SELECT * FROM courses WHERE id = ? AND access_code = ?", (course_id, access_code))
    course = c.fetchone()
    if not course:
        raise HTTPException(status_code=400, detail="Invalid course ID or access code")

    user_id = get_user_id_from_token(token)

    c.execute("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", (user_id, course_id))
    conn.commit()
    conn.close()
    return {"message": "Successfully enrolled in the course"}


def get_user_id_from_token(token: str) -> int:
    return 1


@app.post("/token/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn, c = get_db()
    c.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
    user = c.fetchone()
    conn.close()

    if not user or not hashlib.sha256(form_data.password.encode()).hexdigest() == user[3]:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": user[0], "token_type": "bearer"}
