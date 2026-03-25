from typing import Any, Literal

from pydantic import BaseModel, Field


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


class QueryResponse(BaseModel):
    message: str
    action: ActionPayload | None = None
    requires_confirmation: bool = False
    result: dict[str, Any] | None = None


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
