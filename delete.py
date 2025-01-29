import jwt
from flask import Flask, request, jsonify
from functools import wraps
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "супер пупер секретний ключ")
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600

app = Flask(__name__)

def create_token(data):
    payload = {
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS),
        'iat': datetime.utcnow(),
        'sub': data
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Токен не надано!'}), 403

        token = auth_header.split(' ')[1]
        user_data = verify_token(token)
        if not user_data:
            return jsonify({'message': 'Токен недійсний або прострочений!'}), 403

        request.user = user_data
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            sslmode="require"
        )
        return conn
    except psycopg2.Error as e:
        print(f"Помилка підключення до бази даних: {e}")
        return None

@app.route('/courses/<int:course_id>', methods=['DELETE'])
@auth_required
def delete_course(course_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Помилка підключення до бази даних'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM assignments WHERE course_id = %s", (course_id,))
        cursor.execute("DELETE FROM enrollments WHERE course_id = %s", (course_id,))
        cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        conn.commit()
    except psycopg2.Error as e:
        return jsonify({'message': f'Помилка видалення курсу: {e}'})
    finally:
        cursor.close()
        conn.close()
    return jsonify({'message': 'Курс успішно видалено!'})

@app.route('/courses/<int:course_id>/students/<int:student_id>', methods=['DELETE'])
@auth_required
def remove_student_from_course(course_id, student_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Помилка підключення до бази даних'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM enrollments WHERE course_id = %s AND user_id = %s", (course_id, student_id))
        conn.commit()
    except psycopg2.Error as e:
        return jsonify({'message': f'Помилка видалення студента: {e}'})
    finally:
        cursor.close()
        conn.close()
    return jsonify({'message': 'Студента успішно видалено!'})

@app.route('/courses/<int:course_id>', methods=['PUT'])
@auth_required
def update_course(course_id):
    data = request.json
    name = data.get('name')
    description = data.get('description')
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Помилка підключення до бази даних'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE courses SET name = %s, description = %s WHERE id = %s", (name, description, course_id))
        conn.commit()
    except psycopg2.Error as e:
        return jsonify({'message': f'Помилка оновлення курсу: {e}'})
    finally:
        cursor.close()
        conn.close()
    return jsonify({'message': 'Курс успішно оновлено!'})

if __name__ == '__main__':
    app.run(debug=True)
