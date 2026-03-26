from typing import Any

from app.db import get_connection
from app.schemas import ActionPayload, FilterCondition


OPERATOR_MAP = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


def _build_where_clause(filters: list[FilterCondition] | None) -> tuple[str, list[Any]]:
    if not filters:
        return "", []

    clauses: list[str] = []
    params: list[Any] = []

    for filter_item in filters:
        if filter_item.operator in OPERATOR_MAP:
            clauses.append(f"{filter_item.field} {OPERATOR_MAP[filter_item.operator]} ?")
            params.append(filter_item.value)
        elif filter_item.operator == "like":
            clauses.append(f"{filter_item.field} LIKE ?")
            params.append(f"%{filter_item.value}%")
        elif filter_item.operator == "in":
            if not isinstance(filter_item.value, list) or not filter_item.value:
                raise ValueError("'in' operator requires a non-empty list value.")
            placeholders = ", ".join(["?"] * len(filter_item.value))
            clauses.append(f"{filter_item.field} IN ({placeholders})")
            params.extend(filter_item.value)
        else:
            raise ValueError(f"Unsupported operator: {filter_item.operator}")

    return " WHERE " + " AND ".join(clauses), params


def execute_action(action: ActionPayload) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.cursor()

        if action.action == "insert":
            data = action.data or {}
            
            # Ensure required fields are present
            required_fields = ["first_name", "last_name", "phone", "ministry", "status", "gender", "date_of_birth", "occupational"]
            for field in required_fields:
                if field not in data or data[field] is None or str(data[field]).strip() == "":
                    raise ValueError(f"Required field '{field}' is missing or empty")
            
            fields = list(data.keys())
            placeholders = ", ".join(["?"] * len(fields))
            query = f"INSERT INTO members ({', '.join(fields)}) VALUES ({placeholders})"
            
            try:
                cursor.execute(query, [data[field] for field in fields])
                connection.commit()
                return {
                    "operation": "insert",
                    "member_id": cursor.lastrowid,
                    "rows_affected": cursor.rowcount,
                }
            except Exception as e:
                connection.rollback()
                raise ValueError(f"Database error during insert: {str(e)}")

        if action.action == "select":
            selected_fields = ", ".join(action.fields) if action.fields else "*"
            where_clause, params = _build_where_clause(action.filters)
            limit = action.limit or 100
            query = f"SELECT {selected_fields} FROM members{where_clause} LIMIT ?"
            rows = cursor.execute(query, params + [limit]).fetchall()
            return {
                "operation": "select",
                "count": len(rows),
                "rows": [dict(row) for row in rows],
            }

        if action.action == "update":
            data = action.data or {}
            set_clause = ", ".join([f"{field} = ?" for field in data.keys()])
            where_clause, params = _build_where_clause(action.filters)
            query = f"UPDATE members SET {set_clause}{where_clause}"
            cursor.execute(query, list(data.values()) + params)
            connection.commit()
            return {
                "operation": "update",
                "rows_affected": cursor.rowcount,
            }

        if action.action == "delete":
            where_clause, params = _build_where_clause(action.filters)
            query = f"DELETE FROM members{where_clause}"
            cursor.execute(query, params)
            connection.commit()
            return {
                "operation": "delete",
                "rows_affected": cursor.rowcount,
            }

        raise ValueError(f"Unknown action '{action.action}'")
