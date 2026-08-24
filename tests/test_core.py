"""Personal Growth OS 的核心业务与持久化测试。"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from database import execute, fetch_one, init_database
from services.books import add_reading_log
from services.habits import calculate_streak, save_habit_log
from services.planner import assess_capacity, build_today_advice
from services.reminder import collect_reminders, is_night_closing
from services.stats import task_summary
from services.tasks import (
    complete_task,
    create_daily_task,
    create_task,
    get_task,
    list_tasks,
    materialize_daily_tasks,
    postpone_task,
    update_task,
)


def make_database(tmp_path: Path) -> Path:
    db_path = tmp_path / "growth-test.db"
    init_database(db_path)
    return db_path


def test_database_seeds_required_defaults(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM habits").fetchone()[0] == 6
        assert connection.execute(
            "SELECT target_minutes FROM habits WHERE name = '睡眠 8 小时'"
        ).fetchone()[0] == 480
        assert connection.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 17
        assert connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 8
        assert connection.execute(
            "SELECT COUNT(*) FROM recurring_task_templates"
        ).fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM directions").fetchone()[0] == 1


def test_daily_tasks_materialize_once_and_sleep_does_not_use_capacity(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    today = date.today().isoformat()
    materialize_daily_tasks(today, db_path)
    materialize_daily_tasks(today, db_path)
    sleep_task = fetch_one(
        """
        SELECT recurring_template_id, estimated_minutes, counts_toward_capacity
        FROM tasks
        WHERE title = ? AND planned_date = ?
        LIMIT 1
        """,
        ("保持 8 小时睡眠", today),
        db_path,
    )
    assert sleep_task["recurring_template_id"]
    assert sleep_task["estimated_minutes"] == 480
    assert sleep_task["counts_toward_capacity"] == 0
    assert len(list_tasks(today, db_path=db_path)) == 9


def test_user_can_create_a_daily_task(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    create_daily_task(
        {
            "title": "每日背单词",
            "category": "英语",
            "time_slot": "晚上",
            "estimated_minutes": 20,
            "acceptance_criteria": "复习并掌握 20 个单词",
        },
        db_path,
    )
    today_tasks = list_tasks(date.today().isoformat(), db_path=db_path)
    matching = [task for task in today_tasks if task["title"] == "每日背单词"]
    assert len(matching) == 1
    assert matching[0]["recurring_template_id"]


def test_manual_today_task_is_included_in_total_and_persists(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    today = date.today().isoformat()
    task_id = create_task(
        {
            "title": "去理发",
            "category": "个人事务",
            "planned_date": today,
            "estimated_minutes": 30,
            "acceptance_criteria": "完成理发并回家",
            "source": "user",
        },
        db_path,
    )
    tasks = list_tasks(today, db_path=db_path)
    assert any(task["id"] == task_id and task["source"] == "user" for task in tasks)
    assert task_summary(1, db_path)["total"] == 9
    assert get_task(task_id, db_path)["title"] == "去理发"


def test_task_update_complete_and_postpone(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    task_id = create_task(
        {
            "title": "Docker 练习",
            "category": "部署",
            "planned_date": date.today().isoformat(),
            "acceptance_criteria": "独立启动容器",
        },
        db_path,
    )
    update_task(task_id, {"title": "Dockerfile 练习", "completion_percentage": 40}, db_path)
    assert get_task(task_id, db_path)["completion_percentage"] == 40
    for _ in range(3):
        postpone_task(task_id, db_path=db_path)
    assert get_task(task_id, db_path)["postponement_count"] == 3
    complete_task(task_id, 55, db_path)
    task = get_task(task_id, db_path)
    assert task["status"] == "已完成"
    assert task["actual_minutes"] == 55
    assert task["completed_at"]


def test_capacity_detects_overload() -> None:
    tasks = [
        {"status": "待开始", "estimated_minutes": 360, "category": "AI技术", "must_today": 1, "priority": "主任务", "title": "深度任务"},
        {"status": "待开始", "estimated_minutes": 300, "category": "生活", "must_today": 0, "priority": "普通", "title": "生活任务"},
    ]
    result = assess_capacity(tasks)
    assert result["overloaded"] is True
    assert result["total_minutes"] == 660


def test_habit_streak_and_reading_progress(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    habit = fetch_one("SELECT id FROM habits WHERE name = ? LIMIT 1", ("阅读",), db_path)
    for offset in range(3):
        log_date = (date.today() - timedelta(days=offset)).isoformat()
        save_habit_log(habit["id"], log_date, True, 30, db_path=db_path)
    assert calculate_streak(habit["id"], db_path) == 3

    book = fetch_one("SELECT id FROM books WHERE title = ? LIMIT 1", ("原子习惯",), db_path)
    execute(
        "UPDATE books SET total_pages = 300, status = '当前阅读' WHERE id = ?",
        (book["id"],),
        db_path,
    )
    add_reading_log(book["id"], 30, 20, "复利", "", "", "建立触发器", db_path)
    updated = fetch_one(
        "SELECT current_page, total_minutes FROM books WHERE id = ? LIMIT 1",
        (book["id"],),
        db_path,
    )
    assert updated == {"current_page": 20, "total_minutes": 30}


def test_rule_advice_and_reminders(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    advice = build_today_advice(db_path)
    assert advice
    assert all(item["reason"] for item in advice)

    current = datetime.combine(date.today(), datetime.min.time()).replace(hour=8, minute=55)
    reminders = collect_reminders(current, db_path)
    assert any("5 分钟后开始" in item["message"] for item in reminders)

    night = datetime.combine(date.today(), datetime.min.time()).replace(hour=23, minute=1)
    assert is_night_closing(night, db_path) is True
    assert any(item["level"] == "error" for item in collect_reminders(night, db_path))
