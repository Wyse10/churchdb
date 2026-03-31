from fastapi import APIRouter, HTTPException, Depends
from typing import Any
import json
import traceback
from datetime import datetime

from app.schemas import QueryRequest, QueryResponse, ActionPayload
from app.services.action_validator import is_write_action, validate_action
from app.services.llama_nl import parse_natural_language, detect_add_member_intent
from app.services.member_repository import execute_action
from app.services.audit_logger import log_action, get_audit_logs, get_user_audit_logs
from app.services.form_builder import (
    get_next_form_step,
    is_form_complete,
    build_action_from_form,
    get_form_summary,
)
from app.api.auth_routes import get_current_user


router = APIRouter(tags=["query"])

MENU_OPTIONS = [
    "1. Add a new member",
    "2. Update a member",
    "3. Delete a member",
    "4. Show all members",
    "5. Query you want to perform"
]

MENU_MESSAGE = """
Welcome to Church Database Management System!

What would you like to do?

1. Add a new member
2. Update a member
3. Delete a member
4. Show all members
5. Query you want to perform

Please enter the number of your choice (1-5) or the command name.
""".strip()


def get_menu_response() -> QueryResponse:
    """Return the main menu."""
    return QueryResponse(
        message=MENU_MESSAGE,
        show_menu=True,
        menu_options=MENU_OPTIONS,
    )


def is_menu_selection(message: str) -> bool:
    """Check if message is a valid menu selection."""
    msg = message.strip().lower()
    # Check if it's a number 1-5
    if msg in ["1", "2", "3", "4", "5"]:
        return True
    # Check if it's a command keyword
    if any(keyword in msg for keyword in ["add", "update", "delete", "show", "query"]):
        return True
    return False


def parse_menu_selection(message: str) -> str:
    """Parse menu selection and return the command type."""
    msg = message.strip().lower()
    
    # Map number selections to commands
    number_map = {
        "1": "add",
        "2": "update",
        "3": "delete",
        "4": "show",
        "5": "query",
    }
    
    if msg in number_map:
        return number_map[msg]
    
    # Map keyword selections to commands
    if "add" in msg:
        return "add"
    elif "update" in msg:
        return "update"
    elif "delete" in msg:
        return "delete"
    elif "show" in msg:
        return "show"
    elif "query" in msg:
        return "query"
    
    return ""


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> QueryResponse:
    try:
        # Debug logging
        print(f"DEBUG: request.confirm={request.confirm}, type={type(request.confirm)}, message='{request.message}'")
        print(f"DEBUG: pending_action={request.pending_action is not None}")
        print(f"DEBUG: form_data={request.form_data is not None}")
        print(f"DEBUG: selected_command={request.selected_command}")
        
        # FIRST: Handle confirmation (highest priority)
        if request.confirm:
            print(f"DEBUG: Handling confirmation")
            if request.pending_action is None:
                raise HTTPException(
                    status_code=400,
                    detail="Please try your request again. Something went wrong.",
                )

            # Convert dict to ActionPayload if needed
            pending_action = request.pending_action
            if isinstance(pending_action, dict):
                print(f"DEBUG: Converting dict to ActionPayload: {pending_action}")
                pending_action = ActionPayload(**pending_action)
            
            action = validate_action(pending_action)
            print(f"DEBUG: Validated action: {action.action}")
            
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
                action_completed=True,  # Signal that the action is done
                show_menu=True,
                menu_options=MENU_OPTIONS
            )
        
        # If no command selected and no form in progress, show menu
        if request.selected_command is None and request.form_data is None:
            # Check if this message is a menu selection
            if is_menu_selection(request.message):
                command = parse_menu_selection(request.message)
                request.selected_command = command
            else:
                # Show menu if message is empty or doesn't match menu selection
                if request.message.strip() == "":
                    return get_menu_response()
                # Try to parse as menu selection anyway, if not found, show menu again
                if not is_menu_selection(request.message):
                    error_msg = f"Invalid selection. Please select a number from 1-5.\n\n{MENU_MESSAGE}"
                    return QueryResponse(
                        message=error_msg,
                        show_menu=True,
                        menu_options=MENU_OPTIONS,
                    )
        
        # Handle selected command
        if request.selected_command:
            command = request.selected_command.lower()
            
            # Handle "Add" command - start form collection
            if command == "add":
                if request.form_data is None:
                    # Start member addition form
                    next_step = {
                        "field": "first_name",
                        "prompt": "Enter the first name of the member:",
                        "optional": False,
                    }
                    return QueryResponse(
                        message=next_step["prompt"],
                        collecting_form=True,
                        form_data={},
                        form_step=next_step["field"],
                    )
                else:
                    # Continue with form collection
                    form_data = request.form_data.copy()
                    
                    if request.message.strip() or not next_step.get("optional"):
                        next_step = get_next_form_step(form_data)
                        if next_step:
                            incoming_value = request.message.strip()
                            if next_step["field"] in ["date_of_birth", "join_date"] and incoming_value:
                                try:
                                    datetime.strptime(incoming_value, "%Y-%m-%d")
                                except ValueError:
                                    return QueryResponse(
                                        message=f"Invalid date format for {next_step['field']}. Use YYYY-MM-DD (example: 2001-11-20).",
                                        collecting_form=True,
                                        form_data=form_data,
                                        form_step=next_step["field"],
                                    )
                            form_data[next_step["field"]] = incoming_value
                    
                    if is_form_complete(form_data):
                        action_dict = build_action_from_form(form_data)
                        action = validate_action(action_dict)
                        
                        if current_user.get("role") not in ["admin", "operator"]:
                            raise HTTPException(
                                status_code=403,
                                detail="You don't have permission to add members."
                            )
                        
                        summary = get_form_summary(form_data)
                        return QueryResponse(
                            message=f"{summary}\n\nPlease confirm by typing 'confirm' or 'yes'.",
                            action=action,
                            requires_confirmation=True,
                            result={"preview": action_dict},
                            collecting_form=False,
                            form_data=None,
                        )
                    
                    next_step = get_next_form_step(form_data)
                    if next_step:
                        return QueryResponse(
                            message=next_step["prompt"],
                            collecting_form=True,
                            form_data=form_data,
                            form_step=next_step["field"],
                        )
            
            # Handle "Show" command
            elif command == "show":
                action = validate_action({
                    "action": "select",
                    "table": "members",
                    "limit": 500,
                })
                result = execute_action(action)
                
                log_action(
                    user_id=current_user.get("user_id"),
                    username=current_user.get("username"),
                    action="QUERY",
                    table_name="members",
                    details=json.dumps({"action": "show all members"})
                )
                
                return QueryResponse(
                    message="All members retrieved successfully.",
                    action=action,
                    result=result,
                    action_completed=True,
                    show_menu=True,
                    menu_options=MENU_OPTIONS
                )
            
            # Handle "Delete" command
            elif command == "delete":
                if current_user.get("role") != "admin":
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to delete members. Please contact an administrator."
                    )
                
                # Start delete form if no form data exists
                if request.form_data is None:
                    return QueryResponse(
                        message="Do you want to delete all members or a particular member? (Type 'all' or 'particular')",
                        collecting_form=True,
                        form_data={},
                        form_step="delete_scope",
                    )
                else:
                    # Continue with delete form collection
                    form_data = request.form_data.copy()
                    
                    # Step 1: Get scope (all or particular)
                    if "delete_scope" not in form_data:
                        scope = request.message.strip().lower()
                        
                        if scope not in ["all", "particular"]:
                            return QueryResponse(
                                message="Invalid choice. Please type 'all' to delete all members or 'particular' to delete a specific member.",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="delete_scope",
                            )
                        
                        form_data["delete_scope"] = scope
                        
                        if scope == "all":
                            # Build action to delete all members
                            action_dict = {
                                "action": "delete",
                                "table": "members",
                                "filters": []
                            }
                            action = validate_action(action_dict)
                            
                            return QueryResponse(
                                message="WARNING: You are about to delete ALL members. This action cannot be undone. \n\nPlease confirm by typing 'confirm' or 'yes'.",
                                action=action,
                                requires_confirmation=True,
                                result={"preview": action_dict},
                                collecting_form=False,
                                form_data=None,
                            )
                        else:
                            # Ask for specific member identity fields
                            return QueryResponse(
                                message="Enter the first name of the member you want to delete:",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="first_name",
                            )
                    
                    # Step 2: Capture first name for particular delete
                    elif form_data.get("delete_scope") == "particular" and "first_name" not in form_data:
                        first_name = request.message.strip()
                        if not first_name:
                            return QueryResponse(
                                message="First name is required. Enter the first name of the member you want to delete:",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="first_name",
                            )

                        form_data["first_name"] = first_name
                        return QueryResponse(
                            message="Enter the last name of the member you want to delete:",
                            collecting_form=True,
                            form_data=form_data,
                            form_step="last_name",
                        )

                    # Step 3: Capture last name for particular delete
                    elif form_data.get("delete_scope") == "particular" and "last_name" not in form_data:
                        last_name = request.message.strip()
                        if not last_name:
                            return QueryResponse(
                                message="Last name is required. Enter the last name of the member you want to delete:",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="last_name",
                            )

                        form_data["last_name"] = last_name
                        return QueryResponse(
                            message="Enter the date of birth (YYYY-MM-DD):",
                            collecting_form=True,
                            form_data=form_data,
                            form_step="date_of_birth",
                        )

                    # Step 4: Capture DOB and build delete action for particular member
                    elif form_data.get("delete_scope") == "particular" and "date_of_birth" not in form_data:
                        date_of_birth = request.message.strip()
                        if not date_of_birth:
                            return QueryResponse(
                                message="Date of birth is required. Enter the date of birth (YYYY-MM-DD):",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="date_of_birth",
                            )

                        # Enforce strict date format for safer record matching.
                        try:
                            datetime.strptime(date_of_birth, "%Y-%m-%d")
                        except ValueError:
                            return QueryResponse(
                                message="Invalid date format. Enter date of birth as YYYY-MM-DD (example: 2001-11-20).",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="date_of_birth",
                            )

                        form_data["date_of_birth"] = date_of_birth

                        action_dict = {
                            "action": "delete",
                            "table": "members",
                            "filters": [
                                {"field": "first_name", "operator": "eq", "value": form_data["first_name"]},
                                {"field": "last_name", "operator": "eq", "value": form_data["last_name"]},
                                {"field": "date_of_birth", "operator": "eq", "value": form_data["date_of_birth"]},
                            ],
                        }
                        action = validate_action(action_dict)

                        member_label = f"{form_data['first_name']} {form_data['last_name']} ({form_data['date_of_birth']})"
                        return QueryResponse(
                            message=f"Are you sure you want to delete member '{member_label}'? Please confirm by typing 'confirm' or 'yes'.",
                            action=action,
                            requires_confirmation=True,
                            result={"preview": action_dict},
                            collecting_form=False,
                            form_data=None,
                        )
            
            # Handle "Update" command
            elif command == "update":
                if current_user.get("role") not in ["admin", "operator"]:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to update members."
                    )
                
                # Start update form if no form data exists
                if request.form_data is None:
                    return QueryResponse(
                        message="Enter the first name of the member you want to update:",
                        collecting_form=True,
                        form_data={},
                        form_step="member_name",
                    )
                else:
                    # Continue with update form collection
                    form_data = request.form_data.copy()
                    
                    # Step 1: Get member name
                    if "member_name" not in form_data:
                        form_data["member_name"] = request.message.strip()
                        return QueryResponse(
                            message="Which field would you like to update? (phone, ministry, status, email, occupational, gender, date_of_birth)",
                            collecting_form=True,
                            form_data=form_data,
                            form_step="field_to_update",
                        )
                    
                    # Step 2: Get field to update
                    elif "field_to_update" not in form_data:
                        field = request.message.strip().lower()
                        valid_fields = ["phone", "ministry", "status", "email", "occupational", "gender", "date_of_birth"]
                        
                        if field not in valid_fields:
                            return QueryResponse(
                                message=f"Invalid field. Please choose from: {', '.join(valid_fields)}",
                                collecting_form=True,
                                form_data=form_data,
                                form_step="field_to_update",
                            )
                        
                        form_data["field_to_update"] = field
                        return QueryResponse(
                            message=f"Enter the new value for {field}:",
                            collecting_form=True,
                            form_data=form_data,
                            form_step="new_value",
                        )
                    
                    # Step 3: Get new value and build action
                    elif "new_value" not in form_data:
                        new_value_input = request.message.strip()
                        if form_data.get("field_to_update") == "date_of_birth":
                            try:
                                datetime.strptime(new_value_input, "%Y-%m-%d")
                            except ValueError:
                                return QueryResponse(
                                    message="Invalid date format. Enter date_of_birth as YYYY-MM-DD (example: 2001-11-20).",
                                    collecting_form=True,
                                    form_data=form_data,
                                    form_step="new_value",
                                )

                        form_data["new_value"] = new_value_input
                        
                        # Build the update action
                        member_name = form_data["member_name"]
                        field_to_update = form_data["field_to_update"]
                        new_value = form_data["new_value"]
                        
                        action_dict = {
                            "action": "update",
                            "table": "members",
                            "data": {field_to_update: new_value},
                            "filters": [{"field": "first_name", "operator": "like", "value": member_name}]
                        }
                        
                        action = validate_action(action_dict)
                        summary = f"Update {member_name}'s {field_to_update} to: {new_value}"
                        
                        return QueryResponse(
                            message=f"{summary}\n\nPlease confirm by typing 'confirm' or 'yes'.",
                            action=action,
                            requires_confirmation=True,
                            result={"preview": action_dict},
                            collecting_form=False,
                            form_data=None,
                        )
            
            # Handle "Query" command
            elif command == "query":
                query_text = request.message.strip()
                if query_text in ["", "5", "5. Query you want to perform", "query"]:
                    return QueryResponse(
                        message="Please describe what information you're looking for or what action you'd like to perform.",
                        show_menu=False,
                    )

                action = await parse_natural_language(query_text)
                action = validate_action(action)

                if action.action == "delete" and current_user.get("role") != "admin":
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to delete members. Please contact an administrator."
                    )

                if action.action in ["insert", "update"] and current_user.get("role") not in ["admin", "operator"]:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to add or update members."
                    )

                if is_write_action(action):
                    return QueryResponse(
                        message="Please confirm this write action before execution.",
                        action=action,
                        requires_confirmation=True,
                        result={"preview": action.model_dump()},
                    )

                result = execute_action(action)

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
                    action_completed=True,
                    show_menu=True,
                    menu_options=MENU_OPTIONS,
                )
        
        # Handle form-based member addition
        if request.form_data is not None:
            form_data = request.form_data.copy()
            
            if request.message.strip() or not next_step.get("optional"):
                next_step = get_next_form_step(form_data)
                if next_step:
                    incoming_value = request.message.strip()
                    if next_step["field"] in ["date_of_birth", "join_date"] and incoming_value:
                        try:
                            datetime.strptime(incoming_value, "%Y-%m-%d")
                        except ValueError:
                            return QueryResponse(
                                message=f"Invalid date format for {next_step['field']}. Use YYYY-MM-DD (example: 2001-11-20).",
                                collecting_form=True,
                                form_data=form_data,
                                form_step=next_step["field"],
                            )
                    form_data[next_step["field"]] = incoming_value
            
            if is_form_complete(form_data):
                action_dict = build_action_from_form(form_data)
                action = validate_action(action_dict)
                
                if current_user.get("role") not in ["admin", "operator"]:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to add members."
                    )
                
                summary = get_form_summary(form_data)
                return QueryResponse(
                    message=f"{summary}\n\nPlease confirm by typing 'confirm' or 'yes'.",
                    action=action,
                    requires_confirmation=True,
                    result={"preview": action_dict},
                    collecting_form=False,
                    form_data=None,
                )
            
            next_step = get_next_form_step(form_data)
            if next_step:
                return QueryResponse(
                    message=next_step["prompt"],
                    collecting_form=True,
                    form_data=form_data,
                    form_step=next_step["field"],
                )

        # Check if message is about adding a member (old flow)
        if detect_add_member_intent(request.message):
            next_step = {
                "field": "first_name",
                "prompt": "Enter the first name of the member:",
                "optional": False,
            }
            return QueryResponse(
                message=next_step["prompt"],
                collecting_form=True,
                form_data={},
                form_step=next_step["field"],
            )

        # Otherwise, use natural language parsing for other queries
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
    except HTTPException as http_err:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        # Log the actual error for debugging
        print(f"ERROR in /query endpoint: {str(error)}")
        print(traceback.format_exc())
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
