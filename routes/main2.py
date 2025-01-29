from fastapi import FastAPI, UploadFile, File, Form, APIRouter
from fastapi.responses import JSONResponse
from typing import List, Optional
import shutil
import os
import uvicorn


router = APIRouter()

UPLOAD_DIRECTORY = "./uploaded_files"

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


class Task:
    def __init__(self, task_id, files, text):
        self.task_id = task_id
        self.files = files
        self.text = text
        self.status = "Здано"
        self.is_graded = False
        self.grade = None  # Новое поле для оценки


tasks_db = {}


@router.post("/upload")
async def upload_files(
        task_id: int = Form(...),
        files: List[UploadFile] = File(...),
        text: str = Form(None)
):
    for file in files:
        file_location = f"{UPLOAD_DIRECTORY}/{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

    tasks_db[task_id] = Task(task_id, [file.filename for file in files], text)

    response_data = {
        "task_id": task_id,
        "file_names": tasks_db[task_id].files,
        "text": tasks_db[task_id].text,
        "status": tasks_db[task_id].status
    }
    return JSONResponse(content=response_data)


@router.put("/update_task/{task_id}")
async def update_task(task_id: int, files: List[UploadFile] = File(None), text: str = Form(None)):
    if task_id not in tasks_db:
        return JSONResponse(content={"error": "Task not found"}, status_code=404)

    task = tasks_db[task_id]
    if task.is_graded:
        return JSONResponse(content={"error": "Task has already been graded and cannot be resubmitted"}, status_code=403)

    if files:
        for file in files:
            file_location = f"{UPLOAD_DIRECTORY}/{file.filename}"
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
        task.files = [file.filename for file in files]

    if text:
        task.text = text

    task.status = "Оновлено"
    response_data = {
        "task_id": task_id,
        "file_names": task.files,
        "text": task.text,
        "status": task.status
    }
    return JSONResponse(content=response_data)


@router.put("/grade_task/{task_id}")
async def grade_task(task_id: int, grade: int = Form(...)):
    if task_id not in tasks_db:
        return JSONResponse(content={"error": "Task not found"}, status_code=404)

    if grade < 1 or grade > 12:
        return JSONResponse(content={"error": "Grade must be between 1 and 12"}, status_code=400)

    task = tasks_db[task_id]
    task.is_graded = True
    task.status = "Оценено"
    task.grade = grade

    response_data = {
        "task_id": task_id,
        "status": task.status,
        "is_graded": task.is_graded,
        "grade": task.grade
    }
    return JSONResponse(content=response_data)



