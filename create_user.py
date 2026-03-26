import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "church.db"

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# Create an admin user
username = "admin"
password = "password"
role = "admin"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

hashed_pwd = hash_password(password)
created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

try:
    cursor.execute(
        """
        INSERT INTO users (username, password, role, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (username, hashed_pwd, role, created_at)
    )
    conn.commit()
    print(f"✓ Admin user created successfully:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Role: {role}")
except Exception as e:
    print(f"✗ Error creating user: {e}")
finally:
    conn.close()
