from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
#место для импорта класса
from typing import Dict

app = FastAPI()


grades_db = {}

#перенести в классы, ну тип где все модели
class Grade(BaseModel):
    student_name: str
    task: str
    grade: int

@app.post("/grades")
def save_grade(grade: Grade):
    if grade.grade < 1 or grade.grade > 12:
        raise HTTPException(status_code=400, detail="Оценка должна быть в диапазоне от 1 до 12")
    if grade.student_name not in grades_db:
        grades_db[grade.student_name] = []
    grades_db[grade.student_name].append(grade.grade)
    return {"message": "Оценка сохранена", "grades": grades_db[grade.student_name]}

@app.get("/statistics")
def get_statistics():
    if not grades_db:
        raise HTTPException(status_code=404, detail="Нет данных об оценках")
    statistics = {
        student: round(sum(grades) / len(grades), 2)
        for student, grades in grades_db.items()
    }
    return statistics
