from fastapi import APIRouter, HTTPException, Depends
from typing import Any
import json

from app.schemas import QueryRequest, QueryResponse
from app.services.action_validator import is_write_action, validate_action
from app.services.llama_nl import parse_natural_language
from app.services.member_repository import execute_action
from app.services.audit_logger import log_action, get_audit_logs, get_user_audit_logs
from app.api.auth_routes import get_current_user


router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> QueryResponse:
    try:
        if request.confirm:
            if request.pending_action is None:
                raise HTTPException(
                    status_code=400,
                    detail="Please try your request again. Something went wrong.",
                )

            action = validate_action(request.pending_action)
            
            # Check permissions for delete
            if action.action == "delete":
                if current_user.get("role") != "admin":
                    raise HTTPException(status_code=403, detail="You don't have permission to delete members. Please contact an administrator.")
            
            # Check permissions for write operations
            if action.action in ["insert", "update"]:
                if current_user.get("role") not in ["admin", "operator"]:
                    raise HTTPException(status_code=403, detail="You don't have permission to add or update members.")
            
            result = execute_action(action)
            
            # Log the action
            log_action(
                user_id=current_user.get("user_id"),
                username=current_user.get("username"),
                action=action.action.upper(),
                table_name=action.table,
                details=json.dumps(action.model_dump())
            )
            
            return QueryResponse(
                message=f"{action.action.title()} operation completed successfully.",
                action=action,
                result=result,
            )

        action = await parse_natural_language(request.message)
        action = validate_action(action)

        # Check permissions before showing confirmation
        if action.action == "delete":
            if current_user.get("role") != "admin":
                raise HTTPException(status_code=403, detail="You don't have permission to delete members. Please contact an administrator.")
        
        if action.action in ["insert", "update"]:
            if current_user.get("role") not in ["admin", "operator"]:
                raise HTTPException(status_code=403, detail="You don't have permission to add or update members.")

        if is_write_action(action):
            return QueryResponse(
                message="Please confirm this write action before execution.",
                action=action,
                requires_confirmation=True,
                result={"preview": action.model_dump()},
            )

        result = execute_action(action)
        
        # Log read actions too (select)
        if action.action == "select":
            log_action(
                user_id=current_user.get("user_id"),
                username=current_user.get("username"),
                action="QUERY",
                table_name=action.table,
                details=json.dumps(action.model_dump())
            )
        
        return QueryResponse(
            message="Query executed successfully.",
            action=action,
            result=result,
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again or contact your administrator.") from error


@router.get("/audit-logs")
def get_logs(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Get audit logs (admin can see all, operators see their own)."""
    if current_user.get("role") == "admin":
        logs = get_audit_logs(limit=100)
        return {"logs": logs, "user": current_user}
    else:
        logs = get_user_audit_logs(current_user.get("user_id"), limit=50)
        return {"logs": logs, "user": current_user}
