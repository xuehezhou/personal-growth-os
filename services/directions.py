"""用户自主维护的阶段方向。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from database import DB_PATH, execute, fetch_one


DIRECTION_FIELDS = (
    "long_term_vision",
    "current_stage",
    "current_goal",
    "primary_conflict",
    "secondary_conflicts",
    "current_priority",
    "not_doing",
)


def get_direction(db_path: Path | str = DB_PATH) -> dict[str, Any]:
    row = fetch_one(
        f"SELECT {', '.join(DIRECTION_FIELDS)}, updated_at FROM directions WHERE id = 1 LIMIT 1",
        (), db_path,
    )
    return row or {**{field: "" for field in DIRECTION_FIELDS}, "updated_at": ""}


def save_direction(values: dict[str, Any], db_path: Path | str = DB_PATH) -> None:
    cleaned = {
        field: str(values.get(field, "") or "").strip() for field in DIRECTION_FIELDS
    }
    execute(
        """
        INSERT INTO directions (
            id, long_term_vision, primary_conflict, secondary_conflicts,
            current_priority, not_doing, updated_at, current_stage, current_goal
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            long_term_vision = excluded.long_term_vision,
            current_stage = excluded.current_stage,
            current_goal = excluded.current_goal,
            primary_conflict = excluded.primary_conflict,
            secondary_conflicts = excluded.secondary_conflicts,
            current_priority = excluded.current_priority,
            not_doing = excluded.not_doing,
            updated_at = excluded.updated_at
        """,
        (
            cleaned["long_term_vision"],
            cleaned["primary_conflict"],
            cleaned["secondary_conflicts"],
            cleaned["current_priority"],
            cleaned["not_doing"],
            datetime.now().isoformat(timespec="seconds"),
            cleaned["current_stage"],
            cleaned["current_goal"],
        ),
        db_path,
    )
