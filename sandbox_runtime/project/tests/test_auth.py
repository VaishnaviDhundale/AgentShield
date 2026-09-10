"""Unit tests for authentication module"""
from src.auth import authenticate_user, generate_session_token

def test_authenticate_valid_user():
    assert authenticate_user("alice", "password123") is True
    assert authenticate_user("bob", "securepass456") is True

def test_authenticate_invalid_password():
    assert authenticate_user("alice", "wrongpass") is False

def test_authenticate_unknown_user():
    assert authenticate_user("charlie", "password123") is False

def test_session_token_generation():
    token = generate_session_token("alice")
    assert token.startswith("sess_")
    assert len(token) > 10
