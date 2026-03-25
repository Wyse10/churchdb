from datetime import date

from app.schemas import ActionPayload


ALLOWED_FIELDS = {"member_id", "name", "phone", "ministry", "status", "join_date"}
WRITE_ACTIONS = {"insert", "update", "delete"}
FORBIDDEN_TOKENS = {
    "drop",
    "alter",
    "truncate",
    "attach",
    "detach",
    "pragma",
    ";",
    "--",
}


def _contains_forbidden_token(value: str) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in FORBIDDEN_TOKENS)


def _validate_fields(field_names: list[str]) -> None:
    for field_name in field_names:
        if field_name not in ALLOWED_FIELDS:
            raise ValueError(f"'{field_name}' is not a valid field. Please use: name, phone, ministry, status, or join date.")


def _validate_phone(phone: str) -> None:
    """Validate phone number is exactly 10 digits."""
    # Remove any spaces, dashes, or plus signs
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if len(digits) != 10:
        raise ValueError(f"Phone number should have 10 digits. You entered {len(digits)} digits. Please check and try again.")


def _normalize_status(data: dict) -> None:
    if "status" not in data:
        return

    value = str(data["status"]).strip().lower()
    if value not in {"active", "inactive"}:
        raise ValueError("Status should be either 'Active' or 'Inactive'.")
    data["status"] = "Active" if value == "active" else "Inactive"


def validate_action(action: ActionPayload) -> ActionPayload:
    if action.table != "members":
        raise ValueError("I can only work with member information right now.")

    if action.fields:
        _validate_fields(action.fields)

    if action.filters:
        for condition in action.filters:
            if condition.field not in ALLOWED_FIELDS:
                raise ValueError(f"I don't recognize '{condition.field}'. Please use: name, phone, ministry, status, or member ID.")
            if isinstance(condition.value, str) and _contains_forbidden_token(condition.value):
                raise ValueError("The text you entered looks suspicious. Please try again with different wording.")

    data = dict(action.data or {})

    if action.action == "insert":
        required_fields = {"name", "phone", "ministry"}
        if not required_fields.issubset(data.keys()):
            missing = ", ".join(sorted(required_fields - set(data.keys())))
            raise ValueError(f"Please provide the member's {missing}. These are required to add a new member.")
        _validate_fields(list(data.keys()))
        _validate_phone(data["phone"])
        _normalize_status(data)
        data.setdefault("status", "Active")
        data.setdefault("join_date", date.today().isoformat())

    if action.action == "update":
        if not data:
            raise ValueError("Please tell me what you'd like to change about this member.")
        if not action.filters:
            raise ValueError("Please specify which member you want to update.")
        _validate_fields(list(data.keys()))
        if "phone" in data:
            _validate_phone(data["phone"])
        _normalize_status(data)

    if action.action == "delete":
        if not action.filters:
            raise ValueError("Please specify which member you want to delete.")

    if action.action == "select" and action.limit is None:
        action.limit = 100

    action.data = data or None
    return action


def is_write_action(action: ActionPayload) -> bool:
    return action.action in WRITE_ACTIONS
