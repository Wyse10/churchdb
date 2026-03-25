import hashlib
from datetime import datetime, timedelta
from typing import Any

import jwt

from app.db import get_connection


SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: int, username: str, role: str) -> str:
    """Create JWT access token."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        return None


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate user and return user data if valid."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT user_id, username, role, password FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if not user:
            return None
        
        if not verify_password(password, user["password"]):
            return None
        
        return dict(user)


def create_user(username: str, password: str, role: str) -> bool:
    """Create a new user. Returns True if successful, False if username exists."""
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """INSERT INTO users (username, password, role, created_at) 
                   VALUES (?, ?, ?, ?)""",
                (username, hash_password(password), role, datetime.now().isoformat())
            )
            connection.commit()
            return True
        except Exception:
            return False


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Get user by ID."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT user_id, username, role FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        return dict(user) if user else None
