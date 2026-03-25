# ChurchDB - AI-Powered Church Member Management System

A secure, web-based Church Management System that converts natural language queries into safe, structured CRUD operations on a SQLite database. Features role-based access control, audit logging, and AI-powered natural language processing.

## Tech Stack

- Backend: FastAPI (Python)
- Frontend: HTML + JavaScript (chat-style interface)
- Database: SQLite
- AI: Groq Llama API (with fallback rule-based parser for common commands)
- Authentication: JWT token-based

## Features

### Member Management
- Add new members with details (name, phone, ministry, status, join date)
- Update existing member information
- Delete members (hard delete - admin only)
- View and filter members by ministry or status
- Search and query members

### Authentication & Authorization
- User login system with JWT tokens
- Role-based access control (Admin and Operator roles)
- Admin-only permissions for user creation and member deletion
- Operator permissions for adding and updating members
- Session management

### Natural Language Interface
- Convert natural language commands to database operations
- AI-powered parsing with Groq Llama API
- Fallback rule-based parser for offline operation
- Confirmation required for all write operations (insert, update, delete)

### Audit & Compliance
- Comprehensive audit logging of all database operations
- Track user actions with timestamps and change details
- Admin access to all audit logs
- Operators can view their own action history
- Log read and write operations separately

### Safety Features
- Confirmation workflow before executing write operations
- Permission validation before operations execute
- Input validation on all requests
- Proper error handling and user feedback

## Project Structure

```
churchdb/
├─ app/
│  ├─ api/routes.py
│  ├─ services/
│  │  ├─ action_validator.py
│  │  ├─ llama_nl.py
│  │  └─ member_repository.py
│  ├─ db.py
│  ├─ main.py
│  └─ schemas.py
├─ web/
│  ├─ index.html
│  ├─ chat.js
│  └─ styles.css
├─ requirements.txt
└─ README.md
```

## Setup

1. Create virtual environment:

```powershell
python -m venv .venv
```

2. Activate virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Configure environment variables (optional but recommended):

```powershell
$env:GROQ_API_KEY="your_groq_api_key"
$env:GROQ_MODEL="llama-3.3-70b-versatile"
```

If `GROQ_API_KEY` is not set, the app uses a small rule-based fallback parser for common commands.

5. Run server:

```powershell
uvicorn app.main:app --reload
```

6. Open in browser:

`http://127.0.0.1:8000`

## Example Commands

- `Add a new member John Doe with phone 0240000000 in the choir`
- `Update Mary's phone number to 0550000000`
- `Delete inactive members`
- `Show all choir members`
- `List all active members in the worship team`

For write operations, the app asks for confirmation. Type `yes` in the chat to execute.

## API Endpoints

### Authentication

#### POST /auth/login
Login to get an access token.

**Request:**
```json
{
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

#### POST /auth/users
Create a new user (admin only).

**Request:**
```json
{
  "username": "john_operator",
  "password": "securepassword",
  "role": "operator"
}
```

#### GET /auth/me
Get current logged-in user information.

### Query Operations

#### POST /query
Execute a natural language query or confirm a pending action.

**Initial query request:**
```json
{
  "message": "Add a new member John Doe with phone 0240000000 in the choir"
}
```

**Confirmation request:**
```json
{
  "message": "yes",
  "confirm": true,
  "pending_action": {
    "action": "insert",
    "table": "members",
    "data": {
      "name": "John Doe",
      "phone": "0240000000",
      "ministry": "Choir",
      "status": "Active"
    }
  }
}
```

**Authorization:** 
- Requires Bearer token in Authorization header
- Admin: Can perform all operations (create, update, delete)
- Operator: Can create and update members only
- Delete operations restricted to admin role

### Audit Logging

#### GET /audit-logs
Retrieve audit logs of all database operations.

**Authorization:**
- Admin: Can view all audit logs (up to 100 recent entries)
- Operator: Can view only their own audit logs (up to 50 recent entries)

**Response:**
```json
{
  "logs": [
    {
      "log_id": 1,
      "user_id": 1,
      "username": "admin",
      "action": "INSERT",
      "table_name": "members",
      "record_id": 5,
      "details": "{...action details...}",
      "timestamp": "2026-03-25 10:30:45"
    }
  ],
  "user": {
    "user_id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

## Security Design

- **No SQL Generation**: The model does not produce executable SQL
- **Structured Actions Only**: Backend only accepts structured JSON actions
- **Input Validation**: All actions and fields are validated before execution
- **Parameterized Queries**: Uses parameterized SQLite queries to prevent injection
- **Limited Scope**: Operations restricted to `members`, `users`, and audit logging
- **Role-Based Access Control**: Permission checks before any operation
- **Audit Trail**: All operations logged with user context and timestamp
- **Confirmation Workflow**: Write operations require explicit confirmation
