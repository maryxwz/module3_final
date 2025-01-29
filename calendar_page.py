# from fastapi import FastAPI, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# from calendar import HTMLCalendar
# from datetime import datetime
#
# app = FastAPI()
# templates = Jinja2Templates(directory="templates")
#
#
# @app.get("/", response_class=HTMLResponse)
# async def calendar_view(request: Request, year: int = None, month: int = None):
#     # Поточний рік і місяць, якщо параметри не задані
#     now = datetime.now()
#     year = year or now.year
#     month = month or now.month
#
#     # Корекція місяців
#     if month < 1:
#         year -= 1
#         month = 12
#     elif month > 12:
#         year += 1
#         month = 1
#
#     # Генерація HTML-календаря
#     cal = HTMLCalendar().formatmonth(year, month)
#
#     return templates.TemplateResponse("calendar.html", {
#         "request": request,
#         "calendar": cal,
#         "year": year,
#         "month": month
#     })
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from calendar import HTMLCalendar
from datetime import datetime
import sqlite3

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def create_db():
    connection = sqlite3.connect('calendar.db')
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        event TEXT NOT NULL
    )
    ''')

    connection.commit()
    connection.close()

create_db()

def add_event(date: str, event: str):
    connection = sqlite3.connect('calendar.db')
    cursor = connection.cursor()

    cursor.execute('''
    INSERT INTO events (date, event)
    VALUES (?, ?)
    ''', (date, event))

    connection.commit()
    connection.close()


def get_events(year: int, month: int):
    connection = sqlite3.connect('calendar.db')
    cursor = connection.cursor()

    month_padded = f"{month:02d}"
    prefix = f"{year}-{month_padded}"

    cursor.execute('''
    SELECT date, event FROM events
    WHERE date LIKE ?
    ORDER BY date
    ''', (prefix + '%',))

    events = {}
    for row in cursor.fetchall():
        date, event = row
        if date not in events:
            events[date] = []
        events[date].append(event)

    connection.close()
    return events


import calendar


def generate_calendar_html(year: int, month: int) -> str:
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdays2calendar(year, month)

    calendar_html = "<tr>"

    week_days = ["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    for day in week_days:
        calendar_html += f"<th>{day}</th>"
    calendar_html += "</tr>"

    # Додаємо дні місяця
    for week in month_days:
        calendar_html += "<tr>"
        for day, _ in week:
            if day == 0:
                calendar_html += "<td></td>"
            else:
                calendar_html += f"<td>{day}</td>"
        calendar_html += "</tr>"

    return calendar_html


@app.get("/")
async def calendar_view(request: Request, year: int = 2025, month: int = 1):
    events = get_events(year, month)
    calendar_html = generate_calendar_html(year, month)
    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "year": year,
        "month": month,
        "calendar": calendar_html,
        "events": events
    })
