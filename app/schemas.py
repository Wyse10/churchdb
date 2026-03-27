from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ActionType = Literal["insert", "select", "update", "delete"]
TableName = Literal["members"]
OperatorType = Literal["eq", "neq", "like", "in", "gt", "gte", "lt", "lte"]
RoleType = Literal["admin", "operator"]


class FilterCondition(BaseModel):
    field: str
    operator: OperatorType = "eq"
    value: Any


class ActionPayload(BaseModel):
    action: ActionType
    table: TableName = "members"
    data: dict[str, Any] | None = None
    filters: list[FilterCondition] | None = None
    fields: list[str] | None = None
    limit: int | None = Field(default=None, ge=1, le=500)


class QueryRequest(BaseModel):
    message: str
    confirm: bool = False
    pending_action: ActionPayload | None = None
    form_data: dict[str, Any] | None = None
    selected_command: str | None = None
    
    @field_validator('pending_action', mode='before')
    @classmethod
    def validate_pending_action(cls, v):
        if v is None:
            return None
        # If it's already a dict, convert it to ActionPayload
        if isinstance(v, dict):
            try:
                return ActionPayload(**v)
            except Exception as e:
                print(f"ERROR validating pending_action: {e}")
                print(f"pending_action data: {v}")
                raise
        return v


class QueryResponse(BaseModel):
    message: str
    action: ActionPayload | None = None
    requires_confirmation: bool = False
    result: dict[str, Any] | None = None
    collecting_form: bool = False
    form_data: dict[str, Any] | None = None
    form_step: str | None = None
    show_menu: bool = False
    menu_options: list[str] | None = None
    action_completed: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict[str, Any]


class UserCreate(BaseModel):
    username: str
    password: str
    role: RoleType


class Member(BaseModel):
    member_id: int | None = None
    first_name: str
    last_name: str
    other_name: str | None = None
    phone: str
    ministry: str
    status: Literal["Active", "Inactive"]
    join_date: str | None = None
    gender: Literal["Male", "Female"]
    date_of_birth: str
    email: str | None = None
    occupational: str
    age: int | None = None
