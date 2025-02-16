from fastapi import FastAPI, Request, APIRouter, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import calendar
from datetime import datetime
import sqlite3

app = FastAPI()
router = APIRouter()
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
    cursor.execute("INSERT INTO events (date, event) VALUES (?, ?)", (date, event))
    connection.commit()
    connection.close()


def delete_event(date: str, event: str):
    connection = sqlite3.connect('calendar.db')
    cursor = connection.cursor()
    cursor.execute("DELETE FROM events WHERE date = ? AND event = ?", (date, event))
    connection.commit()
    connection.close()


def get_events(year: int, month: int):
    connection = sqlite3.connect('calendar.db')
    cursor = connection.cursor()
    month_padded = f"{month:02d}"
    prefix = f"{year}-{month_padded}"

    cursor.execute("SELECT date, event FROM events WHERE date LIKE ? ORDER BY date", (prefix + '%',))
    events = {}
    for row in cursor.fetchall():
        date, event = row
        if date not in events:
            events[date] = []
        events[date].append(event)

    connection.close()
    return events


def generate_calendar_html(year: int, month: int, events: dict) -> str:
    cal = calendar.Calendar(firstweekday=6)  # Початок тижня з понеділка
    month_days = cal.monthdays2calendar(year, month)

    calendar_html = "<tr>"
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    for day in week_days:
        calendar_html += f"<th>{day}</th>"
    calendar_html += "</tr>"

    for week in month_days:
        calendar_html += "<tr>"
        for day, _ in week:
            if day == 0:
                calendar_html += "<td>&nbsp;</td>"
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                event_html = "".join(f"<div class='event'>{e}</div>" for e in events.get(date_str, []))
                calendar_html += f"<td>{day}{event_html}</td>"
        calendar_html += "</tr>"

    return calendar_html


@router.get("/calendar")
async def calendar_view(
    request: Request,
    year: int = Query(default=datetime.today().year),
    month: int = Query(default=datetime.today().month)
):
    events = get_events(year, month)
    calendar_html = generate_calendar_html(year, month, events)
    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "year": year,
        "month": month,
        "calendar": calendar_html,
        "events": events
    })


@router.post("/calendar/add-event")
async def add_event_view(request: Request, event_date: str = Form(...), event_description: str = Form(...)):
    add_event(event_date, event_description)
    year, month = map(int, event_date.split("-")[:2])
    return RedirectResponse(f"/calendar?year={year}&month={month}", status_code=303)


@router.post("/calendar/delete-event")
async def delete_event_view(event_date: str = Form(...), event_description: str = Form(...)):
    delete_event(event_date, event_description)
    year, month = map(int, event_date.split('-')[:2])
    return RedirectResponse(url=f"/calendar?year={year}&month={month}", status_code=303)


app.include_router(router)
