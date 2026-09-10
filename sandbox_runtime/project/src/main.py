"""Simulated Project Entrypoint"""
from src.auth import authenticate_user
from src.database import get_user_by_username

def run_app():
    print("Starting secure application service...")
    user = get_user_by_username("alice")
    if user:
        is_valid = authenticate_user("alice", "password123")
        print(f"Authentication test for alice: {is_valid}")

if __name__ == "__main__":
    run_app()
