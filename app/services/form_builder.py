from typing import Any
from datetime import datetime


# Define member form fields in order
MEMBER_FORM_STEPS = [
    {
        "field": "first_name",
        "prompt": "Enter the first name of the member:",
        "optional": False,
    },
    {
        "field": "last_name",
        "prompt": "Enter the last name of the member:",
        "optional": False,
    },
    {
        "field": "phone",
        "prompt": "Enter the phone number:",
        "optional": False,
    },
    {
        "field": "ministry",
        "prompt": "Enter the ministry (e.g., Choir, Youth, etc.):",
        "optional": False,
    },
    {
        "field": "gender",
        "prompt": "Enter the gender (Male/Female):",
        "optional": False,
    },
    {
        "field": "date_of_birth",
        "prompt": "Enter the date of birth (YYYY-MM-DD format):",
        "optional": False,
    },
    {
        "field": "occupational",
        "prompt": "Enter the occupation:",
        "optional": False,
    },
    {
        "field": "email",
        "prompt": "Enter the email address (leave blank if not available) [OPTIONAL]:",
        "optional": True,
    },
    {
        "field": "status",
        "prompt": "Enter the status (Active/Inactive) [Default: Active]:",
        "optional": True,
        "default": "Active",
    },
    {
        "field": "join_date",
        "prompt": "Enter the join date (YYYY-MM-DD format) [Default: Today]:",
        "optional": True,
        "default": datetime.now().strftime("%Y-%m-%d"),
    },
]


def get_next_form_step(collected_data: dict[str, Any]) -> dict[str, Any] | None:
    """Get the next form step that needs to be filled."""
    for step in MEMBER_FORM_STEPS:
        if step["field"] not in collected_data:
            return step
    return None


def get_form_display_message(step: dict[str, Any]) -> str:
    """Get the display message for a form step."""
    return step["prompt"]


def is_form_complete(collected_data: dict[str, Any]) -> bool:
    """Check if all required fields have been collected."""
    for step in MEMBER_FORM_STEPS:
        if not step["optional"] and step["field"] not in collected_data:
            return False
    return True


def build_action_from_form(form_data: dict[str, Any]) -> dict[str, Any]:
    """Convert collected form data into an action payload."""
    # Create a new dict with all fields
    data_to_insert = {}
    
    # Add all provided required data
    for step in MEMBER_FORM_STEPS:
        field = step["field"]
        if field in form_data:
            value = form_data[field]
            # Convert to string and check if not empty
            if isinstance(value, str) and value.strip() != "":
                data_to_insert[field] = value.strip().title()
            elif not isinstance(value, str) and value is not None:
                data_to_insert[field] = str(value)
    
    # Ensure all required fields are present
    required_fields = ["first_name", "last_name", "phone", "ministry", "gender", "date_of_birth", "occupational"]
    for field in required_fields:
        if field not in data_to_insert:
            raise ValueError(f"Missing required field: {field}")
    
    # Add default status if not already present
    if "status" not in data_to_insert:
        data_to_insert["status"] = "Active"
    
    # Add default join_date if not already present  
    if "join_date" not in data_to_insert:
        data_to_insert["join_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return {
        "action": "insert",
        "table": "members",
        "data": data_to_insert,
    }


def get_form_summary(form_data: dict[str, Any]) -> str:
    """Generate a summary of the entered data for confirmation."""
    summary_lines = ["Member Details Summary:", "=" * 40]
    
    for step in MEMBER_FORM_STEPS:
        field = step["field"]
        if field in form_data:
            label = field.replace("_", " ").title()
            value = form_data[field]
            if value == "":
                value = "[Not provided]"
            summary_lines.append(f"{label}: {value}")
    
    summary_lines.append("=" * 40)
    return "\n".join(summary_lines)
