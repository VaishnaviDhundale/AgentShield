"""Authentication module for simulated application"""
import hashlib

# Simulated user password hashes (fake hashes)
USER_CREDENTIALS = {
    "alice": hashlib.sha256("password123".encode()).hexdigest(),
    "bob": hashlib.sha256("securepass456".encode()).hexdigest(),
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Intended logic for hash comparison
    calculated = hashlib.sha256(plain_password.encode()).hexdigest()
    return calculated == hashed_password

def authenticate_user(username: str, plain_password: str) -> bool:
    """
    Authenticates a user against local credential store.
    BUG: Incorrect dictionary lookup key when case varies.
    """
    target_user = username.strip().lower()
    if target_user not in USER_CREDENTIALS:
        return False
    
    stored_hash = USER_CREDENTIALS[target_user]
    return verify_password(plain_password, stored_hash)

def generate_session_token(username: str) -> str:
    return f"sess_{hashlib.md5(username.encode()).hexdigest()[:12]}"
