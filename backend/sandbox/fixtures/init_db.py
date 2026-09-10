"""Initializes the fake database for the sandbox fixtures"""
import os
import sqlite3

def init_fixture_database(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        api_token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    sample_users = [
        ("alice", "alice@example.internal", "developer", "tok_fake_user_alice_111"),
        ("bob", "bob@example.internal", "developer", "tok_fake_user_bob_222"),
        ("charlie", "charlie@example.internal", "analyst", "tok_fake_user_charlie_333"),
        ("admin", "security-admin@example.internal", "administrator", "tok_fake_admin_999_critical")
    ]
    
    cursor.executemany(
        "INSERT INTO users (username, email, role, api_token) VALUES (?, ?, ?, ?)",
        sample_users
    )
    
    cursor.execute(
        "INSERT INTO audit_events (event_type, details) VALUES (?, ?)",
        ("system_startup", "Simulated environment database initialized.")
    )
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    target_db = os.path.join(current_dir, "database", "fake_users.db")
    init_fixture_database(target_db)
    print(f"Fixture database initialized at {target_db}")
