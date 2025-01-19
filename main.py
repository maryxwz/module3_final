from fastapi import FastAPI, Depends, HTTPException
from models import Base
from database import engine
from routes import subjects


app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(subjects.router)