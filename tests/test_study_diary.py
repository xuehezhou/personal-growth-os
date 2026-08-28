"""Study Diary 核心体验与按日期持久化测试。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from database import fetch_one, init_database
from services.directions import save_direction
from services.journal import (
    create_quick_note,
    delete_quick_note,
    get_goal_snapshot,
    get_journal,
    list_journal_entries,
    list_quick_notes,
    save_journal,
    update_quick_note,
)
from services.tasks import complete_task, create_task, list_tasks


def make_database(tmp_path: Path) -> Path:
    db_path = tmp_path / "study-diary.db"
    init_database(db_path)
    return db_path


def test_full_day_persists_and_two_dates_never_overwrite(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    save_journal(
        "2026-08-28",
        {
            "mood": "🙂 不错",
            "focus": "跑通 Study Diary",
            "day_story": "今天第一次正式使用 Study Diary。",
            "learning_notes": "理解了按日期持久化。",
            "life_notes": "下午散步。",
            "growth_thoughts": "舒服比复杂更重要。",
            "review_gain": "完成了一整天记录。",
            "exercise_minutes": 30,
        },
        db_path,
    )
    save_journal(
        "2026-08-29",
        {"day_story": "今天学习 Agent。", "focus": "完成第二天记录"},
        db_path,
    )

    first = get_journal("2026-08-28", db_path)
    second = get_journal("2026-08-29", db_path)
    assert first["day_story"] == "今天第一次正式使用 Study Diary。"
    assert first["learning_notes"] == "理解了按日期持久化。"
    assert first["exercise_minutes"] == 30
    assert second["day_story"] == "今天学习 Agent。"
    assert len(list_journal_entries("2026-08", db_path)) == 2


def test_direction_snapshot_is_frozen_for_old_diary(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    save_direction(
        {
            "long_term_vision": "成为长期主义者",
            "current_stage": "建立记录习惯",
            "current_goal": "连续记录七天",
            "primary_conflict": "记录不稳定",
            "secondary_conflicts": "",
            "current_priority": "先完成今天",
            "not_doing": "不做复杂系统",
        },
        db_path,
    )
    save_journal("2026-08-28", {"day_story": "第一天"}, db_path)
    save_direction(
        {
            "long_term_vision": "新的长期方向",
            "current_stage": "新的阶段",
            "current_goal": "新的目标",
            "primary_conflict": "新的问题",
            "secondary_conflicts": "",
            "current_priority": "",
            "not_doing": "",
        },
        db_path,
    )
    save_journal("2026-08-28", {"day_story": "编辑第一天"}, db_path)

    snapshot = get_goal_snapshot("2026-08-28", db_path)
    assert snapshot["current_goal"] == "连续记录七天"
    assert snapshot["primary_conflict"] == "记录不稳定"


def test_quick_note_edit_delete_and_persist(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    note_id = create_quick_note(
        "想研究AI企业服务商业模式。", "2026-08-28", db_path
    )
    assert list_quick_notes("2026-08-28", db_path)[0]["content"].startswith("想研究")
    update_quick_note(note_id, "想研究 AI 企业服务。", db_path)
    assert list_quick_notes("2026-08-28", db_path)[0]["content"] == "想研究 AI 企业服务。"
    delete_quick_note(note_id, db_path)
    assert list_quick_notes("2026-08-28", db_path) == []


def test_today_task_appears_and_completion_changes_state(tmp_path: Path) -> None:
    db_path = make_database(tmp_path)
    task_id = create_task(
        {
            "title": "下午修项目 Bug",
            "planned_date": "2026-08-28",
            "time_slot": "下午",
            "category": "个人事务",
            "acceptance_criteria": "任务已完成",
        },
        db_path,
    )
    assert [item["title"] for item in list_tasks("2026-08-28", db_path=db_path)] == [
        "下午修项目 Bug"
    ]
    complete_task(task_id, db_path=db_path)
    task = fetch_one("SELECT status FROM tasks WHERE id = ?", (task_id,), db_path)
    assert task["status"] == "已完成"
