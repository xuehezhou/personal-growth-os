"""一天一页日记、方向快照与灵感箱。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from database import DB_PATH, execute, fetch_all, fetch_one, get_connection


JOURNAL_FIELDS = (
    "mood", "focus", "secondary_focus_1", "secondary_focus_2",
    "day_story", "learning_notes", "technical_gain", "life_notes",
    "growth_thoughts", "reading_note", "exercise_minutes", "exercise_content",
    "review_best", "review_problem", "review_gain", "improvement_learning",
    "improvement_life", "improvement_self", "tomorrow_focus", "self_message",
)


def _date_text(value: date | str) -> str:
    text = value.isoformat() if isinstance(value, date) else str(value)
    date.fromisoformat(text)
    return text


def empty_journal(journal_date: date | str) -> dict[str, Any]:
    result: dict[str, Any] = {field: "" for field in JOURNAL_FIELDS}
    result["exercise_minutes"] = 0
    result["journal_date"] = _date_text(journal_date)
    result["created_at"] = ""
    result["updated_at"] = ""
    return result


def get_journal(
    journal_date: date | str,
    db_path: Path | str = DB_PATH,
) -> dict[str, Any]:
    day = _date_text(journal_date)
    row = fetch_one(
        f"""
        SELECT journal_date, {', '.join(JOURNAL_FIELDS)}, created_at, updated_at
        FROM daily_journals
        WHERE journal_date = ?
        LIMIT 1
        """,
        (day,),
        db_path,
    )
    return row or empty_journal(day)


def save_journal(
    journal_date: date | str,
    values: dict[str, Any],
    db_path: Path | str = DB_PATH,
) -> str:
    """保存日记并在首次保存当天时冻结方向快照。"""
    day = _date_text(journal_date)
    merged = {**get_journal(day, db_path), **values}
    merged["exercise_minutes"] = max(
        0, int(merged.get("exercise_minutes", 0) or 0)
    )
    for field in JOURNAL_FIELDS:
        if field != "exercise_minutes":
            merged[field] = str(merged.get(field, "") or "").strip()
    now = datetime.now().isoformat(timespec="seconds")
    columns = ", ".join(JOURNAL_FIELDS)
    placeholders = ", ".join("?" for _ in JOURNAL_FIELDS)
    updates = ", ".join(
        f"{field} = excluded.{field}" for field in JOURNAL_FIELDS
    )
    with get_connection(db_path) as connection:
        connection.execute(
            f"""
            INSERT INTO daily_journals (
                journal_date, {columns}, created_at, updated_at
            ) VALUES (?, {placeholders}, ?, ?)
            ON CONFLICT(journal_date) DO UPDATE SET
                {updates}, updated_at = excluded.updated_at
            """,
            (
                day,
                *(merged[field] for field in JOURNAL_FIELDS),
                merged.get("created_at") or now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO goal_snapshots (
                snapshot_date, long_term_vision, current_stage, current_goal,
                primary_conflict, secondary_conflicts, current_priority,
                not_doing, created_at
            )
            SELECT ?, long_term_vision, current_stage, current_goal,
                   primary_conflict, secondary_conflicts, current_priority,
                   not_doing, ?
            FROM directions
            WHERE id = 1
            """,
            (day, now),
        )
    return now


def list_journal_entries(
    month_prefix: str,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            j.journal_date, j.mood, j.focus, j.day_story, j.updated_at,
            COUNT(t.id) AS task_total,
            SUM(CASE WHEN t.status = '已完成' THEN 1 ELSE 0 END) AS task_completed
        FROM daily_journals j
        LEFT JOIN tasks t ON t.planned_date = j.journal_date
        WHERE j.journal_date LIKE ?
        GROUP BY j.journal_date
        ORDER BY j.journal_date DESC
        LIMIT 62
        """,
        (f"{month_prefix}%",),
        db_path,
    )


def get_goal_snapshot(
    snapshot_date: date | str,
    db_path: Path | str = DB_PATH,
) -> dict[str, Any] | None:
    return fetch_one(
        "SELECT * FROM goal_snapshots WHERE snapshot_date = ? LIMIT 1",
        (_date_text(snapshot_date),),
        db_path,
    )


def create_quick_note(
    content: str,
    note_date: date | str | None = None,
    db_path: Path | str = DB_PATH,
) -> int:
    clean = content.strip()
    if not clean:
        raise ValueError("灵感内容不能为空")
    day = _date_text(note_date or date.today())
    now = datetime.now().isoformat(timespec="seconds")
    return execute(
        """
        INSERT INTO quick_notes (note_date, content, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (day, clean, now, now),
        db_path,
    )


def list_quick_notes(
    note_date: date | str,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, note_date, content, created_at, updated_at
        FROM quick_notes
        WHERE note_date = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 200
        """,
        (_date_text(note_date),),
        db_path,
    )


def update_quick_note(
    note_id: int,
    content: str,
    db_path: Path | str = DB_PATH,
) -> None:
    clean = content.strip()
    if not clean:
        raise ValueError("灵感内容不能为空")
    execute(
        "UPDATE quick_notes SET content = ?, updated_at = ? WHERE id = ?",
        (clean, datetime.now().isoformat(timespec="seconds"), note_id),
        db_path,
    )


def delete_quick_note(note_id: int, db_path: Path | str = DB_PATH) -> None:
    execute("DELETE FROM quick_notes WHERE id = ?", (note_id,), db_path)


def get_day_details(
    journal_date: date | str,
    db_path: Path | str = DB_PATH,
) -> dict[str, Any]:
    day = _date_text(journal_date)
    return {
        "journal": get_journal(day, db_path),
        "snapshot": get_goal_snapshot(day, db_path),
        "tasks": fetch_all(
            """
            SELECT id, title, start_time, end_time, time_slot, status, notes
            FROM tasks WHERE planned_date = ?
            ORDER BY COALESCE(start_time, '23:59'), id
            """,
            (day,), db_path,
        ),
        "notes": list_quick_notes(day, db_path),
        "reading": fetch_all(
            """
            SELECT b.title, r.minutes, r.pages_read, r.learned
            FROM reading_logs r JOIN books b ON b.id = r.book_id
            WHERE r.log_date = ? ORDER BY r.created_at
            """,
            (day,), db_path,
        ),
        "habits": fetch_all(
            """
            SELECT h.name, hl.completed, hl.minutes, hl.notes
            FROM habit_logs hl JOIN habits h ON h.id = hl.habit_id
            WHERE hl.log_date = ? ORDER BY h.id
            """,
            (day,), db_path,
        ),
    }


def recent_seven_day_stats(
    end_date: date | str | None = None,
    db_path: Path | str = DB_PATH,
) -> dict[str, int]:
    end = date.fromisoformat(_date_text(end_date or date.today()))
    start = (end - timedelta(days=6)).isoformat()
    end_text = end.isoformat()
    journal_days = fetch_one(
        "SELECT COUNT(*) AS value FROM daily_journals WHERE journal_date BETWEEN ? AND ?",
        (start, end_text), db_path,
    )["value"]
    reading_minutes = fetch_one(
        "SELECT COALESCE(SUM(minutes), 0) AS value FROM reading_logs WHERE log_date BETWEEN ? AND ?",
        (start, end_text), db_path,
    )["value"]
    task_counts = fetch_one(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status = '已完成' THEN 1 ELSE 0 END) AS completed
        FROM tasks WHERE planned_date BETWEEN ? AND ?
        """,
        (start, end_text), db_path,
    )
    exercise_days = fetch_one(
        """
        SELECT COUNT(*) AS value FROM daily_journals
        WHERE journal_date BETWEEN ? AND ? AND exercise_minutes > 0
        """,
        (start, end_text), db_path,
    )["value"]
    total = int(task_counts["total"] or 0)
    completed = int(task_counts["completed"] or 0)
    return {
        "journal_days": int(journal_days),
        "reading_minutes": int(reading_minutes),
        "exercise_days": int(exercise_days),
        "task_completion_rate": round(completed / total * 100) if total else 0,
    }
