"""习惯打卡与连续天数。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from database import DB_PATH, execute, fetch_all, fetch_one


def create_habit(
    name: str,
    category: str,
    target_minutes: int,
    db_path: Path | str = DB_PATH,
) -> int:
    """创建一个每天重复的习惯目标。"""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("习惯名称不能为空")
    existing = fetch_one(
        "SELECT id FROM habits WHERE name = ? LIMIT 1", (clean_name,), db_path
    )
    if existing:
        raise ValueError("已经存在同名的每日习惯")
    return execute(
        """
        INSERT INTO habits (name, category, target_minutes, active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            clean_name,
            category,
            max(0, int(target_minutes)),
            datetime.now().isoformat(timespec="seconds"),
        ),
        db_path,
    )


def list_habits(log_date: str, db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            h.id,
            h.name,
            h.category,
            h.target_minutes,
            COALESCE(hl.completed, 0) AS completed,
            COALESCE(hl.minutes, 0) AS minutes,
            COALESCE(hl.notes, '') AS notes
        FROM habits h
        LEFT JOIN habit_logs hl
            ON hl.habit_id = h.id AND hl.log_date = ?
        WHERE h.active = 1
        ORDER BY h.id
        LIMIT 100
        """,
        (log_date,),
        db_path,
    )


def save_habit_log(
    habit_id: int,
    log_date: str,
    completed: bool,
    minutes: int,
    notes: str = "",
    db_path: Path | str = DB_PATH,
) -> None:
    execute(
        """
        INSERT INTO habit_logs (habit_id, log_date, completed, minutes, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(habit_id, log_date) DO UPDATE SET
            completed = excluded.completed,
            minutes = excluded.minutes,
            notes = excluded.notes
        """,
        (habit_id, log_date, int(completed), max(0, int(minutes)), notes.strip()),
        db_path,
    )


def calculate_streak(habit_id: int, db_path: Path | str = DB_PATH) -> int:
    rows = fetch_all(
        """
        SELECT log_date
        FROM habit_logs
        WHERE habit_id = ? AND completed = 1
        ORDER BY log_date DESC
        LIMIT 366
        """,
        (habit_id,),
        db_path,
    )
    completed_dates = {row["log_date"] for row in rows}
    cursor = date.today()
    if cursor.isoformat() not in completed_dates:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor.isoformat() in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
