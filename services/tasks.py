"""任务业务：查询、创建、更新、完成、延期与放弃。"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from database import DB_PATH, execute, fetch_all, fetch_one, get_connection


TASK_COLUMNS = """
    id, title, description, category, priority, planned_date, start_time,
    end_time, time_slot, estimated_minutes, actual_minutes,
    acceptance_criteria, status, completion_percentage, notes, source,
    goal_id, must_today, postponement_count, recurring_template_id,
    counts_toward_capacity, created_at, completed_at
"""


def _validated_time(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    text = str(value).strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError as error:
        raise ValueError("时间必须使用 HH:MM 格式，例如 09:30") from error
    return text


def _validated_criteria(value: Any) -> str:
    criteria = str(value or "").strip()
    if not criteria:
        raise ValueError("请填写验收标准：做到什么才算真正完成？")
    return criteria


def list_tasks(
    planned_date: str | None = None,
    status: str | None = None,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if planned_date:
        conditions.append("planned_date = ?")
        params.append(planned_date)
    if status:
        conditions.append("status = ?")
        params.append(status)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return fetch_all(
        f"""
        SELECT {TASK_COLUMNS}
        FROM tasks
        {where_clause}
        ORDER BY
            CASE priority
                WHEN '主任务' THEN 1
                WHEN '重要' THEN 2
                WHEN '普通' THEN 3
                ELSE 4
            END,
            COALESCE(start_time, '23:59'),
            id
        LIMIT 500
        """,
        params,
        db_path,
    )


def get_task(task_id: int, db_path: Path | str = DB_PATH) -> dict[str, Any] | None:
    return fetch_one(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = ? LIMIT 1",
        (task_id,),
        db_path,
    )


def create_task(data: dict[str, Any], db_path: Path | str = DB_PATH) -> int:
    title = str(data.get("title", "")).strip()
    if not title:
        raise ValueError("任务名称不能为空")
    criteria = _validated_criteria(data.get("acceptance_criteria"))
    start_time = _validated_time(data.get("start_time"))
    end_time = _validated_time(data.get("end_time"))
    if start_time and end_time and end_time <= start_time:
        raise ValueError("结束时间必须晚于开始时间")
    estimated_minutes = max(0, int(data.get("estimated_minutes", 30)))
    now = datetime.now().isoformat(timespec="seconds")
    return execute(
        """
        INSERT INTO tasks (
            title, description, category, priority, planned_date, start_time,
            end_time, time_slot, estimated_minutes, actual_minutes,
            acceptance_criteria, status, completion_percentage, notes, source,
            goal_id, must_today, postponement_count, recurring_template_id,
            counts_toward_capacity, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """,
        (
            title,
            str(data.get("description", "")).strip(),
            data.get("category", "个人事务"),
            data.get("priority", "普通"),
            data.get("planned_date", date.today().isoformat()),
            start_time,
            end_time,
            data.get("time_slot", "全天"),
            estimated_minutes,
            max(0, int(data.get("actual_minutes", 0))),
            criteria,
            data.get("status", "待开始"),
            int(data.get("completion_percentage", 0)),
            str(data.get("notes", "")).strip(),
            data.get("source", "user"),
            data.get("goal_id"),
            1 if data.get("must_today") else 0,
            data.get("recurring_template_id"),
            1 if data.get("counts_toward_capacity", True) else 0,
            now,
        ),
        db_path,
    )


def update_task(task_id: int, data: dict[str, Any], db_path: Path | str = DB_PATH) -> None:
    current = get_task(task_id, db_path)
    if not current:
        raise ValueError("任务不存在")
    merged = {**current, **data}
    title = str(merged.get("title", "")).strip()
    if not title:
        raise ValueError("任务名称不能为空")
    criteria = _validated_criteria(merged.get("acceptance_criteria"))
    start_time = _validated_time(merged.get("start_time"))
    end_time = _validated_time(merged.get("end_time"))
    if start_time and end_time and end_time <= start_time:
        raise ValueError("结束时间必须晚于开始时间")
    completion = max(0, min(100, int(merged.get("completion_percentage", 0))))
    completed_at = current.get("completed_at")
    if merged["status"] == "已完成":
        completion = 100
        completed_at = completed_at or datetime.now().isoformat(timespec="seconds")
    elif current["status"] == "已完成":
        completed_at = None
    execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, category = ?, priority = ?,
            planned_date = ?, start_time = ?, end_time = ?, time_slot = ?,
            estimated_minutes = ?, actual_minutes = ?, acceptance_criteria = ?,
            status = ?, completion_percentage = ?, notes = ?, goal_id = ?,
            must_today = ?, counts_toward_capacity = ?, completed_at = ?
        WHERE id = ?
        """,
        (
            title,
            str(merged.get("description", "")).strip(),
            merged["category"],
            merged["priority"],
            merged["planned_date"],
            start_time,
            end_time,
            merged["time_slot"],
            max(0, int(merged["estimated_minutes"])),
            max(0, int(merged["actual_minutes"])),
            criteria,
            merged["status"],
            completion,
            str(merged.get("notes", "")).strip(),
            merged.get("goal_id"),
            1 if merged.get("must_today") else 0,
            1 if merged.get("counts_toward_capacity", True) else 0,
            completed_at,
            task_id,
        ),
        db_path,
    )


def complete_task(
    task_id: int,
    actual_minutes: int | None = None,
    db_path: Path | str = DB_PATH,
) -> None:
    task = get_task(task_id, db_path)
    if not task:
        raise ValueError("任务不存在")
    _validated_criteria(task.get("acceptance_criteria"))
    minutes = task["estimated_minutes"] if actual_minutes is None else actual_minutes
    execute(
        """
        UPDATE tasks
        SET status = '已完成', completion_percentage = 100,
            actual_minutes = ?, completed_at = ?
        WHERE id = ?
        """,
        (max(0, int(minutes)), datetime.now().isoformat(timespec="seconds"), task_id),
        db_path,
    )


def postpone_task(
    task_id: int,
    target_date: str | None = None,
    db_path: Path | str = DB_PATH,
) -> int:
    task = get_task(task_id, db_path)
    if not task:
        raise ValueError("任务不存在")
    next_date = target_date or (date.today() + timedelta(days=1)).isoformat()
    new_count = int(task["postponement_count"]) + 1
    execute(
        """
        UPDATE tasks
        SET planned_date = ?, status = '待开始', postponement_count = ?,
            completion_percentage = 0, completed_at = NULL,
            recurring_template_id = NULL
        WHERE id = ?
        """,
        (next_date, new_count, task_id),
        db_path,
    )
    return new_count


def abandon_task(task_id: int, db_path: Path | str = DB_PATH) -> None:
    execute(
        """
        UPDATE tasks
        SET status = '已放弃', completed_at = ?, completion_percentage = 0
        WHERE id = ?
        """,
        (datetime.now().isoformat(timespec="seconds"), task_id),
        db_path,
    )


def delete_task(task_id: int, db_path: Path | str = DB_PATH) -> None:
    task = get_task(task_id, db_path)
    if task and task.get("recurring_template_id"):
        abandon_task(task_id, db_path)
        return
    execute("DELETE FROM tasks WHERE id = ?", (task_id,), db_path)


def list_recurring_tasks(
    active_only: bool = True,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    where_clause = "WHERE active = 1" if active_only else ""
    return fetch_all(
        f"""
        SELECT
            id, title, description, category, priority, start_time, end_time,
            time_slot, estimated_minutes, acceptance_criteria, notes, goal_id,
            must_today, counts_toward_capacity, active, created_at
        FROM recurring_task_templates
        {where_clause}
        ORDER BY
            CASE priority WHEN '主任务' THEN 1 WHEN '重要' THEN 2 ELSE 3 END,
            COALESCE(start_time, '23:59'),
            id
        LIMIT 100
        """,
        (),
        db_path,
    )


def create_daily_task(data: dict[str, Any], db_path: Path | str = DB_PATH) -> int:
    """创建每日任务模板，并立即生成今天的任务实例。"""
    title = str(data.get("title", "")).strip()
    if not title:
        raise ValueError("任务名称不能为空")
    criteria = _validated_criteria(data.get("acceptance_criteria"))
    start_time = _validated_time(data.get("start_time"))
    end_time = _validated_time(data.get("end_time"))
    if start_time and end_time and end_time <= start_time:
        raise ValueError("结束时间必须晚于开始时间")
    now = datetime.now().isoformat(timespec="seconds")
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO recurring_task_templates (
                    title, description, category, priority, start_time, end_time,
                    time_slot, estimated_minutes, acceptance_criteria, notes,
                    goal_id, must_today, counts_toward_capacity, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    title,
                    str(data.get("description", "")).strip(),
                    data.get("category", "个人事务"),
                    data.get("priority", "普通"),
                    start_time,
                    end_time,
                    data.get("time_slot", "全天"),
                    max(0, int(data.get("estimated_minutes", 30))),
                    criteria,
                    str(data.get("notes", "")).strip(),
                    data.get("goal_id"),
                    1 if data.get("must_today", True) else 0,
                    1 if data.get("counts_toward_capacity", True) else 0,
                    now,
                ),
            )
            template_id = int(cursor.lastrowid)
            _materialize_with_connection(connection, date.today().isoformat(), now)
            return template_id
    except sqlite3.IntegrityError as error:
        raise ValueError("已经存在同名的每日任务") from error


def _materialize_with_connection(
    connection: sqlite3.Connection,
    planned_date: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO tasks (
            title, description, category, priority, planned_date, start_time,
            end_time, time_slot, estimated_minutes, actual_minutes,
            acceptance_criteria, status, completion_percentage, notes, source,
            goal_id, must_today, postponement_count, recurring_template_id,
            counts_toward_capacity, created_at
        )
        SELECT
            title, description, category, priority, ?, start_time,
            end_time, time_slot, estimated_minutes, 0,
            acceptance_criteria, '待开始', 0, notes, 'user',
            goal_id, must_today, 0, id, counts_toward_capacity, ?
        FROM recurring_task_templates
        WHERE active = 1
        """,
        (planned_date, created_at),
    )


def materialize_daily_tasks(
    planned_date: str | None = None,
    db_path: Path | str = DB_PATH,
) -> None:
    target_date = planned_date or date.today().isoformat()
    with get_connection(db_path) as connection:
        _materialize_with_connection(
            connection,
            target_date,
            datetime.now().isoformat(timespec="seconds"),
        )


def stop_recurring_task(template_id: int, db_path: Path | str = DB_PATH) -> None:
    """停止未来生成，保留历史任务和统计。"""
    execute(
        "UPDATE recurring_task_templates SET active = 0 WHERE id = ?",
        (template_id,),
        db_path,
    )
