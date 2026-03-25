from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Any

from app.schemas import LoginRequest, LoginResponse, UserCreate
from app.services.auth import authenticate_user, create_access_token, verify_token, create_user, get_user_by_id


router = APIRouter(tags=["auth"], prefix="/auth")


def get_current_user(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Dependency to verify and return current user from token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Please log in first.")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Your session is invalid. Please log in again.")
    
    token = parts[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.")
    
    return payload


def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Dependency to ensure user is admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can do this. Please contact your admin.")
    return current_user


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    """Login endpoint to get access token."""
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Username or password is incorrect. Please try again.")
    
    token = create_access_token(user["user_id"], user["username"], user["role"])
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        }
    )


@router.post("/users")
def create_new_user(request: UserCreate, current_user: dict[str, Any] = Depends(require_admin)) -> dict[str, str]:
    """Create a new user (admin only)."""
    if create_user(request.username, request.password, request.role):
        return {"message": f"User {request.username} has been created successfully."}
    else:
        raise HTTPException(status_code=400, detail="This username already exists. Please choose a different username.")


@router.get("/me")
def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Get current user info."""
    return current_user
