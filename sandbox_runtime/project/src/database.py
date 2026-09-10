"""Database connection and query helpers for simulated project"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "fake_users.db")

def get_connection(custom_path: str = None):
    target_path = custom_path or DB_PATH
    return sqlite3.connect(target_path)

def get_user_by_username(username: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2], "role": row[3]}
        return None
    except Exception as e:
        return {"error": str(e)}

def list_all_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "username": r[1], "email": r[2], "role": r[3]} for r in rows]
    except Exception as e:
        return {"error": str(e)}
