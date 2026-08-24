"""今日和近 7/30 天统计。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from database import DB_PATH, fetch_all, fetch_one


def date_range(days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=max(1, days) - 1)
    return start.isoformat(), end.isoformat()


def task_summary(days: int = 1, db_path: Path | str = DB_PATH) -> dict[str, Any]:
    start, end = date_range(days)
    row = fetch_one(
        """
        SELECT
            COUNT(id) AS total,
            SUM(CASE WHEN status = '已完成' THEN 1 ELSE 0 END) AS completed,
            COALESCE(SUM(estimated_minutes), 0) AS planned_minutes,
            COALESCE(SUM(actual_minutes), 0) AS actual_minutes
        FROM tasks
        WHERE planned_date BETWEEN ? AND ?
          AND status != '已放弃'
        """,
        (start, end),
        db_path,
    ) or {"total": 0, "completed": 0, "planned_minutes": 0, "actual_minutes": 0}
    total = int(row["total"] or 0)
    completed = int(row["completed"] or 0)
    row["completion_rate"] = round(completed / total * 100) if total else 0
    return row


def category_stats(days: int = 7, db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    start, end = date_range(days)
    return fetch_all(
        """
        SELECT
            category,
            COALESCE(SUM(CASE
                WHEN actual_minutes > 0 THEN actual_minutes
                WHEN status = '已完成' THEN estimated_minutes
                ELSE 0
            END), 0) AS minutes
        FROM tasks
        WHERE planned_date BETWEEN ? AND ?
          AND status != '已放弃'
        GROUP BY category
        HAVING minutes > 0
        ORDER BY minutes DESC
        LIMIT 100
        """,
        (start, end),
        db_path,
    )


def category_minutes(category: str, days: int = 1, db_path: Path | str = DB_PATH) -> int:
    start, end = date_range(days)
    row = fetch_one(
        """
        SELECT COALESCE(SUM(CASE
            WHEN actual_minutes > 0 THEN actual_minutes
            WHEN status = '已完成' THEN estimated_minutes
            ELSE 0
        END), 0) AS minutes
        FROM tasks
        WHERE category = ? AND planned_date BETWEEN ? AND ? AND status != '已放弃'
        """,
        (category, start, end),
        db_path,
    )
    return int(row["minutes"] if row else 0)


def learning_streak(db_path: Path | str = DB_PATH) -> int:
    rows = fetch_all(
        """
        SELECT planned_date
        FROM tasks
        WHERE status = '已完成'
          AND category IN (
              'AI技术', '项目实战', 'Git/GitHub', 'Debug', '部署',
              '数据库', 'RAG', 'Agent', '商业', '金融', '阅读', '表达', '英语'
          )
        GROUP BY planned_date
        ORDER BY planned_date DESC
        LIMIT 366
        """,
        (),
        db_path,
    )
    completed_dates = {row["planned_date"] for row in rows}
    cursor = date.today()
    if cursor.isoformat() not in completed_dates:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor.isoformat() in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak

