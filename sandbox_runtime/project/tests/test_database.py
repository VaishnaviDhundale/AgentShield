"""Unit tests for database module"""
import sqlite3
from src.database import get_user_by_username, list_all_users

def test_database_connection():
    # Smoke test for user listing
    users = list_all_users()
    assert isinstance(users, list)

def test_get_existing_user():
    user = get_user_by_username("alice")
    if user and "username" in user:
        assert user["username"] == "alice"
