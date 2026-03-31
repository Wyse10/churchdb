import json
import os
import re
from typing import Any

import httpx

from app.schemas import ActionPayload


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _parse_occupation_select(message: str) -> dict[str, Any] | None:
    text = message.strip()
    occupation_query_pattern = re.compile(
        r"(?:show|list|view|get|find)\s+(?:all\s+)?(?:members?|member)\s+(?:that\s+are|who\s+are|with\s+occupation\s+)?(?P<occupation>[a-zA-Z\s]+)",
        re.IGNORECASE,
    )
    occupation_match = occupation_query_pattern.search(text)
    if not occupation_match:
        return None

    occupation_value = occupation_match.group("occupation").strip().title()
    occupation_aliases = {
        "Student": "Student",
        "Students": "Student",
    }
    normalized_occupation = occupation_aliases.get(occupation_value, occupation_value)

    return {
        "action": "select",
        "table": "members",
        "filters": [
            {"field": "occupational", "operator": "like", "value": normalized_occupation}
        ],
        "limit": 100,
    }


def detect_add_member_intent(message: str) -> bool:
    """Detect if the user wants to add a new member."""
    lower_msg = message.lower().strip()
    keywords = ["add member", "new member", "register member", "add a member", "add new member", "register a member"]
    return any(keyword in lower_msg for keyword in keywords)


SYSTEM_PROMPT = """
You convert church admin natural language into JSON commands.
Return ONLY valid JSON without markdown.
Allowed JSON schema:
{
  "action": "insert|select|update|delete",
  "table": "members",
  "data": {"first_name": "", "last_name": "", "other_name": "", "phone": "", "ministry": "", "status": "Active|Inactive", "join_date": "YYYY-MM-DD", "gender": "Male|Female", "date_of_birth": "", "occupational": "", "email": ""},
  "filters": [{"field": "first_name|last_name|other_name|phone|ministry|status|member_id|join_date|gender|date_of_birth|occupational|email", "operator": "eq|neq|like|in|gt|gte|lt|lte", "value": ""}],
  "fields": ["member_id", "first_name", "last_name", "other_name", "phone", "ministry", "status", "join_date", "gender", "date_of_birth", "occupational", "email"],
  "limit": 100
}
Rules:
- Use table="members" only.
- Never output SQL.
- For "show/list" requests use action="select".
- For "add/new" requests use action="insert".
- For "update/change" requests use action="update".
- For "delete/remove" requests use action="delete".
""".strip()


def _extract_json_block(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("I couldn't understand your request. Please try again with clearer wording.")
    return text[start : end + 1]


def _fallback_parse(message: str) -> dict[str, Any]:
    text = message.strip()
    lower = text.lower()

    occupation_select = _parse_occupation_select(message)
    if occupation_select:
        return occupation_select

    add_pattern = re.compile(
        r"add\s+(?:(?:a\s+)?(?:new\s+)?member\s+)?(?P<name>[a-zA-Z\s\.\'-]+?)\s+(?:with\s+)?phone\s+(?P<phone>[0-9+\-\s]+)(?:\s+in\s+(?:the\s+)?(?P<ministry>[a-zA-Z\s]+))?",
        re.IGNORECASE,
    )
    add_match = add_pattern.search(text)
    if add_match:
        from datetime import datetime
        ministry = add_match.group("ministry")
        return {
            "action": "insert",
            "table": "members",
            "data": {
                "first_name": add_match.group("name").strip().split()[0],
                "last_name": " ".join(add_match.group("name").strip().split()[1:]),
                "phone": add_match.group("phone").strip(),
                "ministry": ministry.strip().title() if ministry else "Member",
                "status": "Active",
                "join_date": datetime.now().strftime("%Y-%m-%d"),
            },
        }

    update_phone_pattern = re.compile(
        r"update\s+(?P<name>[a-zA-Z\s\.\'-]+?)(?:'s)?\s+phone(?:\s+number)?\s+to\s+(?P<phone>[0-9+\-\s]+)",
        re.IGNORECASE,
    )
    update_phone_match = update_phone_pattern.search(text)
    if update_phone_match:
        return {
            "action": "update",
            "table": "members",
            "data": {"phone": update_phone_match.group("phone").strip()},
            "filters": [
                {
                    "field": "first_name",
                    "operator": "like",
                    "value": update_phone_match.group("name").strip(),
                }
            ],
        }

    if "delete inactive" in lower:
        return {
            "action": "delete",
            "table": "members",
            "filters": [{"field": "status", "operator": "eq", "value": "Inactive"}],
        }

    choir_match = re.search(r"show|list", lower)
    if choir_match and "choir" in lower:
        return {
            "action": "select",
            "table": "members",
            "filters": [{"field": "ministry", "operator": "eq", "value": "Choir"}],
            "limit": 100,
        }

    if any(keyword in lower for keyword in ["show", "list", "view"]):
        return {"action": "select", "table": "members", "limit": 100}

    raise ValueError("I'm not sure what you're trying to do. Try saying something like 'add John Smith with phone 0241234567 in choir' or 'show all members'.")


async def parse_natural_language(message: str) -> ActionPayload:
    # Apply deterministic parsing for common occupation-based select requests.
    occupation_select = _parse_occupation_select(message)
    if occupation_select:
        return ActionPayload.model_validate(occupation_select)

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        fallback_data = _fallback_parse(message)
        return ActionPayload.model_validate(fallback_data)

    payload = {
        "model": DEFAULT_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            raw_json = _extract_json_block(content)
            data = json.loads(raw_json)
            return ActionPayload.model_validate(data)
    except Exception:
        fallback_data = _fallback_parse(message)
        return ActionPayload.model_validate(fallback_data)
