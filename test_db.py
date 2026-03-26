#!/usr/bin/env python
"""Quick test to verify database insertion works"""

from app.db import get_connection, initialize_database
from datetime import datetime

# Initialize the database
initialize_database()

# Test inserting a member
conn = get_connection()
cursor = conn.cursor()

test_data = {
    "name": "Solomon Monne",
    "phone": "0251763496",
    "ministry": "Choir",
    "gender": "Male",
    "date_of_birth": "2000-11-21",
    "occupational": "Student",
    "status": "Active",
    "join_date": datetime.now().strftime("%Y-%m-%d"),
}

try:
    fields = list(test_data.keys())
    placeholders = ", ".join(["?"] * len(fields))
    query = f"INSERT INTO members ({', '.join(fields)}) VALUES ({placeholders})"
    
    print(f"Query: {query}")
    print(f"Values: {[test_data[f] for f in fields]}")
    
    cursor.execute(query, [test_data[f] for f in fields])
    conn.commit()
    
    print(f"✓ Success! Member added with ID: {cursor.lastrowid}")
    
    # Verify it was inserted
    cursor.execute("SELECT * FROM members WHERE member_id = ?", (cursor.lastrowid,))
    row = cursor.fetchone()
    print(f"✓ Verified: {dict(row)}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
