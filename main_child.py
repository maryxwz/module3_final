#ROOTS FOR PUT IN MAIN FILE




@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("child_index.html", {"request": request})

@app.get("/progress")
async def progress(request: Request):
    return templates.TemplateResponse("progress.html", {"request": request, "courses": grades_data.keys()})

@app.get("/api/progress/{course}")
async def get_progress(course: str):
    return {"course": course, "grades": grades_data.get(course, [])}