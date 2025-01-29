import sqlite3

conn = sqlite3.connect('test.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    course_name TEXT NOT NULL,
    access_code TEXT NOT NULL
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (course_id) REFERENCES courses (id)
)
''')

conn.commit()
conn.close()
